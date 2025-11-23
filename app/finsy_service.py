"""
Finsy Finance Automation Service - Main Flask Application
Production-ready service with IBM integrations, security, and error handling.
"""
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError
import os
import joblib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Import configuration and utilities
from app.config import Config
from app.logger import get_logger, setup_logging
from app.schemas import (
    InvoiceParseRequest, InvoiceParseResponse,
    RiskScoreRequest, RiskScoreResponse,
    ApprovalCreateRequest, ApprovalActionRequest, ApprovalResponse,
    HealthResponse, ErrorResponse
)
from app.utils import (
    init_db, save_invoice_record, get_invoice, list_invoices,
    save_approval, get_approval, update_approval, get_pending_approvals,
    summary_report
)
from app.analytics import (
    log_invoice_parsed, log_risk_scored, log_approval_created, log_approval_action
)
from app.auth import require_auth, require_approver, require_admin
from app.cloudant_client import cloudant_client
from app.nlu_service import nlu_service
from app.watsonx_client import watsonx_client
from app.speech_service import speech_service
from app.orchestrate.flow_runner import flow_runner
from app.orchestrate.skills import orchestrate_skills

# Initialize logging
logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='../static', static_url_path='/static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Configure CORS
if Config.CORS_ORIGINS == ["*"]:
    CORS(app)
else:
    CORS(app, origins=Config.CORS_ORIGINS)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{Config.RATE_LIMIT_PER_MINUTE} per minute"]
)

# Global risk model
risk_model = None
risk_scaler = None


def load_risk_model():
    """Load ML risk model"""
    global risk_model, risk_scaler
    try:
        model_path = Config.RISK_MODEL
        if os.path.exists(model_path):
            loaded = joblib.load(model_path)
            if isinstance(loaded, tuple):
                risk_model, risk_scaler = loaded
            else:
                risk_model = loaded
            logger.info(f"Loaded risk model from {model_path}")
        else:
            logger.warning(f"Risk model not found at {model_path}")
    except Exception as e:
        logger.error(f"Failed to load risk model: {str(e)}")


def rule_based_features(invoice: Dict[str, Any]) -> Dict[str, float]:
    """Extract features for risk scoring"""
    amount = float(invoice.get('amount', 0))
    has_po = 1 if invoice.get('po_number') or invoice.get('has_po') else 0
    vendor = invoice.get('vendor', '').lower()
    vendor_suspicious = 1 if 'suspicious' in vendor or 'unknown' in vendor else 0
    
    return {
        'amount': amount,
        'has_po': has_po,
        'vendor_suspicious': vendor_suspicious
    }


def compute_risk_with_model(inv: Dict[str, Any]) -> Optional[float]:
    """Compute risk score using ML model"""
    if not risk_model:
        return None
    
    try:
        feats = rule_based_features(inv)
        X = [[feats['amount'], feats['has_po'], feats['vendor_suspicious']]]
        
        if risk_scaler:
            import pandas as pd
            X_df = pd.DataFrame(X, columns=['amount', 'has_po', 'vendor_suspicious'])
            X_df['amount'] = risk_scaler.transform(X_df[['amount']])
            X = X_df.values
        
        score = float(risk_model.predict_proba(X)[0, 1])
        return score
    except Exception as e:
        logger.error(f"Model prediction failed: {str(e)}")
        return None


# Request logging middleware
@app.before_request
def log_request():
    """Log incoming requests"""
    logger.info(f"{request.method} {request.path} - IP: {get_remote_address()}")


@app.after_request
def log_response(response):
    """Log outgoing responses"""
    logger.info(f"{request.method} {request.path} - Status: {response.status_code}")
    return response


# Error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle Pydantic validation errors"""
    return jsonify({
        "error": "Validation error",
        "message": str(e),
        "details": e.errors() if hasattr(e, 'errors') else None
    }), 400


@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404


@app.errorhandler(500)
def handle_internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


