###############################################################################
# Finsy Project Setup Script (PowerShell)
# This script creates the complete directory structure and all necessary files
###############################################################################

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Finsy Finance Automation Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Project root
$PROJECT_NAME = "finsy"
$PROJECT_ROOT = Join-Path (Get-Location) $PROJECT_NAME

Write-Host "Creating project directory: $PROJECT_ROOT" -ForegroundColor Blue

# Create main directory
New-Item -ItemType Directory -Path $PROJECT_NAME -Force | Out-Null
Set-Location $PROJECT_NAME

Write-Host "[OK] Created project root" -ForegroundColor Green

###############################################################################
# Create Directory Structure
###############################################################################

Write-Host "Creating directory structure..." -ForegroundColor Blue

$directories = @(
    "app/db",
    "app/models",
    "app/templates",
    "tests",
    "docs",
    "openapi",
    ".github/workflows"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Host "[OK] Directory structure created" -ForegroundColor Green

###############################################################################
# Create __init__.py files
###############################################################################

Write-Host "Creating __init__.py files..." -ForegroundColor Blue

# app/__init__.py
$appInit = @'
"""
Finsy - Finance Automation Service

A microservice for invoice processing, risk scoring,
approval workflows, and financial reporting.
"""

__version__ = "1.0.0"
__author__ = "Your Team"

# Make key components easily importable
from .finsy_service import app
from .utils import (
    init_db,
    get_invoice,
    save_invoice_record,
    get_approval,
    save_approval,
    update_approval,
    summary_report
)

__all__ = [
    'app',
    'init_db',
    'get_invoice',
    'save_invoice_record',
    'get_approval',
    'save_approval',
    'update_approval',
    'summary_report',
]
'@
$appInit | Out-File -FilePath "app/__init__.py" -Encoding UTF8

# tests/__init__.py
$testsInit = @'
"""
Test suite for Finsy Finance Automation Service
"""
'@
$testsInit | Out-File -FilePath "tests/__init__.py" -Encoding UTF8

Write-Host "[OK] __init__.py files created" -ForegroundColor Green

###############################################################################
# Create .gitignore
###############################################################################

Write-Host "Creating .gitignore..." -ForegroundColor Blue

$gitignore = @'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Flask
instance/
.webassets-cache

# Database
*.db
*.sqlite

# ML Models (optional - you may want to commit these)
# app/models/*.pkl

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
.dockerignore

# Environment
.env
.env.local

# Testing
.pytest_cache/
htmlcov/
.coverage
coverage.xml
'@
$gitignore | Out-File -FilePath ".gitignore" -Encoding UTF8

Write-Host "[OK] .gitignore created" -ForegroundColor Green

###############################################################################
# Create .dockerignore
###############################################################################

Write-Host "Creating .dockerignore..." -ForegroundColor Blue

$dockerignore = @'
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv
.git
.gitignore
README.md
.dockerignore
Dockerfile
docker-compose*.yml
tests/
docs/
*.md
.github/
setup_finsy.ps1
'@
$dockerignore | Out-File -FilePath ".dockerignore" -Encoding UTF8

Write-Host "[OK] .dockerignore created" -ForegroundColor Green

###############################################################################
# Create requirements-dev.txt
###############################################################################

Write-Host "Creating requirements-dev.txt..." -ForegroundColor Blue

$reqDev = @'
-r requirements.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-flask==1.2.0
black==23.12.0
flake8==6.1.0
mypy==1.7.1
requests==2.31.0
'@
$reqDev | Out-File -FilePath "requirements-dev.txt" -Encoding UTF8

Write-Host "[OK] requirements-dev.txt created" -ForegroundColor Green

###############################################################################
# Create setup.py
###############################################################################

Write-Host "Creating setup.py..." -ForegroundColor Blue

$setupPy = @'
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="finsy",
    version="1.0.0",
    description="Finance Automation Service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@company.com",
    url="https://github.com/yourusername/finsy",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.2.5",
        "flask-cors>=3.0.10",
        "pydantic>=1.10.11",
        "scikit-learn>=1.3.2",
        "pandas>=2.2.2",
        "joblib>=1.3.2",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.19",
        "werkzeug>=3.0.0",
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "finsy=app.finsy_service:main",
        ],
    },
)
'@
$setupPy | Out-File -FilePath "setup.py" -Encoding UTF8

Write-Host "[OK] setup.py created" -ForegroundColor Green

###############################################################################
# Create docker-compose.prod.yml
###############################################################################

Write-Host "Creating docker-compose.prod.yml..." -ForegroundColor Blue

$dockerComposeProd = @'
version: "3.8"
services:
  finsy:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FINSY_DB=/app/app/db/finsy.db
      - RISK_MODEL=/app/app/models/risk_model.pkl
      - FLASK_ENV=production
    volumes:
      - finsy-data:/app/app/db
      - finsy-models:/app/app/models
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - finsy-network

