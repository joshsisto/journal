from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response, current_app, send_file, session
from flask_login import login_user, logout_user, login_required, current_user
from security import limiter  # Import limiter for rate limiting

from werkzeug.utils import secure_filename
from flask_mail import Mail
from sqlalchemy import func, or_, and_, desc
import pytz
import json
import re
import os
import uuid


from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag, Photo
from services.user_service import (
    register_user, authenticate_user, update_user_timezone, change_user_password,
    change_user_email, add_user_email, resend_verification_email, request_password_reset, reset_password
)
from services.journal_service import create_quick_entry, create_guided_entry
from services.tag_service import get_all_tags_for_user, create_tag, edit_tag, delete_tag
from export_utils import format_entry_for_text, format_multi_entry_filename

from emotions import get_emotions_by_category
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)
from services.journal_service import create_quick_entry, create_guided_entry

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)
tag_bp = Blueprint('tag', __name__)
export_bp = Blueprint('export', __name__)
ai_bp = Blueprint('ai', __name__)
reminder_bp = Blueprint('reminder', __name__)

# Authentication routes
from services.user_service import register_user

from forms import RegistrationForm

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Rate limiting
def register():
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user, message = register_user(form.username.data, form.email.data, form.password.data, form.timezone.data)
        if user:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')

    # Get common timezones
    common_timezones = pytz.common_timezones

    return render_template('register.html', form=form, timezones=common_timezones)


from forms import LoginForm

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limiting
def login():
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data, form.password.data)

        if not user:
            current_app.logger.warning(f'Failed login attempt for user: {form.username.data} from IP: {request.remote_addr}')
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))

        # Store user ID in session for 2FA
        session['pre_verified_user_id'] = user.id
        session['pre_verified_remember'] = form.remember.data

        # Check if 2FA is required
        if user.two_factor_enabled and is_verification_required(user.id):
            # Send verification code
            success, message = send_verification_code(user.id)

            if not success:
                flash(f'Failed to send verification code: {message}', 'danger')
                return redirect(url_for('auth.login'))

            # Set flag in session
            session['requires_verification'] = True

            # Redirect to verification page
            return redirect(url_for('auth.verify_login'))

        # Log successful login
        current_app.logger.info(f'User logged in: {form.username.data} from IP: {request.remote_addr}')

        # Check for 'next' parameter to prevent open redirect
        next_page = request.args.get('next')
        if next_page and not next_page.startswith('/'):
            next_page = None  # Only allow relative paths

        # Login the user and redirect
        login_user(user, remember=form.remember.data)
        return redirect(next_page or url_for('journal.index'))

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
        # Check CSRF token
        token = session.get('_csrf_token')
        form_token = request.form.get('_csrf_token')
        
        if not token or token != form_token:
            current_app.logger.warning(f'CSRF attack detected on verification from {request.remote_addr}')
            flash('Invalid form submission. Please try again.', 'danger')
            return redirect(url_for('auth.verify_login'))
        
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
    # Check CSRF token
    token = session.get('_csrf_token')
    form_token = request.form.get('_csrf_token')
    
    if not token or token != form_token:
        current_app.logger.warning(f'CSRF attack detected on 2FA toggle from {request.remote_addr}')
        flash('Invalid form submission. Please try again.', 'danger')
        return redirect(url_for('auth.settings'))
    
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


from services.journal_service import create_quick_entry

from forms import QuickJournalForm