@app.errorhandler(429)
def handle_rate_limit(e):
    """Handle rate limit errors"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(e.description)
    }), 429


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "unknown",
            "cloudant": "disabled",
            "nlu": "disabled",
            "watsonx": "disabled",
            "orchestrate": "disabled",
            "speech": "disabled"
        }
    }
    
    # Check SQLite/DB
    try:
        from app.utils import _get_connection
        with _get_connection() as conn:
            conn.execute("SELECT 1")
        status["services"]["database"] = "connected"
    except Exception as e:
        logger.warning(f"Database check failed: {str(e)}")
        status["services"]["database"] = "disconnected"
        status["status"] = "degraded"
        
    # Check Cloudant
    if Config.USE_CLOUDANT:
        status["services"]["cloudant"] = "connected" if cloudant_client.is_connected() else "disconnected"
        if status["services"]["cloudant"] == "disconnected":
            status["status"] = "degraded"
            
    # Check NLU
    if Config.ENABLE_NLU:
        status["services"]["nlu"] = "connected" if nlu_service.is_connected() else "disconnected"
        
    # Check watsonx
    if Config.ENABLE_WATSONX:
        status["services"]["watsonx"] = "connected" if watsonx_client.is_connected() else "disconnected"
        
    # Check Orchestrate
    if Config.ENABLE_ORCHESTRATE:
        status["services"]["orchestrate"] = "connected" if orchestrate_skills.is_connected() else "disconnected"
        
    # Check Speech
    if Config.ENABLE_SPEECH:
        stt = speech_service.is_stt_connected()
        tts = speech_service.is_tts_connected()
        status["services"]["speech"] = f"stt:{'ok' if stt else 'down'}, tts:{'ok' if tts else 'down'}"

    return jsonify(status), 200


# Root endpoint - serve the dashboard
@app.route("/", methods=["GET"])
def root():
    """Serve the dashboard frontend"""
    from flask import send_from_directory
    return send_from_directory('../static', 'index.html')


# Demo endpoint for quick verification
@app.route("/demo", methods=["GET"])
@limiter.limit("5 per minute")
def demo():
    """Simple demo endpoint to verify system works and execute a sample flow."""
    try:
        # Execute the default InvoiceProcessingFlow with empty input
        result = flow_runner.execute_flow("InvoiceProcessingFlow", {})
        return jsonify({"demo": "success", "flow_result": result}), 200
    except Exception as e:
        logger.error(f"Demo endpoint error: {str(e)}")
        return jsonify({"error": "demo_failed", "message": str(e)}), 500


# API info endpoint
@app.route("/api", methods=["GET"])
def api_info():
    """API information endpoint"""
    return jsonify({
        "service": "Finsy Finance Automation Agent",
        "version": "1.0",
        "status": "operational",
        "description": "AI-powered invoice processing and approval automation",
        "documentation": "/health for health check",
        "endpoints": {
            "health": {
                "method": "GET",
                "path": "/health",
                "description": "System health and service status"
            },
            "invoices": {
                "parse": "POST /invoices/parse",
                "list": "GET /invoices",
                "details": "GET /invoices/<id>",
                "parse_audio": "POST /invoices/parse/audio"
            },
            "risk": {
                "score": "POST /risk/score"
            },
            "approvals": {
                "create": "POST /approvals/create",
                "action": "POST /approvals/<id>/action",
                "status": "GET /approvals/<id>",
                "list": "GET /approvals",
                "pending": "GET /approvals/pending",
                "audio": "GET /approvals/<id>/audio"
            },
            "speech": {
                "transcribe": "POST /speech/transcribe",
                "synthesize": "POST /speech/synthesize"
            },
            "orchestrate": {
                "execute_flow": "POST /flows/execute",
                "flow_status": "GET /flows/<id>",
                "list_flows": "GET /orchestrate/flows"
            },
            "reports": {
                "summary": "GET /reports/summary"
            }
        },
        "services": {
            "nlu": "enabled" if Config.ENABLE_NLU else "disabled",
            "speech": "enabled" if Config.ENABLE_SPEECH else "disabled",
            "cloudant": "enabled" if Config.USE_CLOUDANT else "disabled",
            "orchestrate": "enabled" if Config.ENABLE_ORCHESTRATE else "disabled",
            "watsonx": "enabled" if Config.ENABLE_WATSONX else "disabled"
        },
        "note": "This is a protected API. Most endpoints require authentication."
    }), 200




# Invoice endpoints
@app.route("/invoices/parse", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def parse_invoice():
    """Parse invoice text and extract structured data"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
        
        # Validate request
        try:
            req_data = InvoiceParseRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "message": str(e)}), 400
        
        # Generate invoice ID
        invoice_id = str(uuid.uuid4())[:8]
        
        # Use NLU to extract entities if enabled
        extracted_entities = {}
        if Config.ENABLE_NLU and req_data.invoice_text:
            extracted_entities = nlu_service.extract_invoice_entities(req_data.invoice_text)
        
        # Build invoice record
        invoice = {
            'invoice_id': invoice_id,
            'vendor': req_data.vendor or extracted_entities.get('vendor', 'Unknown'),
            'date': req_data.date or datetime.now().isoformat(),
            'total': req_data.amount or 0.0,
            'currency': req_data.currency or 'USD',
            'po_number': req_data.po_number,
            'confidence': extracted_entities.get('confidence', 0.8),
            'text': req_data.invoice_text,
            'parsed': True
        }
        
        # Save to database
        try:
            save_invoice_record(Config.FINSY_DB, invoice)
            
            # Also save to Cloudant if enabled
            if Config.USE_CLOUDANT and cloudant_client.is_connected():
                cloudant_client.save_invoice(invoice)
        except Exception as e:
            logger.error(f"Failed to save invoice: {str(e)}")
            return jsonify({"error": "Database error", "message": "Failed to save invoice"}), 500
        
        logger.info(f"Invoice parsed: {invoice_id}")
        
        # Log analytics
        log_invoice_parsed(
            invoice_id, 
            invoice['vendor'], 
            invoice['total'], 
            invoice['confidence']
        )
        
        return jsonify(InvoiceParseResponse(
            invoice_id=invoice_id,
            vendor=invoice['vendor'],
            date=invoice['date'],
            total=invoice['total'],
            currency=invoice['currency'],
            po_number=invoice['po_number'],
            confidence=invoice['confidence'],
            parsed=True,
            text=invoice.get('text'),
            created_at=invoice['date']
        ).dict()), 200
        
    except Exception as e:
        logger.error(f"Invoice parsing failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to parse invoice"}), 500

