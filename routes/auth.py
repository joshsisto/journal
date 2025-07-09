"""Authentication routes for the journal application."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
import pytz

from models import db, User
from security import limiter
from email_utils import send_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    from validators import (
        sanitize_username, sanitize_email, validate_password,
        ValidationError
    )
    from forms import RegistrationForm
    
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    # Get common timezones for the form
    common_timezones = [(tz, tz) for tz in pytz.common_timezones]
    form = RegistrationForm()
    form.timezone.choices = common_timezones
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Get form data (already validated by WTForms)
                username = form.username.data
                email_input = form.email.data.strip() if form.email.data else ''
                password = form.password.data
                timezone = form.timezone.data
                
                # Debug print inputs
                print(f"Registration attempt: username={username}, email_input={email_input}, timezone={timezone}")
                
                # Email is now optional
                email = None
                if email_input:
                    email = sanitize_email(email_input)
                
                # Debug print sanitized email
                print(f"Sanitized email: {email}")
                
                # Additional validation
                validate_password(password)
                
                # Validate timezone
                try:
                    pytz.timezone(timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    timezone = 'UTC'  # Default to UTC if invalid
                
                # Check if username exists
                user = User.query.filter_by(username=username).first()
                if user:
                    flash('Username already exists.', 'danger')
                    return render_template('register.html', form=form, timezones=common_timezones)
                
                # Check if email exists (if provided)
                if email:
                    user = User.query.filter_by(email=email).first()
                    if user:
                        flash('Email already registered.', 'danger')
                        return render_template('register.html', form=form, timezones=common_timezones)
                
                # Check for common passwords
                common_passwords = ['password', '123456', 'qwerty', 'admin', 'welcome']
                if password.lower() in common_passwords:
                    flash('Please choose a stronger password.', 'danger')
                    return render_template('register.html', form=form, timezones=common_timezones)
                
                # Create new user with timezone - explicitly set all fields
                new_user = User()
                new_user.username = username
                new_user.timezone = timezone
                if email:  # Only set email if provided
                    new_user.email = email
                else:
                    new_user.email = None  # Explicitly set to None
                    
                # Set is_email_verified based on whether email was provided
                new_user.is_email_verified = False
                
                new_user.set_password(password)
                print(f"Creating user: username={username}, email={new_user.email}, timezone={timezone}")
                
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
                        # Get configuration with defaults
                        app_name = current_app.config.get('APP_NAME', 'Journal App')
                        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
                        
                        # Force production URL for emails
                        app_url = "https://journal.joshsisto.com"
                        
                        verify_url = f"{app_url}/verify-email/{verification_token}"
                        
                        subject = f"{app_name} - Verify Your Email"
                        
                        # Plain text email
                        text_body = f"""
Hello {new_user.username},

Please verify your email address by visiting the following link:
{verify_url}

This link will expire in 24 hours.

If you did not create an account with us, you can safely ignore this email.

Thank you,
{app_name} Team
                        """
                        
                        # HTML email
                        html_body = f"""