@journal_bp.route('/journal/quick', methods=['GET', 'POST'])
@login_required
def quick_journal():
    form = QuickJournalForm()
    if form.validate_on_submit():
        token = session.get('_csrf_token'); form_token = request.form.get('_csrf_token')
        if not token or token != form_token:
            current_app.logger.warning(f'CSRF attack detected on quick journal from {request.remote_addr}'); flash('Invalid form submission. Please try again.', 'danger'); return redirect(url_for('journal.quick_journal'))
        try:
            content = form.content.data
            if not content or len(content.strip()) == 0: flash('Journal entry cannot be empty.', 'danger'); return redirect(url_for('journal.quick_journal'))
            if len(content) > 10000: flash('Journal entry is too long. Please shorten your entry.', 'danger'); return redirect(url_for('journal.quick_journal'))
            entry = JournalEntry(user_id=current_user.id, content=content, entry_type='quick'); db.session.add(entry); db.session.flush()
            _process_tags_for_entry(entry, request.form.getlist('tags'), request.form.get('new_tags', '[]'), current_user.id)
            _handle_photo_uploads(request.files.getlist('photos'), entry.id, current_app.config)
            db.session.commit(); flash('Journal entry saved successfully.', 'success'); return redirect(url_for('journal.index'))
        except SQLAlchemyError as e:
            db.session.rollback(); current_app.logger.error(f"Database error in quick_journal: {str(e)} {traceback.format_exc()}"); flash('A database error occurred. Please try again or contact support if the issue persists.', 'danger'); return redirect(url_for('journal.quick_journal'))
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f'Error saving quick journal entry: {str(e)}'); current_app.logger.error(traceback.format_exc()); flash('An error occurred while saving your journal entry. Please try again.', 'danger'); return redirect(url_for('journal.quick_journal'))
    return render_template('journal/quick.html', tags=Tag.query.filter_by(user_id=current_user.id).all(), form=form)


from services.journal_service import create_guided_entry

from forms import QuickJournalForm, GuidedJournalForm

@journal_bp.route('/journal/guided', methods=['GET', 'POST'])
@login_required
def guided_journal():
    form = GuidedJournalForm()
    if form.validate_on_submit():
        token = session.get('_csrf_token'); form_token = request.form.get('_csrf_token')
        if not token or token != form_token:
            current_app.logger.warning(f'CSRF attack detected on guided journal from {request.remote_addr}'); flash('Invalid form submission. Please try again.', 'danger'); return redirect(url_for('journal.guided_journal'))
        try:
            entry = JournalEntry(user_id=current_user.id, entry_type='guided'); db.session.add(entry); db.session.flush()
            _process_tags_for_entry(entry, request.form.getlist('tags'), request.form.get('new_tags', '[]'), current_user.id)
            _process_guided_journal_responses(entry, request.form, current_user.id, form.content.data)
            _handle_photo_uploads(request.files.getlist('photos'), entry.id, current_app.config)
            db.session.commit(); flash('Guided journal entry saved successfully.'); return redirect(url_for('journal.index'))
        except SQLAlchemyError as e:
            db.session.rollback(); current_app.logger.error(f"Database error in guided_journal: {str(e)} {traceback.format_exc()}"); flash('A database error occurred. Please try again or contact support if the issue persists.', 'danger'); return redirect(url_for('journal.guided_journal'))
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f'Error saving guided journal entry: {str(e)}'); current_app.logger.error(traceback.format_exc()); flash('An error occurred while saving your guided journal entry. Please try again.', 'danger'); return redirect(url_for('journal.guided_journal'))
    context = prepare_guided_journal_context(); questions = QuestionManager.get_applicable_questions(context)
    for q_item in questions:
        if '{time_since}' in q_item.get('text', ''): q_item['text'] = q_item['text'].format(time_since=context.get('time_since', 'your last entry')) 
    return render_template('journal/guided.html', questions=questions, tags=Tag.query.filter_by(user_id=current_user.id).all(), emotions_by_category=get_emotions_by_category(), form=form)


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
        
        # Get the original questions for context
        all_questions = QuestionManager.get_questions()
        question_map = {q['id']: q for q in all_questions}
        
        # Add question text to responses
        for resp in guided_responses:
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
    # API endpoint to check if user has exercised today.
    return jsonify({
        'exercised_today': has_exercised_today()
    })


