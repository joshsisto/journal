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

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag, Photo, JournalTemplate, TemplateQuestion
from export_utils import format_entry_for_text, format_multi_entry_filename
from email_utils import send_password_reset_email, send_email_change_confirmation
from emotions import get_emotions_by_category
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)
from services.journal_service import create_quick_entry, create_guided_entry
from validators import sanitize_input

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)
tag_bp = Blueprint('tag', __name__)
export_bp = Blueprint('export', __name__)
ai_bp = Blueprint('ai', __name__)

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
    # Get tag filter if present
    tag_id = request.args.get('tag')
    page = request.args.get('page', 1, type=int)
    entries_per_page = request.args.get('per_page', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    selected_year = request.args.get('year')
    selected_month = request.args.get('month')
    
    # Base query
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply tag filter if provided
    if tag_id:
        tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
        query = query.filter(JournalEntry.tags.any(Tag.id == tag_id))
        selected_tag = tag
    else:
        selected_tag = None
    
    # Apply date filters if provided
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(JournalEntry.created_at >= start_date_obj)
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date fully
            end_date_obj = end_date_obj + timedelta(days=1)
            query = query.filter(JournalEntry.created_at < end_date_obj)
        except ValueError:
            end_date = None
    
    # Apply year/month filter if provided
    if selected_year and selected_month:
        try:
            year = int(selected_year)
            month = int(selected_month)
            start_of_month = datetime(year, month, 1)
            if month == 12:
                end_of_month = datetime(year + 1, 1, 1)
            else:
                end_of_month = datetime(year, month + 1, 1)
            
            query = query.filter(
                JournalEntry.created_at >= start_of_month,
                JournalEntry.created_at < end_of_month
            )
        except (ValueError, TypeError):
            selected_year = None
            selected_month = None
    
    # Count total entries for stats
    total_entries = query.count()
    
    # Get paginated entries
    paginated_entries = query.order_by(JournalEntry.created_at.desc()).paginate(
        page=page, per_page=entries_per_page, error_out=False
    )
    entries = paginated_entries.items
    
    # Get all user tags for filter menu
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get feeling data for guided entries
    feeling_data = {}
    guided_entry_ids = [entry.id for entry in entries if entry.entry_type == 'guided']
    if guided_entry_ids:
        feeling_responses = GuidedResponse.query.filter(
            GuidedResponse.journal_entry_id.in_(guided_entry_ids),
            GuidedResponse.question_id == 'feeling_scale'
        ).all()
        
        for resp in feeling_responses:
            feeling_data[resp.journal_entry_id] = resp.response
    
    # Get timeline data by manual processing (SQLite compatibility)
    all_entries = JournalEntry.query.filter_by(user_id=current_user.id).all()
    
    # Dictionary to store counts by year and month
    entry_counts = {}
    for entry in all_entries:
        year = entry.created_at.strftime('%Y')
        month = entry.created_at.strftime('%m')
        
        if year not in entry_counts:
            entry_counts[year] = {}
        
        if month not in entry_counts[year]:
            entry_counts[year][month] = 0
            
        entry_counts[year][month] += 1
    
    # Format timeline data for the template
    timeline_data = []
    for year in sorted(entry_counts.keys()):
        for month in sorted(entry_counts[year].keys()):
            timeline_data.append({
                'year': year,
                'month': month,
                'count': entry_counts[year][month]
            })
    
    # Format archive data for the template
    archive_data = {}
    for year in sorted(entry_counts.keys()):
        archive_data[year] = []
        for month in sorted(entry_counts[year].keys()):
            archive_data[year].append({
                'month': month,
                'count': entry_counts[year][month]
            })
    
    # If no month selected, default to current month for calendar
    if not selected_year or not selected_month:
        current_datetime = datetime.now()
        selected_year = current_datetime.strftime('%Y')
        selected_month = current_datetime.strftime('%m')
        
    # Calculate first day of month (0 = Sunday, ... 6 = Saturday)
    # This calculation is done here instead of in the template
    first_date = datetime(int(selected_year), int(selected_month), 1)
    weekday = first_date.weekday()  # Monday=0...Sunday=6
    first_day_of_week = (weekday + 1) % 7  # Convert to Sunday-based (Sunday=0)
    
    # Get daily data for the selected month or current month
    year_int = int(selected_year)
    month_int = int(selected_month)
    
    start_of_month = datetime(year_int, month_int, 1)
    if month_int == 12:
        end_of_month = datetime(year_int + 1, 1, 1)
    else:
        end_of_month = datetime(year_int, month_int + 1, 1)
    
    # Get day parameter if present
    selected_day = request.args.get('day')
    
    # If a day is selected, filter entries for that specific day
    if selected_day:
        try:
            day_int = int(selected_day)
            
            # Get the user's timezone
            user_timezone = pytz.timezone(current_user.timezone)
            
            # Create datetime objects in user's local timezone
            local_start_date = datetime(year_int, month_int, day_int)
            local_end_date = local_start_date + timedelta(days=1)
            
            # Convert local dates to UTC for database filtering
            utc_start_date = user_timezone.localize(local_start_date).astimezone(pytz.UTC).replace(tzinfo=None)
            utc_end_date = user_timezone.localize(local_end_date).astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Filter the query to show only entries from the selected day (in user's timezone)
            query = query.filter(
                JournalEntry.created_at >= utc_start_date,
                JournalEntry.created_at < utc_end_date
            )
            
            # Update entries and pagination
            paginated_entries = query.order_by(JournalEntry.created_at.desc()).paginate(
                page=page, per_page=entries_per_page, error_out=False
            )
            entries = paginated_entries.items
            
            # Update feeling data for the filtered entries
            feeling_data = {}
            guided_entry_ids = [entry.id for entry in entries if entry.entry_type == 'guided']
            if guided_entry_ids:
                feeling_responses = GuidedResponse.query.filter(
                    GuidedResponse.journal_entry_id.in_(guided_entry_ids),
                    GuidedResponse.question_id == 'feeling_scale'
                ).all()
                
                for resp in feeling_responses:
                    feeling_data[resp.journal_entry_id] = resp.response
        except (ValueError, TypeError, OverflowError):
            # Invalid day parameter, ignore
            selected_day = None
    
    # Get the user's timezone
    user_timezone = pytz.timezone(current_user.timezone)
    
    # Create datetime objects in user's local timezone for the month boundaries
    local_start_of_month = datetime(year_int, month_int, 1)
    if month_int == 12:
        local_end_of_month = datetime(year_int + 1, 1, 1)
    else:
        local_end_of_month = datetime(year_int, month_int + 1, 1)
    
    # Convert local dates to UTC for database comparison
    utc_start_of_month = user_timezone.localize(local_start_of_month).astimezone(pytz.UTC).replace(tzinfo=None)
    utc_end_of_month = user_timezone.localize(local_end_of_month).astimezone(pytz.UTC).replace(tzinfo=None)
    
    # Get entries for this month in user's timezone
    month_entries = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.created_at >= utc_start_of_month,
        JournalEntry.created_at < utc_end_of_month
    ).all()
    
    # Manual processing for daily counts using user's timezone
    daily_counts = {}
    days_with_entries = set()  # Track which days have entries
    
    for entry in month_entries:
        # Convert UTC timestamp to user's local timezone
        local_dt = pytz.UTC.localize(entry.created_at).astimezone(user_timezone)
        day = local_dt.strftime('%d')
        days_with_entries.add(int(day))
        if day not in daily_counts:
            daily_counts[day] = 0
        daily_counts[day] += 1
    
    # Format daily data
    for day in sorted(daily_counts.keys()):
        timeline_data.append({
            'year': selected_year,
            'month': selected_month,
            'day': day,
            'count': daily_counts[day]
        })
        
    # Debug info for timezone understanding
    # Uncomment if you need to debug timezone issues
    """
    print(f"User timezone: {current_user.timezone}")
    print(f"Days with entries: {days_with_entries}")
    print(f"Current month entries count: {len(month_entries)}")
    """
    
    return render_template(
        'dashboard.html', 
        entries=entries,
        paginated_entries=paginated_entries,
        tags=tags, 
        selected_tag=selected_tag,
        feeling_data=feeling_data,
        total_entries=total_entries,
        timeline_data=timeline_data,
        archive_data=archive_data,
        selected_year=selected_year,
        selected_month=selected_month,
        selected_day=selected_day,
        days_with_entries=days_with_entries,
        first_day_of_week=first_day_of_week,
        start_date=start_date,
        end_date=end_date,
        page=page,
        entries_per_page=entries_per_page
    )


@journal_bp.route('/journal/quick', methods=['GET', 'POST'])
@login_required
@sanitize_input
def quick_journal():
    if request.method == 'POST':
        
        # Get form data
        content = request.form.get('content', '')
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        photos = request.files.getlist('photos')
        
        # Use service function to create entry
        entry, error = create_quick_entry(
            user_id=current_user.id,
            content=content,
            tag_ids=tag_ids,
            new_tags_json=new_tags_json,
            photos=photos,
            allowed_file_func=allowed_file
        )
        
        if error:
            flash(error, 'danger')
            return redirect(url_for('journal.quick_journal'))
        
        flash('Journal entry saved successfully.', 'success')
        return redirect(url_for('journal.index'))
    
    # Get user's tags
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    return render_template('journal/quick.html', tags=tags)


@journal_bp.route('/journal/guided', methods=['GET', 'POST'])
@login_required
@sanitize_input
def guided_journal():
    # Get template_id from URL parameter or form
    template_id = request.args.get('template_id', type=int) or request.form.get('template_id', type=int)
    
    if request.method == 'POST':
        
        # Get form data
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        photos = request.files.getlist('photos')
        
        # Generate main content from responses (optional - could be empty)
        main_content = "Guided journal entry"  # Simple default content
        
        # Use service function to create entry
        entry, error = create_guided_entry(
            user_id=current_user.id,
            form_data=request.form,
            tag_ids=tag_ids,
            new_tags_json=new_tags_json,
            photos=photos,
            main_content=main_content,
            allowed_file_func=allowed_file,
            template_id=template_id
        )
        
        if error:
            flash(error, 'danger')
            return redirect(url_for('journal.guided_journal'))
        
        flash('Guided journal entry saved successfully.', 'success')
        return redirect(url_for('journal.index'))
    
    # Prepare context data for conditionals
    context = prepare_guided_journal_context()
    
    # Get questions based on template or default behavior
    if template_id:
        # Get all questions from the template
        questions = QuestionManager.get_questions(template_id)
        # Filter by conditions 
        questions = [q for q in questions if q['condition'](context)]
        selected_template = JournalTemplate.query.get(template_id)
    else:
        # Use original hardcoded questions for backward compatibility
        questions = QuestionManager.get_applicable_questions(context)
        selected_template = None
    
    # Format the time_since placeholder in questions
    for q in questions:
        if '{time_since}' in q.get('text', ''):
            q['text'] = q['text'].format(time_since=context['time_since'])
    
    # Get available templates for the template selector
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    # Get user's tags
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get emotions by category for the template
    emotions_by_category = get_emotions_by_category()
    
    return render_template(
        'journal/guided.html', 
        questions=questions, 
        tags=tags, 
        emotions_by_category=emotions_by_category,
        system_templates=system_templates,
        user_templates=user_templates,
        selected_template=selected_template,
        template_id=template_id
    )


@journal_bp.route('/templates')
@login_required
def templates():
    """Display available journal templates."""
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'journal/templates.html',
        system_templates=system_templates,
        user_templates=user_templates
    )


