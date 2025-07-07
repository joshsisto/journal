from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response, current_app, send_file, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail
from sqlalchemy import func, or_, and_, desc
from sqlalchemy.exc import SQLAlchemyError
import pytz
import json
import re
import os
import uuid
from security import limiter  # Import limiter for rate limiting

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag, Photo, JournalTemplate, TemplateQuestion, Location, WeatherData
from export_utils import format_entry_for_text, format_multi_entry_filename
from email_utils import send_password_reset_email, send_email_change_confirmation
from emotions import get_emotions_by_category
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)
from services.journal_service import create_quick_entry, create_guided_entry
from services.weather_service import weather_service
from validators import sanitize_input

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)
tag_bp = Blueprint('tag', __name__)
export_bp = Blueprint('export', __name__)
ai_bp = Blueprint('ai', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Authentication routes
@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Rate limiting
def register():
    from validators import (
        sanitize_username, sanitize_email, validate_password,
        ValidationError
    )
    from email_utils import send_email
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
@limiter.limit("5 per minute")  # Rate limiting
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
@limiter.limit("1/minute")  # Strict rate limiting
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


# Journal routes
@journal_bp.route('/')
@login_required
def index():
    # Redirect to dashboard
    return redirect(url_for('journal.dashboard'))


@journal_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with immediate writing and compact design"""
    page = request.args.get('page', 1, type=int)
    entries_per_page = 20  # Show more entries per page for better overview
    
    # Get entries query for current user
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Paginate entries
    paginated_entries = query.order_by(JournalEntry.created_at.desc()).paginate(
        page=page, per_page=entries_per_page, error_out=False
    )
    entries = paginated_entries.items
    
    # Load available templates
    from models import JournalTemplate
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'dashboard.html', 
        entries=entries,
        paginated_entries=paginated_entries,
        system_templates=system_templates,
        user_templates=user_templates
    )


@journal_bp.route('/dashboard', methods=['POST'])
@login_required
def dashboard_post():
    """Handle journal entry submission from dashboard (both quick and guided)"""
    entry_type = request.form.get('entry_type', 'quick')
    template_id = request.form.get('template_id', '').strip()
    location_data = request.form.get('location_data', '').strip()
    weather_data = request.form.get('weather_data', '').strip()
    
    
    if entry_type == 'guided':
        # Handle guided journal entry
        try:
            # Create the journal entry
            entry = JournalEntry(
                user_id=current_user.id,
                content='',  # Guided entries store content in responses
                entry_type='guided',
                template_id=int(template_id) if template_id else None
            )
            db.session.add(entry)
            db.session.flush()  # Get the entry ID
            
            # Handle location and weather data
            location_record = None
            weather_record = None
            
            if location_data:
                try:
                    loc_data = json.loads(location_data)
                    location_record = Location(
                        latitude=loc_data.get('latitude'),
                        longitude=loc_data.get('longitude'),
                        address=loc_data.get('address', ''),
                        city='Unknown',  # Will be updated by location service
                        state='Unknown'
                    )
                    db.session.add(location_record)
                    db.session.flush()
                    entry.location_id = location_record.id
                except (json.JSONDecodeError, KeyError) as e:
                    current_app.logger.warning(f"Invalid location data: {e}")
            
            if weather_data:
                try:
                    weather_info = json.loads(weather_data)
                    weather_record = WeatherData(
                        temperature=weather_info.get('temperature'),
                        weather_condition=weather_info.get('condition', ''),
                        humidity=weather_info.get('humidity'),
                        journal_entry_id=entry.id
                    )
                    db.session.add(weather_record)
                    db.session.flush()
                    entry.weather_id = weather_record.id
                except (json.JSONDecodeError, KeyError) as e:
                    current_app.logger.warning(f"Invalid weather data: {e}")
            
            # Store guided responses
            guided_responses = []
            
            if template_id:
                # Load template questions and process responses
                from models import JournalTemplate, TemplateQuestion
                template = JournalTemplate.query.get(int(template_id))
                if template:
                    entry_content_set = False
                    for question in template.questions.order_by(TemplateQuestion.question_order):
                        response_value = request.form.get(question.question_id, '').strip()
                        if response_value:
                            guided_responses.append(GuidedResponse(
                                journal_entry_id=entry.id,
                                question_id=question.question_id,
                                question_text=question.question_text,
                                response=response_value
                            ))
                            
                            # Set main content from first text response or content/day questions
                            if not entry_content_set and (
                                'content' in question.question_id.lower() or 
                                'day' in question.question_id.lower() or
                                question.question_type == 'text'
                            ):
                                entry.content = response_value
                                entry_content_set = True
            else:
                # Default guided questions
                question_texts = {
                    'feeling_scale': 'How are you feeling?',
                    'additional_emotions': 'Select emotions',
                    'feeling_reason': 'Why do you feel that way?',
                    'about_day': 'Tell me about your day',
                    'exercise': 'Did you exercise today?',
                    'exercise_type': 'What type of workout?',
                    'anything_else': 'Anything else to discuss?'
                }
                
                for question_id, question_text in question_texts.items():
                    response_value = request.form.get(question_id, '').strip()
                    
                    # Skip exercise_type if exercise wasn't "Yes"
                    if question_id == 'exercise_type':
                        exercise_response = request.form.get('exercise', '').strip()
                        if exercise_response != 'Yes':
                            continue
                    
                    if response_value:
                        guided_responses.append(GuidedResponse(
                            journal_entry_id=entry.id,
                            question_id=question_id,
                            question_text=question_text,
                            response=response_value
                        ))
                        
                        # Set main content from about_day for entry content
                        if question_id == 'about_day':
                            entry.content = response_value
            
            # Add all responses to session
            for response in guided_responses:
                db.session.add(response)
            
            db.session.commit()
            flash('Guided journal entry saved successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving guided entry: {str(e)}")
            flash('Error saving guided entry. Please try again.', 'error')
    else:
        # Handle quick journal entry
        content = request.form.get('content', '').strip()
        if content:
            try:
                entry = JournalEntry(
                    user_id=current_user.id,
                    content=content,
                    entry_type='quick'
                )
                db.session.add(entry)
                db.session.flush()
                
                # Handle location and weather data for quick entries too
                if location_data:
                    try:
                        loc_data = json.loads(location_data)
                        location_record = Location(
                            latitude=loc_data.get('latitude'),
                            longitude=loc_data.get('longitude'),
                            address=loc_data.get('address', ''),
                            city='Unknown',
                            state='Unknown'
                        )
                        db.session.add(location_record)
                        db.session.flush()
                        entry.location_id = location_record.id
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid location data: {e}")
                
                if weather_data:
                    try:
                        weather_info = json.loads(weather_data)
                        weather_record = WeatherData(
                            temperature=weather_info.get('temperature'),
                            weather_condition=weather_info.get('condition', ''),
                            humidity=weather_info.get('humidity'),
                            journal_entry_id=entry.id
                        )
                        db.session.add(weather_record)
                        db.session.flush()
                        entry.weather_id = weather_record.id
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid weather data: {e}")
                
                db.session.commit()
                flash('Journal entry saved successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving quick entry: {str(e)}")
                flash('Error saving entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))


@api_bp.route('/templates/<int:template_id>/questions')
@login_required
def get_template_questions(template_id):
    """API endpoint to get questions for a specific template"""
    from models import JournalTemplate, TemplateQuestion
    
    # Get template and verify access
    template = JournalTemplate.query.get_or_404(template_id)
    
    # Check if user has access to this template (system templates or own templates)
    if not template.is_system and template.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # Get questions for this template
    questions = []
    for question in template.questions.order_by(TemplateQuestion.question_order):
        questions.append({
            'question_id': question.question_id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'required': question.required,
            'properties': question.properties
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'questions': questions
    })


@journal_bp.route('/create_template')
@login_required
def create_template():
    """Template creation page"""
    return render_template('journal/create_template.html')


@journal_bp.route('/dashboard/legacy')
@login_required
def dashboard_legacy():
    """Legacy dashboard with full calendar and filtering features"""
    return render_template("dashboard_legacy.html")


@journal_bp.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    """View individual journal entry with options to delete or have AI conversation"""
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    return render_template(
        'view_entry.html',
        entry=entry
    )


@journal_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Delete a journal entry"""
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    try:
        # Clear weather record references before deletion (if any)
        if entry.weather_id:
            weather_record = db.session.get(WeatherData, entry.weather_id)
            if weather_record and weather_record.journal_entry_id == entry.id:
                weather_record.journal_entry_id = None

        # Clear any other weather records referencing this entry
        WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
        
        # Delete guided responses if any
        if entry.guided_responses:
            for response in entry.guided_responses:
                db.session.delete(response)
        
        # Delete the entry itself
        db.session.delete(entry)
        db.session.commit()
        
        flash('Journal entry deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting entry {entry_id}: {str(e)}")
        flash('Error deleting entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))
