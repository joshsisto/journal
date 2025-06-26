from models import db, Reminder
from datetime import datetime, time

def create_reminder(user_id, frequency, time_of_day, message=None):
    reminder = Reminder(
        user_id=user_id,
        frequency=frequency,
        time_of_day=time_of_day,
        message=message,
        enabled=True,
        last_sent=None  # Set to None initially
    )
    db.session.add(reminder)
    db.session.commit()
    return reminder

def get_reminders_for_user(user_id):
    return Reminder.query.filter_by(user_id=user_id).all()

def get_reminder_by_id(reminder_id, user_id):
    return Reminder.query.filter_by(id=reminder_id, user_id=user_id).first()

def update_reminder(reminder_id, user_id, frequency=None, time_of_day=None, message=None, enabled=None):
    reminder = get_reminder_by_id(reminder_id, user_id)
    if not reminder:
        return None

    if frequency: reminder.frequency = frequency
    if time_of_day: reminder.time_of_day = time_of_day
    if message is not None: reminder.message = message
    if enabled is not None: reminder.enabled = enabled

    db.session.commit()
    return reminder

def delete_reminder(reminder_id, user_id):
    reminder = get_reminder_by_id(reminder_id, user_id)
    if not reminder:
        return False

    db.session.delete(reminder)
    db.session.commit()
    return True

def get_due_reminders():
    # This function would be called by a scheduled task
    # It needs to consider user timezones for accurate scheduling
    # For simplicity, this example assumes UTC for now.
    # A more robust solution would involve converting reminder_time to UTC for each user.
    now = datetime.utcnow()
    # Filter for enabled reminders that are due
    # This is a simplified check and would need more complex logic for different frequencies
    # and timezone conversions.
    due_reminders = Reminder.query.filter(
        Reminder.enabled == True,
        # Example: for daily reminders, check if last_sent was before today
        # and current time is past time_of_day
        # This part needs careful implementation considering timezones
    ).all()
    return due_reminders

def mark_reminder_sent(reminder_id):
    reminder = Reminder.query.get(reminder_id)
    if reminder:
        reminder.last_sent = datetime.utcnow()
        db.session.commit()