# ----------------------------------------------------------------------
# Demo‑only endpoint – does NOT require JWT authentication
# ----------------------------------------------------------------------
@app.route("/demo/invoices/parse", methods=["POST"])
@limiter.limit("30 per minute")
def demo_parse_invoice():
    """Same logic as the protected /invoices/parse endpoint but usable
    without a JWT token. Intended for quick hackathon demos.
    """
    # ---- validation (identical to protected version) ----
    if not request.is_json:
        return jsonify({"error": "Invalid request",
                        "message": "Content-Type must be application/json"}), 400
    try:
        req_data = InvoiceParseRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation error",
                        "message": str(e)}), 400

    # ---- generate invoice ID & build record ----
    invoice_id = str(uuid.uuid4())[:8]
    invoice = {
        "invoice_id": invoice_id,
        "vendor": req_data.vendor,
        "date": req_data.date or datetime.utcnow().isoformat(),
        "total": req_data.amount,
        "currency": req_data.currency or "USD",
        "po_number": req_data.po_number,
        "confidence": 0.8,  # NLU not run in demo mode
        "parsed": True,
        "text": req_data.invoice_text,
    }

    # ---- persist the record ----
    try:
        save_invoice_record(Config.FINSY_DB, invoice)
    except Exception as exc:
        logger.error(f"Demo invoice save failed: {exc}")
        return jsonify({"error": "Database error",
                        "message": "Failed to save invoice"}), 500

    # ---- success response (mirrors protected endpoint) ----
    return jsonify(InvoiceParseResponse(
        invoice_id=invoice_id,
        vendor=invoice["vendor"],
        date=invoice["date"],
        total=invoice["total"],
        currency=invoice["currency"],
        po_number=invoice["po_number"],
        confidence=invoice["confidence"],
        parsed=True,
        text=invoice["text"],
        created_at=invoice["date"]
    ).dict()), 200



