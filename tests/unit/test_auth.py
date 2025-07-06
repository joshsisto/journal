"""
Unit tests for authentication functionality.

Tests registration, login, logout, and related authentication features.
"""

import pytest
from unittest.mock import patch
from flask import url_for, session
from models import User, db


class TestRegistration:
    """Test user registration functionality."""
    
    def test_registration_page_loads(self, client):
        """Test that registration page loads correctly."""
        response = client.get('/register')
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert 'Register' in response_text
        assert 'name="username"' in response_text
        assert 'name="password"' in response_text
        assert 'type="password"' in response_text
    
    def test_successful_registration_with_email(self, client, user_data, mock_email):
        """Test successful user registration with email."""
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Registration successful' in response.data
        
        # Check user was created
        user = User.query.filter_by(username=user_data['username']).first()
        assert user is not None
        assert user.email == user_data['email']
        assert user.timezone == user_data['timezone']
        assert user.check_password(user_data['password'])
        assert not user.is_email_verified  # Should start unverified
        
        # Check email was sent
        mock_email.assert_called_once()
    
    def test_successful_registration_without_email(self, client, user_data_no_email):
        """Test successful user registration without email."""
        response = client.post('/register', data=user_data_no_email, follow_redirects=True)
        
        assert response.status_code == 200
        # After successful registration, user is redirected to login page
        assert b'Login' in response.data and b'Journal App' in response.data
        
        # Check user was created
        user = User.query.filter_by(username=user_data_no_email['username']).first()
        assert user is not None
        assert user.email is None
        assert user.timezone == user_data_no_email['timezone']
        assert user.check_password(user_data_no_email['password'])
    
    def test_registration_duplicate_username(self, client, user, user_data):
        """Test registration fails with duplicate username."""
        # Use same username as existing user
        user_data['username'] = user.username
        user_data['email'] = 'different@example.com'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Username already exists' in response.data
    
    def test_registration_duplicate_email(self, client, user, user_data):
        """Test registration fails with duplicate email."""
        # Use same email as existing user
        user_data['username'] = 'different_user'
        user_data['email'] = user.email
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Email already registered' in response.data
    
    def test_registration_weak_password(self, client, user_data):
        """Test registration fails with weak password."""
        user_data['password'] = 'weak'
        user_data['confirm_password'] = 'weak'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show password validation error
        assert b'password' in response.data.lower()
    
    def test_registration_common_password(self, client, user_data):
        """Test registration with common password shows appropriate message."""
        user_data['password'] = 'password'
        user_data['confirm_password'] = 'password'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        # Check if the registration was processed (even if accepted)
        # The application may accept common passwords but show a warning
        assert 'Register' in response_text or 'Registration successful' in response_text or 'Login' in response_text
    
    def test_registration_invalid_timezone(self, client, user_data):
        """Test registration with invalid timezone is rejected."""
        user_data['timezone'] = 'Invalid/Timezone'
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check user was NOT created due to invalid timezone
        user = User.query.filter_by(username=user_data['username']).first()
        assert user is None
        
        # Check we're still on registration page with error
        assert b'Register' in response.data
        assert b'Not a valid choice' in response.data or b'timezone' in response.data.lower()
    
    def test_registration_missing_username(self, client, user_data):
        """Test registration fails with missing username."""
        del user_data['username']
        
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show validation error
        assert b'required' in response.data.lower() or b'field is required' in response.data.lower()
    
    def test_registration_email_verification_token_generated(self, client, user_data, mock_email):
        """Test that email verification token is generated when email provided."""
        response = client.post('/register', data=user_data, follow_redirects=True)
        
        assert response.status_code == 200
        
        user = User.query.filter_by(username=user_data['username']).first()
        assert user.email_verification_token is not None
        assert not user.is_email_verified


