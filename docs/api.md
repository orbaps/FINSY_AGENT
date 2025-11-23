# Finsy API Documentation

## Authentication
All endpoints require a JWT token in the `Authorization` header:
`Authorization: Bearer <token>`

## Endpoints

### Invoices

#### `POST /invoices/parse`
Parse an invoice text or file.
**Body:**
```json
{
  "invoice_text": "Invoice #123...",
  "amount": 100.0,
  "vendor": "Acme"
}
```

#### `GET /invoices`
List invoices.
**Params:** `limit`, `offset`, `vendor`

#### `GET /invoices/<id>`
Get invoice details.

### Risk

#### `POST /risk/score`
Calculate risk score for a transaction.
**Body:**
```json
{
  "amount": 1000.0,
  "vendor": "Unknown",
  "invoice_text": "..."
}
```

### Approvals

#### `POST /approvals/create`
Create an approval request.

#### `POST /approvals/<id>/action`
Approve or reject.
**Body:**
```json
{
  "action": "approve",
  "comment": "Approved"
}
```

### Orchestrate

#### `POST /flows/execute`
Execute a flow.
**Body:**
```json
{
  "flow_name": "InvoiceProcessingFlow",
  "input": { ... }
}
```

#### `GET /flows/<id>`
Get flow execution status.

### Speech

#### `POST /speech/transcribe`
Transcribe audio file.
**Body:** Multipart form data with `file` field.

#### `POST /speech/synthesize`
Convert text to speech.
**Body:**
```json
{
  "text": "Hello world"
}
```

### Health

#### `GET /health`
System health status.
