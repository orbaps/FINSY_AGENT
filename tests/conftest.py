import pytest
import os
import tempfile
from app.finsy_service import app
from app.utils import init_db
from app.auth import generate_token

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['FINSY_DB'] = db_path
    app.config['ENABLE_AUTH'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    
    # Initialize DB
    init_db(db_path)
    
    # Patch Config
    from app.config import Config
    Config.JWT_SECRET_KEY = 'test-secret'
    Config.ENABLE_AUTH = True
    Config.FINSY_DB = db_path
    
    with app.test_client() as client:
        yield client
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def auth_headers():
    token = generate_token("test-user", roles=["admin", "approver"])
    return {"Authorization": f"Bearer {token}"}
