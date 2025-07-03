#!/usr/bin/env python3
"""
Fix timezone issues in ExerciseLog entries.

This script converts UTC dates in ExerciseLog entries to user local dates
to fix the timezone bug where exercise questions weren't being asked properly.
"""

from app import create_app
from models import db, User, ExerciseLog
from time_utils import TimeUtils
from datetime import datetime
import pytz

def fix_exercise_timezone():
    """Fix timezone issues in ExerciseLog entries."""
    app = create_app()
    
    with app.app_context():
        print("🔧 Starting ExerciseLog timezone fix...")
        
        # Get all users with exercise logs
        users_with_logs = db.session.query(User).join(ExerciseLog).distinct().all()
        
        if not users_with_logs:
            print("✅ No users with exercise logs found. Nothing to fix.")
            return
        
        total_fixed = 0
        
        for user in users_with_logs:
            print(f"\n👤 Processing user: {user.username} (timezone: {user.timezone})")
            
            # Get user's timezone
            if user.timezone:
                try:
                    user_tz = pytz.timezone(user.timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    print(f"  ⚠️  Unknown timezone {user.timezone}, using UTC")
                    user_tz = pytz.UTC
            else:
                print(f"  ⚠️  No timezone set, using UTC")
                user_tz = pytz.UTC
            
            # Get all exercise logs for this user
            exercise_logs = ExerciseLog.query.filter_by(user_id=user.id).all()
            
            for log in exercise_logs:
                # Treat the current date as if it were a UTC date
                # Then convert it to the user's local date
                
                # Create a datetime from the stored date (treating as UTC midnight)
                utc_datetime = datetime.combine(log.date, datetime.min.time())
                utc_datetime = pytz.UTC.localize(utc_datetime)
                
                # Convert to user's local time
                local_datetime = utc_datetime.astimezone(user_tz)
                local_date = local_datetime.date()
                
                # Only update if the date actually changes
                if log.date != local_date:
                    print(f"  🔧 Fixing ExerciseLog {log.id}: {log.date} → {local_date}")
                    
                    # Check if there's already a log for the corrected local date
                    existing_log = ExerciseLog.query.filter_by(
                        user_id=user.id,
                        date=local_date
                    ).first()
                    
                    if existing_log and existing_log.id != log.id:
                        print(f"    ⚠️  Duplicate log exists for {local_date}, merging...")
                        # Keep the one that shows exercise was done
                        if log.has_exercised and not existing_log.has_exercised:
                            existing_log.has_exercised = True
                            existing_log.workout_type = log.workout_type or existing_log.workout_type
                        elif log.workout_type and not existing_log.workout_type:
                            existing_log.workout_type = log.workout_type
                        
                        # Remove the duplicate
                        db.session.delete(log)
                        print(f"    🗑️  Removed duplicate log {log.id}")
                    else:
                        # Safe to update the date
                        log.date = local_date
                        print(f"    ✅ Updated log {log.id} to {local_date}")
                    
                    total_fixed += 1
                else:
                    print(f"  ✅ ExerciseLog {log.id} already correct: {log.date}")
        
        if total_fixed > 0:
            print(f"\n💾 Committing {total_fixed} fixes to database...")
            db.session.commit()
            print("✅ Database updated successfully!")
        else:
            print("\n✅ No fixes needed - all exercise logs have correct dates")
        
        # Verify the fix
        print("\n🔍 Verification:")
        for user in users_with_logs:
            logs = ExerciseLog.query.filter_by(user_id=user.id).all()
            print(f"  👤 {user.username}: {len(logs)} exercise logs")
            for log in logs:
                print(f"    📅 {log.date}: exercised={log.has_exercised}, type={log.workout_type}")

if __name__ == "__main__":
    fix_exercise_timezone()