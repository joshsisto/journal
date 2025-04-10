from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response, current_app, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail
from sqlalchemy import func, or_, and_, desc
import pytz
import json
import re
import os
import uuid

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag, Photo
from export_utils import format_entry_for_text, format_multi_entry_filename
from email_utils import send_password_reset_email, send_email_change_confirmation
from emotions import get_emotions_by_category
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)
tag_bp = Blueprint('tag', __name__)
export_bp = Blueprint('export', __name__)
ai_bp = Blueprint('ai', __name__)

# Authentication routes
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        timezone = request.form.get('timezone', 'UTC')
        
        # Validate timezone
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            timezone = 'UTC'  # Default to UTC if invalid
        
        # Check if username exists
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('auth.register'))
        
        # Check if email exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.')
            return redirect(url_for('auth.register'))
        
        # Create new user with timezone
        new_user = User(username=username, email=email, timezone=timezone)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('auth.login'))
    
    # Get common timezones
    common_timezones = pytz.common_timezones
    
    return render_template('register.html', timezones=common_timezones)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('journal.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password.')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('journal.index'))
    
    return render_template('login.html')


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
def quick_journal():
    if request.method == 'POST':
        content = request.form.get('content')
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        
        if not content:
            flash('Journal entry cannot be empty.')
            return redirect(url_for('journal.quick_journal'))
        
        entry = JournalEntry(
            user_id=current_user.id,
            content=content,
            entry_type='quick'
        )
        
        # Add selected existing tags
        if tag_ids:
            tags = Tag.query.filter(
                Tag.id.in_(tag_ids), 
                Tag.user_id == current_user.id
            ).all()
            entry.tags = tags
        else:
            entry.tags = []
        
        # Create and add new tags
        if new_tags_json:
            try:
                new_tags_data = json.loads(new_tags_json)
                for tag_data in new_tags_data:
                    # Check if tag with this name already exists for this user
                    existing_tag = Tag.query.filter_by(
                        name=tag_data.get('name'),
                        user_id=current_user.id
                    ).first()
                    
                    if existing_tag:
                        # Use existing tag if it exists
                        if existing_tag not in entry.tags:
                            entry.tags.append(existing_tag)
                    else:
                        # Create new tag
                        new_tag = Tag(
                            name=tag_data.get('name'),
                            color=tag_data.get('color', '#6c757d'),
                            user_id=current_user.id
                        )
                        db.session.add(new_tag)
                        db.session.flush()  # Get ID without committing
                        entry.tags.append(new_tag)
            except json.JSONDecodeError:
                # If JSON parsing fails, just continue
                pass
        
        db.session.add(entry)
        db.session.flush()  # Get ID without committing
        
        # Handle photo uploads
        photos = request.files.getlist('photos')
        if photos:
            for photo in photos:
                if photo and photo.filename and allowed_file(photo.filename):
                    # Create a secure filename with a UUID prefix
                    original_filename = photo.filename
                    filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"
                    
                    # Save file to upload folder
                    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    photo_path = os.path.join(upload_folder, filename)
                    photo.save(photo_path)
                    
                    # Create photo record in database
                    new_photo = Photo(
                        journal_entry_id=entry.id,
                        filename=filename,
                        original_filename=original_filename
                    )
                    db.session.add(new_photo)
        
        db.session.commit()
        
        flash('Journal entry saved successfully.')
        return redirect(url_for('journal.index'))
    
    # Get user's tags
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    return render_template('journal/quick.html', tags=tags)


