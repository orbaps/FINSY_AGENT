import pytest
from unittest.mock import Mock, patch
from app.orchestrate.skills import OrchestrateSkills

@pytest.fixture
def mock_config():
    with patch('app.orchestrate.skills.Config') as mock:
        mock.ENABLE_ORCHESTRATE = True
        mock.ORCHESTRATE_API_KEY = "test-key"
        mock.ORCHESTRATE_URL = "https://api.orchestrate.ibm.com"
        mock.ORCHESTRATE_PROJECT_ID = "proj-123"
        yield mock

@pytest.fixture
def skills_client(mock_config):
    client = OrchestrateSkills()
    client.connect()
    return client

def test_connect_success(skills_client):
    assert skills_client.is_connected() is True
    assert skills_client.api_key == "test-key"

def test_invoke_skill_success(skills_client):
    with patch.object(skills_client.session, 'post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "success", "data": "result"}
        
        result = skills_client.invoke_skill("test-skill", {"input": "value"})
        
        assert result is not None
        assert result["status"] == "success"
        mock_post.assert_called_once()
        
        # Verify URL and headers
        args, kwargs = mock_post.call_args
        assert "test-skill/invoke" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"

def test_invoke_skill_failure(skills_client):
    with patch.object(skills_client.session, 'post') as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"
        
        result = skills_client.invoke_skill("test-skill", {})
        assert result is None

def test_list_skills(skills_client):
    with patch.object(skills_client.session, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"skills": [{"name": "skill1"}]}
        
        skills = skills_client.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "skill1"
