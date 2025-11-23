import pytest
from unittest.mock import Mock, patch, MagicMock
from app.nlu_service import NLUService

@pytest.fixture
def mock_config():
    with patch('app.nlu_service.Config') as mock:
        mock.ENABLE_NLU = True
        mock.NLU_API_KEY = "test-key"
        mock.NLU_URL = "https://api.nlu.ibm.com"
        mock.NLU_VERSION = "2022-04-07"
        yield mock

@pytest.fixture
def nlu_client(mock_config):
    # Mock SDK import
    with patch.dict('sys.modules', {
        'ibm_watson': MagicMock(),
        'ibm_cloud_sdk_core.authenticators': MagicMock()
    }):
        client = NLUService()
        client.connect()
        return client

def test_connect_success(nlu_client):
    assert nlu_client.is_connected() is True
    assert nlu_client.client is not None

def test_extract_invoice_entities(nlu_client):
    # Mock analyze response
    mock_response = {
        "entities": [
            {"type": "Organization", "text": "Acme Corp", "confidence": 0.95},
            {"type": "Money", "text": "$1,234.56", "confidence": 0.9}
        ],
        "keywords": []
    }
    
    nlu_client.client.analyze.return_value.get_result.return_value = mock_response
    
    result = nlu_client.extract_invoice_entities("Invoice from Acme Corp for $1,234.56")
    
    assert result["vendor"] == "Acme Corp"
    assert result["amount"] == 1234.56
    assert result["confidence"] == 0.95

def test_process_nlu_response(nlu_client):
    response = {
        "entities": [
            {"type": "Company", "text": "Test Vendor", "confidence": 0.8}
        ]
    }
    result = nlu_client._process_nlu_response(response)
    assert result["vendor"] == "Test Vendor"
    assert result["confidence"] == 0.8
