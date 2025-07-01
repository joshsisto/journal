"""
Test configuration and fixtures for journal application.

This module provides pytest fixtures and configuration for all tests.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from flask import url_for
from werkzeug.security import generate_password_hash

# Set environment variables before importing app
os.environ['TESTING'] = 'True'
os.environ['WTF_CSRF_ENABLED'] = 'False'  # Disable CSRF for testing
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['MAIL_SUPPRESS_SEND'] = '1'
os.environ['GEMINI_API_KEY'] = 'test-api-key-for-testing'

# Import will be done in fixtures to avoid circular imports
# from app import create_app  # Moved to fixture
# from models import db, User, JournalEntry, GuidedResponse, Tag, Photo  # Moved to fixture
from config import Config


class TestConfig(Config):
    """Test configuration class."""
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier testing
    SECRET_KEY = 'test-secret-key-for-testing-only'
    SECURITY_PASSWORD_SALT = 'test-salt-for-testing-only'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MAIL_SUPPRESS_SEND = True
    GEMINI_API_KEY = 'test-api-key-for-testing'
    UPLOAD_FOLDER = tempfile.mkdtemp()
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    LOGIN_DISABLED = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RATELIMIT_ENABLED = False  # Disable rate limiting for testing
    TALISMAN_ENABLED = False  # Disable Talisman for testing
    

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    # Import app creation function
    from app import create_app
    
    app = create_app(TestConfig)
    
    # Push application context
    ctx = app.app_context()
    ctx.push()
    
    # Create all database tables
    from models import db
    db.create_all()
    
    yield app
    
    # Clean up
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    from models import db
    
    yield db.session
    
    # Clean up after test
    db.session.rollback()


@pytest.fixture
def user_data():
    """Sample user data for testing."""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'timezone': 'UTC'
    }


@pytest.fixture
def user_data_no_email():
    """Sample user data without email for testing."""
    return {
        'username': 'testuser_no_email',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'timezone': 'UTC'
    }


@pytest.fixture
def user(app, db_session):
    """Create a test user."""
    from models import User
    
    user = User(
        username='testuser',
        email='test@example.com',
        timezone='UTC'
    )
    user.set_password('TestPassword123!')
    user.is_email_verified = True
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def user_no_email(app, db_session):
    """Create a test user without email."""
    from models import User
    
    user = User(
        username='testuser_no_email',
        timezone='UTC'
    )
    user.set_password('TestPassword123!')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def user_with_mfa(app, db_session):
    """Create a test user with MFA enabled."""
    from models import User
    
    user = User(
        username='mfa_user',
        email='mfa@example.com',
        timezone='UTC',
        two_factor_enabled=True
    )
    user.set_password('TestPassword123!')
    user.is_email_verified = True
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def logged_in_user(client, user):
    """Log in a test user and return the client."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def journal_entry_data():
    """Sample journal entry data."""
    return {
        'content': 'This is a test journal entry with some thoughts about the day.',
        'tags': [],
        'new_tags': '[]'
    }


@pytest.fixture
def guided_entry_data():
    """Sample guided journal entry data."""
    return {
        'feeling_scale': '7',
        'feeling_reason': 'Had a good day at work',
        'additional_emotions': '["happy", "accomplished"]',
        'grateful_for': 'My family and friends',
        'challenge_overcome': 'Completed a difficult project',
        'tomorrow_goal': 'Start learning something new',
        'tags': [],
        'new_tags': '[]'
    }


@pytest.fixture
def journal_entry(app, db_session, user):
    """Create a test journal entry."""
    from models import JournalEntry
    
    entry = JournalEntry(
        user_id=user.id,
        content='Test journal entry content',
        entry_type='quick'
    )
    db_session.add(entry)
    db_session.commit()
    return entry


@pytest.fixture
def guided_journal_entry(app, db_session, user):
    """Create a test guided journal entry."""
    from models import JournalEntry, GuidedResponse
    
    entry = JournalEntry(
        user_id=user.id,
        content='Guided journal entry',
        entry_type='guided'
    )
    db_session.add(entry)
    db_session.flush()  # Get the ID
    
    # Add guided responses
    responses = [
        GuidedResponse(journal_entry_id=entry.id, question_id='feeling_scale', response='8'),
        GuidedResponse(journal_entry_id=entry.id, question_id='feeling_reason', response='Great day'),
        GuidedResponse(journal_entry_id=entry.id, question_id='additional_emotions', response='["happy", "grateful"]')
    ]
    for response in responses:
        db_session.add(response)
    
    db_session.commit()
    return entry


@pytest.fixture
def tag(app, db_session, user):
    """Create a test tag."""
    from models import Tag
    
    tag = Tag(
        name='test-tag',
        color='#007bff',
        user_id=user.id
    )
    db_session.add(tag)
    db_session.commit()
    return tag


@pytest.fixture
def mock_email():
    """Mock email sending functionality."""
    with patch('email_utils.send_email') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini AI API."""
    with patch('ai_utils.get_ai_response') as mock:
        mock.return_value = "This is a mocked AI response for testing purposes."
        yield mock


@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing."""
    from io import BytesIO
    from werkzeug.datastructures import FileStorage
    
    def create_test_file(filename='test.jpg', content=b'fake image data'):
        return FileStorage(
            stream=BytesIO(content),
            filename=filename,
            content_type='image/jpeg'
        )
    
    return create_test_file


@pytest.fixture
def csrf_token(client):
    """Get CSRF token for testing."""
    with client.session_transaction() as sess:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()


@pytest.fixture
def mock_two_factor():
    """Mock two-factor authentication functionality."""
    with patch('two_factor.send_verification_code') as send_mock, \
         patch('two_factor.verify_code') as verify_mock, \
         patch('two_factor.is_verification_required') as required_mock:
        
        send_mock.return_value = (True, "Code sent successfully")
        verify_mock.return_value = (True, "Code verified")
        required_mock.return_value = True
        
        yield {
            'send': send_mock,
            'verify': verify_mock,
            'required': required_mock
        }


# Helper functions for tests
def login_user(client, username='testuser', password='TestPassword123!'):
    """Helper function to log in a user."""
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)


def logout_user(client):
    """Helper function to log out a user."""
    return client.get('/logout', follow_redirects=True)


def create_user_via_registration(client, user_data):
    """Helper function to create user via registration."""
    return client.post('/register', data=user_data, follow_redirects=True)


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure test reports directory exists
    os.makedirs('reports', exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to test files in unit directory
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to test files in integration directory
        if 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add specific markers based on test names
        if 'auth' in item.name or 'login' in item.name or 'register' in item.name:
            item.add_marker(pytest.mark.auth)
        
        if 'email' in item.name:
            item.add_marker(pytest.mark.email)
            
        if 'mfa' in item.name or 'two_factor' in item.name:
            item.add_marker(pytest.mark.mfa)
            
        if 'journal' in item.name or 'entry' in item.name:
            item.add_marker(pytest.mark.journal)
            
        if 'ai' in item.name:
            item.add_marker(pytest.mark.ai)
            
        if 'csrf' in item.name:
            item.add_marker(pytest.mark.csrf)