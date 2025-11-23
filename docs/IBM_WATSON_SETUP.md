# IBM Watson Services Configuration

## Overview
This document describes the IBM Watson services integrated into the Finsy Agent application for the watsonx Orchestrate hackathon.

## Configured Services

### 1. IBM Natural Language Understanding (NLU)
- **Purpose**: Extract entities and insights from invoice text
- **Region**: Sydney (au-syd)
- **Status**: ✅ Configured and Enabled
- **Instance ID**: `9a297eae-8507-418c-954e-f0de3ec94c19`
- **Environment Variables**:
  - `ENABLE_NLU=True`
  - `NLU_API_KEY` - Configured
  - `NLU_URL` - Configured
  - `NLU_VERSION=2022-04-07`

### 2. IBM Cloudant NoSQL Database
- **Purpose**: Persistent storage for invoices, approvals, and transactions
- **Region**: Sydney (au-syd)
- **Status**: ✅ Configured and Enabled
- **Host**: `b6ac0edc-c1c8-4799-bb09-588d2fe2b8e8-bluemix.cloudantnosqldb.appdomain.cloud`
- **Environment Variables**:
  - `USE_CLOUDANT=True`
  - `CLOUDANT_URL` - Configured
  - `CLOUDANT_API_KEY` - Configured
  - `CLOUDANT_DB_NAME=finsy`

### 3. IBM Speech-to-Text
- **Purpose**: Transcribe audio invoices to text
- **Region**: Sydney (au-syd)
- **Status**: ✅ Configured and Enabled
- **Instance ID**: `49bcec0a-1b0c-4d45-96b1-fdb9704fb4d1`
- **Environment Variables**:
  - `ENABLE_SPEECH=True`
  - `STT_API_KEY` - Configured
  - `STT_URL` - Configured

### 4. IBM watsonx Orchestrate
- **Purpose**: Workflow orchestration and automation
- **Region**: US South
- **Status**: ✅ Configured and Enabled
- **Instance ID**: `4454a6b7-d61c-4d9d-8b25-200c0a8663c4`
- **Environment Variables**:
  - `ENABLE_ORCHESTRATE=True`
  - `ORCHESTRATE_API_KEY` - Configured
  - `ORCHESTRATE_URL` - Configured

### 5. IBM watsonx.ai (Optional)
- **Purpose**: LLM-based invoice analysis and generation
- **Status**: ⚠️ Disabled (Requires Project ID)
- **Environment Variables**:
  - `ENABLE_WATSONX=False`
  - `WATSONX_API_KEY` - Available
  - `WATSONX_URL` - Configured
  - `WATSONX_PROJECT_ID` - ⚠️ **NEEDS CONFIGURATION**

### 6. IBM Text-to-Speech
- **Purpose**: Convert text responses to audio
- **Status**: ⚠️ Not Configured
- **Environment Variables**:
  - `TTS_API_KEY` - ⚠️ **NEEDS CONFIGURATION**
  - `TTS_URL` - ⚠️ **NEEDS CONFIGURATION**

## Service Integration Details

### Natural Language Understanding Integration
File: `app/nlu_service.py`

The NLU service:
- Extracts vendor names, amounts, dates from invoice text
- Identifies keywords for categorization
- Provides confidence scores for extracted entities
- Uses both IBM Watson SDK and REST API fallback

**Usage Example**:
```python
from app.nlu_service import nlu_service

# Connect to NLU
nlu_service.connect()

# Extract invoice entities
entities = nlu_service.extract_invoice_entities(invoice_text)
# Returns: {"vendor": "Acme Corp", "amount": 1500.00, "keywords": [...]}
```

### Cloudant Database Integration
File: `app/cloudant_client.py`

The Cloudant client:
- Stores invoices, approvals, and transactions
- Provides CRUD operations with error recovery
- Supports querying and filtering
- Handles authentication via IAM API key

### Speech-to-Text Integration
File: `app/speech_service.py`