@journal_bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
@sanitize_input
def create_template():
    """Create a new custom template."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Template name is required.', 'danger')
            return redirect(url_for('journal.create_template'))
        
        # Create the template
        template = JournalTemplate(
            name=name,
            description=description,
            user_id=current_user.id,
            is_system=False
        )
        
        try:
            db.session.add(template)
            db.session.commit()
            flash(f'Template "{name}" created successfully!', 'success')
            return redirect(url_for('journal.edit_template', template_id=template.id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating template. Please try again.', 'danger')
            current_app.logger.error(f'Template creation error: {str(e)}')
    
    return render_template('journal/create_template.html')


@journal_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@sanitize_input
def edit_template(template_id):
    """Edit a custom template."""
    template = JournalTemplate.query.get_or_404(template_id)
    
    # Check permissions - user can only edit their own templates
    if template.user_id != current_user.id:
        flash('You can only edit your own templates.', 'danger')
        return redirect(url_for('journal.templates'))
    
    if request.method == 'POST':
        # Handle template updates and question management
        # This would be a complex form handler for the template editor
        # For now, just update basic template info
        template.name = request.form.get('name', template.name)
        template.description = request.form.get('description', template.description)
        
        try:
            db.session.commit()
            flash('Template updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating template.', 'danger')
            current_app.logger.error(f'Template update error: {str(e)}')
    
    return render_template(
        'journal/edit_template.html',
        template=template,
        questions=template.questions.order_by(TemplateQuestion.question_order).all()
    )


@journal_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a custom template."""
    template = JournalTemplate.query.get_or_404(template_id)
    
    # Check permissions
    if template.user_id != current_user.id:
        flash('You can only delete your own templates.', 'danger')
        return redirect(url_for('journal.templates'))
    
    if template.is_system:
        flash('System templates cannot be deleted.', 'danger')
        return redirect(url_for('journal.templates'))
    
    try:
        db.session.delete(template)
        db.session.commit()
        flash(f'Template "{template.name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting template.', 'danger')
        current_app.logger.error(f'Template deletion error: {str(e)}')
    
    return redirect(url_for('journal.templates'))