@app.route("/invoices", methods=["GET"])
@limiter.limit("60 per minute")
@require_auth
def list_invoices_endpoint():
    """List invoices"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        vendor = request.args.get('vendor')
        
        # Try Cloudant first
        invoices = []
        used_cloudant = False
        if Config.USE_CLOUDANT and cloudant_client.is_connected():
            # Note: Cloudant pagination is complex, simplified here
            invoices = cloudant_client.query_invoices(vendor=vendor, limit=limit)
            used_cloudant = True
            
        # Fallback to SQLite if Cloudant failed or returned empty (and we expected data? No, empty is valid)
        # Actually, if Cloudant is connected, we assume it's the source of truth. 
        # But for migration, we might want to merge? 
        # For now, if Cloudant is connected, use it. If not, use SQLite.
        if not used_cloudant:
            invoices = list_invoices(Config.FINSY_DB, limit=limit, offset=offset, vendor=vendor)
        
        return jsonify({"invoices": invoices, "count": len(invoices)}), 200
    except Exception as e:
        logger.error(f"Failed to list invoices: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to list invoices"}), 500


@app.route("/invoices/<invoice_id>", methods=["GET"])
@require_auth
def get_invoice_details(invoice_id: str):
    """Get invoice details"""
    try:
        # Try Cloudant first
        invoice = None
        if Config.USE_CLOUDANT and cloudant_client.is_connected():
            invoice = cloudant_client.get_invoice(invoice_id)
            
        # Fallback to SQLite
        if not invoice:
            invoice = get_invoice(Config.FINSY_DB, invoice_id)
            
        if not invoice:
            return jsonify({"error": "Not found", "message": "Invoice not found"}), 404
            
        return jsonify(invoice), 200
    except Exception as e:
        logger.error(f"Failed to get invoice: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to get invoice"}), 500


# Risk scoring endpoint
@app.route("/risk/score", methods=["POST"])
@limiter.limit("60 per minute")
@require_auth
def risk_score():
    """Score the risk of an invoice"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
        
        # Validate request
        try:
            req_data = RiskScoreRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "message": str(e)}), 400
        
        invoice_data = req_data.dict()
        
        # Rule-based scoring
        rule_score = 0.0
        reasons = []
        
        amount = invoice_data.get('amount', 0)
        if amount > Config.HIGH_AMOUNT_THRESHOLD:
            rule_score += 0.3
            reasons.append("High amount transaction")
        
        if not invoice_data.get('po_number') and not invoice_data.get('has_po'):
            rule_score += 0.2
            reasons.append("Missing PO number")
        
        vendor = invoice_data.get('vendor', '').lower()
        if 'suspicious' in vendor or 'unknown' in vendor:
            rule_score += 0.3
            reasons.append("Vendor flagged suspicious")
        
        # NLU-based analysis if enabled
        nlu_risk = None
        if Config.ENABLE_NLU and invoice_data.get('invoice_text'):
            nlu_analysis = nlu_service.extract_invoice_entities(invoice_data.get('invoice_text', ''))
            # Check for risky keywords
            risky_keywords = ['overdue', 'penalty', 'urgent', 'immediate', 'final notice']
            found_risky = [k for k in nlu_analysis.get('keywords', []) if k.lower() in risky_keywords]
            
            if found_risky:
                nlu_risk = 0.8
                reasons.append(f"Risky keywords found: {', '.join(found_risky)}")
            else:
                nlu_risk = 0.1
        
        # ML model scoring
        model_score = compute_risk_with_model(invoice_data)
        
        # watsonx.ai LLM analysis if enabled
        llm_analysis = None
        if Config.ENABLE_WATSONX and watsonx_client.is_connected():
            llm_analysis = watsonx_client.analyze_invoice_risk(invoice_data)
            if llm_analysis:
                llm_risk_level = llm_analysis.get('risk_level', 'medium')
                if llm_risk_level == 'high':
                    rule_score += 0.2
                elif llm_risk_level == 'medium':
                    rule_score += 0.1
                if llm_analysis.get('risk_factors'):
                    reasons.extend(llm_analysis['risk_factors'])
        
        # Combine scores
        final_score = rule_score
        if model_score is not None:
            final_score = Config.RULE_BASED_WEIGHT * rule_score + Config.MODEL_WEIGHT * model_score
        
        # Adjust with NLU if available
        if nlu_risk is not None:
            final_score = (final_score + nlu_risk) / 2
        
        final_score = min(1.0, max(0.0, final_score))
        
        # Determine risk level
        risk_level = "low"
        if final_score > Config.RISK_THRESHOLD_HIGH:
            risk_level = "high"
        elif final_score > Config.RISK_THRESHOLD_MEDIUM:
            risk_level = "medium"
        
        response = RiskScoreResponse(
            risk_score=round(final_score, 3),
            risk_level=risk_level,
            reasons=reasons,
            requires_approval=final_score > Config.RISK_THRESHOLD_APPROVAL,
            invoice_id=invoice_data.get('invoice_id'),
            model_score=model_score,
            rule_score=round(rule_score, 3)
        )
        
        logger.info(f"Risk scored for invoice {req_data.invoice_id}: {risk_level}")
        
        # Log analytics
        if req_data.invoice_id:
            log_risk_scored(req_data.invoice_id, risk_level, final_score)
        
        return jsonify(response.dict()), 200
        
    except Exception as e:
        logger.error(f"Risk scoring failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to score risk"}), 500