The Speech service:
- Transcribes audio files to text for voice invoice submission
- Supports multiple audio formats (WAV, MP3, etc.)
- Uses circuit breaker pattern for resilience
- Includes retry logic for failed requests

**Usage Example**:
```python
from app.speech_service import speech_service

# Connect to Speech service
speech_service.connect()

# Transcribe audio
with open("invoice.wav", "rb") as audio_file:
    transcript = speech_service.transcribe_audio(audio_file)
```

### Orchestrate Integration
File: `app/orchestrate/` directory

The Orchestrate integration:
- Manages workflow execution
- Coordinates multi-step approval processes
- Integrates with IBM watsonx Orchestrate platform

## Configuration Files

### Environment Variables (.env)
All credentials are stored in `.env` file (not committed to git). See `.env.example` for template.

### Config Class (app/config.py)
The `Config` class loads and validates all environment variables with sensible defaults.

## Security Notes

> [!CAUTION]
> **Never commit `.env` file to version control!**

- All API keys use IAM authentication
- JWT tokens expire after 24 hours (configurable)
- CORS is currently set to `*` for development - restrict in production
- Rate limiting is set to 60 requests/minute

## Testing the Configuration

### 1. Verify Environment Variables
```powershell
python -c "from app.config import Config; missing = Config.validate(); print('Missing:' if missing else 'All configured:', missing or 'None')"
```

### 2. Test Service Connections
```powershell
pytest tests/test_speech_service.py -v
pytest tests/test_nlu_service.py -v    # If exists
```

### 3. Check Health Endpoint
```powershell
# Start the application
python app.py

# In another terminal
curl http://localhost:5000/health
```

## Next Steps

### To Enable watsonx.ai:
1. Create a watsonx.ai project in IBM Cloud
2. Copy the Project ID
3. Set `WATSONX_PROJECT_ID` in `.env`
4. Set `ENABLE_WATSONX=True`

### To Enable Text-to-Speech:
1. Create IBM Text-to-Speech service in IBM Cloud (Sydney region recommended)
2. Get the API key and URL
3. Set `TTS_API_KEY` and `TTS_URL` in `.env`
4. The service will auto-enable when credentials are present

## Troubleshooting

### Common Issues

**Issue**: "NLU credentials not configured"
- **Solution**: Ensure `ENABLE_NLU=True` and both `NLU_API_KEY` and `NLU_URL` are set

**Issue**: "Failed to connect to Cloudant"
- **Solution**: Verify the `CLOUDANT_URL` and `CLOUDANT_API_KEY` are correct. Check network connectivity.

**Issue**: "Speech-to-Text initialization failed"
- **Solution**: Ensure `ibm-watson` SDK is installed: `pip install ibm-watson==6.1.0`

### Checking Logs
```powershell
# View application logs
Get-Content app/logs/finsy.log -Tail 50

# View with log level filtering
$env:LOG_LEVEL="DEBUG"
python app.py
```

## Resources

- [IBM Natural Language Understanding Docs](https://cloud.ibm.com/apidocs/natural-language-understanding)
- [IBM Cloudant Docs](https://cloud.ibm.com/docs/Cloudant)
- [IBM Speech Services Docs](https://cloud.ibm.com/apidocs/speech-to-text)
- [IBM watsonx Orchestrate Docs](https://www.ibm.com/docs/en/watson-orchestrate)

## Credential Summary

| Service | Region | Status | Feature Flag |
|---------|--------|--------|--------------|
| NLU | Sydney | ✅ Active | `ENABLE_NLU=True` |
| Cloudant | Sydney | ✅ Active | `USE_CLOUDANT=True` |
| Speech-to-Text | Sydney | ✅ Active | `ENABLE_SPEECH=True` |
| Orchestrate | US South | ✅ Active | `ENABLE_ORCHESTRATE=True` |
| watsonx.ai | US South | ⚠️ Needs Project ID | `ENABLE_WATSONX=False` |
| Text-to-Speech | - | ❌ Not Configured | - |