@journal_bp.route('/journal/guided', methods=['GET', 'POST'])
@login_required
def guided_journal():
    if request.method == 'POST':
        # Get tag IDs from form
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        
        # First, create the journal entry
        entry = JournalEntry(
            user_id=current_user.id,
            entry_type='guided'
        )
        
        # Add selected existing tags
        if tag_ids:
            tags = Tag.query.filter(
                Tag.id.in_(tag_ids), 
                Tag.user_id == current_user.id
            ).all()
            entry.tags = tags
        else:
            entry.tags = []
            
        # Create and add new tags
        if new_tags_json:
            try:
                new_tags_data = json.loads(new_tags_json)
                for tag_data in new_tags_data:
                    # Check if tag with this name already exists for this user
                    existing_tag = Tag.query.filter_by(
                        name=tag_data.get('name'),
                        user_id=current_user.id
                    ).first()
                    
                    if existing_tag:
                        # Use existing tag if it exists
                        if existing_tag not in entry.tags:
                            entry.tags.append(existing_tag)
                    else:
                        # Create new tag
                        new_tag = Tag(
                            name=tag_data.get('name'),
                            color=tag_data.get('color', '#6c757d'),
                            user_id=current_user.id
                        )
                        db.session.add(new_tag)
                        db.session.flush()  # Get ID without committing
                        entry.tags.append(new_tag)
            except json.JSONDecodeError:
                # If JSON parsing fails, just continue
                pass
        
        db.session.add(entry)
        db.session.flush()  # Get the ID without committing
        
        # Process form data
        for key, value in request.form.items():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                
                # Special handling for exercise question
                if question_id == 'exercise' and value == 'Yes':
                    today = datetime.utcnow().date()
                    exercise_log = ExerciseLog.query.filter_by(
                        user_id=current_user.id,
                        date=today
                    ).first()
                    
                    if not exercise_log:
                        exercise_log = ExerciseLog(
                            user_id=current_user.id,
                            date=today,
                            has_exercised=True
                        )
                        db.session.add(exercise_log)
                    else:
                        exercise_log.has_exercised = True
                    
                    # If there's an exercise type question, get its value and update workout_type
                    workout_type = request.form.get('question_exercise_type')
                    if workout_type:
                        exercise_log.workout_type = workout_type
                
                # Handle additional emotions (JSON array from multiselect)
                if question_id == 'additional_emotions' and value:
                    # Store emotions as a JSON string
                    value = value
                
                # Save the response
                guided_response = GuidedResponse(
                    journal_entry_id=entry.id,
                    question_id=question_id,
                    response=value
                )
                db.session.add(guided_response)
        
        # Handle photo uploads
        photos = request.files.getlist('photos')
        if photos:
            for photo in photos:
                if photo and photo.filename and allowed_file(photo.filename):
                    # Create a secure filename with a UUID prefix
                    original_filename = photo.filename
                    filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"
                    
                    # Save file to upload folder
                    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    photo_path = os.path.join(upload_folder, filename)
                    photo.save(photo_path)
                    
                    # Create photo record in database
                    new_photo = Photo(
                        journal_entry_id=entry.id,
                        filename=filename,
                        original_filename=original_filename
                    )
                    db.session.add(new_photo)
        
        db.session.commit()
        flash('Guided journal entry saved successfully.')
        return redirect(url_for('journal.index'))
    
    # Prepare context data for conditionals
    context = prepare_guided_journal_context()
    
    # Get applicable questions
    questions = QuestionManager.get_applicable_questions(context)
    
    # Format the time_since placeholder in questions
    for q in questions:
        if '{time_since}' in q.get('text', ''):
            q['text'] = q['text'].format(time_since=context['time_since'])
    
    # Get user's tags
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get emotions by category for the template
    emotions_by_category = get_emotions_by_category()
    
    return render_template(
        'journal/guided.html', 
        questions=questions, 
        tags=tags, 
        emotions_by_category=emotions_by_category
    )


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
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate passwords
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('auth.settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('auth.settings'))
    
    if len(new_password) < 8:
        flash('Password must be at least 8 characters long.', 'danger')
        return redirect(url_for('auth.settings'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    
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
def add_tag():
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    
    if not name:
        flash('Tag name is required.', 'danger')
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
def edit_tag(tag_id):
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
    
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    
    if not name:
        flash('Tag name is required.', 'danger')
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
    
    # Build the file path
    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    photo_path = os.path.join(upload_folder, photo.filename)
    
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


@ai_bp.route('/conversation/original', methods=['GET', 'POST'])
@login_required
def original_multiple_entries_conversation():
    """Original (non-working) version of multiple entries conversation."""
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
    """Test page for AI conversation functionality."""
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
    return render_template('ai/basic_multiple.html', entries=entries_data)

@ai_bp.route('/basic', methods=['GET'])
@login_required
def basic_multiple_conversation():
    """Legacy route for basic multiple entries conversation."""
    # Redirect to the main multiple conversation route
    return redirect(url_for('ai.multiple_entries_conversation'))

@ai_bp.route('/api/conversation', methods=['POST', 'OPTIONS'])
@login_required
def ai_conversation_api():
    """API endpoint for AI conversations."""
    
    # For debugging
    print("="*50)
    print(f"AI conversation API called by user: {current_user.username}")
    print("Request details:")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"URL: {request.url}")
    print(f"Raw data: {request.data.decode('utf-8')[:1000] if request.data else 'None'}")
    
    # Handle OPTIONS requests for CORS
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request")
        response = current_app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Accept'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
        
    # Handle regular POST requests
    """API endpoint for AI conversations."""
    print("="*50)
    print(f"AI conversation API called by user: {current_user.username}")
    print("="*50)
    
    # Log request details
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request endpoint: {request.endpoint}")
    print(f"Request data: {request.data.decode('utf-8')[:500] if request.data else 'empty'}")
    
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
    
    print(f"Entries count: {len(entries_data)}")
    print(f"Question: '{question}'")
    
    if not entries_data:
        return jsonify({'error': 'No journal entries provided'}), 400
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Import AI utils
        from ai_utils import get_ai_response
        
        print(f"Calling AI response function")
        # Get AI response (now synchronous)
        response = get_ai_response(entries_data, question)
        print(f"AI response received, length: {len(response) if response else 0}")
        
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
        return jsonify({'error': f"Error: {error_msg}"}), 500
