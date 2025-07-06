"""
Tests for security module to prevent false positives on legitimate data.

These tests ensure that legitimate form data (like JSON emotion arrays)
doesn't get blocked by security validation.
"""
import pytest
import json
from flask import Flask
from unittest.mock import patch, MagicMock
from security import monitor_suspicious_activity


class TestSecurityValidation:
    """Test security validation doesn't block legitimate data."""
    
    def setup_method(self):
        """Set up test app and mock request."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    @pytest.fixture
    def mock_request_with_emotions(self):
        """Mock request with legitimate emotion data."""
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.remote_addr = '127.0.0.1'
        mock_request.args.items.return_value = []
        mock_request.endpoint = 'test.endpoint'  # Add endpoint to pass context check
        
        # Legitimate emotion data that was previously blocked
        emotion_data = json.dumps(["Happy", "Excited", "Grateful"])
        mock_request.form.items.return_value = [
            ('question_additional_emotions', emotion_data),
            ('question_feeling_scale', '8'),
            ('question_feeling_reason', 'Had a great day at work'),
            ('new_tags', '[]'),
            ('_csrf_token', 'valid_token_here')
        ]
        
        return mock_request
    
    @pytest.fixture
    def mock_request_with_malicious_data(self):
        """Mock request with actually malicious data."""
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.remote_addr = '127.0.0.1'
        mock_request.args.items.return_value = []
        mock_request.endpoint = 'test.endpoint'  # Add endpoint to pass context check
        
        # Actually malicious data that should be blocked
        # Use data that matches the regex patterns in security.py
        mock_request.form.items.return_value = [
            ('malicious_input', "1=1 OR DROP"),  # Matches SQL injection pattern
            ('other_field', '<script>alert(1)</script>'),  # Matches XSS pattern
            ('_csrf_token', 'valid_token_here')
        ]
        
        return mock_request
    
    def test_legitimate_emotion_json_allowed(self, mock_request_with_emotions):
        """Test that legitimate JSON emotion data is allowed."""
        with self.app.app_context():
            with patch('flask.request', mock_request_with_emotions):
                with patch('flask.abort') as mock_abort:
                    # This should not raise any exceptions or call abort
                    try:
                        monitor_suspicious_activity()
                        # If we get here, no exception was raised (good!)
                        mock_abort.assert_not_called()
                    except Exception as e:
                        pytest.fail(f"Legitimate emotion data was blocked: {e}")
    
    def test_legitimate_tag_json_allowed(self):
        """Test that legitimate JSON tag data is allowed."""
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.remote_addr = '127.0.0.1'
        mock_request.args.items.return_value = []
        
        # Legitimate tag data
        tag_data = json.dumps([{"name": "work", "color": "#ff0000"}])
        mock_request.form.items.return_value = [
            ('new_tags', tag_data),
            ('question_feeling_scale', '5'),
            ('_csrf_token', 'valid_token_here')
        ]
        
        with self.app.app_context():
            with patch('flask.request', mock_request):
                with patch('flask.abort') as mock_abort:
                    monitor_suspicious_activity()
                    mock_abort.assert_not_called()
    
    def test_malicious_data_blocked(self, mock_request_with_malicious_data):
        """Test that actually malicious data is still blocked."""
        with self.app.app_context():
            with patch('flask.request', mock_request_with_malicious_data):
                # Debug: print the form data being checked
                print("Form data:", list(mock_request_with_malicious_data.form.items()))
                print("Method:", mock_request_with_malicious_data.method)
                
                # Test that the function raises an abort by catching the exception
                try:
                    monitor_suspicious_activity()
                    # If we get here, no exception was raised - this means the test failed
                    assert False, "Expected monitor_suspicious_activity to raise an exception for malicious data"
                except Exception as e:
                    # This is expected for malicious data
                    print("Exception raised:", str(e))
                    assert "Malicious input detected" in str(e) or "400" in str(e)
    
    def test_complex_emotion_combinations(self):
        """Test various complex but legitimate emotion combinations."""
        legitimate_emotions = [
            '["Happy"]',
            '["Happy", "Excited", "Grateful"]',
            '["Sad", "Disappointed", "Tired"]',
            '["Happy", "Nervous", "Curious"]',  # Mixed emotions
            '[]',  # Empty selection
        ]
        
        for emotion_json in legitimate_emotions:
            mock_request = MagicMock()
            mock_request.method = 'POST'
            mock_request.remote_addr = '127.0.0.1'
            mock_request.args.items.return_value = []
            mock_request.form.items.return_value = [
                ('question_additional_emotions', emotion_json),
                ('_csrf_token', 'valid_token_here')
            ]
            
            with self.app.app_context():
                with patch('flask.request', mock_request):
                    with patch('flask.abort') as mock_abort:
                        monitor_suspicious_activity()
                        mock_abort.assert_not_called(), f"Legitimate emotion data blocked: {emotion_json}"
    
    def test_password_fields_skipped(self):
        """Test that password fields are properly skipped from validation."""
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.remote_addr = '127.0.0.1'
        mock_request.args.items.return_value = []
        
        # Password fields with characters that might trigger false positives
        mock_request.form.items.return_value = [
            ('password', "P@ssw0rd'with\"quotes"),
            ('new_password', "SELECT * FROM secure;"),
            ('confirm_password', "<script>alert('test')</script>"),
            ('current_password', "'; DROP TABLE users; --"),
            ('username', 'testuser'),
            ('_csrf_token', 'valid_token_here')
        ]
        
        with self.app.app_context():
            with patch('flask.request', mock_request):
                with patch('flask.abort') as mock_abort:
                    monitor_suspicious_activity()
                    # Should not block despite suspicious content in password fields
                    mock_abort.assert_not_called()
    
    def test_content_fields_allow_html(self):
        """Test that content fields allow legitimate HTML."""
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.remote_addr = '127.0.0.1'
        mock_request.args.items.return_value = []
        
        # Content with legitimate HTML
        mock_request.form.items.return_value = [
            ('content', '<p>This is <strong>bold</strong> text with <em>emphasis</em>.</p>'),
            ('response', '<ul><li>Item 1</li><li>Item 2</li></ul>'),
            ('_csrf_token', 'valid_token_here')
        ]
        
        with self.app.app_context():
            with patch('flask.request', mock_request):
                with patch('flask.abort') as mock_abort:
                    monitor_suspicious_activity()
                    mock_abort.assert_not_called()


class TestEmotionDataValidation:
    """Specific tests for emotion data that was causing issues."""
    
    def test_real_world_emotion_combinations(self):
        """Test actual emotion combinations that users might select."""
        real_combinations = [
            ["Happy", "Excited", "Grateful"],
            ["Inspired", "Passionate", "Exhausted"],  # This combination was blocked before
            ["Sad", "Disappointed", "Hopeful"],
            ["Anxious", "Determined", "Curious"],
            ["Peaceful", "Content", "Reflective"],
            ["Frustrated", "Motivated", "Focused"],
        ]
        
        for emotions in real_combinations:
            emotion_json = json.dumps(emotions)
            
            mock_request = MagicMock()
            mock_request.method = 'POST'
            mock_request.remote_addr = '127.0.0.1'
            mock_request.args.items.return_value = []
            mock_request.form.items.return_value = [
                ('question_additional_emotions', emotion_json),
                ('question_feeling_scale', '7'),
                ('_csrf_token', 'valid_token_here')
            ]
            
            app = Flask(__name__)
            with app.app_context():
                with patch('flask.request', mock_request):
                    with patch('flask.abort') as mock_abort:
                        monitor_suspicious_activity()
                        mock_abort.assert_not_called(), f"Real emotion combination blocked: {emotions}"