@journal_bp.route('/search', methods=['GET'])
@login_required
def search():
    # Search journal entries.
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
    # Mood tracking visualization for journal entries.
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
    # Display user settings page.
    # Get list of common timezones for the form
    common_timezones = pytz.common_timezones
    
    # Get user's tags for the settings page
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    password_change_form = PasswordChangeForm()
    email_change_form = EmailChangeForm()
    add_email_form = AddEmailForm()
    return render_template(
        'settings.html', 
        timezones=common_timezones, 
        current_timezone=current_user.timezone,
        tags=tags,
        password_change_form=password_change_form,
        email_change_form=email_change_form,
        add_email_form=add_email_form
    )


from services.user_service import update_user_timezone

@auth_bp.route('/settings/timezone', methods=['POST'])
@login_required
def update_timezone():
    # Update user timezone.
    timezone = request.form.get('timezone')
    success, message = update_user_timezone(current_user.id, timezone)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('auth.settings'))


from services.user_service import change_user_password

from forms import PasswordChangeForm

@auth_bp.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    # Change user password.
    import time
    
    # Add slight delay to prevent timing attacks
    time.sleep(0.1)

    form = PasswordChangeForm()
    if form.validate_on_submit():
        success, message = change_user_password(
            current_user.id,
            form.current_password.data,
            form.new_password.data,
            form.confirm_new_password.data
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

    return redirect(url_for('auth.settings'))




from forms import EmailChangeForm, AddEmailForm

@auth_bp.route('/settings/email', methods=['POST'])
@login_required
def change_email():
    # Initiate email change process.
    form = EmailChangeForm()
    if form.validate_on_submit():
        success, message = change_user_email(
            current_user.id,
            form.password.data,
            form.new_email.data,
            form.confirm_new_email.data
        )

        if success:
            flash(message, 'info')
        else:
            flash(message, 'danger')

    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/add-email', methods=['POST'])
@login_required
def add_email():
    # Add email to an account that doesn't have one.
    form = AddEmailForm()
    if form.validate_on_submit():
        success, message = add_user_email(
            current_user.id,
            form.password.data,
            form.email.data
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

    return redirect(url_for('auth.settings'))


from services.user_service import resend_verification_email

@auth_bp.route('/settings/resend-verification', methods=['POST'])
@login_required
@limiter.limit("3/hour")  # Prevent abuse
def resend_verification():
    # Resend email verification link.
    # Check CSRF token
    token = session.get('_csrf_token')
    form_token = request.form.get('_csrf_token')
    
    if not token or token != form_token:
        current_app.logger.warning(f'CSRF attack detected on resend verification from {request.remote_addr}')
        flash('Invalid form submission. Please try again.', 'danger')
        return redirect(url_for('auth.settings'))
    
    success, message = resend_verification_email(current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('auth.settings'))


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    # Verify email address with token.
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
    # Confirm email change with token.
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


from services.user_service import request_password_reset, reset_password

from forms import RequestResetForm, ResetPasswordForm

@auth_bp.route('/request-reset', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Rate limiting
def request_reset():
    # Request password reset.
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        message = request_password_reset(form.email.data)
        flash(message, 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/request_reset.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_route(token):
    # Reset password with token.
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        success, message = reset_password(token, form.password.data, form.confirm_password.data)
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            return redirect(url_for('auth.reset_password', token=token))
    
    return render_template('auth/reset_password.html', form=form)


from services.tag_service import get_all_tags_for_user, create_tag, edit_tag, delete_tag
from services.reminder_service import create_reminder, get_reminders_for_user, get_reminder_by_id, update_reminder, delete_reminder

# Tag Management Routes
@tag_bp.route('/tags', methods=['GET'])
@login_required
def manage_tags():
    tags = get_all_tags_for_user(current_user.id)
    return render_template('tags/manage.html', tags=tags)


@tag_bp.route('/tags/add', methods=['POST'])
@login_required
def add_tag():
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    tag, message = create_tag(current_user.id, name, color)
    if tag:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('tag.manage_tags'))


@tag_bp.route('/tags/edit/<int:tag_id>', methods=['POST'])
@login_required
def edit_tag(tag_id):
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    tag, message = edit_tag(current_user.id, tag_id, name, color)
    if tag:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('tag.manage_tags'))


@tag_bp.route('/tags/delete/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    success, message = delete_tag(current_user.id, tag_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('tag.manage_tags'))


# Reminder Routes
@reminder_bp.route('/', methods=['GET', 'POST'])
@login_required
def manage_reminders():
    form = ReminderForm()
    if form.validate_on_submit():
        frequency = form.frequency.data
        time_of_day_str = form.time_of_day.data
        message = form.message.data

        time_of_day = None
        if time_of_day_str:
            try:
                time_of_day = datetime.strptime(time_of_day_str, '%H:%M').time()
            except ValueError:
                flash('Invalid time format. Please use HH:MM.', 'danger')
                return redirect(url_for('reminder.manage_reminders'))

        reminder, msg = create_reminder(current_user.id, frequency, time_of_day, message)
        if reminder:
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
        return redirect(url_for('reminder.manage_reminders'))

    reminders = get_reminders_for_user(current_user.id)
    return render_template('reminders/manage.html', reminders=reminders, form=form)

@reminder_bp.route('/edit/<int:reminder_id>', methods=['GET', 'POST'])
@login_required
def edit_reminder(reminder_id):
    reminder = get_reminder_by_id(reminder_id, current_user.id)
    if not reminder:
        flash('Reminder not found.', 'danger')
        return redirect(url_for('reminder.manage_reminders'))

    form = ReminderForm(obj=reminder) # Populate form with existing reminder data
    if form.validate_on_submit():
        frequency = form.frequency.data
        time_of_day_str = form.time_of_day.data
        message = form.message.data
        enabled = form.enabled.data

        time_of_day = None
        if time_of_day_str:
            try:
                time_of_day = datetime.strptime(time_of_day_str, '%H:%M').time()
            except ValueError:
                flash('Invalid time format. Please use HH:MM.', 'danger')
                return redirect(url_for('reminder.edit_reminder', reminder_id=reminder_id))

        updated_reminder = update_reminder(reminder_id, current_user.id, frequency, time_of_day, message, enabled)
        if updated_reminder:
            flash('Reminder updated successfully.', 'success')
        else:
            flash('Error updating reminder.', 'danger')
        return redirect(url_for('reminder.manage_reminders'))

    return render_template('reminders/edit.html', reminder=reminder, form=form)

@reminder_bp.route('/delete/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    success, message = delete_reminder(reminder_id, current_user.id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('reminder.manage_reminders'))

# Export routes
@export_bp.route('/export/entry/<int:entry_id>')
@login_required
def export_entry(entry_id):
    # Export a single journal entry as text.
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
    # Export journal entries based on search criteria.
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
    # Export all journal entries.
    # Get all entries sorted by date
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).all()
    
    return export_entries_as_text(entries)





@journal_bp.route('/journal/photo/<int:photo_id>')
@login_required
def view_photo(photo_id):
    # Serve a photo file.
    # First verify that the photo belongs to the current user
    photo = Photo.query.join(JournalEntry).filter(
        Photo.id == photo_id,
        JournalEntry.user_id == current_user.id
    ).first_or_404()
    
    # Build the file path
    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    photo_path = os.path.join(upload_folder, photo.filename)
    
    # Send the file
    return send_file(photo_path)


def export_entries_as_text(entries, filter_info=None):
    # Helper function to export entries as text.
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
    
    # Process each entry
    for entry in entries:
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
    # AI conversation based on a single journal entry.
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


@ai_bp.route('/conversation/original', methods=['GET', 'POST'])
@login_required
def original_multiple_entries_conversation():
    # Original (non-working) version of multiple entries conversation.
    # Get the 10 most recent entries only - simplify for troubleshooting
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    print(f"Original multiple entries conversation requested")
    print(f"Using {len(entries)} most recent entries for simplicity")
    
    # Format entries for template with the TimeUtils helper
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content or "",
        }
        entries_data.append(entry_data)
    
    # Use the direct template for multiple conversations
    
    # Base query for user's journal entries
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if tag_id:
        try:
            tag_id = int(tag_id)
            selected_tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
            if selected_tag:
                query = query.filter(JournalEntry.tags.contains(selected_tag))
        except ValueError:
            pass
    else:
        selected_tag = None
    
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
    
    if entry_type in ['quick', 'guided']:
        query = query.filter_by(entry_type=entry_type)
    
    # If specific entries are selected
    if selected_entries:
        entry_ids = [int(id) for id in selected_entries if id.isdigit()]
        if entry_ids:
            query = query.filter(JournalEntry.id.in_(entry_ids))
    
    # Order entries by date
    entries = query.order_by(JournalEntry.created_at.desc()).all()
    
    # Format entries with timezone conversion
    from time_utils import TimeUtils
    entries_data = []
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'date': TimeUtils.format_datetime(entry.created_at),
            'entry_type': entry.entry_type,
            'content': entry.content,
            'tags': [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in entry.tags]
        }
        
        # If it's a guided entry, get the feeling value and emotions
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
    
    # Get emotions categories for badge styling
    return render_template(
        'ai/multiple_conversation.html',
        entries=entries_data
    )


@ai_bp.route('/test/conversation', methods=['GET'])
@login_required
def test_conversation():
    # Test page for AI conversation functionality.
    # Get some recent entries for the select dropdown
    recent_entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    return render_template(
        'ai/test_conversation.html',
        recent_entries=recent_entries
    )
    
@ai_bp.route('/simple', methods=['GET'])
@login_required
def simple_ai_conversation():
    # Simple AI conversation with the most recent entry.
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

@ai_bp.route('/test/multiple', methods=['GET'])
@login_required
def test_multiple_conversation():
    # Test page for multiple entries AI conversation.
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
    # Extra direct version of the multiple entries conversation.
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
    # Absolute bare minimum test page for AI conversations.
    print("Rendering bare minimum test page")
    return render_template('ai/bare_minimum.html')

@ai_bp.route('/working', methods=['GET'])
@login_required
def working_multiple_conversation():
    # Working version of multiple entries conversation.
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
    # Working multiple entries conversation (default).
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
    # Legacy route for basic multiple entries conversation.
    # Redirect to the main multiple conversation route
    return redirect(url_for('ai.multiple_entries_conversation'))

@ai_bp.route('/test-cors', methods=['GET'])
@login_required
def test_cors():
    # Test page for debugging CORS issues.
    return render_template('ai/test_cors.html')

@ai_bp.route('/api/conversation', methods=['POST', 'OPTIONS'])
@login_required
@limiter.limit("10 per minute")  # Rate limiting
def ai_conversation_api():
    # API endpoint for AI conversations.
    from validators import sanitize_text
    
    # For debugging
    print("="*50)
    print(f"AI conversation API called by user: {current_user.username}")
    print("Request details:")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"URL: {request.url}")
    
    # Handle OPTIONS requests for CORS
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request")
        response = current_app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Accept, X-CSRF-Token'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    # Handle regular POST requests
    print("="*50)
    print(f"AI conversation API called by user: {current_user.username}")
    print("="*50)
    
    # Log request details
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request endpoint: {request.endpoint}")
    
    # Check CSRF token in header
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('_csrf_token'):
        print(f"CSRF token verification failed")
        current_app.logger.warning(f'CSRF token verification failed for AI API from {request.remote_addr}')
        return jsonify({'error': 'Invalid CSRF token'}), 403
    
    # Check if request has JSON
    if not request.is_json:
        print(f"Request is not JSON. Content-Type: {request.headers.get('Content-Type')}")
        # Try to parse JSON even if content type is not set correctly
        try:
            data = request.get_json(force=True)
            print(f"Forced JSON parsing successful: {type(data)}")
        except Exception as json_error:
            print(f"Error forcing JSON parse: {json_error}")
            return jsonify({'error': 'Request must be JSON'}), 400
    else:
        # Get the JSON data
        try:
            data = request.get_json()
            print(f"JSON parsing successful: {type(data)}")
        except Exception as json_error:
            print(f"Error parsing JSON: {json_error}")
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400
    
    if not data:
        print(f"No JSON data in request")
        return jsonify({'error': 'No data provided'}), 400
    
    # Extract data
    entries_data = data.get('entries', [])
    question = data.get('question', '')
    
    # Sanitize the question
    question = sanitize_text(question, 500)  # Limit to 500 chars
    
    print(f"Entries count: {len(entries_data)}")
    print(f"Question: '{question}'")
    
    # Validate request
    if not entries_data:
        return jsonify({'error': 'No journal entries provided'}), 400
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    # Limit the number of entries to prevent abuse
    if len(entries_data) > 20:
        print(f"Too many entries: {len(entries_data)}")
        return jsonify({'error': 'Too many entries provided. Please limit to 20 entries.'}), 400
    
    # Sanitize entries data
    sanitized_entries = []
    for entry in entries_data:
        # Ensure all entries belong to the current user
        entry_id = entry.get('id')
        if entry_id:
            db_entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first()
            if not db_entry:
                print(f"Entry {entry_id} does not belong to user {current_user.id}")
                continue  # Skip entries that don't belong to the user
        
        # Sanitize entry fields
        sanitized_entry = {
            'id': entry.get('id'),
            'date': entry.get('date'),
            'entry_type': entry.get('entry_type'),
            'content': sanitize_text(entry.get('content', ''), 10000)
        }
        
        # Only include additional fields if they exist
        if 'feeling_value' in entry:
            try:
                sanitized_entry['feeling_value'] = int(entry['feeling_value'])
            except (ValueError, TypeError):
                pass
                
        if 'emotions' in entry and isinstance(entry['emotions'], list):
            sanitized_entry['emotions'] = [sanitize_text(e, 100) for e in entry['emotions'] if isinstance(e, str)]
            
        if 'guided_responses' in entry and isinstance(entry['guided_responses'], dict):
            sanitized_responses = {}
            for key, value in entry['guided_responses'].items():
                sanitized_responses[sanitize_text(key, 100)] = sanitize_text(value, 5000)
            sanitized_entry['guided_responses'] = sanitized_responses
            
        sanitized_entries.append(sanitized_entry)
    
    if not sanitized_entries:
        print(f"No valid entries after sanitization")
        return jsonify({'error': 'No valid entries provided'}), 400
    
    try:
        # Import AI utils
        from ai_utils import get_ai_response
        
        print(f"Calling AI response function")
        # Get AI response (now synchronous)
        response = get_ai_response(sanitized_entries, question)
        print(f"AI response received, length: {len(response) if response else 0}")
        
        # Sanitize response to prevent XSS
        response = sanitize_text(response, 10000)
        
        # Create response and log it
        result = {'response': response}
        print(f"Returning result with response beginning: {response[:100] if response else 'None'}")
        print("="*50)
        
        # Explicitly create a JSON response with appropriate CORS headers
        resp = jsonify(result)
        resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        print(f"JSON response created, status: 200, Content-Type: {resp.headers.get('Content-Type')}")
        return resp
    except Exception as e:
        import traceback
        error_msg = str(e)
        trace = traceback.format_exc()
        current_app.logger.error(f"AI conversation error: {error_msg}\n{trace}")
        print(f"AI conversation error: {error_msg}\n{trace}")
        print("="*50)
        return jsonify({'error': f"An error occurred processing your request"}), 500
