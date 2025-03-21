from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func
import pytz

from models import db, User, JournalEntry, GuidedResponse, ExerciseLog, QuestionManager
from helpers import (
    get_time_since_last_entry, format_time_since, has_exercised_today,
    has_set_goals_today, is_before_noon, prepare_guided_journal_context
)

# Blueprints
auth_bp = Blueprint('auth', __name__)
journal_bp = Blueprint('journal', __name__)

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
    entries = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).limit(10).all()
    
    return render_template('home.html', entries=entries)


@journal_bp.route('/journal/quick', methods=['GET', 'POST'])
@login_required
def quick_journal():
    if request.method == 'POST':
        content = request.form.get('content')
        
        if not content:
            flash('Journal entry cannot be empty.')
            return redirect(url_for('journal.quick_journal'))
        
        entry = JournalEntry(
            user_id=current_user.id,
            content=content,
            entry_type='quick'
        )
        
        db.session.add(entry)
        db.session.commit()
        
        flash('Journal entry saved successfully.')
        return redirect(url_for('journal.index'))
    
    return render_template('journal/quick.html')


@journal_bp.route('/journal/guided', methods=['GET', 'POST'])
@login_required
def guided_journal():
    if request.method == 'POST':
        # First, create the journal entry
        entry = JournalEntry(
            user_id=current_user.id,
            entry_type='guided'
        )
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
    
    return render_template('journal/guided.html', questions=questions)


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
    
    return render_template('journal/view.html', entry=entry, guided_responses=guided_responses)


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


@journal_bp.route('/journal/exercise/check')
@login_required
def check_exercise():
    """API endpoint to check if user has exercised today."""
    return jsonify({
        'exercised_today': has_exercised_today()
    })


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
    
    return render_template(
        'settings.html', 
        timezones=common_timezones, 
        current_timezone=current_user.timezone
    )
