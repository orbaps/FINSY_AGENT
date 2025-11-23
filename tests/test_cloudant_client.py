import pytest
from unittest.mock import Mock, patch
from app.cloudant_client import CloudantClient
from app.config import Config

@pytest.fixture
def mock_config():
    with patch('app.cloudant_client.Config') as mock:
        mock.USE_CLOUDANT = True
        mock.CLOUDANT_URL = "https://test-cloudant.com"
        mock.CLOUDANT_API_KEY = "test-key"
        mock.CLOUDANT_DB_NAME = "finsy-db"
        yield mock

@pytest.fixture
def client(mock_config):
    return CloudantClient()

def test_connect_success(client):
    with patch.object(client.session, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        assert client.connect() is True
        assert client.is_connected() is True
        mock_get.assert_called_once()

def test_connect_create_db(client):
    with patch.object(client.session, 'get') as mock_get, \
         patch.object(client.session, 'put') as mock_put:
        
        # First check returns 404 (not found)
        mock_get.return_value.status_code = 404
        # Create returns 201 (created)
        mock_put.return_value.status_code = 201
        
        assert client.connect() is True
        mock_put.assert_called_once()

def test_connect_fail(client):
    with patch.object(client.session, 'get') as mock_get:
        mock_get.return_value.status_code = 500
        assert client.connect() is False

def test_save_invoice_success(client):
    client._initialized = True
    client.base_url = "https://test.com"
    client.api_key = "key"
    
    with patch.object(client.session, 'put') as mock_put, \
         patch.object(client.session, 'get') as mock_get:
        
        # Mock get (check existing) - 404 not found
        mock_get.return_value.status_code = 404
        # Mock put - 201 created
        mock_put.return_value.status_code = 201
        
        invoice = {"invoice_id": "123", "total": 100}
        assert client.save_invoice(invoice) is True
        
        # Verify call args
        call_args = mock_put.call_args
        assert call_args[1]['json']['_id'] == "123"
        assert call_args[1]['json']['type'] == "invoice"

def test_get_invoice_success(client):
    client._initialized = True
    client.base_url = "https://test.com"
    client.api_key = "key"
    
    with patch.object(client.session, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "_id": "123",
            "type": "invoice",
            "total": 100
        }
        
        result = client.get_invoice("123")
        assert result is not None
        assert result['total'] == 100
        assert '_id' not in result  # Should be cleaned

def test_query_approvals(client):
    client._initialized = True
    client.base_url = "https://test.com"
    client.api_key = "key"
    
    with patch.object(client.session, 'post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "docs": [
                {"_id": "1", "type": "approval", "status": "pending"},
                {"_id": "2", "type": "approval", "status": "pending"}
            ]
        }
        
        results = client.query_approvals(status="pending")
        assert len(results) == 2
        assert results[0]['status'] == "pending"