networks:
  finsy-network:
    driver: bridge

volumes:
  finsy-data:
  finsy-models:
'@
$dockerComposeProd | Out-File -FilePath "docker-compose.prod.yml" -Encoding UTF8

Write-Host "[OK] docker-compose.prod.yml created" -ForegroundColor Green

###############################################################################
# Create test files
###############################################################################

Write-Host "Creating test files..." -ForegroundColor Blue

# tests/test_invoices.py
$testInvoices = @'
import pytest
import io
from app.finsy_service import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_parse_invoice_no_file(client):
    """Test invoice parsing without file"""
    rv = client.post('/invoices/parse')
    assert rv.status_code == 400
    assert b'file required' in rv.data

def test_parse_invoice_empty_filename(client):
    """Test invoice parsing with empty filename"""
    data = {'file': (io.BytesIO(b''), '')}
    rv = client.post('/invoices/parse', data=data, content_type='multipart/form-data')
    assert rv.status_code == 400

def test_parse_invoice_invalid_type(client):
    """Test invoice parsing with invalid file type"""
    data = {'file': (io.BytesIO(b'test'), 'test.txt')}
    rv = client.post('/invoices/parse', data=data, content_type='multipart/form-data')
    assert rv.status_code == 400

def test_get_invoice_not_found(client):
    """Test getting non-existent invoice"""
    rv = client.get('/invoices/nonexistent')
    assert rv.status_code == 404

def test_health_check(client):
    """Test health check endpoint"""
    rv = client.get('/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'status' in data
    assert data['status'] == 'healthy'
'@
$testInvoices | Out-File -FilePath "tests/test_invoices.py" -Encoding UTF8

# tests/test_risk.py
$testRisk = @'
import pytest
from app.finsy_service import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_risk_score_no_body(client):
    """Test risk scoring without invoice data"""
    rv = client.post('/risk/score')
    assert rv.status_code == 400

def test_risk_score_low_risk(client):
    """Test low risk invoice"""
    invoice = {
        "invoice_id": "test123",
        "vendor": "Safe Vendor",
        "total": 5000,
        "po_number": "PO-123"
    }
    rv = client.post('/risk/score', json=invoice)
    assert rv.status_code == 200
    result = rv.get_json()
    assert result['level'] == 'low'
    assert result['suggest_action'] == 'auto-approve'

def test_risk_score_medium_risk(client):
    """Test medium risk invoice"""
    invoice = {
        "invoice_id": "test456",
        "vendor": "Regular Vendor",
        "total": 45000,
        "po_number": "PO-456"
    }
    rv = client.post('/risk/score', json=invoice)
    assert rv.status_code == 200
    result = rv.get_json()
    assert result['level'] in ['low', 'medium']

def test_risk_score_high_risk(client):
    """Test high risk invoice"""
    invoice = {
        "invoice_id": "test789",
        "vendor": "suspicious vendor",
        "total": 100000,
        "po_number": None
    }
    rv = client.post('/risk/score', json=invoice)
    assert rv.status_code == 200
    result = rv.get_json()
    assert result['level'] == 'high'
    assert result['suggest_action'] == 'route-for-review'
    assert len(result['reasons']) > 0
'@
$testRisk | Out-File -FilePath "tests/test_risk.py" -Encoding UTF8

# tests/test_approvals.py
$testApprovals = @'
import pytest
from app.finsy_service import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_approval_no_body(client):
    """Test creating approval without body"""
    rv = client.post('/approvals/create')
    assert rv.status_code == 400

def test_create_approval_success(client):
    """Test successful approval creation"""
    approval_data = {
        "invoice_id": "inv123",
        "requester": "finance@test.com",
        "approver": "manager@test.com",
        "reason": "High value invoice"
    }
    rv = client.post('/approvals/create', json=approval_data)
    assert rv.status_code == 200
    result = rv.get_json()
    assert 'approval_id' in result
    assert result['status'] == 'pending'

def test_approval_action_invalid(client):
    """Test invalid approval action"""
    rv = client.post('/approvals/test123/action', json={"action": "invalid"})
    assert rv.status_code == 400

def test_approval_not_found(client):
    """Test getting non-existent approval"""
    rv = client.get('/approvals/nonexistent')
    assert rv.status_code == 404
'@
$testApprovals | Out-File -FilePath "tests/test_approvals.py" -Encoding UTF8

# tests/test_utils.py
$testUtils = @'
import pytest
import tempfile
import os
from app.utils import (
    init_db, save_invoice_record, get_invoice,
    save_approval, get_approval, update_approval,
    summary_report
)

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)