<p>Hello {new_user.username},</p>
<p>Please verify your email address by <a href="{verify_url}">clicking here</a>.</p>
<p>Alternatively, you can paste the following link in your browser's address bar:</p>
<p>{verify_url}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not create an account with us, you can safely ignore this email.</p>
<p>Thank you,<br>{app_name} Team</p>
                        """
                        
                        send_email(subject, [email], text_body, html_body)
                        
                        flash('Registration successful. Please check your email to verify your address, then log in.', 'success')
                    except Exception as e:
                        current_app.logger.error(f"Failed to send verification email: {str(e)}")
                        flash('Registration successful, but we could not send a verification email. You can verify your email later from settings.', 'warning')
                else:
                    flash('Registration successful. Please log in.', 'success')
                    
                return redirect(url_for('auth.login'))
                
            except ValidationError as e:
                flash(str(e), 'danger')
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f'Database error during registration: {str(e)}')
                flash('Registration failed due to a database error. Please try again.', 'danger')
            except Exception as e:
                db.session.rollback()
                import traceback
                error_details = traceback.format_exc()
                current_app.logger.error(f'Unexpected registration error: {str(e)}\n{error_details}')
                
                # Debug log the exact error
                print(f'Registration error detail: {str(e)} (Type: {type(e).__name__})')
                print(f'Traceback: {error_details}')
                
                # More user-friendly error message
                flash(f'Registration error: {str(e)}', 'danger')
        else:
            # Form validation failed - errors are already attached to form fields
            print(f"Form validation failed. Errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'danger')
    
    return render_template('register.html', form=form, timezones=common_timezones)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    import time
    from validators import sanitize_text
    from two_factor import is_verification_required, send_verification_code
    from forms import LoginForm
    
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Add slight delay to prevent timing attacks
            time.sleep(0.1)
            
            # Get form data
            username = sanitize_text(form.username.data)
            password = form.password.data
            remember = form.remember.data
            
            # Attempt to find the user
            user = User.query.filter_by(username=username).first()
            
            # Check if user exists and password is correct
            if not user or not user.check_password(password):
                current_app.logger.warning(f'Failed login attempt for user: {username} from IP: {request.remote_addr}')
                flash('Invalid username or password.', 'danger')
                return render_template('login.html', form=form)
            
            # Store user ID in session for 2FA
            session['pre_verified_user_id'] = user.id
            session['pre_verified_remember'] = remember
            
            # Check if 2FA is required
            if user.two_factor_enabled and is_verification_required(user.id):
                # Send verification code
                success, message = send_verification_code(user.id)
                
                if not success:
                    flash(f'Failed to send verification code: {message}', 'danger')
                    return render_template('login.html', form=form)
                
                # Set flag in session
                session['requires_verification'] = True
                
                # Redirect to verification page
                return redirect(url_for('auth.verify_login'))
            
            # Log successful login
            current_app.logger.info(f'User logged in: {username} from IP: {request.remote_addr}')
            
            # Check for 'next' parameter to prevent open redirect
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                next_page = None  # Only allow relative paths
            
            # Login the user and redirect
            login_user(user, remember=remember)
            return redirect(next_page or url_for('journal.index'))
        else:
            # Form validation failed
            print(f"Login form validation failed. Errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'danger')
    
    return render_template('login.html', form=form)


@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify_login():
    """Verify login with 2FA code."""
    from two_factor import verify_code, mark_verified
    
    # Check if verification is required
    if 'requires_verification' not in session or 'pre_verified_user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session.get('pre_verified_user_id')
    remember = session.get('pre_verified_remember', False)
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        flash('Invalid session. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        
        # Get verification code
        code = request.form.get('code', '')
        
        # Verify code
        success, message = verify_code(user_id, code)
        
        if not success:
            flash(f'Verification failed: {message}', 'danger')
            return redirect(url_for('auth.verify_login'))
        
        # Mark as verified
        mark_verified(user_id)
        
        # Log successful login with 2FA
        current_app.logger.info(f'User {user.username} completed 2FA verification from IP: {request.remote_addr}')
        
        # Login user
        login_user(user, remember=remember)
        
        # Clear verification session
        if 'requires_verification' in session:
            session.pop('requires_verification')
        if 'pre_verified_user_id' in session:
            session.pop('pre_verified_user_id')
        if 'pre_verified_remember' in session:
            session.pop('pre_verified_remember')
        
        # Redirect to dashboard
        return redirect(url_for('journal.index'))
    
    return render_template('auth/verify.html')


@auth_bp.route('/resend-code', methods=['POST'])
@limiter.limit("1/minute")
def resend_code():
    """Resend verification code."""
    from two_factor import send_verification_code
    
    # Check if verification is required
    if 'requires_verification' not in session or 'pre_verified_user_id' not in session:
        return jsonify({'success': False, 'message': 'Invalid session'})
    
    user_id = session.get('pre_verified_user_id')
    
    # Resend code
    success, message = send_verification_code(user_id)
    
    return jsonify({'success': success, 'message': message})


@auth_bp.route('/toggle-two-factor', methods=['POST'])
@login_required
def toggle_two_factor():
    """Toggle two-factor authentication."""
    
    # Get enabled state
    enabled = 'enabled' in request.form
    
    # Update user
    current_user.two_factor_enabled = enabled
    db.session.commit()
    
    if enabled:
        flash('Two-factor authentication has been enabled.', 'success')
        current_app.logger.info(f'User {current_user.username} enabled 2FA')
    else:
        flash('Two-factor authentication has been disabled.', 'warning')
        current_app.logger.info(f'User {current_user.username} disabled 2FA')
    
    return redirect(url_for('auth.settings'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/settings')
@login_required
def settings():
    """User settings page."""
    return render_template('auth/settings.html')