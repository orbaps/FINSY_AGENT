"""
IBM Cloudant client wrapper using REST API.
Provides connection pooling and error handling via requests.
"""
import requests
import json
from typing import Optional, Dict, Any, List
from app.config import Config
from app.logger import get_logger
from app.error_recovery import cloudant_circuit_breaker, retry

logger = get_logger(__name__)

class CloudantClient:
    """Cloudant database client using REST API"""
    
    def __init__(self):
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.db_name: str = Config.CLOUDANT_DB_NAME
        self.session = requests.Session()
        self._initialized = False
    
    def connect(self) -> bool:
        """Initialize Cloudant connection settings"""
        if not Config.USE_CLOUDANT:
            logger.info("Cloudant disabled, using SQLite")
            return False
        
        self.base_url = Config.CLOUDANT_URL
        self.api_key = Config.CLOUDANT_API_KEY
        
        if not self.base_url or not self.api_key:
            logger.warning("Cloudant credentials not configured")
            return False
            
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
            
        self._initialized = True
        
        # Verify connection and ensure DB exists
        try:
            return self._ensure_database()
        except Exception as e:
            logger.error(f"Failed to connect to Cloudant: {str(e)}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_auth(self):
        """Get authentication for requests (Basic Auth with apikey)"""
        # Cloudant IAM auth uses 'apikey' as username and the actual key as password
        return ('apikey', self.api_key)

    def _ensure_database(self) -> bool:
        """Ensure database exists, create if not"""
        if not self._initialized:
            return False
            
        url = f"{self.base_url}/{self.db_name}"
        
        # Check if exists
        response = self.session.get(url, auth=self._get_auth())
        
        if response.status_code == 200:
            logger.info(f"Connected to Cloudant database: {self.db_name}")
            return True
        elif response.status_code == 404:
            # Create it
            response = self.session.put(url, auth=self._get_auth())
            if response.status_code in [201, 202]:
                logger.info(f"Created Cloudant database: {self.db_name}")
                return True
            else:
                logger.error(f"Failed to create database: {response.text}")
                return False
        else:
            logger.error(f"Failed to check database: {response.text}")
            return False

    def is_connected(self) -> bool:
        """Check if client is initialized"""
        return self._initialized

    @retry(max_attempts=3, delay=1.0)
    def save_invoice(self, invoice: Dict[str, Any]) -> bool:
        """Save invoice document"""
        if not self.is_connected():
            return False
        
        try:
            return cloudant_circuit_breaker.call(self._save_doc_impl, invoice, "invoice", "invoice_id")
        except Exception as e:
            logger.error(f"Failed to save invoice after retries: {str(e)}")
            return False

    @retry(max_attempts=3, delay=1.0)
    def save_approval(self, approval: Dict[str, Any]) -> bool:
        """Save approval document"""
        if not self.is_connected():
            return False
            
        try:
            return cloudant_circuit_breaker.call(self._save_doc_impl, approval, "approval", "approval_id")
        except Exception as e:
            logger.error(f"Failed to save approval after retries: {str(e)}")
            return False

    def _save_doc_impl(self, data: Dict[str, Any], doc_type: str, id_field: str) -> bool:
        """Internal implementation to save a document"""
        doc_id = data.get(id_field)
        if not doc_id:
            logger.error(f"Missing ID field {id_field} for {doc_type}")
            return False
            
        # Prepare document
        doc = data.copy()
        doc["_id"] = doc_id
        doc["type"] = doc_type
        
        url = f"{self.base_url}/{self.db_name}/{doc_id}"
        
        # Try to get existing revision first to handle updates
        existing_rev = None
        get_resp = self.session.get(url, auth=self._get_auth())
        if get_resp.status_code == 200:
            existing_rev = get_resp.json().get("_rev")
            doc["_rev"] = existing_rev
            
        # Put document (Create or Update)
        response = self.session.put(
            url, 
            json=doc, 
            headers=self._get_headers(), 
            auth=self._get_auth()
        )
        
        if response.status_code in [201, 202]:
            logger.debug(f"Saved {doc_type} to Cloudant: {doc_id}")
            return True
        else:
            logger.error(f"Failed to save {doc_type}: {response.text}")
            raise Exception(f"Cloudant save failed: {response.status_code}")

    @retry(max_attempts=3, delay=1.0)
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        return self._get_doc_impl(invoice_id, "invoice")

    @retry(max_attempts=3, delay=1.0)
    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Get approval by ID"""
        return self._get_doc_impl(approval_id, "approval")

    def _get_doc_impl(self, doc_id: str, expected_type: str) -> Optional[Dict[str, Any]]:
        """Internal implementation to get a document"""
        if not self.is_connected():
            return None
            
        url = f"{self.base_url}/{self.db_name}/{doc_id}"
        
        try:
            response = self.session.get(url, auth=self._get_auth())
            if response.status_code == 200:
                doc = response.json()
                if doc.get("type") == expected_type:
                    # Clean metadata
                    doc.pop("_id", None)
                    doc.pop("_rev", None)
                    doc.pop("type", None)
                    return doc
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Failed to get document {doc_id}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {str(e)}")
            
        return None

    def query_approvals(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query approvals using Mango query"""
        if not self.is_connected():
            return []
            
        url = f"{self.base_url}/{self.db_name}/_find"
        
        selector = {"type": "approval"}
        if status:
            selector["status"] = status
            
        payload = {
            "selector": selector,
            "limit": limit,
            "sort": [{"created_at": "desc"}]
        }
        
        # Note: Sorting requires an index. If index doesn't exist, this might fail or warn.
        # For simplicity in this REST client, we might need to create the index or remove sort if it fails.
        # Let's try without sort first if we suspect no index, but the original code had it.
        # We will keep it simple for now.
        
        try:
            response = self.session.post(
                url, 
                json=payload, 
                headers=self._get_headers(), 
                auth=self._get_auth()
            )
            
            if response.status_code == 200:
                docs = response.json().get("docs", [])
                # Clean docs
                cleaned = []
                for doc in docs:
                    doc.pop("_id", None)
                    doc.pop("_rev", None)
                    doc.pop("type", None)
                    cleaned.append(doc)
                return cleaned
            else:
                logger.error(f"Query failed: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying approvals: {str(e)}")
            return []

    def query_invoices(self, vendor: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query invoices using Mango query"""
        if not self.is_connected():
            return []
            
        url = f"{self.base_url}/{self.db_name}/_find"
        
        selector = {"type": "invoice"}
        if vendor:
            selector["vendor"] = {"$regex": f"(?i){vendor}"}  # Case insensitive regex
            
        payload = {
            "selector": selector,
            "limit": limit,
            "sort": [{"created_at": "desc"}]
        }
        
        try:
            response = self.session.post(
                url, 
                json=payload, 
                headers=self._get_headers(), 
                auth=self._get_auth()
            )
            
            if response.status_code == 200:
                docs = response.json().get("docs", [])
                cleaned = []
                for doc in docs:
                    doc.pop("_id", None)
                    doc.pop("_rev", None)
                    doc.pop("type", None)
                    cleaned.append(doc)
                return cleaned
            else:
                logger.error(f"Query invoices failed: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying invoices: {str(e)}")
            return []

    @retry(max_attempts=3, delay=1.0)
    def save_analytics(self, analytics: Dict[str, Any]) -> bool:
        """Save analytics document"""
        if not self.is_connected():
            return False
            
        try:
            # Analytics docs might not have an ID, let Cloudant generate one or use timestamp
            if "id" not in analytics and "_id" not in analytics:
                import uuid
                analytics["_id"] = f"analytics-{uuid.uuid4()}"
            
            return cloudant_circuit_breaker.call(self._save_doc_impl, analytics, "analytics", "_id")
        except Exception as e:
            logger.error(f"Failed to save analytics: {str(e)}")
            return False

# Global instance
cloudant_client = CloudantClient()
