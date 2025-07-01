"""Unit tests for register function dependency interactions."""

import pytest
from unittest.mock import patch, MagicMock, call
from sqlalchemy.exc import SQLAlchemyError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import create_app
from models import User


class TestRegisterDependencyInteractions:
    """Test cases for register function interactions with external dependencies."""
    
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

    @patch('routes.send_email')
    @patch('routes.db.session.commit')
    @patch('routes.db.session.add')
    @patch('routes.User.query')
    def test_successful_registration_with_email(self, mock_user_query, mock_db_add, 
                                               mock_db_commit, mock_send_email, client):
        """Test successful registration flow when user provides email."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        # Mock database operations
        mock_db_add.return_value = None
        mock_db_commit.return_value = None
        
        # Mock email sending
        mock_send_email.return_value = None
        
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should redirect to login page
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Verify database operations were called
        mock_db_add.assert_called_once()
        mock_db_commit.assert_called_once()
        
        # Verify email was sent
        mock_send_email.assert_called_once()

    @patch('routes.send_email')
    @patch('routes.db.session.commit')
    @patch('routes.db.session.add')
    @patch('routes.User.query')
    def test_successful_registration_without_email(self, mock_user_query, mock_db_add,
                                                  mock_db_commit, mock_send_email, client):
        """Test successful registration flow when user doesn't provide email."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        # Mock database operations
        mock_db_add.return_value = None
        mock_db_commit.return_value = None
        
        response = client.post('/register', data={
            'username': 'testuser',
            'email': '',  # Empty email
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should redirect to login page
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Verify database operations were called
        mock_db_add.assert_called_once()
        mock_db_commit.assert_called_once()
        
        # Verify email was NOT sent
        mock_send_email.assert_not_called()

    @patch('routes.current_app.logger')
    @patch('routes.db.session.commit')
    @patch('routes.db.session.add')
    @patch('routes.User.query')
    def test_database_commit_fails(self, mock_user_query, mock_db_add,
                                  mock_db_commit, mock_logger, client):
        """Test system behavior when database commit operation fails."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        # Mock database add to succeed but commit to fail
        mock_db_add.return_value = None
        mock_db_commit.side_effect = SQLAlchemyError("Database error")
        
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should return 200 (render registration template again)
        assert response.status_code == 200
        
        # Should contain error message in response
        assert b'Registration error' in response.data
        
        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('routes.current_app.logger')
    @patch('routes.send_email')
    @patch('routes.db.session.commit')
    @patch('routes.db.session.add')
    @patch('routes.User.query')
    def test_email_sending_fails(self, mock_user_query, mock_db_add, mock_db_commit,
                                mock_send_email, mock_logger, client):
        """Test that registration succeeds even if email sending fails."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        # Mock database operations to succeed
        mock_db_add.return_value = None
        mock_db_commit.return_value = None
        
        # Mock email sending to fail
        mock_send_email.side_effect = Exception("SMTP server error")
        
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should still redirect to login page
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Verify database operations were called
        mock_db_add.assert_called_once()
        mock_db_commit.assert_called_once()
        
        # Verify email sending was attempted
        mock_send_email.assert_called_once()
        
        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('routes.User.query')
    def test_username_already_exists(self, mock_user_query, client):
        """Test that system prevents registration with existing username."""
        # Mock User.query.filter_by to return existing user for username check
        mock_existing_user = MagicMock(spec=User)
        mock_user_query.filter_by.return_value.first.return_value = mock_existing_user
        
        response = client.post('/register', data={
            'username': 'existinguser',
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should return 200 (render registration template again)
        assert response.status_code == 200
        
        # Should contain error message
        assert b'Username already exists' in response.data

    @patch('routes.db.session')
    @patch('routes.User.query')
    def test_email_already_exists(self, mock_user_query, mock_db_session, client):
        """Test that system prevents registration with existing email."""
        # Mock User.query.filter_by to return None for username but existing user for email
        def mock_filter_by(**kwargs):
            mock_query = MagicMock()
            if 'username' in kwargs:
                mock_query.first.return_value = None  # No existing username
            elif 'email' in kwargs:
                mock_query.first.return_value = MagicMock(spec=User)  # Existing email
            return mock_query
        
        mock_user_query.filter_by.side_effect = mock_filter_by
        
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'existing@example.com',
            'password': 'strongpassword123',
            'confirm_password': 'strongpassword123',
            'timezone': 'UTC'
        })
        
        # Should return 200 (render registration template again)
        assert response.status_code == 200
        
        # Should contain error message
        assert b'Email already registered' in response.data
        
        # Verify database operations were NOT called
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @patch('routes.User.query')
    def test_weak_password_rejection(self, mock_user_query, client):
        """Test that system rejects common weak passwords."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        weak_passwords = ['password', '123456', 'qwerty', 'admin', 'welcome']
        
        for weak_password in weak_passwords:
            response = client.post('/register', data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': weak_password,
                'confirm_password': weak_password,
                'timezone': 'UTC'
            })
            
            # Should return 200 (render registration template again)
            assert response.status_code == 200
            
            # Should contain error message
            assert b'stronger password' in response.data

    @patch('routes.User.query')
    def test_invalid_timezone_defaults_to_utc(self, mock_user_query, client):
        """Test that invalid timezone defaults to UTC."""
        # Mock User.query.filter_by to return None (no existing user)
        mock_user_query.filter_by.return_value.first.return_value = None
        
        with patch('routes.db.session.add') as mock_db_add:
            with patch('routes.db.session.commit') as mock_db_commit:
                response = client.post('/register', data={
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'strongpassword123',
                    'confirm_password': 'strongpassword123',
                    'timezone': 'Invalid/Timezone'
                })
                
                # Should redirect to login page
                assert response.status_code == 302
                assert '/login' in response.location
                
                # Verify user was created with UTC timezone
                mock_db_add.assert_called_once()
                added_user = mock_db_add.call_args[0][0]
                assert added_user.timezone == 'UTC'