"""
IBM watsonx Orchestrate Skills wrapper.
Maps existing endpoints to Orchestrate Skills.
"""
import requests
import json
from typing import Optional, Dict, Any, List
from app.config import Config
from app.logger import get_logger
from app.error_recovery import retry

logger = get_logger(__name__)


class OrchestrateSkills:
    """Orchestrate Skills wrapper"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.url: Optional[str] = None
        self.project_id: Optional[str] = None
        self.session = requests.Session()
        self._initialized = False
    
    def connect(self) -> bool:
        """Initialize Orchestrate connection"""
        if not Config.ENABLE_ORCHESTRATE:
            logger.info("Orchestrate disabled")
            return False
        
        if not Config.ORCHESTRATE_API_KEY or not Config.ORCHESTRATE_URL or not Config.ORCHESTRATE_PROJECT_ID:
            logger.warning("Orchestrate credentials not configured")
            return False
        
        self.api_key = Config.ORCHESTRATE_API_KEY
        self.url = Config.ORCHESTRATE_URL
        self.project_id = Config.ORCHESTRATE_PROJECT_ID
        
        # Remove trailing slash
        if self.url.endswith('/'):
            self.url = self.url[:-1]
            
        self._initialized = True
        logger.info("Initialized Orchestrate client")
        return True
    
    def is_connected(self) -> bool:
        """Check if connected to Orchestrate"""
        return self._initialized
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Project-ID": self.project_id
        }
    
    @retry(max_attempts=3, delay=1.0)
    def invoke_skill(self, skill_name: str, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invoke an Orchestrate skill"""
        if not self.is_connected():
            logger.warning("Orchestrate not connected, returning mock response")
            return {
                "skill": skill_name,
                "status": "mock_success",
                "result": input_data
            }
        
        # Construct endpoint URL - assuming standard pattern
        # Adjust this based on actual API docs if available
        endpoint = f"{self.url}/v1/skills/{skill_name}/invoke"
        
        try:
            logger.info(f"Invoking Orchestrate skill: {skill_name}")
            response = self.session.post(
                endpoint,
                json=input_data,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Skill invocation failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error invoking skill {skill_name}: {str(e)}")
            return None

    def list_skills(self) -> List[Dict[str, Any]]:
        """List available skills"""
        if not self.is_connected():
            return []
            
        endpoint = f"{self.url}/v1/skills"
        
        try:
            response = self.session.get(endpoint, headers=self._get_headers())
            if response.status_code == 200:
                return response.json().get("skills", [])
            return []
        except Exception as e:
            logger.error(f"Error listing skills: {str(e)}")
            return []


# Global Orchestrate skills instance
orchestrate_skills = OrchestrateSkills()
