"""
Unit tests for email functionality.

Tests email add/change/verify operations and email-related features.
"""

import pytest
from unittest.mock import patch
from flask import url_for
from models import User, db


class TestEmailVerification:
    """Test email verification functionality."""
    
    def test_verify_email_with_valid_token(self, client, user):
        """Test email verification with valid token."""
        # Set up user with unverified email
        user.is_email_verified = False
        token = user.generate_email_verification_token()
        db.session.commit()
        
        response = client.get(f'/verify-email/{token}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verified successfully' in response.data
        
        # Check user is verified
        db.session.refresh(user)
        assert user.is_email_verified
        assert user.email_verification_token is None
    
    def test_verify_email_with_invalid_token(self, client):
        """Test email verification with invalid token."""
        response = client.get('/verify-email/invalid-token-12345', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data
    
    def test_verify_email_with_expired_token(self, client, user):
        """Test email verification with expired token."""
        # Simulate expired token by using invalid token
        user.is_email_verified = False
        user.email_verification_token = 'expired-token'
        db.session.commit()
        
        response = client.get('/verify-email/expired-token', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data
        
        # User should still be unverified
        db.session.refresh(user)
        assert not user.is_email_verified
    
    def test_verify_email_already_verified(self, client, user):
        """Test email verification when already verified."""
        # User is already verified
        assert user.is_email_verified
        
        token = user.generate_email_verification_token()
        db.session.commit()
        
        response = client.get(f'/verify-email/{token}', follow_redirects=True)
        
        assert response.status_code == 200
        # Should handle gracefully
        assert b'verified' in response.data


class TestAddEmail:
    """Test adding email to accounts without email."""
    
    def test_add_email_to_account_without_email(self, client, user_no_email, mock_email):
        """Test adding email to account that doesn't have one."""
        # Login first
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        new_email = 'newemail@example.com'
        response = client.post('/settings/add-email', data={
            'email': new_email,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'added' in response.data
        
        # Check email was added
        db.session.refresh(user_no_email)
        assert user_no_email.email == new_email
        assert not user_no_email.is_email_verified  # Should start unverified
        
        # Check verification email was sent
        mock_email.assert_called_once()
    
    def test_add_email_to_account_with_email(self, client, logged_in_user, user):
        """Test adding email to account that already has one fails."""
        response = client.post('/settings/add-email', data={
            'email': 'another@example.com',
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already have an email' in response.data
    
    def test_add_email_invalid_password(self, client, user_no_email):
        """Test adding email with invalid password fails."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        response = client.post('/settings/add-email', data={
            'email': 'newemail@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'incorrect' in response.data.lower()
        
        # Email should not be added
        db.session.refresh(user_no_email)
        assert user_no_email.email is None
    
    def test_add_email_duplicate_email(self, client, user, user_no_email):
        """Test adding email that already exists fails."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        response = client.post('/settings/add-email', data={
            'email': user.email,  # Use existing user's email
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already in use' in response.data
        
        # Email should not be added
        db.session.refresh(user_no_email)
        assert user_no_email.email is None
    
    def test_add_email_requires_login(self, client):
        """Test adding email requires user to be logged in."""
        response = client.post('/settings/add-email', data={
            'email': 'test@example.com',
            'password': 'password'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_add_email_missing_fields(self, client, user_no_email):
        """Test adding email with missing fields fails."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        # Missing email
        response = client.post('/settings/add-email', data={
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower()
        
        # Missing password
        response = client.post('/settings/add-email', data={
            'email': 'test@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower()


class TestChangeEmail:
    """Test changing email for existing accounts."""
    
    def test_change_email_valid_request(self, client, logged_in_user, user, mock_email):
        """Test changing email with valid data."""
        new_email = 'newemail@example.com'
        
        response = client.post('/settings/email', data={
            'password': 'TestPassword123!',
            'new_email': new_email,
            'confirm_email': new_email
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'confirmation link' in response.data
        
        # Check confirmation email was sent
        mock_email.assert_called_once()
        
        # Email should not be changed yet (pending confirmation)
        db.session.refresh(user)
        assert user.email != new_email
        assert user.email_change_token is not None
        assert user.pending_email == new_email
    
    def test_change_email_invalid_password(self, client, logged_in_user, user):
        """Test changing email with invalid password fails."""
        response = client.post('/settings/email', data={
            'password': 'wrongpassword',
            'new_email': 'newemail@example.com',
            'confirm_email': 'newemail@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'incorrect' in response.data.lower()
    
    def test_change_email_mismatch(self, client, logged_in_user, user):
        """Test changing email with mismatched emails fails."""
        response = client.post('/settings/email', data={
            'password': 'TestPassword123!',
            'new_email': 'email1@example.com',
            'confirm_email': 'email2@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'do not match' in response.data
    
    def test_change_email_duplicate_email(self, client, logged_in_user, user, user_no_email):
        """Test changing to an email that already exists fails."""
        import uuid
        unique_email = f'existing_{str(uuid.uuid4())[:8]}@example.com'
        
        # Give user_no_email an email first
        user_no_email.email = unique_email
        db.session.commit()
        
        response = client.post('/settings/email', data={
            'password': 'TestPassword123!',
            'new_email': unique_email,
            'confirm_email': unique_email
        }, follow_redirects=True)
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert 'already in use' in response_text or 'already exists' in response_text
    
    def test_change_email_requires_login(self, client):
        """Test changing email requires login."""
        response = client.post('/settings/email', data={
            'password': 'password',
            'new_email': 'test@example.com',
            'confirm_email': 'test@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_confirm_email_change_valid_token(self, client, user):
        """Test confirming email change with valid token."""
        new_email = 'confirmed@example.com'
        
        # Set up email change
        token = user.generate_email_change_token(new_email)
        db.session.commit()
        
        response = client.get(f'/confirm-email-change/{token}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated successfully' in response.data
        
        # Check email was changed
        db.session.refresh(user)
        assert user.email == new_email
        assert user.email_change_token is None
        assert user.pending_email is None
    
    def test_confirm_email_change_invalid_token(self, client):
        """Test confirming email change with invalid token."""
        response = client.get('/confirm-email-change/invalid-token', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data


class TestResendVerification:
    """Test resending email verification."""
    
    def test_resend_verification_unverified_user(self, client, logged_in_user, user, mock_email):
        """Test resending verification for unverified user."""
        # Make user unverified
        user.is_email_verified = False
        db.session.commit()
        
        response = client.post('/settings/resend-verification', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Verification email sent' in response.data
        
        # Check email was sent
        mock_email.assert_called_once()
        
        # Check new token was generated
        db.session.refresh(user)
        assert user.email_verification_token is not None
    
    def test_resend_verification_verified_user(self, client, logged_in_user, user):
        """Test resending verification for already verified user."""
        # User is already verified
        assert user.is_email_verified
        
        response = client.post('/settings/resend-verification', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already verified' in response.data
    
    def test_resend_verification_no_email(self, client, user_no_email):
        """Test resending verification for user without email."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        response = client.post('/settings/resend-verification', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'add an email' in response.data
    
    def test_resend_verification_requires_login(self, client):
        """Test resending verification requires login."""
        response = client.post('/settings/resend-verification', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_resend_verification_rate_limited(self, client, logged_in_user, user, mock_email):
        """Test resend verification is rate limited."""
        # Make user unverified
        user.is_email_verified = False
        db.session.commit()
        
        # Try to resend multiple times
        responses = []
        for _ in range(5):
            response = client.post('/settings/resend-verification', follow_redirects=True)
            responses.append(response)
        
        # Should be rate limited after several attempts
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or any(b'try again later' in r.data for r in responses)


class TestEmailIntegration:
    """Test email integration with other features."""
    
    def test_email_in_settings_page(self, client, logged_in_user, user):
        """Test email information is displayed in settings."""
        response = client.get('/settings')
        
        assert response.status_code == 200
        assert user.email.encode() in response.data
        
        if user.is_email_verified:
            assert b'verified' in response.data.lower()
        else:
            assert b'verify' in response.data.lower()
    
    def test_no_email_in_settings_page(self, client, user_no_email):
        """Test settings page for user without email."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_no_email.id)
            sess['_fresh'] = True
        
        response = client.get('/settings')
        
        assert response.status_code == 200
        assert b'add an email' in response.data.lower() or b'no email' in response.data.lower()
    
    def test_password_reset_requires_email(self, client, user_no_email):
        """Test password reset requires user to have email."""
        response = client.post('/request-reset', data={
            'email': 'nonexistent@example.com'
        }, follow_redirects=True)
        
        # Should show generic success message for security
        assert response.status_code == 200
        assert b'password reset link' in response.data
    
    def test_email_validation_in_forms(self, client, logged_in_user):
        """Test email validation in various forms."""
        # Test invalid email format
        response = client.post('/settings/add-email', data={
            'email': 'invalid-email-format',
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show validation error
        assert (b'invalid' in response.data.lower() or 
                b'valid email' in response.data.lower())


class TestEmailSecurityFeatures:
    """Test email-related security features."""
    
    def test_email_verification_token_uniqueness(self, app, db_session):
        """Test that email verification tokens are unique."""
        with app.app_context():
            user1 = User(username='user1', email='user1@test.com', timezone='UTC')
            user2 = User(username='user2', email='user2@test.com', timezone='UTC')
            
            token1 = user1.generate_email_verification_token()
            token2 = user2.generate_email_verification_token()
            
            assert token1 != token2
            assert token1 is not None
            assert token2 is not None
    
    def test_email_change_token_security(self, user):
        """Test email change token generation and verification."""
        new_email = 'newemail@example.com'
        
        # Generate token
        token = user.generate_email_change_token(new_email)
        assert token is not None
        
        # Verify token
        assert user.verify_email_change_token(token)
        assert user.pending_email == new_email
        
        # Invalid token should fail
        assert not user.verify_email_change_token('invalid-token')
    
    def test_email_case_insensitive_handling(self, client, user_data, mock_email):
        """Test that email addresses are handled case-insensitively."""
        # Register with uppercase email
        user_data['email'] = 'TEST@EXAMPLE.COM'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        assert response.status_code == 200
        
        # Try to register with lowercase version
        user_data['username'] = 'different_user'
        user_data['email'] = 'test@example.com'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        # Should detect duplicate (case-insensitive)
        assert response.status_code == 200
        assert b'already registered' in response.data or b'already in use' in response.data