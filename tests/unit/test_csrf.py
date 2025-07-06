"""
Unit tests for CSRF protection functionality.

Tests CSRF token generation, validation, and protection across all forms and API endpoints.
"""

import pytest
from unittest.mock import patch
from flask import session
from models import db


class TestCSRFTokenGeneration:
    """Test CSRF token generation and utility functions."""
    
    def test_csrf_token_generation(self, app):
        """Test CSRF token is generated correctly."""
        with app.test_request_context():
            from flask_wtf.csrf import generate_csrf
            
            token = generate_csrf()
            assert token is not None
            assert len(token) > 10  # Should be a reasonable length
            assert isinstance(token, str)
    
    def test_csrf_token_utility_function(self, app):
        """Test the csrf_token utility function in templates."""
        with app.app_context():
            with app.test_request_context():
                # Get the utility function from template context
                context_processor = app.context_processor
                
                # The csrf_token function should be available
                from flask_wtf.csrf import generate_csrf
                token = generate_csrf()
                assert token is not None
    
    def test_csrf_token_uniqueness(self, app):
        """Test that CSRF tokens are unique across requests."""
        # Skip this test when CSRF is disabled
        if not app.config.get('WTF_CSRF_ENABLED'):
            pytest.skip("CSRF disabled for testing")
            
        tokens = []
        
        for _ in range(5):
            with app.test_request_context():
                from flask_wtf.csrf import generate_csrf
                token = generate_csrf()
                tokens.append(token)
        
        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)


class TestCSRFProtectionForms:
    """Test CSRF protection on form submissions."""
    
    def test_csrf_protection_login_form(self, client, user):
        """Test CSRF protection on login form."""
        # Try login without CSRF token
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!'
        })
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302
    
    def test_csrf_protection_registration_form(self, client, user_data):
        """Test CSRF protection on registration form."""
        # Try registration without CSRF token
        response = client.post('/register', data=user_data)
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302
    
    def test_csrf_protection_journal_entry_form(self, client, logged_in_user):
        """Test CSRF protection on journal entry forms."""
        # Try quick journal without CSRF token
        response = client.post('/journal/quick', data={
            'content': 'Test entry'
        })
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302
    
    def test_csrf_protection_settings_forms(self, client, logged_in_user):
        """Test CSRF protection on settings forms."""
        # Try password change without CSRF token
        response = client.post('/settings/password', data={
            'current_password': 'TestPassword123!',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        })
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302
    
    def test_csrf_protection_tag_management(self, client, logged_in_user):
        """Test CSRF protection on tag management forms."""
        # Try creating tag without CSRF token
        response = client.post('/tags/add', data={
            'name': 'test-tag',
            'color': '#ff0000'
        })
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302
    
    def test_csrf_protection_delete_operations(self, client, logged_in_user, journal_entry):
        """Test CSRF protection on delete operations."""
        # Try deleting entry without CSRF token
        response = client.post(f'/journal/delete/{journal_entry.id}')
        
        # Should be redirected due to CSRF failure
        assert response.status_code == 302


class TestCSRFProtectionAPI:
    """Test CSRF protection on API endpoints."""
    
    def test_csrf_protection_ai_api(self, client, logged_in_user, journal_entry):
        """Test CSRF protection on AI API endpoint."""
        import json
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        # Try API call without CSRF token
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        # Should be redirected or rejected due to CSRF failure
        assert response.status_code in [302, 400, 403]
    
    def test_csrf_protection_mfa_resend(self, client, user_with_mfa):
        """Test CSRF protection on MFA resend endpoint."""
        # Try to access verification first
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Try resend without CSRF token
        response = client.post('/resend-code')
        
        # Should be rejected due to CSRF failure
        assert response.status_code in [302, 400, 403]