# Approval endpoints
@app.route("/approvals/create", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def create_approval():
    """Create a new approval request"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
        
        # Validate request
        try:
            req_data = ApprovalCreateRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "message": str(e)}), 400
        
        approval_id = str(uuid.uuid4())[:8]
        
        # Get watsonx.ai recommendation if enabled
        recommendation = None
        if Config.ENABLE_WATSONX and watsonx_client.is_connected():
            recommendation = watsonx_client.generate_approval_recommendation(req_data.dict())
        
        approval = {
            'approval_id': approval_id,
            'invoice_id': req_data.invoice_id,
            'amount': req_data.amount,
            'vendor': req_data.vendor,
            'reason': req_data.reason,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'requester': req_data.requester or g.user.get('user_id', 'system'),
            'approver': req_data.approver,
            'recommendation': recommendation
        }
        
        # Save to database
        try:
            save_approval(Config.FINSY_DB, approval)
            
            # Also save to Cloudant if enabled
            if Config.USE_CLOUDANT and cloudant_client.is_connected():
                cloudant_client.save_approval(approval)
        except Exception as e:
            logger.error(f"Failed to save approval: {str(e)}")
            return jsonify({"error": "Database error", "message": "Failed to create approval"}), 500
        
        logger.info(f"Approval created: {approval_id} for invoice {req_data.invoice_id}")
        
        # Log analytics
        log_approval_created(approval_id, req_data.invoice_id, approval['requester'])
        
        return jsonify(ApprovalResponse(**approval).dict()), 201
        
    except Exception as e:
        logger.error(f"Failed to create approval: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to create approval"}), 500


@app.route("/approvals/<approval_id>/action", methods=["POST"])
@limiter.limit("30 per minute")
@require_approver
def approval_action(approval_id: str):
    """Approve or reject an approval request"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
        
        # Validate request
        try:
            req_data = ApprovalActionRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "message": str(e)}), 400
        
        # Get approval
        approval = get_approval(Config.FINSY_DB, approval_id)
        
        # Try Cloudant if not found
        if not approval and Config.USE_CLOUDANT and cloudant_client.is_connected():
            approval = cloudant_client.get_approval(approval_id)
        
        if not approval:
            return jsonify({"error": "Not found", "message": f"Approval {approval_id} not found"}), 404
        
        # Update approval
        approver = req_data.approver or g.user.get('user_id', 'system')
        updated = update_approval(
            Config.FINSY_DB,
            approval_id,
            req_data.action,
            req_data.comment,
            approver
        )
        
        if not updated:
            return jsonify({"error": "Update failed", "message": "Failed to update approval"}), 500
        
        # Update in Cloudant if enabled
        # Update in Cloudant if enabled
        if Config.USE_CLOUDANT and cloudant_client.is_connected():
            cloudant_client.save_approval(updated)
        
        # Log audit trail
        logger.info(f"Approval {approval_id} {req_data.action}d by {approver}")
        
        # Log analytics
        log_approval_action(approval_id, req_data.action, approver)
        
        return jsonify(ApprovalResponse(**updated).dict()), 200
        
    except Exception as e:
        logger.error(f"Failed to process approval action: {str(e)}")
        print(f"DEBUG ERROR: {str(e)}", flush=True)
        return jsonify({"error": "Internal error", "message": "Failed to process approval"}), 500


@app.route("/approvals/<approval_id>", methods=["GET"])
@require_auth
def get_approval_status(approval_id: str):
    """Get approval status"""
    try:
        # Try Cloudant first
        approval = None
        if Config.USE_CLOUDANT and cloudant_client.is_connected():
            approval = cloudant_client.get_approval(approval_id)
            
        # Fallback to SQLite
        if not approval:
            approval = get_approval(Config.FINSY_DB, approval_id)
            
        if not approval:
            return jsonify({"error": "Not found", "message": "Approval not found"}), 404
            
        return jsonify(ApprovalResponse(**approval).dict()), 200
    except Exception as e:
        logger.error(f"Failed to get approval: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to get approval"}), 500


