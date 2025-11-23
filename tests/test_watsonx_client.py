import pytest
from unittest.mock import Mock, patch
from app.watsonx_client import WatsonXClient

@pytest.fixture
def mock_config():
    with patch('app.watsonx_client.Config') as mock:
        mock.ENABLE_WATSONX = True
        mock.WATSONX_API_KEY = "test-key"
        mock.WATSONX_URL = "https://us-south.ml.cloud.ibm.com"
        mock.WATSONX_PROJECT_ID = "proj-123"
        mock.WATSONX_MODEL_ID = "test-model"
        yield mock

@pytest.fixture
def wx_client(mock_config):
    client = WatsonXClient()
    client.connect()
    return client

def test_connect_success(wx_client):
    assert wx_client.is_connected() is True
    assert wx_client.api_key == "test-key"

@patch('app.watsonx_client.requests.post')
def test_get_access_token(mock_post, wx_client):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "token-123"}
    
    token = wx_client._get_access_token()
    assert token == "token-123"

@patch('app.watsonx_client.requests.post')
def test_generate_success(mock_post, wx_client):
    # Mock token response
    mock_post.side_effect = [
        Mock(status_code=200, json=lambda: {"access_token": "token-123"}),
        Mock(status_code=200, json=lambda: {"results": [{"generated_text": "Generated response"}]})
    ]
    
    result = wx_client.generate("Test prompt")
    assert result == "Generated response"

@patch('app.watsonx_client.requests.post')
def test_analyze_invoice_risk(mock_post, wx_client):
    # Mock token and generation response
    mock_post.side_effect = [
        Mock(status_code=200, json=lambda: {"access_token": "token-123"}),
        Mock(status_code=200, json=lambda: {"results": [{"generated_text": '{"risk_level": "high", "risk_factors": ["Factor 1"], "recommendation": "reject", "explanation": "Bad"}'}]})
    ]
    
    invoice_data = {"invoice_id": "INV-1", "amount": 1000}
    result = wx_client.analyze_invoice_risk(invoice_data)
    
    assert result["risk_level"] == "high"
    assert "Factor 1" in result["risk_factors"]

@patch('app.watsonx_client.requests.post')
def test_generate_approval_recommendation(mock_post, wx_client):
    # Mock token and generation response
    mock_post.side_effect = [
        Mock(status_code=200, json=lambda: {"access_token": "token-123"}),
        Mock(status_code=200, json=lambda: {"results": [{"generated_text": "Approve it."}]})
    ]
    
    approval_data = {"invoice_id": "INV-1"}
    result = wx_client.generate_approval_recommendation(approval_data)
    
    assert result == "Approve it."
