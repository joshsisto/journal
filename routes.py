from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_, and_, desc
import pytz

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager, Tag
from export_utils import format_entry_for_text, format_multi_entry_filename
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)
tag_bp = Blueprint('tag', __name__)
export_bp = Blueprint('export', __name__)

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
    # Get tag filter if present
    tag_id = request.args.get('tag')
    
    # Base query
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply tag filter if provided
    if tag_id:
        tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
        query = query.filter(JournalEntry.tags.any(Tag.id == tag_id))
        selected_tag = tag
    else:
        selected_tag = None
    
    # Get entries
    entries = query.order_by(JournalEntry.created_at.desc()).limit(10).all()
    
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
    
    return render_template('home.html', entries=entries, tags=tags, selected_tag=selected_tag, feeling_data=feeling_data)


@journal_bp.route('/journal/quick', methods=['GET', 'POST'])
@login_required
def quick_journal():
    if request.method == 'POST':
        content = request.form.get('content')
        tag_ids = request.form.getlist('tags')
        
        if not content:
            flash('Journal entry cannot be empty.')
            return redirect(url_for('journal.quick_journal'))
        
        entry = JournalEntry(
            user_id=current_user.id,
            content=content,
            entry_type='quick'
        )
        
        # Add selected tags
        if tag_ids:
            tags = Tag.query.filter(
                Tag.id.in_(tag_ids), 
                Tag.user_id == current_user.id
            ).all()
            entry.tags = tags
        
        db.session.add(entry)
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
        
        # First, create the journal entry
        entry = JournalEntry(
            user_id=current_user.id,
            entry_type='guided'
        )
        
        # Add selected tags
        if tag_ids:
            tags = Tag.query.filter(
                Tag.id.in_(tag_ids), 
                Tag.user_id == current_user.id
            ).all()
            entry.tags = tags
        
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
                
                # Save the response
                guided_response = GuidedResponse(
                    journal_entry_id=entry.id,
                    question_id=question_id,
                    response=value
                )
                db.session.add(guided_response)
        
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
    
    return render_template('journal/guided.html', questions=questions, tags=tags)


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
    
    return render_template('journal/view.html', entry=entry, guided_responses=guided_responses, all_tags=all_tags)


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


@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
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
