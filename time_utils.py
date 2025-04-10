# time_utils.py

from datetime import datetime, timedelta
import pytz
from flask import g, current_app
from flask_login import current_user

class TimeUtils:
    """Centralized class for handling all timezone conversions and time-related utilities."""
    
    @staticmethod
    def get_user_timezone():
        """Get the current user's timezone or UTC if not set."""
        if hasattr(g, 'user_timezone'):
            return g.user_timezone
            
        if current_user.is_authenticated and hasattr(current_user, 'timezone') and current_user.timezone:
            try:
                tz = pytz.timezone(current_user.timezone)
                g.user_timezone = tz
                return tz
            except pytz.exceptions.UnknownTimeZoneError:
                pass
                
        g.user_timezone = pytz.UTC
        return pytz.UTC
    
    @staticmethod
    def utc_to_local(utc_dt):
        """Convert UTC datetime to user's local timezone."""
        if not utc_dt:
            return None
            
        # Make sure we have a timezone-aware datetime
        if not utc_dt.tzinfo:
            utc_dt = pytz.UTC.localize(utc_dt)
            
        # Convert to user's timezone
        return utc_dt.astimezone(TimeUtils.get_user_timezone())
    
    @staticmethod
    def format_datetime(utc_dt, format_str='%Y-%m-%d %H:%M'):
        """Format a UTC datetime in user's local timezone with the given format."""
        if not utc_dt:
            return ""
        local_dt = TimeUtils.utc_to_local(utc_dt)
        return local_dt.strftime(format_str)
    
    @staticmethod
    def get_local_now():
        """Get current datetime in user's timezone."""
        utc_now = pytz.UTC.localize(datetime.utcnow())
        return TimeUtils.utc_to_local(utc_now)
    
    @staticmethod
    def get_local_today():
        """Get current date in user's timezone."""
        return TimeUtils.get_local_now().date()
    
    @staticmethod
    def is_same_day(utc_dt1, utc_dt2):
        """Check if two UTC datetimes are on the same day in user's timezone."""
        if not utc_dt1 or not utc_dt2:
            return False
            
        local_dt1 = TimeUtils.utc_to_local(utc_dt1)
        local_dt2 = TimeUtils.utc_to_local(utc_dt2)
        
        return (local_dt1.year == local_dt2.year and 
                local_dt1.month == local_dt2.month and 
                local_dt1.day == local_dt2.day)
    
    @staticmethod
    def get_day_start_end_utc(local_date=None):
        """Get UTC datetime range for a given local date (or today)."""
        user_tz = TimeUtils.get_user_timezone()
        
        # Use provided date or today in user's timezone
        if not local_date:
            local_date = TimeUtils.get_local_today()
            
        # Create start and end of day in user's timezone
        day_start = user_tz.localize(datetime.combine(local_date, datetime.min.time()))
        day_end = user_tz.localize(datetime.combine(local_date, datetime.max.time()))
        
        # Convert to UTC for database queries
        return day_start.astimezone(pytz.UTC), day_end.astimezone(pytz.UTC)
    
    @staticmethod
    def is_before_noon():
        """Check if current time is before noon in user's timezone."""
        return TimeUtils.get_local_now().hour < 12

# Function to register jinja2 template utilities
def register_template_utils(app):
    """Register time utility functions with the Jinja2 environment."""
    @app.context_processor
    def inject_time_utils():
        return {
            'format_datetime': TimeUtils.format_datetime,
            'user_timezone': TimeUtils.get_user_timezone().zone,
            'now': datetime.now,  # Current time function
            'strftime': lambda dt, fmt: dt.strftime(fmt),  # Strftime helper for templates
            'datetime': datetime  # Make datetime class available in templates
        }
