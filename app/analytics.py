"""
Analytics module for logging events to Cloudant.
"""
import datetime
from typing import Dict, Any, Optional
from app.config import Config
from app.cloudant_client import cloudant_client
from app.logger import get_logger

logger = get_logger(__name__)

def log_analytics(event_type: str, data: Dict[str, Any]) -> None:
    """Log an analytics event"""
    try:
        if not Config.USE_CLOUDANT or not cloudant_client.is_connected():
            return

        event = {
            "event_type": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": data
        }
        
        cloudant_client.save_analytics(event)
        logger.debug(f"Logged analytics event: {event_type}")
        
    except Exception as e:
        logger.error(f"Failed to log analytics: {str(e)}")

def log_invoice_parsed(invoice_id: str, vendor: str, amount: float, confidence: float) -> None:
    """Log invoice parsed event"""
    log_analytics("invoice_parsed", {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "amount": amount,
        "confidence": confidence
    })

def log_risk_scored(invoice_id: str, risk_level: str, score: float) -> None:
    """Log risk scored event"""
    log_analytics("risk_scored", {
        "invoice_id": invoice_id,
        "risk_level": risk_level,
        "score": score
    })

def log_approval_created(approval_id: str, invoice_id: str, requester: str) -> None:
    """Log approval created event"""
    log_analytics("approval_created", {
        "approval_id": approval_id,
        "invoice_id": invoice_id,
        "requester": requester
    })

def log_approval_action(approval_id: str, action: str, approver: str) -> None:
    """Log approval action event"""
    log_analytics("approval_action", {
        "approval_id": approval_id,
        "action": action,
        "approver": approver
    })
