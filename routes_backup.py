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
import base64
from security import limiter  # Import limiter for rate limiting

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag, Photo, JournalTemplate, TemplateQuestion, Location, WeatherData, entry_tags
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
import ai_utils

def save_photo_from_base64(base64_data, entry_id):
    """Save a base64 encoded photo to disk and return the filename."""
    try:
        # Remove the data URL prefix if it exists
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        
        # Create photos directory if it doesn't exist
        photos_dir = os.path.join(current_app.static_folder, 'photos')
        os.makedirs(photos_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"entry_{entry_id}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(photos_dir, filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return filename
        
    except Exception as e:
        current_app.logger.error(f"Error saving photo: {str(e)}")
        return None

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


@journal_bp.route('/journal/guided', methods=['GET'])
@login_required
def guided_journal():
    """Display the guided journal entry form."""
    from models import JournalTemplate
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template('journal/guided.html', 
                         system_templates=system_templates,
                         user_templates=user_templates)

def dashboard_post_guided():
    """Handle guided journal entry submission (extracted from dashboard_post)."""
    template_id = request.form.get('template_id', '').strip()
    location_data = request.form.get('location_data', '').strip()
    weather_data = request.form.get('weather_data', '').strip()
    
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
            question_responses = [
                ('feeling_scale', 'How are you feeling today? (1-10)', 'number'),
                ('feeling_reason', 'What made you feel this way?', 'text'),
                ('daily_highlight', 'What was the best part of your day?', 'text'),
                ('challenge_overcome', 'Did you overcome any challenges today?', 'text'),
                ('gratitude', 'What are you grateful for today?', 'text'),
                ('tomorrow_goal', 'What do you want to accomplish tomorrow?', 'text'),
                ('additional_emotions', 'Additional emotions', 'emotions'),
                ('exercise', 'Did you exercise today?', 'boolean'),
                ('exercise_type', 'What type of exercise?', 'text'),
                ('exercise_duration', 'How long did you exercise? (minutes)', 'number'),
                ('sleep_hours', 'How many hours did you sleep last night?', 'number'),
                ('mood_summary', 'How would you describe your overall mood?', 'text')
            ]
            
            entry_content_set = False
            for question_id, question_text, question_type in question_responses:
                response_value = request.form.get(question_id, '').strip()
                if response_value:
                    guided_responses.append(GuidedResponse(
                        journal_entry_id=entry.id,
                        question_id=question_id,
                        question_text=question_text,
                        response=response_value
                    ))
                    
                    # Use the first meaningful text response as the main content
                    if not entry_content_set and question_type == 'text' and len(response_value) > 10:
                        entry.content = response_value
                        entry_content_set = True
        
        # Add guided responses to session
        for response in guided_responses:
            db.session.add(response)
        
        # Handle tags
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        
        try:
            new_tags = json.loads(new_tags_json) if new_tags_json else []
        except json.JSONDecodeError:
            new_tags = []
        
        # Add existing tags
        if tag_ids:
            from models import Tag
            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag and tag.user_id == current_user.id:
                    entry.tags.append(tag)
        
        # Create new tags
        for tag_name in new_tags:
            if tag_name.strip():
                from models import Tag
                new_tag = Tag(name=tag_name.strip(), user_id=current_user.id)
                db.session.add(new_tag)
                db.session.flush()
                entry.tags.append(new_tag)
        
        db.session.commit()
        flash('Guided journal entry saved successfully!', 'success')
        return redirect(url_for('journal.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating guided journal entry: {e}")
        flash('An error occurred while saving your entry. Please try again.', 'error')
        return redirect(url_for('journal.dashboard'))

@journal_bp.route('/journal/guided', methods=['POST'])
@login_required
def guided_journal_post():
    """Handle guided journal entry submission."""
    return dashboard_post_guided()

@journal_bp.route('/dashboard', methods=['POST'])
@login_required
def dashboard_post():
    """Handle journal entry submission from dashboard (both quick and guided)"""
    entry_type = request.form.get('entry_type', 'quick')
    template_id = request.form.get('template_id', '').strip()
    location_data = request.form.get('location_data', '').strip()
    weather_data = request.form.get('weather_data', '').strip()
    photo_data = request.form.get('photo_data', '').strip()
    
    
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
                        name=loc_data.get('name', ''),
                        latitude=loc_data.get('latitude'),
                        longitude=loc_data.get('longitude'),
                        address=loc_data.get('address', ''),
                        city=loc_data.get('city', 'Unknown'),
                        state=loc_data.get('state', 'Unknown'),
                        country=loc_data.get('country', ''),
                        postal_code=loc_data.get('postal_code', ''),
                        location_type=loc_data.get('location_type', 'manual')
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
            
            # Handle photo data
            if photo_data:
                try:
                    photo_info = json.loads(photo_data)
                    if 'data' in photo_info:
                        # Save photo to disk
                        photo_filename = save_photo_from_base64(photo_info['data'], entry.id)
                        if photo_filename:
                            photo_record = Photo(
                                journal_entry_id=entry.id,
                                filename=photo_filename,
                                original_filename=f"photo_{entry.id}.jpg"
                            )
                            db.session.add(photo_record)
                except (json.JSONDecodeError, KeyError) as e:
                    current_app.logger.warning(f"Invalid photo data: {e}")
            
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
                            name=loc_data.get('name', ''),
                            latitude=loc_data.get('latitude'),
                            longitude=loc_data.get('longitude'),
                            address=loc_data.get('address', ''),
                            city=loc_data.get('city', 'Unknown'),
                            state=loc_data.get('state', 'Unknown'),
                            country=loc_data.get('country', ''),
                            postal_code=loc_data.get('postal_code', ''),
                            location_type=loc_data.get('location_type', 'manual')
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
                
                # Handle photo data for quick entries
                if photo_data:
                    try:
                        photo_info = json.loads(photo_data)
                        if 'data' in photo_info:
                            # Save photo to disk
                            photo_filename = save_photo_from_base64(photo_info['data'], entry.id)
                            if photo_filename:
                                photo_record = Photo(
                                    journal_entry_id=entry.id,
                                    filename=photo_filename,
                                    original_filename=f"photo_{entry.id}.jpg"
                                )
                                db.session.add(photo_record)
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid photo data: {e}")
                
                db.session.commit()
                flash('Journal entry saved successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving quick entry: {str(e)}")
                flash('Error saving entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))


# AI conversation routes
@ai_bp.route('/chat', methods=['POST'])
@login_required
def ai_chat():
    """Handle AI chat messages from dashboard and individual entries."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
        
        conversation_history = data.get('conversation_history', [])
        entry_id = data.get('entry_id')  # For individual entry conversations
        
        # Get user's recent journal entries for context
        recent_entries = JournalEntry.query.filter_by(user_id=current_user.id)\
            .order_by(JournalEntry.created_at.desc())\
            .limit(20).all()
        
        # Build context for AI
        context = {
            'user_id': current_user.id,
            'username': current_user.username,
            'recent_entries': [],
            'conversation_history': conversation_history,
            'specific_entry': None
        }
        
        # Add recent entries to context
        for entry in recent_entries:
            entry_data = {
                'id': entry.id,
                'content': entry.content,
                'created_at': entry.created_at.isoformat(),
                'entry_type': entry.entry_type
            }
            
            # Add guided responses if available
            if entry.entry_type == 'guided':
                entry_data['guided_responses'] = [
                    {
                        'question': response.question_text,
                        'answer': response.response
                    }
                    for response in entry.guided_responses
                ]
            
            context['recent_entries'].append(entry_data)
        
        # If this is about a specific entry, add more details
        if entry_id:
            specific_entry = JournalEntry.query.filter_by(
                id=entry_id, 
                user_id=current_user.id
            ).first()
            
            if specific_entry:
                context['specific_entry'] = {
                    'id': specific_entry.id,
                    'content': specific_entry.content,
                    'created_at': specific_entry.created_at.isoformat(),
                    'entry_type': specific_entry.entry_type,
                    'guided_responses': [
                        {
                            'question': response.question_text,
                            'answer': response.response
                        }
                        for response in specific_entry.guided_responses
                    ] if specific_entry.entry_type == 'guided' else []
                }
        
        # Generate AI response (placeholder for now)
        ai_response = generate_ai_response(message, context)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
        
    except Exception as e:
        current_app.logger.error(f"AI chat error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your message'
        }), 500


def generate_ai_response(message, context):
    """Generate AI response based on message and context."""
    import re
    from datetime import datetime, timedelta
    
    user_entries_count = len(context['recent_entries'])
    message_lower = message.lower()
    entries = context['recent_entries']
    specific_entry = context['specific_entry']
    
    # Helper function to analyze entries
    def analyze_entries_for_keywords(keywords):
        matching_entries = []
        for entry in entries:
            content = entry['content'].lower()
            if any(keyword in content for keyword in keywords):
                matching_entries.append(entry)
        return matching_entries
    
    def get_recent_entries_summary():
        if not entries:
            return "You haven't written any journal entries yet."
        
        recent_count = len([e for e in entries if (datetime.now() - datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))).days <= 7])
        return f"You have {user_entries_count} recent entries, with {recent_count} from the past week."
    
    def analyze_emotions():
        emotion_words = ['happy', 'sad', 'angry', 'excited', 'anxious', 'calm', 'stressed', 'grateful', 'frustrated', 'peaceful', 'overwhelmed', 'content', 'disappointed', 'proud', 'lonely', 'confident']
        emotion_mentions = {}
        
        for entry in entries:
            content = entry['content'].lower()
            for emotion in emotion_words:
                if emotion in content:
                    emotion_mentions[emotion] = emotion_mentions.get(emotion, 0) + 1
        
        if emotion_mentions:
            top_emotions = sorted(emotion_mentions.items(), key=lambda x: x[1], reverse=True)[:3]
            return f"Looking at your entries, I notice you've mentioned: {', '.join([f'{emotion} ({count} times)' for emotion, count in top_emotions])}."
        return "I don't see many explicit emotion words in your recent entries."
    
    def find_patterns():
        if len(entries) < 2:
            return "I need more entries to identify patterns."
        
        # Analyze writing times
        morning_entries = sum(1 for e in entries if 6 <= datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).hour < 12)
        evening_entries = sum(1 for e in entries if 18 <= datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).hour < 24)
        
        time_pattern = ""
        if morning_entries > evening_entries:
            time_pattern = "You tend to write more in the mornings. "
        elif evening_entries > morning_entries:
            time_pattern = "You tend to write more in the evenings. "
        
        # Analyze content length
        avg_length = sum(len(e['content']) for e in entries) / len(entries)
        length_insight = f"Your entries average {int(avg_length)} characters. "
        
        return time_pattern + length_insight
    
    # Handle specific entry context
    if specific_entry:
        entry_date = datetime.fromisoformat(specific_entry['created_at'].replace('Z', '+00:00')).strftime('%B %d, %Y')
        entry_content = specific_entry['content']
        
        if 'what' in message_lower and ('think' in message_lower or 'about' in message_lower):
            return f"Looking at your entry from {entry_date}, I can see you wrote about {entry_content[:100]}{'...' if len(entry_content) > 100 else ''}. What stands out to me is the tone and themes you've explored. What specific aspect would you like to discuss?"
        
        elif 'mood' in message_lower or 'feel' in message_lower:
            emotions = analyze_emotions()
            return f"In your entry from {entry_date}, {emotions} What was driving these feelings that day?"
        
        elif 'summary' in message_lower or 'summarize' in message_lower:
            return f"Your entry from {entry_date} covers: {entry_content[:200]}{'...' if len(entry_content) > 200 else ''}. The main themes seem to be around your daily experiences and reflections."
        
        else:
            return f"I'm looking at your entry from {entry_date}. It's {len(entry_content)} characters long and covers some interesting thoughts. What would you like to explore about this entry?"
    
    # Greeting responses - only for actual greetings, not analysis requests
    if any(greeting in message_lower for greeting in ['hello', 'hi', 'hey', 'good morning', 'good evening']) and not any(analysis_word in message_lower for analysis_word in ['tell me', 'what', 'analyze', 'about', 'think', 'something']):
        summary = get_recent_entries_summary()
        return f"Hello! {summary} I'm here to help you reflect on your journaling journey. What would you like to explore?"
    
    # Mood and emotion analysis
    if any(word in message_lower for word in ['mood', 'feel', 'emotion', 'happy', 'sad', 'anxious', 'stress']):
        emotions = analyze_emotions()
        return f"Let me analyze your emotional patterns. {emotions} Would you like me to dive deeper into any specific emotions or time periods?"
    
    # Pattern and trend analysis - expanded to catch more conversational phrases
    if any(phrase in message_lower for phrase in [
        'pattern', 'trend', 'habit', 'frequency', 'when do i', 'how often',
        'analyze my patterns', 'what patterns', 'any patterns', 'patterns you see',
        'habits you notice', 'trends you see', 'recurring', 'consistent',
        'tell me about my patterns', 'patterns in my'
    ]):
        patterns = find_patterns()
        return f"I can see some interesting patterns in your journaling. {patterns} What patterns are you most curious about?"
    
    # Theme and content analysis
    if any(phrase in message_lower for phrase in [
        'theme', 'topic', 'write about', 'subject', 'content',
        'what do i write about', 'what themes', 'common themes',
        'what topics', 'subjects i cover', 'content analysis'
    ]):
        common_words = {}
        for entry in entries:
            words = re.findall(r'\b\w+\b', entry['content'].lower())
            for word in words:
                if len(word) > 3:  # Skip short words
                    common_words[word] = common_words.get(word, 0) + 1
        
        if common_words:
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:5]
            return f"Looking at your writing themes, you frequently mention: {', '.join([word for word, count in top_words])}. These seem to be important topics in your life right now."
        return "I'd need to analyze your entries more to identify key themes."
    
    # General analysis request - catches broader conversational patterns
    if any(phrase in message_lower for phrase in [
        'analyze my', 'tell me about my', 'what about my', 'describe my',
        'summary of my', 'overview of my', 'look at my', 'review my',
        'examine my', 'evaluate my', 'assess my', 'study my',
        'interesting about', 'notable about', 'significant about'
    ]):
        patterns = find_patterns()
        emotions = analyze_emotions()
        
        # Get theme info too
        common_words = {}
        for entry in entries:
            words = re.findall(r'\b\w+\b', entry['content'].lower())
            for word in words:
                if len(word) > 3:
                    common_words[word] = common_words.get(word, 0) + 1
        
        theme_info = ""
        if common_words:
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:3]
            theme_info = f" Your most common themes include: {', '.join([word for word, count in top_words])}."
        
        return f"Here's my analysis of your journaling: {patterns} {emotions}{theme_info} What specific aspect would you like to explore further?"
    
    # Insight and reflection requests - expanded to catch more phrases
    if any(phrase in message_lower for phrase in [
        'insight', 'reflection', 'analysis', 'what do you see', 'notice',
        'what can you tell me', 'what stands out', 'tell me something',
        'what do you think', 'your thoughts', 'observe', 'what have you found',
        'what do you notice', 'give me insights', 'what insights'
    ]):
        patterns = find_patterns()
        emotions = analyze_emotions()
        return f"Here's what I notice about your journaling: {patterns} From an emotional perspective: {emotions} What aspects of these insights resonate with you?"
    
    # Time-based questions
    if any(word in message_lower for word in ['today', 'yesterday', 'this week', 'recently', 'lately']):
        recent_entries = [e for e in entries if (datetime.now() - datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))).days <= 7]
        if recent_entries:
            return f"Looking at your recent entries from the past week, I see {len(recent_entries)} entries. The topics you've been exploring include themes around your daily experiences. What's been on your mind lately?"
        return "I don't see any very recent entries. How has your week been going?"
    
    # Progress and growth questions
    if any(word in message_lower for word in ['progress', 'growth', 'improve', 'better', 'change']):
        if len(entries) >= 3:
            return f"Based on your {user_entries_count} entries, I can see your journaling journey evolving. Your writing style and the depth of reflection seem to be developing. What changes have you noticed in yourself?"
        return "With more entries over time, I'll be able to better track your personal growth and progress."
    
    # Questions about specific topics
    if any(word in message_lower for word in ['work', 'job', 'career']):
        work_entries = analyze_entries_for_keywords(['work', 'job', 'career', 'office', 'boss', 'colleague'])
        if work_entries:
            return f"I found {len(work_entries)} entries where you mentioned work-related topics. It seems like work plays a significant role in your reflections. What aspects of your work life would you like to explore?"
        return "I don't see many work-related mentions in your recent entries. How has your professional life been?"
    
    if any(word in message_lower for word in ['relationship', 'family', 'friend', 'partner']):
        relationship_entries = analyze_entries_for_keywords(['family', 'friend', 'partner', 'relationship', 'love', 'boyfriend', 'girlfriend', 'spouse'])
        if relationship_entries:
            return f"I see relationships are important in your journaling - {len(relationship_entries)} entries mention people in your life. What relationship dynamics have been on your mind?"
        return "Relationships don't appear frequently in your recent entries. How are your connections with others?"
    
    # Catch-all for conversational requests that might not be caught above
    if any(phrase in message_lower for phrase in [
        'what do you think', 'tell me something', 'anything interesting',
        'what can you', 'what would you', 'do you see', 'can you tell',
        'what have you', 'something about', 'thoughts on', 'opinion on',
        'what\'s interesting', 'what\'s notable', 'what\'s significant'
    ]):
        patterns = find_patterns()
        emotions = analyze_emotions()
        
        # Get theme info
        common_words = {}
        for entry in entries:
            words = re.findall(r'\b\w+\b', entry['content'].lower())
            for word in words:
                if len(word) > 3:
                    common_words[word] = common_words.get(word, 0) + 1
        
        theme_info = ""
        if common_words:
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:3]
            theme_info = f" Your most frequent topics are: {', '.join([word for word, count in top_words])}."
        
        return f"Here's what I find interesting about your journaling: {patterns} {emotions}{theme_info} What would you like to explore more deeply?"
    
    # Default response with actual insights
    if entries:
        patterns = find_patterns()
        recent_summary = get_recent_entries_summary()
        return f"I'm here to help you reflect on your journaling. {recent_summary} {patterns} I can analyze your emotions, identify patterns, discuss themes, or explore specific entries. What interests you most?"
    else:
        return "I'd love to help you reflect on your journaling, but I don't see any entries yet. Once you start writing, I can help you identify patterns, analyze emotions, and provide insights about your thoughts and experiences."


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
        
        # Flush to ensure weather references are cleared before deleting entry
        db.session.flush()
        
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


@journal_bp.route('/tags')
@login_required
def manage_tags():
    """View and manage tags"""
    # Get all tags for the current user
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    
    # Count entries per tag
    tag_stats = []
    for tag in tags:
        entry_count = db.session.query(entry_tags).filter_by(tag_id=tag.id).count()
        tag_stats.append({
            'tag': tag,
            'entry_count': entry_count
        })
    
    return render_template('journal/tags.html', tag_stats=tag_stats)


@journal_bp.route('/templates')
@login_required
def templates():
    """View and manage journal templates"""
    # Get user templates
    user_templates = JournalTemplate.query.filter_by(
        user_id=current_user.id,
        is_system=False
    ).order_by(JournalTemplate.name).all()
    
    # Get system templates
    system_templates = JournalTemplate.query.filter_by(
        is_system=True
    ).order_by(JournalTemplate.name).all()
    
    return render_template('journal/templates.html', 
                         user_templates=user_templates,
                         system_templates=system_templates)


@journal_bp.route('/map')
@login_required
def map():
    """View journal entries on a map"""
    # Get all entries with location data
    entries_with_location = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).filter(JournalEntry.location_id.isnot(None)).all()
    
    # Prepare location data for the map
    locations = []
    for entry in entries_with_location:
        if entry.location and entry.location.latitude and entry.location.longitude:
            locations.append({
                'id': entry.id,
                'lat': entry.location.latitude,
                'lng': entry.location.longitude,
                'title': entry.location.name or f"{entry.location.city}, {entry.location.state}",
                'date': entry.created_at.strftime('%B %d, %Y'),
                'preview': entry.content[:100] + '...' if len(entry.content) > 100 else entry.content
            })
    
    return render_template('journal/map.html', locations=locations)


# Weather and Location API endpoints
@api_bp.route('/weather/current', methods=['POST'])
@login_required
def get_weather():
    """Get current weather for coordinates"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing coordinates'}), 400
            
        weather_data = weather_service.get_weather_by_coordinates(latitude, longitude)
        
        if weather_data:
            return jsonify(weather_data)
        else:
            return jsonify({'error': 'Weather data unavailable'}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error fetching weather: {e}")
        return jsonify({'error': 'Weather service error'}), 500


@api_bp.route('/location/reverse-geocode', methods=['POST'])
@login_required
def reverse_geocode():
    """Reverse geocode coordinates to location"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing coordinates'}), 400
            
        location_info = weather_service.reverse_geocode(latitude, longitude)
        
        if location_info:
            return jsonify(location_info)
        else:
            return jsonify({'error': 'Location information unavailable'}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error reverse geocoding: {e}")
        return jsonify({'error': 'Geocoding service error'}), 500


@api_bp.route('/location/search', methods=['POST'])
@login_required
def search_location():
    """Search for location by name"""
    try:
        data = request.get_json()
        location_name = data.get('location_name')
        
        if not location_name:
            return jsonify({'error': 'Missing location name'}), 400
            
        # First try to geocode the location
        coordinates = weather_service.geocode_location(location_name)
        
        if coordinates:
            latitude, longitude = coordinates
            # Get detailed location info
            location_info = weather_service.reverse_geocode(latitude, longitude)
            
            if location_info:
                location_info['latitude'] = latitude
                location_info['longitude'] = longitude
                return jsonify(location_info)
            else:
                # Just return coordinates if reverse geocoding fails
                return jsonify({
                    'latitude': latitude,
                    'longitude': longitude,
                    'name': location_name
                })
        else:
            return jsonify({'error': 'Location not found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error searching location: {e}")
        return jsonify({'error': 'Location search error'}), 500


@api_bp.route('/location/<int:location_id>', methods=['GET'])
@login_required
def get_location(location_id):
    """Get location by ID"""
    try:
        location = Location.query.get_or_404(location_id)
        
        location_data = {
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'city': location.city,
            'state': location.state,
            'country': location.country,
            'address': location.address
        }
        
        return jsonify(location_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting location: {e}")
        return jsonify({'error': 'Location not found'}), 404
