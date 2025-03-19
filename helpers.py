from datetime import datetime, timedelta
from models import JournalEntry, ExerciseLog, GuidedResponse
from flask_login import current_user
from sqlalchemy import func
import pytz


def get_time_since_last_entry():
    """Get time since last entry for the current user.
    
    Returns:
        timedelta or None: Time since last entry, or None if no previous entries.
    """
    last_entry = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(JournalEntry.created_at.desc()).first()
    
    if last_entry:
        now = datetime.utcnow()
        return now - last_entry.created_at
    return None


def format_time_since(delta):
    """Format a timedelta into a human-readable string.
    
    Args:
        delta (timedelta): Time difference.
        
    Returns:
        str: Formatted time string.
    """
    if not delta:
        return "your first entry"
    
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 and days == 0:  # Only show minutes if less than a day
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    if not parts:
        return "less than a minute"
    
    return ", ".join(parts)


def has_exercised_today():
    """Check if the user has already logged exercise today.
    
    Returns:
        bool: True if exercised today, False otherwise.
    """
    today = datetime.utcnow().date()
    exercise_log = ExerciseLog.query.filter_by(
        user_id=current_user.id,
        date=today,
        has_exercised=True
    ).first()
    
    return bool(exercise_log)


def has_set_goals_today():
    """Check if the user has already set goals today.
    
    Returns:
        bool: True if goals set today, False otherwise.
    """
    today = datetime.utcnow().date()
    goals_entry = JournalEntry.query.join(
        GuidedResponse
    ).filter(
        JournalEntry.user_id == current_user.id,
        func.date(JournalEntry.created_at) == today,
        GuidedResponse.question_id == 'goals',
        GuidedResponse.response.isnot(None),
        GuidedResponse.response != ''
    ).first()
    
    return bool(goals_entry)


def is_before_noon():
    """Check if the current time is before noon.
    
    Returns:
        bool: True if before noon, False otherwise.
    """
    # Assuming user's local timezone or UTC
    now = datetime.utcnow()
    return now.hour < 12


def prepare_guided_journal_context():
    """Prepare context data for guided journal entry form.
    
    Returns:
        dict: Context data for evaluating question conditions.
    """
    time_since = get_time_since_last_entry()
    hours_since = (time_since.days * 24 + time_since.seconds // 3600) if time_since else 0
    
    return {
        'hours_since_last_entry': hours_since,
        'time_since': format_time_since(time_since),
        'exercised_today': has_exercised_today(),
        'is_before_noon': is_before_noon(),
        'goals_set_today': has_set_goals_today(),
        'exercise_response': None  # Will be filled during form processing
    }