@journal_bp.route('/templates/<int:template_id>/questions/add', methods=['POST'])
@login_required
@sanitize_input
def add_question_to_template(template_id):
    """Add a new question to a template."""
    template = JournalTemplate.query.get_or_404(template_id)
    
    # Check permissions
    if template.user_id != current_user.id:
        flash('You can only edit your own templates.', 'danger')
        return redirect(url_for('journal.templates'))
    
    try:
        # Get form data
        question_text = request.form.get('question_text', '').strip()
        question_type = request.form.get('question_type', 'text')
        required = request.form.get('required') == 'on'
        condition_expression = request.form.get('condition_expression', '').strip()
        
        if not question_text:
            flash('Question text is required.', 'danger')
            return redirect(url_for('journal.edit_template', template_id=template_id))
        
        # Generate question_id from text
        import re
        question_id = re.sub(r'[^a-zA-Z0-9_]', '_', question_text.lower())[:50]
        question_id = f"custom_{question_id}_{len(template.questions.all()) + 1}"
        
        # Get next order number
        max_order = db.session.query(db.func.max(TemplateQuestion.question_order)).filter_by(template_id=template_id).scalar() or 0
        
        # Handle type-specific properties
        properties = {}
        if question_type == 'number':
            properties['min'] = int(request.form.get('min_value', 1))
            properties['max'] = int(request.form.get('max_value', 10))
        elif question_type == 'select':
            options = request.form.get('select_options', '').strip()
            if options:
                properties['options'] = [opt.strip() for opt in options.split('\n') if opt.strip()]
        
        # Create the question
        question = TemplateQuestion(
            template_id=template_id,
            question_id=question_id,
            question_text=question_text,
            question_type=question_type,
            question_order=max_order + 1,
            required=required,
            condition_expression=condition_expression if condition_expression else None
        )
        
        if properties:
            question.set_properties(properties)
        
        db.session.add(question)
        db.session.commit()
        
        flash(f'Question "{question_text}" added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error adding question. Please try again.', 'danger')
        current_app.logger.error(f'Question creation error: {str(e)}')
    
    return redirect(url_for('journal.edit_template', template_id=template_id))


@journal_bp.route('/templates/<int:template_id>/questions/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question_from_template(template_id, question_id):
    """Delete a question from a template."""
    template = JournalTemplate.query.get_or_404(template_id)
    question = TemplateQuestion.query.get_or_404(question_id)
    
    # Check permissions
    if template.user_id != current_user.id or question.template_id != template_id:
        flash('You can only edit your own templates.', 'danger')
        return redirect(url_for('journal.templates'))
    
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting question.', 'danger')
        current_app.logger.error(f'Question deletion error: {str(e)}')
    
    return redirect(url_for('journal.edit_template', template_id=template_id))


@journal_bp.route('/journal/view/<int:entry_id>')
@login_required
def view_entry(entry_id):
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    guided_responses = None
    if entry.entry_type == 'guided':
        guided_responses = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id
        ).all()
        
        # Get the original questions for context (fallback for older entries)
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Add question text to responses (prioritize stored question_text for template questions)
        for resp in guided_responses:
            if not resp.question_text:  # Only use fallback if question_text is empty/null
                resp.question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
    
    # Get all user tags for adding/removing tags
    all_tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get emotions categories for badge coloring
    emotions_by_category = get_emotions_by_category()
    positive_emotions = set(emotions_by_category.get('Positive', []))
    negative_emotions = set(emotions_by_category.get('Negative', []))
    
    return render_template('journal/view.html', 
                           entry=entry, 
                           guided_responses=guided_responses, 
                           all_tags=all_tags,
                           positive_emotions=positive_emotions,
                           negative_emotions=negative_emotions)