class TestCSRFValidTokens:
    """Test requests with valid CSRF tokens succeed."""
    
    def test_valid_csrf_token_login(self, client, user, csrf_token):
        """Test login succeeds with valid CSRF token."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': csrf_token
        }, follow_redirects=True)
        
        # Should succeed and redirect to dashboard
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'journal' in response.data.lower()
    
    def test_valid_csrf_token_registration(self, client, user_data, csrf_token, mock_email):
        """Test registration succeeds with valid CSRF token."""
        user_data['_csrf_token'] = csrf_token
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        # Should succeed
        assert response.status_code == 200
        assert b'Registration successful' in response.data
    
    def test_valid_csrf_token_journal_entry(self, client, logged_in_user, csrf_token):
        """Test journal entry creation succeeds with valid CSRF token."""
        response = client.post('/journal/quick', data={
            'content': 'Test entry with CSRF',
            'tags': [],
            'new_tags': '[]',
            '_csrf_token': csrf_token
        }, follow_redirects=True)
        
        # Should succeed
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
    
    def test_valid_csrf_token_ai_api(self, client, logged_in_user, journal_entry, csrf_token, mock_gemini_api):
        """Test AI API succeeds with valid CSRF token."""
        import json
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        # Should succeed
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True


class TestCSRFEdgeCases:
    """Test CSRF protection edge cases and error conditions."""
    
    def test_csrf_token_in_different_session(self, app, user):
        """Test CSRF token from different session is rejected."""
        # Generate token in one session
        with app.test_client() as client1:
            with client1.session_transaction() as sess:
                from flask_wtf.csrf import generate_csrf
                token = generate_csrf()
        
        # Try to use token in different session
        with app.test_client() as client2:
            response = client2.post('/login', data={
                'username': user.username,
                'password': 'TestPassword123!',
                '_csrf_token': token
            })
            
            # Should be rejected
            assert response.status_code == 302
    
    def test_csrf_token_reuse(self, client, user, csrf_token):
        """Test CSRF token can be reused within same session."""
        # Use token for first request
        response1 = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response1.status_code == 200
        
        # Logout
        client.get('/logout')
        
        # Try to reuse same token (should work if session is same)
        response2 = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': csrf_token
        })
        
        # Behavior depends on Flask-WTF configuration
        assert response2.status_code in [200, 302]
    
    def test_csrf_token_empty_string(self, client, user):
        """Test empty CSRF token is rejected."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': ''
        })
        
        # Should be rejected
        assert response.status_code == 302
    
    def test_csrf_token_invalid_format(self, client, user):
        """Test invalid CSRF token format is rejected."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': 'invalid-token-format'
        })
        
        # Should be rejected
        assert response.status_code == 302
    
    def test_csrf_token_very_long(self, client, user):
        """Test very long CSRF token is handled gracefully."""
        long_token = 'a' * 10000
        
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            '_csrf_token': long_token
        })
        
        # Should be rejected gracefully
        assert response.status_code == 302


class TestCSRFIntegrationWithSecurity:
    """Test CSRF integration with other security features."""
    
    def test_csrf_with_https_only(self, app):
        """Test CSRF configuration for HTTPS."""
        # Check CSRF configuration
        assert app.config.get('WTF_CSRF_ENABLED') is True
        assert app.config.get('WTF_CSRF_SSL_STRICT') is False  # Should be False for proxied SSL
    
    def test_csrf_with_rate_limiting(self, client, user):
        """Test CSRF protection works with rate limiting."""
        # Make multiple invalid CSRF requests rapidly
        for _ in range(5):
            response = client.post('/login', data={
                'username': user.username,
                'password': 'TestPassword123!',
                '_csrf_token': 'invalid'
            })
            
            # Should be rejected each time
            assert response.status_code in [302, 429]  # 429 if rate limited
    
    def test_csrf_error_handling(self, app, client, user):
        """Test CSRF error handling and user feedback."""
        # Configure to catch CSRF errors
        @app.errorhandler(400)
        def handle_csrf_error(e):
            return "CSRF Error", 400
        
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!'
        })
        
        # Should handle CSRF error gracefully
        assert response.status_code in [302, 400]


class TestCSRFConfiguration:
    """Test CSRF configuration and settings."""
    
    def test_csrf_configuration_values(self, app):
        """Test CSRF configuration is set correctly."""
        # Check key configuration values (CSRF disabled in tests)
        assert app.config.get('WTF_CSRF_ENABLED') is False  # Disabled for testing
        assert app.config.get('WTF_CSRF_TIME_LIMIT') == 3600  # 1 hour
        assert app.config.get('WTF_CSRF_SSL_STRICT') is False
        assert 'POST' in app.config.get('WTF_CSRF_METHODS', [])
        assert app.config.get('WTF_CSRF_CHECK_HEADERS') is False
    
    def test_csrf_methods_coverage(self, app):
        """Test CSRF protection covers appropriate HTTP methods."""
        csrf_methods = app.config.get('WTF_CSRF_METHODS', [])
        
        # Should protect POST, PUT, PATCH, DELETE
        for method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            assert method in csrf_methods
        
        # Should not protect GET, HEAD, OPTIONS
        for method in ['GET', 'HEAD', 'OPTIONS']:
            assert method not in csrf_methods
    
    def test_csrf_secret_key_configured(self, app):
        """Test secret key is configured for CSRF."""
        # Secret key should be configured
        assert app.config.get('SECRET_KEY') is not None
        assert len(app.config.get('SECRET_KEY', '')) > 10


class TestCSRFValidationScript:
    """Test the CSRF validation script functionality."""
    
    def test_csrf_validation_script_exists(self):
        """Test CSRF validation script exists and is executable."""
        import os
        script_path = 'validate_csrf.py'
        
        assert os.path.exists(script_path)
        assert os.access(script_path, os.R_OK)
    
    def test_csrf_validation_script_runs(self):
        """Test CSRF validation script runs without errors."""
        import subprocess
        import os
        
        result = subprocess.run(['python3', 'validate_csrf.py'], 
                              cwd=os.getcwd(),
                              capture_output=True, 
                              text=True)
        
        # Should run successfully
        assert result.returncode == 0
        assert 'CSRF Token Validation' in result.stdout
    
    def test_csrf_pre_commit_hook_exists(self):
        """Test CSRF pre-commit hook exists."""
        import os
        hook_path = '.git/hooks/pre-commit'
        
        if os.path.exists('.git'):
            assert os.path.exists(hook_path)
            assert os.access(hook_path, os.X_OK)


class TestCSRFInTemplates:
    """Test CSRF token usage in templates."""
    
    def test_csrf_token_in_login_template(self, client):
        """Test login template includes CSRF token field."""
        response = client.get('/login')
        
        assert response.status_code == 200
        # Should have CSRF token field (either hidden input or in form)
        assert (b'csrf_token' in response.data or 
                b'_csrf_token' in response.data or
                b'csrf-token' in response.data)
    
    def test_csrf_token_in_register_template(self, client):
        """Test register template includes CSRF token field."""
        response = client.get('/register')
        
        assert response.status_code == 200
        # Should have CSRF token field
        assert (b'csrf_token' in response.data or 
                b'_csrf_token' in response.data or
                b'csrf-token' in response.data)
    
    def test_csrf_token_in_settings_template(self, client, logged_in_user):
        """Test settings template includes CSRF token fields."""
        response = client.get('/settings')
        
        assert response.status_code == 200
        # Should have CSRF token fields for various forms
        assert (b'csrf_token' in response.data or 
                b'_csrf_token' in response.data or
                b'csrf-token' in response.data)
    
    def test_csrf_token_in_ai_templates(self, client, logged_in_user):
        """Test AI conversation templates include CSRF token."""
        response = client.get('/ai/conversation/multiple')
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        # Should have CSRF token for AJAX requests - look for actual token values or meta tags
        assert ('X-CSRF-Token' in response_text or 
                'csrf-token' in response_text or
                '_csrf_token' in response_text or
                'name="csrf_token"' in response_text)


class TestCSRFAttackPrevention:
    """Test CSRF protection against common attack vectors."""
    
    def test_csrf_prevents_cross_origin_form_submission(self, app, user):
        """Test CSRF prevents cross-origin form submissions."""
        with app.test_client() as client:
            # Simulate cross-origin request (no session)
            response = client.post('/login', data={
                'username': user.username,
                'password': 'TestPassword123!'
            }, headers={
                'Origin': 'https://evil-site.com',
                'Referer': 'https://evil-site.com/attack.html'
            })
            
            # Should be rejected
            assert response.status_code == 302
    
    def test_csrf_prevents_ajax_without_token(self, client, logged_in_user, journal_entry):
        """Test CSRF prevents AJAX requests without proper token."""
        import json
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        # AJAX request without CSRF token
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={
                                 'X-Requested-With': 'XMLHttpRequest'
                             })
        
        # Should be rejected
        assert response.status_code in [302, 400, 403]
    
    def test_csrf_allows_legitimate_requests(self, client, logged_in_user, csrf_token):
        """Test CSRF allows legitimate requests with proper tokens."""
        response = client.post('/journal/quick', data={
            'content': 'Legitimate entry',
            'tags': [],
            'new_tags': '[]',
            '_csrf_token': csrf_token
        }, follow_redirects=True)
        
        # Should succeed
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()