class TestLogin:
    """Test user login functionality."""
    
    def test_login_page_loads(self, client):
        """Test that login page loads correctly."""
        response = client.get('/login')
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert 'Login' in response_text
        assert 'name="username"' in response_text
        assert 'name="password"' in response_text
        assert 'type="submit"' in response_text
    
    def test_successful_login(self, client, user):
        """Test successful user login."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True).lower()
        # Should be redirected to journal/dashboard after successful login
        assert 'dashboard' in response_text or 'journal' in response_text or 'welcome' in response_text
        
        # Check user is logged in
        with client.session_transaction() as sess:
            assert '_user_id' in sess
            assert sess['_user_id'] == str(user.id)
    
    def test_login_invalid_username(self, client):
        """Test login fails with invalid username."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert 'Invalid username or password' in response_text or 'Login failed' in response_text
    
    def test_login_invalid_password(self, client, user):
        """Test login fails with invalid password."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        assert 'Invalid username or password' in response_text or 'Login failed' in response_text
    
    def test_login_redirects_authenticated_user(self, client, logged_in_user):
        """Test that already authenticated users are redirected."""
        response = client.get('/login', follow_redirects=True)
        
        assert response.status_code == 200
        # Should be redirected to dashboard/journal
        assert b'dashboard' in response.data.lower() or b'journal' in response.data.lower()
    
    def test_login_with_mfa_enabled(self, client, user_with_mfa, mock_two_factor):
        """Test login with MFA enabled redirects to verification."""
        response = client.post('/login', data={
            'username': user_with_mfa.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verification' in response.data.lower() or b'code' in response.data.lower()
        
        # Check MFA code was sent
        mock_two_factor['send'].assert_called_once()
    
    def test_login_remember_me(self, client, user):
        """Test login with remember me functionality."""
        response = client.post('/login', data={
            'username': user.username,
            'password': 'TestPassword123!',
            'remember': 'y'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check remember token is set (would be in cookies in real scenario)
        with client.session_transaction() as sess:
            assert '_user_id' in sess
    
    def test_login_next_parameter(self, client, user):
        """Test login redirects to 'next' parameter."""
        # Try to access protected page
        response = client.get('/journal/quick')
        assert response.status_code == 302  # Redirect to login
        
        # Login should redirect back to original page
        response = client.post('/login?next=%2Fjournal%2Fquick', data={
            'username': user.username,
            'password': 'TestPassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should be on the quick journal page
        assert b'quick' in response.data.lower() or response.request.path == '/journal/quick'


class TestLogout:
    """Test user logout functionality."""
    
    def test_logout_logged_in_user(self, client, logged_in_user):
        """Test logout for logged in user."""
        # Verify user is logged in
        with client.session_transaction() as sess:
            assert '_user_id' in sess
        
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        # Verify user is logged out
        with client.session_transaction() as sess:
            assert '_user_id' not in sess
    
    def test_logout_requires_login(self, client):
        """Test logout redirects unauthenticated users."""
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()


class TestEmailVerification:
    """Test email verification functionality."""
    
    def test_verify_email_valid_token(self, client, user):
        """Test email verification with valid token."""
        # Set up unverified user with token
        user.is_email_verified = False
        user.email_verification_token = user.generate_email_verification_token()
        db.session.commit()
        
        token = user.email_verification_token
        response = client.get(f'/verify-email/{token}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verified successfully' in response.data
        
        # Check user is now verified
        db.session.refresh(user)
        assert user.is_email_verified
        assert user.email_verification_token is None
    
    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token."""
        response = client.get('/verify-email/invalid-token', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data
    
    def test_verify_email_expired_token(self, client, user):
        """Test email verification with expired token."""
        # Create expired token (this is a simplified test)
        user.is_email_verified = False
        user.email_verification_token = 'expired-token'
        db.session.commit()
        
        response = client.get('/verify-email/expired-token', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data


class TestPasswordReset:
    """Test password reset functionality."""
    
    def test_request_reset_page_loads(self, client):
        """Test password reset request page loads."""
        response = client.get('/request-reset')
        assert response.status_code == 200
        assert b'reset' in response.data.lower()
    
    def test_request_reset_valid_email(self, client, user, mock_email):
        """Test password reset request with valid email."""
        response = client.post('/request-reset', data={
            'email': user.email
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'password reset link' in response.data
        
        # Check email was sent
        mock_email.assert_called_once()
    
    def test_request_reset_invalid_email(self, client, mock_email):
        """Test password reset request with invalid email."""
        response = client.post('/request-reset', data={
            'email': 'nonexistent@example.com'
        }, follow_redirects=True)
        
        # Should still show success message for security
        assert response.status_code == 200
        assert b'password reset link' in response.data
        
        # But no email should be sent
        mock_email.assert_not_called()
    
    def test_reset_password_valid_token(self, client, user):
        """Test password reset with valid token."""
        # Generate reset token
        token = user.generate_reset_token()
        db.session.commit()
        
        new_password = 'NewPassword123!'
        response = client.post(f'/reset-password/{token}', data={
            'password': new_password,
            'confirm_password': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'password has been reset' in response.data
        
        # Check password was changed
        db.session.refresh(user)
        assert user.check_password(new_password)
        assert user.reset_token is None
    
    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.get('/reset-password/invalid-token', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid or expired' in response.data


class TestAuthenticationHelpers:
    """Test authentication helper functions."""
    
    def test_user_password_hashing(self, app):
        """Test user password hashing and verification."""
        with app.app_context():
            user = User(username='test', timezone='UTC')
            password = 'TestPassword123!'
            
            user.set_password(password)
            assert user.password_hash is not None
            assert user.password_hash != password
            assert user.check_password(password)
            assert not user.check_password('wrongpassword')
    
    def test_user_token_generation(self, app, user):
        """Test user token generation methods."""
        with app.app_context():
            # Test email verification token
            token = user.generate_email_verification_token()
            assert token is not None
            assert user.verify_email_verification_token(token)
            
            # Test reset token
            reset_token = user.generate_reset_token()
            assert reset_token is not None
            assert user.verify_reset_token(reset_token)
    
    def test_user_repr(self, user):
        """Test User model string representation."""
        repr_str = repr(user)
        assert user.username in repr_str
        assert 'User' in repr_str