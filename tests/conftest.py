"""
Test configuration and fixtures for journal application.

This module provides pytest fixtures and configuration for all tests.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from flask import url_for, current_app
from werkzeug.security import generate_password_hash
from sqlalchemy import event

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
    """Test configuration class with PostgreSQL support."""
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier testing
    SECRET_KEY = 'test-secret-key-for-testing-only'
    SECURITY_PASSWORD_SALT = 'test-salt-for-testing-only'
    
    # PostgreSQL configuration for testing
    # Use environment variables if available, fallback to production values
    USE_POSTGRESQL = True
    DB_USER = os.environ.get('TEST_DB_USER', 'journal_user')
    DB_PASSWORD = os.environ.get('TEST_DB_PASSWORD', 'eNP*h^S%1U@KteLeOnFfFfwu')
    DB_HOST = os.environ.get('TEST_DB_HOST', 'localhost')
    DB_PORT = os.environ.get('TEST_DB_PORT', '5432')
    DB_NAME = os.environ.get('TEST_DB_NAME', 'journal_db')  # Same DB, transaction isolated
    
    from urllib.parse import quote_plus
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    
    # Additional PostgreSQL-specific test configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
        'isolation_level': 'READ_COMMITTED'  # Proper isolation for tests
    }
    
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
    
    # For PostgreSQL, don't drop all tables - just clean up test data
    # This avoids foreign key constraint issues
    try:
        # Try to drop all tables if possible
        db.drop_all()
    except Exception as e:
        # If dropping tables fails (common with PostgreSQL constraints), 
        # just clear the session and move on
        current_app.logger.debug(f"Could not drop all tables during test cleanup: {e}")
        db.session.rollback()
    
    ctx.pop()


@pytest.fixture(scope='function')
def client(app):
    """Create test client with proper Flask context."""
    with app.app_context():
        with app.test_request_context():
            yield app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function', autouse=True)
def db_session(app):
    """Create database session for testing with proper transaction isolation."""
    from models import db
    
    # Remove any existing sessions to prevent configuration conflicts
    db.session.remove()
    
    # For PostgreSQL, use savepoints for nested transaction isolation
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Create a savepoint for nested rollback capability
    savepoint = connection.begin_nested()
    
    # Configure session to use our connection with transaction
    db.session.configure(bind=connection, binds={})
    
    # Listen for session commit events and convert to savepoint releases
    @event.listens_for(db.session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction.is_active:
            # Create new savepoint to replace the one just released
            connection.begin_nested()
    
    yield db.session
    
    # Clean up after test - rollback all changes
    try:
        # Remove event listener to prevent memory leaks
        event.remove(db.session, 'after_transaction_end', restart_savepoint)
        
        # Force rollback of any pending changes
        db.session.rollback()
        db.session.close()
        db.session.remove()
        
        # Rollback the savepoint and main transaction
        if savepoint.is_active:
            savepoint.rollback()
        if transaction.is_active:
            transaction.rollback()
    except Exception as e:
        # Log any cleanup errors but don't fail the test
        print(f"Warning: Database cleanup error: {e}")
    finally:
        try:
            connection.close()
        except Exception:
            pass


@pytest.fixture
def user_data():
    """Sample user data for testing."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        'username': f'testuser_{unique_id}',
        'email': f'test_{unique_id}@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'timezone': 'UTC'
    }


@pytest.fixture
def user_data_no_email():
    """Sample user data without email for testing."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        'username': f'testuser_no_email_{unique_id}',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'timezone': 'UTC'
    }


@pytest.fixture
def user(app, db_session):
    """Create a test user."""
    from models import User
    import uuid
    
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f'testuser_{unique_id}',
        email=f'test_{unique_id}@example.com',
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
    import uuid
    
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f'testuser_no_email_{unique_id}',
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
    import uuid
    
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f'mfa_user_{unique_id}',
        email=f'mfa_{unique_id}@example.com',
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


# Standard Mock Fixtures for Consistent Testing

@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock all external services for every test."""
    with patch('email_utils.send_password_reset_email') as mock_reset, \
         patch('email_utils.send_email_change_confirmation') as mock_change, \
         patch('services.weather_service.weather_service') as mock_weather, \
         patch('services.weather_service.requests.get') as mock_requests, \
         patch('email_utils.send_email') as mock_send_email:
        
        # Configure default return values
        mock_reset.return_value = True  
        mock_change.return_value = True
        mock_send_email.return_value = True
        
        # Mock weather service
        mock_weather.get_weather.return_value = {
            'temperature': 72,
            'condition': 'sunny',
            'description': 'Clear skies'
        }
        mock_weather.geocode_location.return_value = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'city': 'New York',
            'country': 'US'
        }
        
        # Mock requests for external APIs
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        
        yield {
            'email_reset': mock_reset,
            'email_change': mock_change,
            'weather': mock_weather,
            'requests': mock_requests,
            'send_email': mock_send_email
        }