@app.route("/approvals", methods=["GET"])
@limiter.limit("60 per minute")
@require_auth
def list_approvals_endpoint():
    """List approvals with optional status filter"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        approvals = list_approvals(Config.FINSY_DB, status=status, limit=limit, offset=offset)
        
        return jsonify({
            "approvals": approvals,
            "limit": limit,
            "offset": offset,
            "count": len(approvals)
        }), 200
    except Exception as e:
        logger.error(f"Failed to list approvals: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to list approvals"}), 500


@app.route("/flows/execute", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def execute_flow_endpoint():
    """Execute an Orchestrate flow"""
    try:
        if not Config.ENABLE_ORCHESTRATE:
            return jsonify({"error": "Not enabled", "message": "Orchestrate integration is disabled"}), 404
            
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
            
        data = request.json
        flow_name = data.get("flow_name", "InvoiceProcessingFlow")
        input_data = data.get("input", {})
        
        result = flow_runner.execute_flow(flow_name, input_data)
        
        if result.get("status") == "failed":
            return jsonify(result), 500
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Failed to execute flow: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to execute flow"}), 500


@app.route("/flows/<flow_id>", methods=["GET"])
@require_auth
def get_flow_status_endpoint(flow_id: str):
    """Get flow execution status"""
    try:
        if not Config.ENABLE_ORCHESTRATE:
            return jsonify({"error": "Not enabled", "message": "Orchestrate integration is disabled"}), 404
            
        status = flow_runner.get_flow_status(flow_id)
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Failed to get flow status: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to get flow status"}), 500


@app.route("/speech/transcribe", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def transcribe_audio_endpoint():
    """Transcribe audio file to text"""
    try:
        if not Config.ENABLE_SPEECH:
            return jsonify({"error": "Not enabled", "message": "Speech services are disabled"}), 404
            
        if 'file' not in request.files:
            return jsonify({"error": "No file", "message": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file", "message": "No selected file"}), 400
            
        transcript = speech_service.transcribe_audio(file, file.content_type or "audio/wav")
        
        if transcript is None:
            return jsonify({"error": "Transcription failed", "message": "Could not transcribe audio"}), 500
            
        return jsonify({"transcript": transcript}), 200
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to transcribe audio"}), 500


@app.route("/speech/synthesize", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def synthesize_speech_endpoint():
    """Convert text to speech"""
    try:
        if not Config.ENABLE_SPEECH:
            return jsonify({"error": "Not enabled", "message": "Speech services are disabled"}), 404
            
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
            
        data = request.json
        text = data.get("text")
        
        if not text:
            return jsonify({"error": "Invalid request", "message": "Text is required"}), 400
            
        audio_content = speech_service.synthesize_speech(text)
        
        if audio_content is None:
            return jsonify({"error": "Synthesis failed", "message": "Could not synthesize speech"}), 500
            
        from flask import Response
        return Response(audio_content, mimetype="audio/wav")
        
    except Exception as e:
        logger.error(f"Synthesis failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to synthesize speech"}), 500
@app.route("/approvals/pending", methods=["GET"])
@limiter.limit("60 per minute")
@require_approver
def get_pending_approvals_endpoint():
    """Get pending approvals"""
    try:
        # Try Cloudant first
        approvals = []
        used_cloudant = False
        if Config.USE_CLOUDANT and cloudant_client.is_connected():
            approvals = cloudant_client.query_approvals(status='pending')
            used_cloudant = True
            
        # Fallback to SQLite
        if not used_cloudant:
            from app.utils import get_pending_approvals
            approvals = get_pending_approvals(Config.FINSY_DB)
        
        return jsonify({"pending_approvals": approvals, "count": len(approvals)}), 200
    except Exception as e:
        logger.error(f"Failed to get pending approvals: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to get pending approvals"}), 500


# Reporting endpoint
@app.route("/reports/summary", methods=["GET"])
@limiter.limit("30 per minute")
@require_auth
def summary_report_endpoint():
    """Get summary report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        report = summary_report(Config.FINSY_DB, start_date=start_date, end_date=end_date)
        
        return jsonify(report), 200
    except Exception as e:
        logger.error(f"Failed to generate summary report: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to generate report"}), 500


