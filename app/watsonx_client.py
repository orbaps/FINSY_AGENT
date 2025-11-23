"""
IBM watsonx.ai client for LLM-based analysis.
"""
from typing import Optional, Dict, Any
import requests
from app.config import Config
from app.logger import get_logger
from app.error_recovery import watsonx_circuit_breaker, retry

logger = get_logger(__name__)


class WatsonXClient:
    """IBM watsonx.ai client"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.url: Optional[str] = None
        self.project_id: Optional[str] = None
        self.model_id: str = Config.WATSONX_MODEL_ID
        self._initialized = False
    
    def connect(self) -> bool:
        """Initialize watsonx.ai connection"""
        if not Config.ENABLE_WATSONX:
            logger.info("watsonx.ai disabled")
            return False
        
        if not Config.WATSONX_API_KEY or not Config.WATSONX_URL or not Config.WATSONX_PROJECT_ID:
            logger.warning("watsonx.ai credentials not configured")
            return False
        
        self.api_key = Config.WATSONX_API_KEY
        self.url = Config.WATSONX_URL
        self.project_id = Config.WATSONX_PROJECT_ID
        self._initialized = True
        logger.info("Initialized watsonx.ai client")
        return True
    
    def is_connected(self) -> bool:
        """Check if connected to watsonx.ai"""
        return self._initialized
    
    def _get_access_token(self) -> Optional[str]:
        """Get IAM access token"""
        if not self.api_key:
            return None
        
        try:
            token_url = "https://iam.cloud.ibm.com/identity/token"
            response = requests.post(
                token_url,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Failed to get watsonx.ai access token: {str(e)}")
            return None
    
    @retry(max_attempts=3, delay=1.0)
    def generate(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Generate text using watsonx.ai"""
        if not self.is_connected():
            return None
        
        token = self._get_access_token()
        if not token:
            return None
        
        try:
            return watsonx_circuit_breaker.call(self._generate_impl, prompt, max_tokens, token)
        except Exception as e:
            logger.error(f"watsonx.ai generation failed after retries: {str(e)}")
            return None
    
    def _generate_impl(self, prompt: str, max_tokens: int, token: str) -> Optional[str]:
        """Internal implementation of generate"""
        url = f"{self.url}/ml/v1/text/generation?version=2024-07-31"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": self.model_id,
            "project_id": self.project_id,
            "input": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("results", [{}])[0].get("generated_text", "")
    
    def analyze_invoice_risk(self, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze invoice risk using LLM"""
        prompt = f"""Analyze the following invoice for potential fraud or risk indicators:

Invoice ID: {invoice_data.get('invoice_id', 'N/A')}
Vendor: {invoice_data.get('vendor', 'N/A')}
Amount: ${invoice_data.get('amount', 0):,.2f}
PO Number: {invoice_data.get('po_number', 'None')}
Date: {invoice_data.get('date', 'N/A')}
Text: {invoice_data.get('invoice_text', 'N/A')[:500]}

Provide a risk assessment with:
1. Risk level (low/medium/high)
2. Key risk factors
3. Recommendation (approve/require_review/reject)

Format as JSON with keys: risk_level, risk_factors (array), recommendation, explanation."""
        
        response = self.generate(prompt, max_tokens=300)
        if not response:
            return None
        
        # Try to extract JSON from response
        try:
            import json
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {str(e)}")
        
        # Fallback: return text response
        return {
            "risk_level": "medium",
            "risk_factors": ["LLM analysis completed"],
            "recommendation": "require_review",
            "explanation": response[:200]
        }
    
    def generate_approval_recommendation(self, approval_data: Dict[str, Any]) -> Optional[str]:
        """Generate approval recommendation using LLM"""
        prompt = f"""Based on the following approval request, provide a brief recommendation:

Invoice ID: {approval_data.get('invoice_id', 'N/A')}
Vendor: {approval_data.get('vendor', 'N/A')}
Amount: ${approval_data.get('amount', 0):,.2f}
Reason: {approval_data.get('reason', 'N/A')}

Provide a concise recommendation (1-2 sentences) on whether to approve or reject."""
        
        return self.generate(prompt, max_tokens=100)


# Global watsonx.ai client instance
watsonx_client = WatsonXClient()

