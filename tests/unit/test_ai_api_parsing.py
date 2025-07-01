"""Unit tests for AI API data parsing edge cases."""

import pytest
import json
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import create_app
from models import User


class TestAIConversationAPIDataParsing:
    """Test cases for ai_conversation_api data parsing edge cases."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def mock_user(self, app):
        """Create mock authenticated user."""
        with app.app_context():
            user = MagicMock(spec=User)
            user.id = 1
            user.username = 'testuser'
            user.is_authenticated = True
            return user
    
    @pytest.fixture
    def authenticated_client(self, client, mock_user):
        """Create authenticated test client."""
        with patch('flask_login.current_user', mock_user):
            with patch('flask_login.utils._get_user', return_value=mock_user):
                yield client

    def test_empty_request_body(self, authenticated_client):
        """Test API with completely empty request body."""
        response = authenticated_client.post('/ai/api/conversation')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No data provided' in data['error']

    def test_invalid_json(self, authenticated_client):
        """Test API with malformed JSON."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            data='{"invalid": json}',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_wrong_content_type(self, authenticated_client):
        """Test API with wrong Content-Type header."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            data='{"entries": [], "question": "test"}',
            content_type='text/plain'
        )
        assert response.status_code == 400

    def test_missing_entries_field(self, authenticated_client):
        """Test API with missing entries field."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"question": "What's my mood?"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No entries provided' in data['error']

    def test_missing_question_field(self, authenticated_client):
        """Test API with missing question field."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"entries": [{"content": "test", "timestamp": "2023-01-01"}]}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No question provided' in data['error']

    def test_empty_entries_array(self, authenticated_client):
        """Test API with empty entries array."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"entries": [], "question": "What's my mood?"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No entries provided' in data['error']

    def test_empty_question_string(self, authenticated_client):
        """Test API with empty question string."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"entries": [{"content": "test", "timestamp": "2023-01-01"}], "question": ""}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No question provided' in data['error']

    def test_entries_not_array(self, authenticated_client):
        """Test API with entries field that's not an array."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"entries": "not an array", "question": "What's my mood?"}
        )
        # Should be handled gracefully - empty check on non-array
        assert response.status_code == 400

    def test_question_not_string(self, authenticated_client):
        """Test API with question field that's not a string."""
        response = authenticated_client.post(
            '/ai/api/conversation',
            json={"entries": [{"content": "test", "timestamp": "2023-01-01"}], "question": 123}
        )
        # Should be handled - empty check on non-string
        assert response.status_code == 400

    def test_entry_missing_content(self, authenticated_client):
        """Test API with entry missing content field."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', return_value='Mock response'):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{"timestamp": "2023-01-01"}],
                        "question": "What's my mood?"
                    }
                )
                # Should pass to AI processing which may handle missing content
                assert response.status_code in [200, 500]

    def test_entry_missing_timestamp(self, authenticated_client):
        """Test API with entry missing timestamp field."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', return_value='Mock response'):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{"content": "test content"}],
                        "question": "What's my mood?"
                    }
                )
                # Should pass to AI processing which may handle missing timestamp
                assert response.status_code in [200, 500]

    def test_extra_top_level_fields(self, authenticated_client):
        """Test API with unexpected top-level fields."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', return_value='Mock response'):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{"content": "test", "timestamp": "2023-01-01"}],
                        "question": "What's my mood?",
                        "unexpected_field": "should be ignored"
                    }
                )
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True

    def test_entry_with_extra_fields(self, authenticated_client):
        """Test API with entries containing unexpected fields."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', return_value='Mock response'):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{
                            "content": "test",
                            "timestamp": "2023-01-01",
                            "extra_field": "should be ignored"
                        }],
                        "question": "What's my mood?"
                    }
                )
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True

    def test_demo_mode_response(self, authenticated_client):
        """Test API response when GEMINI_API_KEY is not set (demo mode)."""
        with patch('os.getenv', return_value=None):
            response = authenticated_client.post(
                '/ai/api/conversation',
                json={
                    "entries": [{"content": "test", "timestamp": "2023-01-01"}],
                    "question": "What's my mood?"
                }
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['demo_mode'] is True
            assert 'demo mode' in data['response']

    def test_ai_processing_exception(self, authenticated_client):
        """Test API handling when AI processing raises exception."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', side_effect=Exception('AI processing failed')):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{"content": "test", "timestamp": "2023-01-01"}],
                        "question": "What's my mood?"
                    }
                )
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'error' in data
                assert 'AI processing failed' in data['error']

    def test_unicode_encoding(self, authenticated_client):
        """Test API with unicode characters in content."""
        with patch('os.getenv', return_value='mock_api_key'):
            with patch('ai_utils.get_ai_response', return_value='Mock response'):
                response = authenticated_client.post(
                    '/ai/api/conversation',
                    json={
                        "entries": [{"content": "Test with emoji 😊 and unicode åäö", "timestamp": "2023-01-01"}],
                        "question": "How do I feel about åäö characters?"
                    }
                )
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True