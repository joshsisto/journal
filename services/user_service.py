from models import db, User
from validators import sanitize_username, sanitize_email, validate_password
from email_utils import send_email_change_confirmation, send_password_reset_email
from flask import current_app
import pytz

def register_user(username, email_input, password, timezone):
    try:
        # Sanitize inputs
        username = sanitize_username(username)
        email = None
        if email_input:
            email = sanitize_email(email_input)

        # Validate password
        validate_password(password)

        # Validate timezone
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            timezone = 'UTC'  # Default to UTC if invalid

        # Check if username exists
        if User.query.filter_by(username=username).first():
            return None, 'Username already exists.'

        # Check if email exists (if provided)
        if email and User.query.filter_by(email=email).first():
            return None, 'Email already registered.'

        # Check for common passwords
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'welcome']
        if password.lower() in common_passwords:
            return None, 'Please choose a stronger password.'

        # Create new user
        new_user = User(
            username=username,
            timezone=timezone,
            email=email,
            is_email_verified=False
        )
        new_user.set_password(password)

        # Generate email verification token if email provided
        verification_token = None
        if email:
            verification_token = new_user.generate_email_verification_token()

        db.session.add(new_user)
        db.session.commit()

        current_app.logger.info(f'New user registered: {username}')

        # Send verification email if email was provided
        if email and verification_token:
            try:
                app_name = current_app.config.get('APP_NAME', 'Journal App')
                app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
                verify_url = f"{app_url}/verify-email/{verification_token}"
                subject = f"{app_name} - Verify Your Email"
                text_body = f'Hello {new_user.username},...'
                html_body = f'<p>Hello {new_user.username},...</p>'
                send_email(subject, [email], text_body, html_body)
                return new_user, 'Registration successful. Please check your email to verify your address, then log in.'
            except Exception as e:
                current_app.logger.error(f"Failed to send verification email: {str(e)}")
                return new_user, 'Registration successful, but we could not send a verification email. You can verify your email later from settings.'
        else:
            return new_user, 'Registration successful. Please log in.'

    except ValidationError as e:
        return None, str(e)
    except Exception as e:
        current_app.logger.error(f'Registration error: {str(e)}')
        return None, f'Registration error: {str(e)}'

def authenticate_user(username, password):
    """Authenticates a user."""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

def update_user_timezone(user_id, timezone):
    """Updates a user's timezone."""
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        return False, 'Invalid timezone selected.'

    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    user.timezone = timezone
    db.session.commit()
    return True, 'Timezone updated successfully.'

def change_user_password(user_id, current_password, new_password, confirm_password):
    """Changes a user's password."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    if not user.check_password(current_password):
        return False, 'Current password is incorrect.'

    if new_password != confirm_password:
        return False, 'New passwords do not match.'

    try:
        validate_password(new_password)
    except ValidationError as e:
        return False, str(e)

    common_passwords = ['password', '123456', 'qwerty', 'admin', 'welcome']
    if new_password.lower() in common_passwords:
        return False, 'Please choose a stronger password.'

    if user.check_password(new_password):
        return False, 'New password must be different from current password.'

    user.set_password(new_password)
    db.session.commit()
    return True, 'Password updated successfully.'

def change_user_email(user_id, password, new_email, confirm_email):
    """Initiates an email change for a user."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    if not user.check_password(password):
        return False, 'Password is incorrect.'

    if new_email != confirm_email:
        return False, 'Email addresses do not match.'

    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != user.id:
        return False, 'This email address is already in use.'

    token = user.generate_email_change_token(new_email)
    db.session.commit()

    send_email_change_confirmation(user, token)

    return True, 'A confirmation link has been sent to your new email address. Please check your inbox.'