def test_init_db(temp_db):
    """Test database initialization"""
    assert os.path.exists(temp_db)

def test_save_and_get_invoice(temp_db):
    """Test saving and retrieving invoice"""
    invoice = {
        "invoice_id": "test123",
        "vendor": "Test Vendor",
        "date": "2024-01-01",
        "total": 1000.0,
        "currency": "USD",
        "po_number": "PO-123",
        "confidence": 0.95
    }
    save_invoice_record(temp_db, invoice)
    retrieved = get_invoice(temp_db, "test123")
    assert retrieved is not None
    assert retrieved['vendor'] == "Test Vendor"

def test_get_nonexistent_invoice(temp_db):
    """Test retrieving non-existent invoice"""
    result = get_invoice(temp_db, "nonexistent")
    assert result is None

def test_approval_workflow(temp_db):
    """Test complete approval workflow"""
    # Save invoice first
    invoice = {
        "invoice_id": "inv123",
        "vendor": "Test Vendor",
        "total": 5000.0
    }
    save_invoice_record(temp_db, invoice)
    
    # Create approval
    approval = {
        "approval_id": "app123",
        "invoice_id": "inv123",
        "requester": "user@test.com",
        "approver": "manager@test.com",
        "reason": "Test",
        "status": "pending"
    }
    save_approval(temp_db, approval)
    
    # Get approval
    retrieved = get_approval(temp_db, "app123")
    assert retrieved is not None
    assert retrieved['status'] == 'pending'
    
    # Update approval
    updated = update_approval(temp_db, "app123", "approve", "Looks good")
    assert updated['status'] == 'approved'
    assert updated['comment'] == 'Looks good'

def test_summary_report(temp_db):
    """Test summary report generation"""
    report = summary_report(temp_db)
    assert 'total_invoices' in report
    assert 'approved_approvals' in report
    assert 'pending_approvals' in report
'@
$testUtils | Out-File -FilePath "tests/test_utils.py" -Encoding UTF8

Write-Host "[OK] Test files created" -ForegroundColor Green

###############################################################################
# Create GitHub Actions CI workflow
###############################################################################

Write-Host "Creating GitHub Actions workflow..." -ForegroundColor Blue

$ciWorkflow = @'
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
    
    - name: Test with pytest
      run: |
        pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t finsy:latest .
    
    - name: Test Docker image
      run: |
        docker run -d -p 5000:5000 --name finsy-test finsy:latest
        sleep 10
        curl -f http://localhost:5000/health || exit 1
        docker stop finsy-test
'@
$ciWorkflow | Out-File -FilePath ".github/workflows/ci.yml" -Encoding UTF8

Write-Host "[OK] GitHub Actions workflow created" -ForegroundColor Green

###############################################################################
# Create LICENSE
###############################################################################

Write-Host "Creating LICENSE..." -ForegroundColor Blue

$license = @'
MIT License

Copyright (c) 2024 Finsy Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'@
$license | Out-File -FilePath "LICENSE" -Encoding UTF8

Write-Host "[OK] LICENSE created" -ForegroundColor Green

###############################################################################
# Create CHANGELOG.md
###############################################################################

Write-Host "Creating CHANGELOG.md..." -ForegroundColor Blue

$changelog = @'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-23

### Added
- Invoice parsing endpoint with OCR support
- Risk scoring with hybrid rule-based and ML model
- Approval workflow with human-in-the-loop
- Summary reporting endpoint
- Health check endpoint
- Docker and Docker Compose support
- Comprehensive test suite
- CI/CD with GitHub Actions
- SQLite database with proper indexing
- Structured logging
- File upload validation

### Fixed
- Model loading to handle both model and scaler
- Feature scaling in risk scoring
- HTML form replaced with JavaScript fetch API
- Database connection management with context managers

### Security
- Input validation for file uploads
- Parameterized SQL queries
- CORS configuration

## [Unreleased]

### Planned
- Integration with real OCR services (Document AI, Textract)
- Slack/Teams notification support
- Authentication and authorization
- Rate limiting
- PostgreSQL support
- Redis caching
- Message queue integration
'@
$changelog | Out-File -FilePath "CHANGELOG.md" -Encoding UTF8

Write-Host "[OK] CHANGELOG.md created" -ForegroundColor Green

###############################################################################
# Create documentation files
###############################################################################

Write-Host "Creating documentation files..." -ForegroundColor Blue

# docs/api.md
$apiDoc = @'
# API Documentation

## Base URL
```
http://localhost:5000
```

## Endpoints

### Health Check
- **GET** `/health`
- Returns service health status

### Invoice Parsing
- **POST** `/invoices/parse`
- Upload and parse invoice files

### Risk Scoring
- **POST** `/risk/score`
- Calculate risk score for invoices

