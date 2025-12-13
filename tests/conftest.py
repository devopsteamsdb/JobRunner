import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db as _db

@pytest.fixture
def app():
    """Create application for the tests."""
    import tempfile
    
    if os.environ.get('TEST_IN_PRODUCTION'):
        # Use development config (main DB)
        app = create_app('development', cleanup_scheduler=False)
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False
        })
        
        with app.app_context():
            # Create tables if they don't exist (safe)
            _db.create_all()
            yield app
            _db.session.remove()
            # DO NOT drop tables
    else:
        # Use temporary isolated DB
        db_fd, db_path = tempfile.mkstemp()
        
        app = create_app('testing', cleanup_scheduler=False)
        app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'WTF_CSRF_ENABLED': False
        })
    
        with app.app_context():
            _db.create_all()
            yield app
            _db.session.remove()
            _db.drop_all()
        
        os.close(db_fd)
        os.unlink(db_path)

@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()
