"""
Two-factor authentication module for email-based verification.

This module handles generating, storing, and validating 2FA codes
sent via email to users for secure login verification.
"""
import random
import string
import time
from datetime import datetime, timedelta
from flask import current_app, session
from email_utils import send_email
from models import db, User

# Constants
CODE_LENGTH = 6  # Length of 2FA verification code
CODE_EXPIRY = 10  # Code expiry time in minutes
MAX_ATTEMPTS = 3  # Maximum number of verification attempts

def generate_verification_code(length=CODE_LENGTH):
    """
    Generate a random verification code.
    
    Args:
        length (int): Length of the verification code
        
    Returns:
        str: Random verification code consisting of digits
    """
    return ''.join(random.choices(string.digits, k=length))

def store_verification_code(user_id, code):
    """
    Store a verification code for a user.
    
    Args:
        user_id (int): User ID
        code (str): Verification code
    """
    # Get user
    user = User.query.get(user_id)
    if not user:
        return False
    
    # Set code and expiry time
    user.two_factor_code = code
    user.two_factor_expiry = datetime.utcnow() + timedelta(minutes=CODE_EXPIRY)
    
    # Reset attempt counter
    session['verification_attempts'] = 0
    
    # Store when the code was sent
    session['last_code_sent'] = int(time.time())
    
    # Save to database
    db.session.commit()
    return True

def send_verification_code(user_id):
    """
    Generate and send a verification code to a user.
    
    Args:
        user_id (int): User ID
        
    Returns:
        bool: True if the code was sent successfully, False otherwise
    """
    # Check rate limiting
    last_sent = session.get('last_code_sent', 0)
    current_time = int(time.time())
    
    # Prevent sending more than 1 code every 60 seconds
    if current_time - last_sent < 60:
        return False, "Please wait before requesting another code"
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    # Generate code
    code = generate_verification_code()
    
    # Store code
    if not store_verification_code(user_id, code):
        return False, "Failed to store verification code"
    
    # Send code via email
    subject = f"{current_app.config.get('APP_NAME', 'Journal App')} - Verification Code"
    
    # Plain text email
    text_body = f"""
Hello {user.username},

Your verification code is: {code}

This code will expire in {CODE_EXPIRY} minutes.

If you did not request this code, please ignore this email and contact support.

Thank you,
{current_app.config.get('APP_NAME', 'Journal App')} Team
    """
    
    # HTML email
    html_body = f"""
<p>Hello {user.username},</p>
<p>Your verification code is: <strong>{code}</strong></p>
<p>This code will expire in {CODE_EXPIRY} minutes.</p>
<p>If you did not request this code, please ignore this email and contact support.</p>
<p>Thank you,<br>{current_app.config.get('APP_NAME', 'Journal App')} Team</p>
    """
    
    try:
        send_email(subject, [user.email], text_body, html_body)
        return True, "Verification code sent"
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return False, "Failed to send verification code"

def verify_code(user_id, code):
    """
    Verify a 2FA code.
    
    Args:
        user_id (int): User ID
        code (str): Verification code to verify
        
    Returns:
        bool: True if the code is valid, False otherwise
        str: Error message if verification failed
    """
    # Check attempts
    attempts = session.get('verification_attempts', 0)
    if attempts >= MAX_ATTEMPTS:
        return False, "Maximum verification attempts exceeded"
    
    # Increment attempts
    session['verification_attempts'] = attempts + 1
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    # Check if code exists
    if not user.two_factor_code:
        return False, "No verification code found"
    
    # Check if code has expired
    if not user.two_factor_expiry or datetime.utcnow() > user.two_factor_expiry:
        return False, "Verification code has expired"
    
    # Check if code matches
    if user.two_factor_code != code:
        return False, "Invalid verification code"
    
    # Clear code
    user.two_factor_code = None
    user.two_factor_expiry = None
    db.session.commit()
    
    # Clear session
    if 'verification_attempts' in session:
        session.pop('verification_attempts')
    if 'last_code_sent' in session:
        session.pop('last_code_sent')
    if 'requires_verification' in session:
        session.pop('requires_verification')
    
    return True, "Verification successful"

def is_verification_required(user_id):
    """
    Check if verification is required for a user.
    
    Args:
        user_id (int): User ID
        
    Returns:
        bool: True if verification is required, False otherwise
    """
    # Check if user has enabled 2FA
    user = User.query.get(user_id)
    if not user or not user.two_factor_enabled:
        return False
    
    # Check if user has been verified recently
    if 'verified_user_id' in session and session['verified_user_id'] == user_id:
        last_verified = session.get('last_verified', 0)
        current_time = int(time.time())
        
        # Verification lasts for 30 days on the same browser
        if current_time - last_verified < 30 * 24 * 60 * 60:
            return False
    
    return True

def mark_verified(user_id):
    """
    Mark a user as verified.
    
    Args:
        user_id (int): User ID
    """
    session['verified_user_id'] = user_id
    session['last_verified'] = int(time.time())