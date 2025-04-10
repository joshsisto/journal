"""
Email utility functions for sending emails from the application.

This module provides functions for sending various types of emails including:
- Password reset emails
- Email change confirmation
"""
from flask import current_app
from flask_mail import Message, Mail
from threading import Thread

def send_async_email(app, msg):
    """Send email asynchronously to avoid blocking the main thread.
    
    Args:
        app: Flask application instance
        msg: Email message to send
    """
    with app.app_context():
        mail = Mail(app)
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body=None, sender=None):
    """Send an email using the configured mail server.
    
    Args:
        subject (str): Email subject line
        recipients (list): List of recipient email addresses
        text_body (str): Plain text version of the email
        html_body (str, optional): HTML version of the email
        sender (str, optional): Sender email address
    """
    app = current_app._get_current_object()
    
    # Get mail configuration with defaults
    default_sender = app.config.get('MAIL_DEFAULT_SENDER', 'noreply@journal-app.com')
    
    # Create the message
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=text_body,
        html=html_body,
        sender=sender or default_sender
    )
    
    # Send email asynchronously
    Thread(target=send_async_email, args=(app, msg)).start()

def send_password_reset_email(user, token):
    """Send password reset email to a user.
    
    Args:
        user (User): User model instance
        token (str): Password reset token
    """
    # Get configuration with defaults
    app_name = current_app.config.get('APP_NAME', 'Journal App')
    # Force the use of the production URL for emails
    app_url = "https://journal.joshsisto.com"
    
    reset_url = f"{app_url}/reset-password/{token}"
    
    subject = f"{app_name} - Password Reset"
    
    # Plain text email
    text_body = f"""
Hello {user.username},

To reset your password, please visit the following link:
{reset_url}

If you did not request a password reset, please ignore this email.

Thank you,
{app_name} Team
    """
    
    # HTML email
    html_body = f"""
<p>Hello {user.username},</p>
<p>To reset your password, please <a href="{reset_url}">click here</a>.</p>
<p>Alternatively, you can paste the following link in your browser's address bar:</p>
<p>{reset_url}</p>
<p>If you did not request a password reset, please ignore this email.</p>
<p>Thank you,<br>{app_name} Team</p>
    """
    
    send_email(subject, [user.email], text_body, html_body)

def send_email_change_confirmation(user, token):
    """Send email change confirmation email.
    
    Args:
        user (User): User model instance
        token (str): Email change token
    """
    # Get configuration with defaults
    app_name = current_app.config.get('APP_NAME', 'Journal App')
    # Force the use of the production URL for emails
    app_url = "https://journal.joshsisto.com"
    
    confirm_url = f"{app_url}/confirm-email-change/{token}"
    
    subject = f"{app_name} - Confirm Email Change"
    
    # Plain text email
    text_body = f"""
Hello {user.username},

Please confirm your email change by visiting the following link:
{confirm_url}

If you did not request this change, please ignore this email and ensure your account password is secure.

Thank you,
{app_name} Team
    """
    
    # HTML email
    html_body = f"""
<p>Hello {user.username},</p>
<p>Please confirm your email change by <a href="{confirm_url}">clicking here</a>.</p>
<p>Alternatively, you can paste the following link in your browser's address bar:</p>
<p>{confirm_url}</p>
<p>If you did not request this change, please ignore this email and ensure your account password is secure.</p>
<p>Thank you,<br>{app_name} Team</p>
    """
    
    # Send to the new email address
    send_email(subject, [user.new_email], text_body, html_body)