@journal_bp.route('/journal/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(entry)
    db.session.commit()
    
    flash('Journal entry deleted successfully.')
    return redirect(url_for('journal.index'))


@journal_bp.route('/journal/update_tags/<int:entry_id>', methods=['POST'])
@login_required
def update_entry_tags(entry_id):
    
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get the selected tag IDs from the form
    tag_ids = request.form.getlist('tags')
    
    # Get the corresponding Tag objects
    if tag_ids:
        tags = Tag.query.filter(
            Tag.id.in_(tag_ids),
            Tag.user_id == current_user.id
        ).all()
        entry.tags = tags
    else:
        entry.tags = []  # Remove all tags if none selected
    
    db.session.commit()
    
    flash('Entry tags updated successfully.')
    return redirect(url_for('journal.view_entry', entry_id=entry.id))


@journal_bp.route('/journal/exercise/check')
@login_required
def check_exercise():
    """API endpoint to check if user has exercised today."""
    return jsonify({
        'exercised_today': has_exercised_today()
    })


@journal_bp.route('/search', methods=['GET'])
@login_required
def search():
    """Search journal entries."""
    query = request.args.get('q', '').strip()
    tag_id = request.args.get('tag')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entry_type = request.args.get('type')
    sort_by = request.args.get('sort', 'recent')  # Default to sorting by most recent
    
    # Base query for user's journal entries
    search_query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if query:
        # Search in quick journal content
        quick_entries = search_query.filter(
            JournalEntry.content.ilike(f'%{query}%')
        )
        
        # Search in guided journal responses
        guided_entries = search_query.filter(
            JournalEntry.id.in_(
                db.session.query(GuidedResponse.journal_entry_id).filter(
                    GuidedResponse.response.ilike(f'%{query}%')
                )
            )
        )
        
        # Combine the results
        search_query = quick_entries.union(guided_entries)
    
    # Filter by tag if provided
    if tag_id:
        search_query = search_query.filter(JournalEntry.tags.any(Tag.id == tag_id))
    
    # Filter by date range if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            search_query = search_query.filter(JournalEntry.created_at >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date fully
            end_date = end_date + timedelta(days=1)
            search_query = search_query.filter(JournalEntry.created_at < end_date)
        except ValueError:
            pass
    
    # Filter by entry type if provided
    if entry_type and entry_type in ['quick', 'guided']:
        search_query = search_query.filter(JournalEntry.entry_type == entry_type)
    
    # Apply sorting
    if sort_by == 'oldest':
        search_query = search_query.order_by(JournalEntry.created_at.asc())
    else:  # Default to most recent
        search_query = search_query.order_by(JournalEntry.created_at.desc())
    
    # Get all entries that match the search criteria
    entries = search_query.all()
    
    # Get all user tags for filtering
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get currently selected tag if any
    selected_tag = None
    if tag_id:
        selected_tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
    
    # For guided entries, fetch the responses
    matched_responses = {}
    feeling_data = {}
    guided_entry_ids = [entry.id for entry in entries if entry.entry_type == 'guided']
    
    if guided_entry_ids:
        # Get all feeling scale responses for display
        feeling_responses = GuidedResponse.query.filter(
            GuidedResponse.journal_entry_id.in_(guided_entry_ids),
            GuidedResponse.question_id == 'feeling_scale'
        ).all()
        
        for resp in feeling_responses:
            feeling_data[resp.journal_entry_id] = resp.response
        
        # If searching, also get matching responses
        if query:
            responses = GuidedResponse.query.filter(
                GuidedResponse.journal_entry_id.in_(guided_entry_ids),
                GuidedResponse.response.ilike(f'%{query}%')
            ).all()
            
            # Get the original questions for context
            all_questions = QuestionManager.get_questions()
            question_map = {q['id']: q for q in all_questions}
            
            # Group responses by entry ID and add question text
            for resp in responses:
                resp.question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
                
                if resp.journal_entry_id not in matched_responses:
                    matched_responses[resp.journal_entry_id] = []
                
                matched_responses[resp.journal_entry_id].append(resp)
    
    return render_template(
        'search.html', 
        entries=entries, 
        tags=tags, 
        selected_tag=selected_tag,
        query=query,
        start_date=request.args.get('start_date', ''),
        end_date=request.args.get('end_date', ''),
        entry_type=entry_type,
        sort_by=sort_by,
        matched_responses=matched_responses,
        feeling_data=feeling_data
    )


@journal_bp.route('/mood_tracker', methods=['GET'])
@login_required
def mood_tracker():
    """Mood tracking visualization for journal entries."""
    # Import TimeUtils for timezone handling
    from time_utils import TimeUtils
    # Get filter parameters
    period = request.args.get('period', 'all')  # Default to show all entries
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Calculate date range based on selected period
    # Use TimeUtils to get today in user's local timezone
    local_today = TimeUtils.get_local_now()
    
    # Get the end of today in user's timezone, then convert to UTC for queries
    end_day_local = local_today.replace(hour=23, minute=59, second=59)
    end_date_obj = TimeUtils.get_user_timezone().localize(end_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    
    if period == 'week':
        # Get start of 7 days ago in user's timezone, then convert to UTC for queries
        start_day_local = (local_today - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    elif period == 'month':
        start_day_local = (local_today - timedelta(days=30)).replace(hour=0, minute=0, second=0)
        start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    elif period == 'quarter':
        start_day_local = (local_today - timedelta(days=90)).replace(hour=0, minute=0, second=0)
        start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    elif period == 'year':
        start_day_local = (local_today - timedelta(days=365)).replace(hour=0, minute=0, second=0)
        start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    elif period == 'all':
        # Use the date of the first entry
        first_entry = JournalEntry.query.filter_by(
            user_id=current_user.id
        ).order_by(JournalEntry.created_at.asc()).first()
        
        if first_entry:
            start_date_obj = first_entry.created_at.replace(hour=0, minute=0, second=0)  # Start of day
        else:
            start_date_obj = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0)  # Default to last 30 days if no entries
    elif period == 'custom':
        # Use custom date range if provided
        try:
            # Parse the date in local timezone
            start_day_local = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            # Convert to UTC for database query
            start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local).astimezone(pytz.UTC).replace(tzinfo=None)
        except (ValueError, TypeError):
            # Default to 30 days ago in user's timezone
            start_day_local = (local_today - timedelta(days=30)).replace(hour=0, minute=0, second=0)
            start_date_obj = TimeUtils.get_user_timezone().localize(start_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
            
        try:
            # Parse the end date in local timezone
            end_day_local = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            # Convert to UTC for database query
            end_date_obj = TimeUtils.get_user_timezone().localize(end_day_local).astimezone(pytz.UTC).replace(tzinfo=None)
        except (ValueError, TypeError):
            # Default to today in user's timezone
            end_day_local = local_today.replace(hour=23, minute=59, second=59)
            end_date_obj = TimeUtils.get_user_timezone().localize(end_day_local.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
    else:
        # Default to last 30 days
        start_date_obj = today - timedelta(days=30)
    
    # Format dates for template
    if not start_date and period == 'custom':
        start_date = start_date_obj.strftime('%Y-%m-%d')
    if not end_date and period == 'custom':
        end_date = today.strftime('%Y-%m-%d')
    
    # Get guided journal entries with feeling_scale responses in the date range
    # Use between for date ranges instead of <= to ensure we catch all entries
    entries = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.entry_type == 'guided',
        JournalEntry.created_at >= start_date_obj,
        JournalEntry.created_at <= end_date_obj + timedelta(days=1)  # Add a day to make sure we include end date fully
    ).order_by(JournalEntry.created_at.asc()).all()
    
    # Get entry IDs to query for feeling_scale responses
    entry_ids = [entry.id for entry in entries]
    
    # Add debug logging to the server console
    print(f"Date range: {start_date_obj} to {end_date_obj}")
    print(f"Found {len(entries)} entries in date range")
    for entry in entries:
        print(f"Entry {entry.id}: date={entry.created_at}, type={entry.entry_type}")
    
    # Query feeling_scale responses for these entries
    feeling_responses = GuidedResponse.query.filter(
        GuidedResponse.journal_entry_id.in_(entry_ids),
        GuidedResponse.question_id == 'feeling_scale'
    ).all()
    
    # Add debug logging for responses
    print(f"Found {len(feeling_responses)} feeling_scale responses")
    for resp in feeling_responses:
        print(f"Response for entry {resp.journal_entry_id}: value={resp.response}")
    
    # Additional emotional data
    emotion_responses = GuidedResponse.query.filter(
        GuidedResponse.journal_entry_id.in_(entry_ids),
        GuidedResponse.question_id == 'additional_emotions'
    ).all()
    
    feeling_reason_responses = GuidedResponse.query.filter(
        GuidedResponse.journal_entry_id.in_(entry_ids),
        GuidedResponse.question_id == 'feeling_reason'
    ).all()
    
    # Create dictionaries for easy lookups
    feeling_data = {}
    emotion_data = {}
    feeling_reason_data = {}
    entry_dates = {}
    
    for entry in entries:
        entry_dates[entry.id] = entry.created_at
        
    for resp in feeling_responses:
        try:
            feeling_data[resp.journal_entry_id] = int(resp.response)
        except (ValueError, TypeError):
            pass
            
    for resp in emotion_responses:
        try:
            if resp.response:
                # Try to parse JSON array of emotions
                try:
                    emotion_data[resp.journal_entry_id] = json.loads(resp.response)
                except json.JSONDecodeError:
                    # Handle comma-separated string format
                    emotion_data[resp.journal_entry_id] = [e.strip() for e in resp.response.split(',')]
        except Exception:
            pass
            
    for resp in feeling_reason_responses:
        feeling_reason_data[resp.journal_entry_id] = resp.response
    
    # Prepare data for chart
    mood_data = []
    print(f"Building mood_data from {len(feeling_data)} feeling_data entries")
    for entry_id, feeling_value in feeling_data.items():
        if entry_id in entry_dates:
            # Convert UTC timestamp to local timezone
            utc_datetime = entry_dates[entry_id]
            local_datetime = TimeUtils.utc_to_local(utc_datetime)
            
            mood_data.append({
                'entry_id': entry_id,
                'feeling_value': feeling_value,
                'created_at': local_datetime,  # Now using local time
                'utc_created_at': utc_datetime,  # Keep original for reference
                'emotions': emotion_data.get(entry_id, []),
                'feeling_reason': feeling_reason_data.get(entry_id, '')
            })
            print(f"Entry {entry_id}: UTC={utc_datetime}, Local={local_datetime}")
        else:
            print(f"Warning: Entry {entry_id} has feeling data but no entry_date")
    
    # Sort by date (using local time)
    mood_data.sort(key=lambda x: x['created_at'])
    
    # Prepare data for chart (using local time)
    dates = [entry['created_at'].strftime('%b %d') for entry in mood_data]  # More readable format (e.g. "Jan 15")
    friendly_dates = [entry['created_at'].strftime('%A, %b %d') for entry in mood_data]  # For tooltips (e.g. "Monday, Jan 15")
    mood_values = [entry['feeling_value'] for entry in mood_data]
    
    # Calculate statistics
    avg_mood = sum(mood_values) / len(mood_values) if mood_values else 0
    highest_mood = max(mood_values) if mood_values else 0
    lowest_mood = min(mood_values) if mood_values else 0
    
    # Get recent entries for display (limit to most recent 6)
    recent_entries = sorted(mood_data, key=lambda x: x['created_at'], reverse=True)[:6]
    
    # Get emotion categories for badge coloring
    emotions_by_category = get_emotions_by_category()
    positive_emotions = set(emotions_by_category.get('Positive', []))
    negative_emotions = set(emotions_by_category.get('Negative', []))
    
    return render_template(
        'mood_tracker.html',
        mood_data=mood_data,
        dates=dates,
        friendly_dates=friendly_dates,
        mood_values=mood_values,
        period=period,
        start_date=start_date,
        end_date=end_date,
        avg_mood=avg_mood,
        highest_mood=highest_mood,
        lowest_mood=lowest_mood,
        recent_entries=recent_entries,
        positive_emotions=positive_emotions,
        negative_emotions=negative_emotions
    )


@auth_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """Display user settings page."""
    # Get list of common timezones for the form
    common_timezones = pytz.common_timezones
    
    # Get user's tags for the settings page
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'settings.html', 
        timezones=common_timezones, 
        current_timezone=current_user.timezone,
        tags=tags
    )


@auth_bp.route('/settings/timezone', methods=['POST'])
@login_required
def update_timezone():
    """Update user timezone."""
    timezone = request.form.get('timezone')
    
    try:
        # Validate timezone
        pytz.timezone(timezone)
        
        # Update user's timezone
        current_user.timezone = timezone
        db.session.commit()
        
        flash('Timezone updated successfully.')
    except pytz.exceptions.UnknownTimeZoneError:
        flash('Invalid timezone selected.')
    
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    from validators import validate_password, ValidationError
    import time
    
    
    # Add slight delay to prevent timing attacks
    time.sleep(0.1)
    
    # Get form data
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validate current password
    if not current_user.check_password(current_password):
        current_app.logger.warning(f'Failed password change attempt for user: {current_user.username}')
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Validate new password
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('auth.settings'))
    
    try:
        validate_password(new_password)
    except ValidationError as e:
        flash(str(e), 'danger')
        return redirect(url_for('auth.settings'))
    
    # Check for common passwords
    common_passwords = ['password', '123456', 'qwerty', 'admin', 'welcome']
    if new_password.lower() in common_passwords:
        flash('Please choose a stronger password.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Prevent using the same password
    if current_user.check_password(new_password):
        flash('New password must be different from current password.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    
    current_app.logger.info(f'Password changed for user: {current_user.username}')
    flash('Password updated successfully.', 'success')
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/email', methods=['POST'])
@login_required
def change_email():
    """Initiate email change process."""
    
    password = request.form.get('password')
    new_email = request.form.get('new_email')
    confirm_email = request.form.get('confirm_email')
    
    # Validate inputs
    if not current_user.check_password(password):
        flash('Password is incorrect.', 'danger')
        return redirect(url_for('auth.settings'))
    
    if new_email != confirm_email:
        flash('Email addresses do not match.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Check if email is already in use
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != current_user.id:
        flash('This email address is already in use.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Generate token and update user
    token = current_user.generate_email_change_token(new_email)
    db.session.commit()
    
    # Send confirmation email
    send_email_change_confirmation(current_user, token)
    
    flash('A confirmation link has been sent to your new email address. Please check your inbox.', 'info')
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/add-email', methods=['POST'])
@login_required
def add_email():
    """Add email to an account that doesn't have one."""
    
    # Only allow adding email if user doesn't have one
    if current_user.email:
        flash('You already have an email address. Use the change email form instead.', 'warning')
        return redirect(url_for('auth.settings'))
    
    password = request.form.get('password')
    email = request.form.get('email')
    
    # Validate inputs
    if not email or not password:
        flash('Email and password are required.', 'danger')
        return redirect(url_for('auth.settings'))
    
    if not current_user.check_password(password):
        flash('Password is incorrect.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Validate email format
    try:
        from validators import sanitize_email
        email = sanitize_email(email)
    except Exception as e:
        flash(f'Invalid email address: {str(e)}', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Check if email is already in use
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('This email address is already in use.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Update user's email and generate verification token
    current_user.email = email
    verification_token = current_user.generate_email_verification_token()
    db.session.commit()
    
    # Send verification email
    try:
        app_name = current_app.config.get('APP_NAME', 'Journal App')
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        
        # Force production URL for emails
        app_url = "https://journal.joshsisto.com"
        
        verify_url = f"{app_url}/verify-email/{verification_token}"
        
        subject = f"{app_name} - Verify Your Email"
        
        # Plain text email
        text_body = f"""
Hello {current_user.username},

Please verify your email address by visiting the following link:
{verify_url}

This link will expire in 24 hours.

If you did not add this email to your account, please contact support.

Thank you,
{app_name} Team
        """
        
        # HTML email
        html_body = f"""
<p>Hello {current_user.username},</p>
<p>Please verify your email address by <a href="{verify_url}">clicking here</a>.</p>
<p>Alternatively, you can paste the following link in your browser's address bar:</p>
<p>{verify_url}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not add this email to your account, please contact support.</p>
<p>Thank you,<br>{app_name} Team</p>
        """
        
        from email_utils import send_email
        send_email(subject, [email], text_body, html_body)
        
        flash('Email address added. Please check your inbox to verify your email.', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        flash('Email address added, but we could not send a verification email. You can resend it from settings.', 'warning')
    
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/resend-verification', methods=['POST'])
@login_required
@limiter.limit("3/hour")  # Prevent abuse
def resend_verification():
    """Resend email verification link."""
    
    # Check if user has an email
    if not current_user.email:
        flash('You need to add an email address first.', 'warning')
        return redirect(url_for('auth.settings'))
    
    # Check if email is already verified
    if current_user.is_email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('auth.settings'))
    
    # Generate a new verification token
    verification_token = current_user.generate_email_verification_token()
    db.session.commit()
    
    # Send verification email
    try:
        app_name = current_app.config.get('APP_NAME', 'Journal App')
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        
        # Force production URL for emails
        app_url = "https://journal.joshsisto.com"
        
        verify_url = f"{app_url}/verify-email/{verification_token}"
        
        subject = f"{app_name} - Verify Your Email"
        
        # Plain text email
        text_body = f"""
Hello {current_user.username},

Please verify your email address by visiting the following link:
{verify_url}

This link will expire in 24 hours.

If you did not request this verification, please contact support.

Thank you,
{app_name} Team
        """
        
        # HTML email
        html_body = f"""
<p>Hello {current_user.username},</p>
<p>Please verify your email address by <a href="{verify_url}">clicking here</a>.</p>
<p>Alternatively, you can paste the following link in your browser's address bar:</p>
<p>{verify_url}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not request this verification, please contact support.</p>
<p>Thank you,<br>{app_name} Team</p>
        """
        
        from email_utils import send_email
        send_email(subject, [current_user.email], text_body, html_body)
        
        flash('Verification email sent. Please check your inbox.', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        flash('Could not send verification email. Please try again later.', 'danger')
    
    return redirect(url_for('auth.settings'))


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address with token."""
    # Find user by token
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user or not user.verify_email_verification_token(token):
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Mark email as verified
    user.complete_email_verification()
    db.session.commit()
    
    flash('Your email address has been verified successfully.', 'success')
    
    # If user is logged in, redirect to settings, otherwise to login
    if current_user.is_authenticated:
        return redirect(url_for('auth.settings'))
    else:
        return redirect(url_for('auth.login'))


@auth_bp.route('/confirm-email-change/<token>')
def confirm_email_change(token):
    """Confirm email change with token."""
    # Find user by token
    user = User.query.filter_by(email_change_token=token).first()
    
    if not user or not user.verify_email_change_token(token):
        flash('Invalid or expired confirmation link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Update email
    user.complete_email_change()
    db.session.commit()
    
    flash('Your email address has been updated successfully.', 'success')
    
    # If user is logged in, redirect to settings, otherwise to login
    if current_user.is_authenticated:
        return redirect(url_for('auth.settings'))
    else:
        return redirect(url_for('auth.login'))


@auth_bp.route('/request-reset', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Rate limiting
def request_reset():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Always show success message even if email not found (security)
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            
            # Send password reset email
            send_password_reset_email(user, token)
        
        flash('If your email address exists in our database, you will receive a password reset link at your email address.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/request_reset.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    # Find user by token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.request_reset'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate passwords
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        # Update password
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html')


# Tag Management Routes
@tag_bp.route('/tags', methods=['GET'])
@login_required
def manage_tags():
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template('tags/manage.html', tags=tags)


@tag_bp.route('/tags/add', methods=['POST'])
@login_required
@sanitize_input
def add_tag():
    from validators import sanitize_tag_name, validate_color_hex, ValidationError
    
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    
    if not name:
        flash('Tag name is required.', 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    try:
        # Validate and sanitize inputs
        name = sanitize_tag_name(name)
        color = validate_color_hex(color)
    except ValidationError as e:
        flash(str(e), 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    # Check if tag already exists
    existing_tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
    if existing_tag:
        flash(f'A tag named "{name}" already exists.', 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    # Create new tag
    tag = Tag(name=name, color=color, user_id=current_user.id)
    db.session.add(tag)
    db.session.commit()
    
    flash(f'Tag "{name}" created successfully.', 'success')
    return redirect(url_for('tag.manage_tags'))


@tag_bp.route('/tags/edit/<int:tag_id>', methods=['POST'])
@login_required
@sanitize_input
def edit_tag(tag_id):
    from validators import sanitize_tag_name, validate_color_hex, ValidationError
    
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
    
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    
    if not name:
        flash('Tag name is required.', 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    try:
        # Validate and sanitize inputs
        name = sanitize_tag_name(name)
        color = validate_color_hex(color)
    except ValidationError as e:
        flash(str(e), 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    # Check if a different tag with the same name exists
    existing_tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
    if existing_tag and existing_tag.id != tag.id:
        flash(f'A tag named "{name}" already exists.', 'danger')
        return redirect(url_for('tag.manage_tags'))
    
    # Update tag
    tag.name = name
    tag.color = color
    db.session.commit()
    
    flash(f'Tag "{name}" updated successfully.', 'success')
    return redirect(url_for('tag.manage_tags'))


@tag_bp.route('/tags/delete/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
    
    # Remove tag from all entries
    for entry in tag.entries:
        entry.tags.remove(tag)
    
    # Delete the tag
    db.session.delete(tag)
    db.session.commit()
    
    flash(f'Tag "{tag.name}" deleted successfully.', 'success')
    return redirect(url_for('tag.manage_tags'))


# Export routes
@export_bp.route('/export/entry/<int:entry_id>')
@login_required
def export_entry(entry_id):
    """Export a single journal entry as text."""
    # Get the entry
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get guided responses if needed
    guided_responses = None
    if entry.entry_type == 'guided':
        guided_responses = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id
        ).all()
        
        # Get the original questions for context
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Add question text to responses
        for resp in guided_responses:
            resp.question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
    
    # Format the entry content
    content = format_entry_for_text(entry, guided_responses, user_timezone=current_user.timezone)
    
    # Create a response with the text content
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=journal_entry_{entry.id}.txt'
    
    return response


@export_bp.route('/export/search')
@login_required
def export_search_entries():
    """Export journal entries based on search criteria."""
    query = request.args.get('q', '').strip()
    tag_id = request.args.get('tag')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entry_type = request.args.get('type')
    
    # Base query for user's journal entries
    search_query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply filters (same logic as in search route)
    if query:
        # Search in quick journal content
        quick_entries = search_query.filter(
            JournalEntry.content.ilike(f'%{query}%')
        )
        
        # Search in guided journal responses
        guided_entries = search_query.filter(
            JournalEntry.id.in_(
                db.session.query(GuidedResponse.journal_entry_id).filter(
                    GuidedResponse.response.ilike(f'%{query}%')
                )
            )
        )
        
        # Combine the results
        search_query = quick_entries.union(guided_entries)
    
    # Filter by tag if provided
    selected_tag = None
    if tag_id:
        selected_tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
        search_query = search_query.filter(JournalEntry.tags.any(Tag.id == tag_id))
    
    # Filter by date range if provided
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            search_query = search_query.filter(JournalEntry.created_at >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date fully
            end_date_obj = end_date_obj + timedelta(days=1)
            search_query = search_query.filter(JournalEntry.created_at < end_date_obj)
        except ValueError:
            pass
    
    # Filter by entry type if provided
    if entry_type and entry_type in ['quick', 'guided']:
        search_query = search_query.filter(JournalEntry.entry_type == entry_type)
    
    # Always sort by date for exports
    entries = search_query.order_by(JournalEntry.created_at.desc()).all()
    
    # Prepare filter info for filename
    filter_info = {
        'query': query,
        'tag': selected_tag,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return export_entries_as_text(entries, filter_info)


@export_bp.route('/export/all')
@login_required
def export_all_entries():
    """Export all journal entries."""
    # Get all entries sorted by date
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).all()
    
    return export_entries_as_text(entries)


def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_PHOTO_EXTENSIONS']


@journal_bp.route('/journal/photo/<int:photo_id>')
@login_required
def view_photo(photo_id):
    """Serve a photo file."""
    # First verify that the photo belongs to the current user
    photo = Photo.query.join(JournalEntry).filter(
        Photo.id == photo_id,
        JournalEntry.user_id == current_user.id
    ).first_or_404()
    
    # Build the file path with directory traversal protection
    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    # Validate filename and prevent directory traversal
    safe_filename = os.path.basename(photo.filename)
    if not safe_filename or safe_filename in ('.', '..') or '/' in safe_filename or '\\' in safe_filename:
        abort(404)
    photo_path = os.path.join(upload_folder, safe_filename)
    
    # Send the file
    return send_file(photo_path)


def export_entries_as_text(entries, filter_info=None):
    """Helper function to export entries as text."""
    # Build text content
    lines = []
    lines.append("JOURNAL ENTRIES EXPORT")
    lines.append("=====================")
    lines.append("")
    
    # Add export metadata
    if filter_info:
        if filter_info.get('tag'):
            lines.append(f"Filtered by tag: {filter_info['tag'].name}")
        if filter_info.get('query'):
            lines.append(f"Search results for: {filter_info['query']}")
        if filter_info.get('start_date') and filter_info.get('end_date'):
            lines.append(f"Date range: {filter_info['start_date']} to {filter_info['end_date']}")
        elif filter_info.get('start_date'):
            lines.append(f"From date: {filter_info['start_date']}")
        elif filter_info.get('end_date'):
            lines.append(f"Until date: {filter_info['end_date']}")
        lines.append("")
    
    lines.append(f"Total entries: {len(entries)}")
    lines.append(f"Export date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("=====================")
    lines.append("")
    
    # Bulk load guided responses to prevent N+1 queries
    entry_ids = [entry.id for entry in entries if entry.entry_type == 'guided']
    guided_responses_map = {}
    
    if entry_ids:
        # Single query to get all guided responses
        all_guided_responses = GuidedResponse.query.filter(
            GuidedResponse.journal_entry_id.in_(entry_ids)
        ).all()
        
        # Group responses by entry_id
        for resp in all_guided_responses:
            if resp.journal_entry_id not in guided_responses_map:
                guided_responses_map[resp.journal_entry_id] = []
            guided_responses_map[resp.journal_entry_id].append(resp)
        
        # Get the original questions for context (once)
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Add question text to all responses
        for responses in guided_responses_map.values():
            for resp in responses:
                resp.question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
    
    # Process each entry
    for entry in entries:
        # Get pre-loaded guided responses
        guided_responses = guided_responses_map.get(entry.id) if entry.entry_type == 'guided' else None
        
        # Format the entry and add to lines
        entry_text = format_entry_for_text(entry, guided_responses, user_timezone=current_user.timezone)
        lines.append(entry_text)
        lines.append("")
        lines.append("-" * 40)
        lines.append("")
    
    # Create a response with the text content
    response = make_response("\n".join(lines))
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    
    # Generate filename
    filename = format_multi_entry_filename(filter_info)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


# AI Conversation Routes
@ai_bp.route('/conversation/<int:entry_id>', methods=['GET'])
@login_required
def single_entry_conversation(entry_id):
    """AI conversation based on a single journal entry."""
    # Get the journal entry
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Format the date with timezone conversion
    from time_utils import TimeUtils
    entry_local_date = TimeUtils.format_datetime(entry.created_at)
    
    # Prepare data for the template
    entry_data = {
        'id': entry.id,
        'date': entry_local_date,
        'entry_type': entry.entry_type,
        'content': entry.content
    }
    
    # If it's a guided entry, get the responses
    if entry.entry_type == 'guided':
        guided_responses = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id
        ).all()
        
        # Get questions for context
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Format responses with questions
        responses_data = {}
        for resp in guided_responses:
            question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
            responses_data[question_text] = resp.response
            
            # Extract feeling value for display
            if resp.question_id == 'feeling_scale':
                try:
                    entry_data['feeling_value'] = int(resp.response)
                except (ValueError, TypeError):
                    pass
            
            # Extract emotions for display
            if resp.question_id == 'additional_emotions':
                try:
                    if resp.response:
                        try:
                            entry_data['emotions'] = json.loads(resp.response)
                        except json.JSONDecodeError:
                            entry_data['emotions'] = [e.strip() for e in resp.response.split(',') if e.strip()]
                except Exception:
                    pass
        
        entry_data['guided_responses'] = responses_data
    
    # Get emotions categories for badge styling
    emotions_by_category = get_emotions_by_category()
    positive_emotions = set(emotions_by_category.get('Positive', []))
    negative_emotions = set(emotions_by_category.get('Negative', []))
    
    return render_template(
        'ai/conversation.html',
        entry=entry_data,
        is_single_entry=True,
        conversation_type='single',
        entry_id=entry_id,
        positive_emotions=positive_emotions,
        negative_emotions=negative_emotions
    )


@ai_bp.route('/simple', methods=['GET'])
@login_required
def simple_ai_conversation():
    """Simple AI conversation with the most recent entry."""
    # Get the most recent entry
    entry = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).first()
    
    if not entry:
        flash("You don't have any journal entries yet.")
        return redirect(url_for('journal.dashboard'))
    
    # Format the date with timezone conversion
    from time_utils import TimeUtils
    entry_local_date = TimeUtils.format_datetime(entry.created_at)
    
    # Prepare data for the template
    entry_data = {
        'id': entry.id,
        'date': entry_local_date,
        'entry_type': entry.entry_type,
        'content': entry.content
    }
    
    # If it's a guided entry, get the responses
    if entry.entry_type == 'guided':
        guided_responses = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id
        ).all()
        
        # Get questions for context
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Format responses with questions
        responses_data = {}
        for resp in guided_responses:
            question_text = question_map.get(resp.question_id, {}).get('text', resp.question_id)
            responses_data[question_text] = resp.response
            
            # Extract feeling value for display
            if resp.question_id == 'feeling_scale':
                try:
                    entry_data['feeling_value'] = int(resp.response)
                except (ValueError, TypeError):
                    pass
            
            # Extract emotions for display
            if resp.question_id == 'additional_emotions':
                try:
                    if resp.response:
                        try:
                            entry_data['emotions'] = json.loads(resp.response)
                        except json.JSONDecodeError:
                            entry_data['emotions'] = [e.strip() for e in resp.response.split(',') if e.strip()]
                except Exception:
                    pass
        
        entry_data['guided_responses'] = responses_data
    
    # Get emotions categories for badge styling
    emotions_by_category = get_emotions_by_category()
    positive_emotions = set(emotions_by_category.get('Positive', []))
    negative_emotions = set(emotions_by_category.get('Negative', []))
    
    return render_template(
        'ai/conversation.html',
        entry=entry_data,
        is_single_entry=True,
        conversation_type='single',
        entry_id=entry.id,
        positive_emotions=positive_emotions,
        negative_emotions=negative_emotions
    )

@ai_bp.route('/test/conversation', methods=['GET'])
@login_required
def test_conversation():
    """Test page for AI conversation functionality."""
    # Get some recent entries for the select dropdown
    recent_entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    return render_template(
        'ai/test_conversation.html',
        recent_entries=recent_entries
    )

@ai_bp.route('/test/multiple', methods=['GET'])
@login_required
def test_multiple_conversation():
    """Test page for multiple entries AI conversation."""
    # Get the 5 most recent entries
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(5).all()
    
    # Format entries for template
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content
        }
        
        # For guided entries, get feeling value and emotions
        if entry.entry_type == 'guided':
            feeling_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='feeling_scale'
            ).first()
            
            if feeling_response:
                try:
                    entry_data['feeling_value'] = int(feeling_response.response)
                except (ValueError, TypeError):
                    pass
            
            emotions_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='additional_emotions'
            ).first()
            
            if emotions_response and emotions_response.response:
                try:
                    entry_data['emotions'] = json.loads(emotions_response.response)
                except json.JSONDecodeError:
                    entry_data['emotions'] = [e.strip() for e in emotions_response.response.split(',') if e.strip()]
                except Exception:
                    pass
                    
        entries_data.append(entry_data)
    
    print(f"Test multiple conversation with {len(entries_data)} entries")
    
    return render_template(
        'ai/multiple_conversation.html',
        entries=entries_data
    )

@ai_bp.route('/direct', methods=['GET'])
@login_required
def direct_ai_conversation():
    """Extra direct version of the multiple entries conversation."""
    # Get entries
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(3).all()
    
    # Format entries
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content
        }
        entries_data.append(entry_data)
    
    print(f"Direct AI conversation with {len(entries_data)} entries")
    return render_template('ai/direct_conversation.html', entries=entries_data)

@ai_bp.route('/bare', methods=['GET'])
@login_required
def bare_minimum_test():
    """Absolute bare minimum test page for AI conversations."""
    print("Rendering bare minimum test page")
    return render_template('ai/bare_minimum.html')

@ai_bp.route('/working', methods=['GET'])
@login_required
def working_multiple_conversation():
    """Working version of multiple entries conversation."""
    # Get the 10 most recent entries
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    # Format entries for template
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content
        }
        
        # For guided entries, get feeling value and emotions
        if entry.entry_type == 'guided':
            feeling_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='feeling_scale'
            ).first()
            
            if feeling_response:
                try:
                    entry_data['feeling_value'] = int(feeling_response.response)
                except (ValueError, TypeError):
                    pass
            
            emotions_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='additional_emotions'
            ).first()
            
            if emotions_response and emotions_response.response:
                try:
                    entry_data['emotions'] = json.loads(emotions_response.response)
                except json.JSONDecodeError:
                    entry_data['emotions'] = [e.strip() for e in emotions_response.response.split(',') if e.strip()]
                except Exception:
                    pass
        
        entries_data.append(entry_data)
    
    print(f"Working multiple conversation with {len(entries_data)} entries")
    return render_template('ai/working_multiple.html', entries=entries_data)

@ai_bp.route('/conversation/multiple', methods=['GET'])
@login_required
def multiple_entries_conversation():
    """Working multiple entries conversation (default)."""
    # Get the 10 most recent entries
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    # Format entries
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content or ""  # Ensure content is never None
        }
        
        # For guided entries, get feeling value and emotions
        if entry.entry_type == 'guided':
            feeling_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='feeling_scale'
            ).first()
            
            if feeling_response:
                try:
                    entry_data['feeling_value'] = int(feeling_response.response)
                except (ValueError, TypeError):
                    pass
            
            emotions_response = GuidedResponse.query.filter_by(
                journal_entry_id=entry.id,
                question_id='additional_emotions'
            ).first()
            
            if emotions_response and emotions_response.response:
                try:
                    entry_data['emotions'] = json.loads(emotions_response.response)
                except json.JSONDecodeError:
                    entry_data['emotions'] = [e.strip() for e in emotions_response.response.split(',') if e.strip()]
                except Exception:
                    pass
        
        entries_data.append(entry_data)
    
    print(f"Multiple entries conversation with {len(entries_data)} entries")
    return render_template('ai/chat_multiple.html', entries=entries_data)

@ai_bp.route('/basic', methods=['GET'])
@login_required
def basic_multiple_conversation():
    """Legacy route for basic multiple entries conversation."""
    # Redirect to the main multiple conversation route
    return redirect(url_for('ai.multiple_entries_conversation'))

@ai_bp.route('/test-cors', methods=['GET'])
@login_required
def test_cors():
    """Test page for debugging CORS issues."""
    return render_template('ai/test_cors.html')

@ai_bp.route('/api/conversation', methods=['POST'])
@login_required
def ai_conversation_api():
    """API endpoint for AI conversations."""
    try:
        # Flask-WTF will handle CSRF validation automatically
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        entries_data = data.get('entries', [])
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        if not entries_data:
            return jsonify({'error': 'No entries provided'}), 400
        
        # Check if GEMINI_API_KEY is available
        import os
        if not os.getenv('GEMINI_API_KEY'):
            # Return a mock response for now
            mock_response = f"I'd love to help you analyze your journal entries about '{question}', but I'm currently configured in demo mode. Please set up the GEMINI_API_KEY environment variable to enable full AI functionality. Based on your entries, I can see you're reflecting on meaningful experiences."
            return jsonify({
                'response': mock_response,
                'success': True,
                'demo_mode': True
            })
        
        # Import AI utility function
        from ai_utils import get_ai_response
        
        # Get AI response
        ai_response = get_ai_response(entries_data, question)
        
        return jsonify({
            'response': ai_response,
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in AI conversation API: {e}")
        return jsonify({
            'error': f'An error occurred: {str(e)}',
            'success': False
        }), 500