### Approvals
- **POST** `/approvals/create`
- **GET** `/approvals/{id}`
- **POST** `/approvals/{id}/action`

### Reporting
- **GET** `/reports/summary`
- Generate summary reports

See README.md for detailed examples.
'@
$apiDoc | Out-File -FilePath "docs/api.md" -Encoding UTF8

# docs/architecture.md
$archDoc = @'
# Architecture

## System Components

1. **Flask API Server**
   - RESTful endpoints
   - Request validation
   - Error handling

2. **Database Layer**
   - SQLite for development
   - PostgreSQL recommended for production

3. **ML Model**
   - Logistic regression
   - Risk scoring

4. **Approval Workflow**
   - Human-in-the-loop
   - Web UI for approvals

## Data Flow

1. Invoice Upload -> Parsing -> Storage
2. Risk Scoring -> Decision
3. High Risk -> Approval Workflow
4. Low Risk -> Auto-approve
5. Reporting & Analytics
'@
$archDoc | Out-File -FilePath "docs/architecture.md" -Encoding UTF8

# docs/deployment.md
$deployDoc = @'
# Deployment Guide

## Docker Deployment

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

- `FINSY_DB`: Database path
- `RISK_MODEL`: Model file path
- `FLASK_ENV`: Environment (production/development)
- `PORT`: Service port

## Production Checklist

- [ ] Use PostgreSQL
- [ ] Enable HTTPS
- [ ] Add authentication
- [ ] Configure rate limiting
- [ ] Set up monitoring
- [ ] Configure backups
'@
$deployDoc | Out-File -FilePath "docs/deployment.md" -Encoding UTF8

Write-Host "[OK] Documentation files created" -ForegroundColor Green

###############################################################################
# Create .env.example
###############################################################################

Write-Host "Creating .env.example..." -ForegroundColor Blue

$envExample = @'
# Finsy Configuration

# Database
FINSY_DB=app/db/finsy.db

# ML Model
RISK_MODEL=app/models/risk_model.pkl

# Flask
FLASK_ENV=development
PORT=5000

# Add your configuration here
'@
$envExample | Out-File -FilePath ".env.example" -Encoding UTF8

Write-Host "[OK] .env.example created" -ForegroundColor Green

###############################################################################
# Create placeholder file for existing files note
###############################################################################

Write-Host "Creating notes for existing files..." -ForegroundColor Blue

$copyFiles = @'
# Files to Copy

Please copy the following files from your existing project or artifacts:

## Required Files (from artifacts)
- [ ] `app/finsy_service.py` - Main Flask application (FIXED version)
- [ ] `app/utils.py` - Database utilities (FIXED version)
- [ ] `app/templates/approval_card.html` - Approval UI (FIXED version)
- [ ] `README.md` - Project README

## Required Files (from your original project)
- [ ] `app/train_risk_model.py` - ML model training script
- [ ] `Dockerfile` - Docker configuration
- [ ] `docker-compose.yml` - Docker Compose configuration
- [ ] `requirements.txt` - Python dependencies

## Optional Files (OpenAPI specs)
- [ ] `openapi/openapi_invoice_skill.yaml`
- [ ] `openapi/openapi_risk_skill.yaml`
- [ ] `openapi/openapi_approval_skill.yaml`
- [ ] `openapi/openapi_reporting_skill.yaml`

## After copying files:
1. Train the model: `python app/train_risk_model.py`
2. Run tests: `pytest tests/ -v`
3. Start the service: `docker-compose up`
'@
$copyFiles | Out-File -FilePath "COPY_THESE_FILES.md" -Encoding UTF8

Write-Host "[OK] COPY_THESE_FILES.md created" -ForegroundColor Green

###############################################################################
# Initialize git repository
###############################################################################

Write-Host "Initializing git repository..." -ForegroundColor Blue

git init 2>$null
if ($LASTEXITCODE -eq 0) {
    git add .
    git commit -m "Initial commit: Project structure setup" 2>$null
    Write-Host "[OK] Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "[SKIP] Git not available or already initialized" -ForegroundColor Yellow
}

###############################################################################
# Summary
###############################################################################

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "[OK] Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project created at: $PROJECT_ROOT" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Copy the required files (see COPY_THESE_FILES.md)"
Write-Host "2. Install dependencies: pip install -r requirements.txt"
Write-Host "3. Train the model: python app/train_risk_model.py"
Write-Host "4. Run tests: pytest tests/ -v"
Write-Host "5. Start the service: docker-compose up"
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Blue
Write-Host "  cd $PROJECT_NAME"
Write-Host "  python app/train_risk_model.py"
Write-Host "  docker-compose up"
Write-Host ""
Write-Host "Happy coding!" -ForegroundColor Magenta
Write-Host ""