# Speech service endpoints
@app.route("/invoices/parse/audio", methods=["POST"])
@limiter.limit("20 per minute")
@require_auth
def parse_audio_invoice():
    """Parse invoice from audio file"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "Missing file", "message": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        content_type = request.form.get('content_type', 'audio/wav')
        
        if not Config.ENABLE_SPEECH or not speech_service.is_stt_connected():
            return jsonify({"error": "Service unavailable", "message": "Speech-to-Text not enabled"}), 503
        
        # Transcribe audio
        transcript = speech_service.transcribe_audio(audio_file, content_type)
        
        if not transcript:
            return jsonify({"error": "Transcription failed", "message": "Failed to transcribe audio"}), 500
        
        # Parse transcript as invoice
        # This would call the regular parse endpoint logic
        return jsonify({
            "transcript": transcript,
            "message": "Audio transcribed. Use /invoices/parse with the transcript."
        }), 200
        
    except Exception as e:
        logger.error(f"Audio parsing failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to parse audio"}), 500


@app.route("/approvals/<approval_id>/audio", methods=["GET"])
@limiter.limit("30 per minute")
@require_auth
def get_approval_audio(approval_id: str):
    """Get audio summary of approval"""
    try:
        approval = get_approval(Config.FINSY_DB, approval_id)
        
        if not approval:
            return jsonify({"error": "Not found", "message": f"Approval {approval_id} not found"}), 404
        
        if not Config.ENABLE_SPEECH or not speech_service.is_tts_connected():
            return jsonify({"error": "Service unavailable", "message": "Text-to-Speech not enabled"}), 503
        
        # Generate audio summary
        text = f"Approval request {approval_id} for invoice {approval.get('invoice_id')}. "
        text += f"Vendor: {approval.get('vendor')}. "
        text += f"Amount: ${approval.get('amount', 0):,.2f}. "
        text += f"Reason: {approval.get('reason')}. "
        text += f"Status: {approval.get('status')}."
        
        audio = speech_service.synthesize_speech(text)
        
        if not audio:
            return jsonify({"error": "Synthesis failed", "message": "Failed to generate audio"}), 500
        
        from flask import Response
        return Response(audio, mimetype='audio/wav'), 200
        
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to generate audio"}), 500


# Orchestrate endpoints
@app.route("/orchestrate/flows", methods=["GET"])
@limiter.limit("30 per minute")
@require_auth
def list_flows():
    """List available Orchestrate flows"""
    try:
        flows = list(flow_runner.flows.keys())
        return jsonify({"flows": flows}), 200
    except Exception as e:
        logger.error(f"Failed to list flows: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to list flows"}), 500


@app.route("/orchestrate/flows/<flow_name>/execute", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def execute_flow(flow_name: str):
    """Execute an Orchestrate flow"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request", "message": "Content-Type must be application/json"}), 400
        
        input_data = request.json
        result = flow_runner.execute_flow(flow_name, input_data)
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Flow execution failed: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to execute flow"}), 500


@app.route("/orchestrate/flows/<flow_id>/status", methods=["GET"])
@limiter.limit("30 per minute")
@require_auth
def get_flow_status(flow_id: str):
    """Get flow execution status"""
    try:
        status = flow_runner.get_flow_status(flow_id)
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Failed to get flow status: {str(e)}")
        return jsonify({"error": "Internal error", "message": "Failed to get flow status"}), 500


# Initialize services on startup
def initialize_services():
    """Initialize all services on startup"""
    logger.info("Initializing Finsy service...")
    
    # Initialize database
    try:
        init_db(Config.FINSY_DB)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Load risk model
    load_risk_model()
    
    # Initialize Cloudant
    if Config.USE_CLOUDANT:
        cloudant_client.connect()
    
    # Initialize NLU
    if Config.ENABLE_NLU:
        nlu_service.connect()
    
    # Initialize watsonx.ai
    if Config.ENABLE_WATSONX:
        watsonx_client.connect()
    
    # Initialize Speech services
    if Config.ENABLE_SPEECH:
        speech_service.connect()
    
    # Initialize Orchestrate
    if Config.ENABLE_ORCHESTRATE:
        flow_runner.flows  # Trigger flow loading
        orchestrate_skills.connect()
    
    logger.info("Finsy service initialized")


# Initialize services before first request
with app.app_context():
    # Validate configuration
    missing = Config.validate()
    if missing:
        logger.warning(f"Missing configuration: {', '.join(missing)}")
    
    # Initialize services
    initialize_services()


if __name__ == '__main__':
    # Run app
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
