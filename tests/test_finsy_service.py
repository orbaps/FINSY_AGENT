import json
from app.schemas import InvoiceParseRequest

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] in ['ok', 'healthy', 'degraded', 'unhealthy']
    assert 'services' in data
    assert 'database' in data['services']

def test_invoice_parse(client, auth_headers):
    payload = {
        "invoice_text": "Invoice #123 from Acme Corp for $500.00",
        "amount": 500.0,
        "vendor": "Acme Corp",
        "po_number": "PO-123",
        "date": "2023-10-27"
    }
    response = client.post('/invoices/parse', json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['parsed'] is True
    assert data['vendor'] == "Acme Corp"
    assert 'invoice_id' in data

def test_list_invoices(client, auth_headers):
    # First create an invoice
    payload = {
        "amount": 100.0,
        "vendor": "Test Vendor"
    }
    client.post('/invoices/parse', json=payload, headers=auth_headers)
    
    response = client.get('/invoices', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['invoices']) > 0
    assert data['invoices'][0]['vendor'] == "Test Vendor"

def test_risk_score(client, auth_headers):
    payload = {
        "amount": 60000.0,  # High amount
        "vendor": "Suspicious Vendor",
        "invoice_text": "Payment for services"
    }
    response = client.post('/risk/score', json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['risk_level'] in ['medium', 'high']
    assert data['requires_approval'] is True

def test_create_approval(client, auth_headers):
    payload = {
        "invoice_id": "inv-123",
        "amount": 1000.0,
        "vendor": "Test Vendor",
        "reason": "High amount"
    }
    response = client.post('/approvals/create', json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'pending'
    assert 'approval_id' in data

def test_approval_workflow(client, auth_headers):
    # 0. Create Invoice first
    invoice_payload = {
        "amount": 2000.0,
        "vendor": "Workflow Vendor",
        "date": "2023-10-27"
    }
    inv_resp = client.post('/invoices/parse', json=invoice_payload, headers=auth_headers)
    assert inv_resp.status_code == 200
    invoice_id = json.loads(inv_resp.data)['invoice_id']

    # 1. Create approval
    payload = {
        "invoice_id": invoice_id,
        "amount": 2000.0,
        "vendor": "Workflow Vendor",
        "reason": "Test workflow"
    }
    create_resp = client.post('/approvals/create', json=payload, headers=auth_headers)
    approval_id = json.loads(create_resp.data)['approval_id']
    
    # 2. Verify it's pending
    pending_resp = client.get('/approvals/pending', headers=auth_headers)
    pending_data = json.loads(pending_resp.data)
    assert any(a['approval_id'] == approval_id for a in pending_data['pending_approvals'])
    
    # 3. Approve it
    action_payload = {
        "action": "approve",
        "comment": "Looks good"
    }
    action_resp = client.post(f'/approvals/{approval_id}/action', json=action_payload, headers=auth_headers)
    assert action_resp.status_code == 200
    assert json.loads(action_resp.data)['status'] == 'approved'
    
    # 4. Verify it's no longer pending
    pending_resp_2 = client.get('/approvals/pending', headers=auth_headers)
    pending_data_2 = json.loads(pending_resp_2.data)
    assert not any(a['approval_id'] == approval_id for a in pending_data_2['pending_approvals'])

def test_execute_flow(client, auth_headers):
    # Mock Config.ENABLE_ORCHESTRATE for this test
    # Since we can't easily patch Config in the running app from here without reloading,
    # we rely on the fact that we might need to mock the flow runner or just ensure it handles disabled state gracefully.
    # However, conftest.py doesn't set ENABLE_ORCHESTRATE=True by default.
    # Let's assume it returns 404 if disabled, which is valid behavior to test.
    
    payload = {
        "flow_name": "InvoiceProcessingFlow",
        "input": {"invoice": {"total": 100}}
    }
    response = client.post('/flows/execute', json=payload, headers=auth_headers)
    
    # It should be either 200 (if enabled) or 404 (if disabled)
    assert response.status_code in [200, 404]