@pytest.fixture
def mock_mail():
    """Mock Flask-Mail for email testing."""
    with patch('routes.mail') as mock:
        mock.send.return_value = None
        yield mock

@pytest.fixture  
def mock_email_service():
    """Mock email service functions."""
    with patch('email_service.send_verification_email') as mock_verify, \
         patch('email_service.send_password_reset_email') as mock_reset, \
         patch('email_service.send_email_change_confirmation') as mock_change:
        mock_verify.return_value = True
        mock_reset.return_value = True  
        mock_change.return_value = True
        yield {
            'verify': mock_verify,
            'reset': mock_reset,
            'change': mock_change
        }

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    with patch('ai_service.generate_response') as mock_ai:
        mock_ai.return_value = "This is a test AI response."
        yield mock_ai

@pytest.fixture
def mock_weather_service():
    """Mock weather service for testing."""
    with patch('weather_service.get_weather') as mock_weather:
        mock_weather.return_value = {
            'temperature': 72,
            'condition': 'sunny',
            'description': 'Clear skies'
        }
        yield mock_weather

@pytest.fixture
def mock_geocoding_service():
    """Mock geocoding service for testing.""" 
    with patch('routes.geocode_location') as mock_geocode:
        mock_geocode.return_value = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'city': 'New York',
            'country': 'US'
        }
        yield mock_geocode


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


# Template-related fixtures for testing template functionality

@pytest.fixture
def custom_template(app, db_session, user):
    """Create a custom journal template for testing."""
    from models import JournalTemplate
    
    template = JournalTemplate(
        name='Test Custom Template',
        description='A template for testing purposes',
        user_id=user.id,
        is_system=False
    )
    db_session.add(template)
    db_session.commit()
    return template


@pytest.fixture
def system_template(app, db_session):
    """Create a system template for testing."""
    from models import JournalTemplate
    
    template = JournalTemplate(
        name='Test System Template',
        description='A system template for testing',
        user_id=None,
        is_system=True
    )
    db_session.add(template)
    db_session.commit()
    return template


@pytest.fixture
def template_question(app, db_session, custom_template):
    """Create a template question for testing."""
    from models import TemplateQuestion
    
    question = TemplateQuestion(
        template_id=custom_template.id,
        question_id='daily_question_1',
        question_text='How was your day?',
        question_type='text',
        question_order=1,
        required=True
    )
    db_session.add(question)
    db_session.commit()
    return question


@pytest.fixture
def custom_template_with_questions(app, db_session, user):
    """Create a custom template with multiple questions for testing."""
    from models import JournalTemplate, TemplateQuestion
    
    template = JournalTemplate(
        name='Template with Questions',
        description='A template with multiple question types',
        user_id=user.id,
        is_system=False
    )
    db_session.add(template)
    db_session.flush()  # Get ID without committing
    
    # Add various question types
    questions = [
        TemplateQuestion(
            template_id=template.id,
            question_id='day_rating',
            question_text='How would you rate your day?',
            question_type='number',
            question_order=1,
            required=True,
            properties='{"min": 1, "max": 10}'
        ),
        TemplateQuestion(
            template_id=template.id,
            question_id='day_highlight',
            question_text='What was the highlight of your day?',
            question_type='text',
            question_order=2,
            required=False
        ),
        TemplateQuestion(
            template_id=template.id,
            question_id='exercise_today',
            question_text='Did you exercise today?',
            question_type='boolean',
            question_order=3,
            required=True
        ),
        TemplateQuestion(
            template_id=template.id,
            question_id='feeling_emotions',
            question_text='How are you feeling?',
            question_type='emotions',
            question_order=4,
            required=False
        )
    ]
    
    for question in questions:
        db_session.add(question)
    
    db_session.commit()
    return template


@pytest.fixture
def template_journal_entry(app, db_session, user, custom_template_with_questions):
    """Create a journal entry created with a template."""
    from models import JournalEntry, GuidedResponse, TemplateQuestion
    
    # Create the journal entry
    entry = JournalEntry(
        user_id=user.id,
        content='Template-based guided journal entry',
        entry_type='guided',
        template_id=custom_template_with_questions.id
    )
    db_session.add(entry)
    db_session.flush()  # Get ID without committing
    
    # Get template questions and create responses
    questions = TemplateQuestion.query.filter_by(
        template_id=custom_template_with_questions.id
    ).order_by(TemplateQuestion.question_order).all()
    
    for question in questions:
        # Create appropriate response based on question type
        if question.question_type == 'number':
            response_text = '8'
        elif question.question_type == 'text':
            response_text = f'Test response to: {question.question_text}'
        elif question.question_type == 'boolean':
            response_text = 'Yes'
        elif question.question_type == 'emotions':
            response_text = '["happy", "content"]'
        else:
            response_text = 'Test response'
        
        guided_response = GuidedResponse(
            journal_entry_id=entry.id,
            question_id=str(question.id),
            question_text=question.question_text,  # Store the question text
            response=response_text
        )
        db_session.add(guided_response)
    
    db_session.commit()
    return entry


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