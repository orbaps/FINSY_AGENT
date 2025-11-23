"""
IBM Natural Language Understanding (NLU) Service wrapper.
Provides entity extraction and sentiment analysis for invoices.
"""
from typing import Optional, Dict, Any, List
import json
from app.config import Config
from app.logger import get_logger
from app.error_recovery import retry

logger = get_logger(__name__)

class NLUService:
    """IBM NLU Service wrapper"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.url: Optional[str] = None
        self.version: str = Config.NLU_VERSION
        self._initialized = False
        self.client = None
    
    def connect(self) -> bool:
        """Initialize NLU connection"""
        if not Config.ENABLE_NLU:
            logger.info("NLU disabled")
            return False
        
        if not Config.NLU_API_KEY or not Config.NLU_URL:
            logger.warning("NLU credentials not configured")
            return False
        
        self.api_key = Config.NLU_API_KEY
        self.url = Config.NLU_URL
        
        try:
            # Try using SDK first
            from ibm_watson import NaturalLanguageUnderstandingV1
            from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
            
            authenticator = IAMAuthenticator(self.api_key)
            self.client = NaturalLanguageUnderstandingV1(
                version=self.version,
                authenticator=authenticator
            )
            self.client.set_service_url(self.url)
            self._initialized = True
            logger.info("Initialized NLU client (SDK)")
            return True
        except ImportError:
            logger.warning("IBM Watson SDK not installed, falling back to REST")
            self._initialized = True # We will use REST
            return True
        except Exception as e:
            logger.error(f"Failed to initialize NLU SDK: {str(e)}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to NLU"""
        return self._initialized

    @retry(max_attempts=3, delay=1.0)
    def extract_invoice_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from invoice text"""
        if not self.is_connected():
            return {}
            
        try:
            # Use SDK if available
            if self.client:
                from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions
                
                response = self.client.analyze(
                    text=text,
                    features=Features(
                        entities=EntitiesOptions(limit=10),
                        keywords=KeywordsOptions(limit=10)
                    )
                ).get_result()
                
                return self._process_nlu_response(response)
            
            else:
                # REST fallback (simplified)
                # In a real scenario, implement requests logic here similar to CloudantClient
                # For hackathon, if SDK fails, we might just return empty or mock
                logger.warning("NLU REST fallback not fully implemented")
                return {}
                
        except Exception as e:
            logger.error(f"NLU analysis failed: {str(e)}")
            return {}

    def _process_nlu_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process NLU response into structured invoice data"""
        result = {
            "vendor": None,
            "amount": None,
            "currency": "USD",
            "date": None,
            "confidence": 0.0,
            "keywords": []
        }
        
        entities = response.get("entities", [])
        keywords = response.get("keywords", [])
        
        # Extract keywords
        result["keywords"] = [k.get("text") for k in keywords if k.get("confidence", 0) > 0.5]
        
        # Simple heuristic mapping
        for entity in entities:
            etype = entity.get("type", "").lower()
            etext = entity.get("text", "")
            econf = entity.get("confidence", 0.0)
            
            if etype == "organization" or etype == "company":
                if not result["vendor"] or econf > result["confidence"]:
                    result["vendor"] = etext
                    result["confidence"] = econf
            
            elif etype == "quantity" or etype == "money":
                # Try to parse amount
                try:
                    import re
                    # Remove currency symbols and commas
                    clean_amount = re.sub(r'[^\d.]', '', etext)
                    if clean_amount:
                        result["amount"] = float(clean_amount)
                except:
                    pass
                    
        return result

# Global NLU service instance
nlu_service = NLUService()
