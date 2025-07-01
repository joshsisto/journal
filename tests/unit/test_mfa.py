"""
Unit tests for Multi-Factor Authentication (MFA) functionality.

Tests MFA enable/disable, verification, and related security features.
"""

import pytest
from unittest.mock import patch
from flask import session
from models import User, db


class TestMFAEnableDisable:
    """Test MFA enable and disable functionality."""
    
    def test_toggle_mfa_enable(self, client, logged_in_user, user):
        """Test enabling MFA for user."""
        assert not user.two_factor_enabled
        
        response = client.post('/toggle-two-factor', data={
            'enabled': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'enabled' in response.data
        
        # Check MFA is enabled in database
        db.session.refresh(user)
        assert user.two_factor_enabled
    
    def test_toggle_mfa_disable(self, client, logged_in_user, user_with_mfa):
        """Test disabling MFA for user."""
        assert user_with_mfa.two_factor_enabled
        
        # Login as MFA user
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_with_mfa.id)
            sess['_fresh'] = True
        
        response = client.post('/toggle-two-factor', data={
            # No 'enabled' field means disabled
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'disabled' in response.data
        
        # Check MFA is disabled in database
        db.session.refresh(user_with_mfa)
        assert not user_with_mfa.two_factor_enabled
    
    def test_toggle_mfa_requires_login(self, client):
        """Test that MFA toggle requires user to be logged in."""
        response = client.post('/toggle-two-factor', data={
            'enabled': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_mfa_status_displayed_in_settings(self, client, logged_in_user, user):
        """Test MFA status is displayed in settings page."""
        response = client.get('/settings')
        
        assert response.status_code == 200
        assert b'two-factor' in response.data.lower() or b'2fa' in response.data.lower()


class TestMFAVerification:
    """Test MFA verification during login process."""
    
    def test_mfa_verification_page_loads(self, client, user_with_mfa, mock_two_factor):
        """Test MFA verification page loads after login."""
        # Login with MFA user - should redirect to verification
        response = client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verification' in response.data.lower() or b'code' in response.data.lower()
        
        # Check that user is in pre-verification state
        with client.session_transaction() as sess:
            assert 'requires_verification' in sess
            assert 'pre_verified_user_id' in sess
    
    def test_mfa_verification_valid_code(self, client, user_with_mfa, mock_two_factor):
        """Test MFA verification with valid code."""
        # First login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Submit verification code
        response = client.post('/verify', data={
            'code': '123456'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'journal' in response.data.lower()
        
        # Check user is fully logged in
        with client.session_transaction() as sess:
            assert '_user_id' in sess
            assert 'requires_verification' not in sess
        
        # Check verification was called
        mock_two_factor['verify'].assert_called_once()
    
    def test_mfa_verification_invalid_code(self, client, user_with_mfa, mock_two_factor):
        """Test MFA verification with invalid code."""
        # Mock invalid code
        mock_two_factor['verify'].return_value = (False, "Invalid code")
        
        # First login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Submit invalid verification code
        response = client.post('/verify', data={
            'code': 'invalid'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'failed' in response.data.lower() or b'invalid' in response.data.lower()
        
        # Check user is not logged in
        with client.session_transaction() as sess:
            assert '_user_id' not in sess or 'requires_verification' in sess
    
    def test_mfa_verification_without_login(self, client):
        """Test accessing verification page without login redirects."""
        response = client.get('/verify', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_mfa_verification_missing_code(self, client, user_with_mfa, mock_two_factor):
        """Test MFA verification with missing code."""
        # First login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Submit empty verification code
        response = client.post('/verify', data={
            'code': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verification' in response.data.lower() or b'code' in response.data.lower()
    
    def test_mfa_code_resend(self, client, user_with_mfa, mock_two_factor):
        """Test MFA code resend functionality."""
        # First login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Resend code
        response = client.post('/resend-code')
        
        assert response.status_code == 200
        
        # Check response is JSON
        json_data = response.get_json()
        assert json_data is not None
        assert 'success' in json_data
        
        # Check resend was called
        assert mock_two_factor['send'].call_count == 2  # Once for login, once for resend
    
    def test_mfa_code_resend_without_session(self, client):
        """Test MFA code resend without proper session."""
        response = client.post('/resend-code')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is False
    
    def test_mfa_code_resend_rate_limited(self, client, user_with_mfa, mock_two_factor):
        """Test MFA code resend is rate limited."""
        # First login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Try to resend multiple times quickly
        responses = []
        for _ in range(5):
            response = client.post('/resend-code')
            responses.append(response)
        
        # At least one should be rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or any(r.get_json().get('success') is False for r in responses)


class TestMFASecurityFeatures:
    """Test MFA security features and edge cases."""
    
    def test_mfa_login_without_mfa_enabled(self, client, user):
        """Test normal login when MFA is not enabled."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'journal' in response.data.lower()
        
        # Should go directly to dashboard, not verification
        with client.session_transaction() as sess:
            assert '_user_id' in sess
            assert 'requires_verification' not in sess
    
    def test_mfa_session_cleanup_on_failed_verification(self, client, user_with_mfa, mock_two_factor):
        """Test that session is cleaned up after failed MFA verification."""
        # Mock failed verification
        mock_two_factor['verify'].return_value = (False, "Invalid code")
        
        # Login and fail verification
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        client.post('/verify', data={
            'code': 'invalid'
        })
        
        # Session should still contain verification state for retry
        with client.session_transaction() as sess:
            assert 'requires_verification' in sess
    
    def test_mfa_bypass_attempt(self, client, user_with_mfa):
        """Test that direct access to protected pages is blocked during MFA."""
        # Login to get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Try to access protected page without completing MFA
        response = client.get('/journal/quick', follow_redirects=True)
        
        # Should be redirected to login or verification
        assert response.status_code == 200
        assert (b'login' in response.data.lower() or 
                b'verification' in response.data.lower() or 
                b'code' in response.data.lower())
    
    def test_mfa_remember_functionality(self, client, user_with_mfa, mock_two_factor):
        """Test MFA with remember me functionality."""
        # Login with remember me
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!',
            'remember': 'y'
        })
        
        # Complete MFA verification
        response = client.post('/verify', data={
            'code': '123456'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check user is logged in with remember flag
        with client.session_transaction() as sess:
            assert '_user_id' in sess
    
    @patch('two_factor.is_verification_required')
    def test_mfa_verification_not_required_for_recent_verification(self, mock_required, client, user_with_mfa):
        """Test that MFA verification is not required if recently verified."""
        # Mock that verification is not required
        mock_required.return_value = False
        
        response = client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        # Should go directly to dashboard
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'journal' in response.data.lower()
        
        # Should not be in verification state
        with client.session_transaction() as sess:
            assert '_user_id' in sess
            assert 'requires_verification' not in sess


class TestMFAIntegration:
    """Test MFA integration with other app features."""
    
    def test_mfa_status_in_user_model(self, user, user_with_mfa):
        """Test MFA status is properly stored in user model."""
        assert not user.two_factor_enabled
        assert user_with_mfa.two_factor_enabled
    
    def test_mfa_user_creation_default_disabled(self, app, db_session):
        """Test that new users have MFA disabled by default."""
        with app.app_context():
            user = User(username='new_user', timezone='UTC')
            user.set_password('password')
            db_session.add(user)
            db_session.commit()
            
            assert not user.two_factor_enabled
    
    def test_mfa_settings_page_integration(self, client, logged_in_user, user):
        """Test MFA settings are integrated in settings page."""
        response = client.get('/settings')
        
        assert response.status_code == 200
        # Should show MFA toggle
        assert (b'two-factor' in response.data.lower() or 
                b'2fa' in response.data.lower() or
                b'authentication' in response.data.lower())
    
    def test_mfa_logout_clears_verification_state(self, client, user_with_mfa, mock_two_factor):
        """Test that logout clears MFA verification state."""
        # Login and get to verification state
        client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        })
        
        # Logout while in verification state
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        # Session should be completely cleared
        with client.session_transaction() as sess:
            assert '_user_id' not in sess
            assert 'requires_verification' not in sess
            assert 'pre_verified_user_id' not in sess