def add_user_email(user_id, password, email):
    """Adds an email to a user's account."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    if user.email:
        return False, 'You already have an email address. Use the change email form instead.'

    if not email or not password:
        return False, 'Email and password are required.'

    if not user.check_password(password):
        return False, 'Password is incorrect.'

    try:
        email = sanitize_email(email)
    except Exception as e:
        return False, f'Invalid email address: {str(e)}'

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return False, 'This email address is already in use.'

    user.email = email
    verification_token = user.generate_email_verification_token()
    db.session.commit()

    try:
        app_name = current_app.config.get('APP_NAME', 'Journal App')
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        verify_url = f"{app_url}/verify-email/{verification_token}"
        subject = f"{app_name} - Verify Your Email"
        text_body = f'Hello {user.username},...'
        html_body = f'<p>Hello {user.username},...</p>'
        send_email(subject, [email], text_body, html_body)
        return True, 'Email address added. Please check your inbox to verify your email.'
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return True, 'Email address added, but we could not send a verification email. You can resend it from settings.'

def resend_verification_email(user_id):
    """Resends the email verification link to the user."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    if not user.email:
        return False, 'You need to add an email address first.'

    if user.is_email_verified:
        return False, 'Your email is already verified.'

    verification_token = user.generate_email_verification_token()
    db.session.commit()

    try:
        app_name = current_app.config.get('APP_NAME', 'Journal App')
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        verify_url = f"{app_url}/verify-email/{verification_token}"
        subject = f"{app_name} - Verify Your Email"
        text_body = f'Hello {user.username},...'
        html_body = f'<p>Hello {user.username},...</p>'
        send_email(subject, [user.email], text_body, html_body)
        return True, 'Verification email sent. Please check your inbox.'
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return False, 'Could not send verification email. Please try again later.'

def request_password_reset(email):
    """Initiates a password reset for a user."""
    user = User.query.filter_by(email=email).first()
    if user:
        token = user.generate_reset_token()
        db.session.commit()
        send_password_reset_email(user, token)
    return 'If your email address exists in our database, you will receive a password reset link at your email address.'

def reset_password(token, password, confirm_password):
    """Resets a user's password."""
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.verify_reset_token(token):
        return False, 'Invalid or expired reset link.'

    if password != confirm_password:
        return False, 'Passwords do not match.'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters long.'

    user.set_password(password)
    user.clear_reset_token()
    db.session.commit()
    return True, 'Your password has been reset successfully. You can now log in with your new password.'



def add_user_email(user_id, password, email):
    """Adds an email to a user's account."""
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    if user.email:
        return False, 'You already have an email address. Use the change email form instead.'

    if not email or not password:
        return False, 'Email and password are required.'

    if not user.check_password(password):
        return False, 'Password is incorrect.'

    try:
        email = sanitize_email(email)
    except Exception as e:
        return False, f'Invalid email address: {str(e)}'

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return False, 'This email address is already in use.'

    user.email = email
    verification_token = user.generate_email_verification_token()
    db.session.commit()

    try:
        app_name = current_app.config.get('APP_NAME', 'Journal App')
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        verify_url = f"{app_url}/verify-email/{verification_token}"
        subject = f"{app_name} - Verify Your Email"
        text_body = f'Hello {user.username},...'
        html_body = f'<p>Hello {user.username},...</p>'
        send_email(subject, [email], text_body, html_body)
        return True, 'Email address added. Please check your inbox to verify your email.'
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return True, 'Email address added, but we could not send a verification email. You can resend it from settings.'



def update_user_timezone(user_id, timezone):
    """Updates a user's timezone.

    Args:
        user_id (int): The ID of the user to update.
        timezone (str): The new timezone string.

    Returns:
        tuple: A tuple containing (success_boolean, message_string).
    """
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        return False, 'Invalid timezone selected.'

    user = User.query.get(user_id)
    if not user:
        return False, 'User not found.'

    user.timezone = timezone
    db.session.commit()
    return True, 'Timezone updated successfully.'


def authenticate_user(username, password):
    """Authenticates a user."""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

