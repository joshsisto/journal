#!/usr/bin/env python3
"""
Test weather saving through form submission simulation.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, JournalEntry, WeatherData
from werkzeug.security import generate_password_hash

def test_form_weather_submission():
    """Test weather saving through simulated form submission."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Create a test user
            test_user = User.query.filter_by(username='testformweather').first()
            if not test_user:
                test_user = User(
                    username='testformweather',
                    email='testformweather@example.com',
                    password_hash=generate_password_hash('testpass123')
                )
                db.session.add(test_user)
                db.session.commit()
            
            # Login the test user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user.id)
                sess['_fresh'] = True
            
            print(f"Testing with user: {test_user.username}")
            
            # Test 1: Quick entry with weather data
            print("\n=== Test 1: Quick entry form submission ===")
            
            weather_data = {
                'temperature': 23.0,
                'condition': 'Sunny',
                'humidity': 60
            }
            
            form_data = {
                'entry_type': 'quick',
                'content': 'Test entry with weather from form',
                'weather_data': json.dumps(weather_data),
                '_csrf_token': ''  # Would need proper CSRF token in real scenario
            }
            
            print(f"Submitting form data: {form_data}")
            
            # Count entries and weather before
            entries_before = JournalEntry.query.filter_by(user_id=test_user.id).count()
            weather_before = WeatherData.query.count()
            
            print(f"Before: {entries_before} entries, {weather_before} weather records")
            
            # Submit the form (this would normally go through routes.py)
            # Let's manually simulate what the route does
            
            try:
                # Create entry
                entry = JournalEntry(
                    user_id=test_user.id,
                    content=form_data['content'],
                    entry_type='quick'
                )
                db.session.add(entry)
                db.session.flush()
                
                # Handle weather data like in routes.py
                weather_data_str = form_data.get('weather_data', '').strip()
                if weather_data_str:
                    try:
                        weather_info = json.loads(weather_data_str)
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
                        print(f"Error parsing weather data: {e}")
                
                db.session.commit()
                print("Form submission simulation successful!")
                
                # Check results
                entries_after = JournalEntry.query.filter_by(user_id=test_user.id).count()
                weather_after = WeatherData.query.count()
                
                print(f"After: {entries_after} entries, {weather_after} weather records")
                print(f"Created entry ID: {entry.id}, weather ID: {entry.weather_id}")
                
                # Verify the entry has weather
                if entry.weather:
                    print(f"Entry weather: {entry.weather.temperature}°C, {entry.weather.weather_condition}")
                else:
                    print("ERROR: Entry has no weather data!")
                
            except Exception as e:
                db.session.rollback()
                print(f"Error during form submission: {e}")
                import traceback
                traceback.print_exc()
            
            # Test 2: Test with empty weather data
            print("\n=== Test 2: Entry without weather data ===")
            
            form_data_no_weather = {
                'entry_type': 'quick',
                'content': 'Test entry without weather',
                'weather_data': '',  # Empty weather data
            }
            
            try:
                entry_no_weather = JournalEntry(
                    user_id=test_user.id,
                    content=form_data_no_weather['content'],
                    entry_type='quick'
                )
                db.session.add(entry_no_weather)
                db.session.flush()
                
                # Handle empty weather data
                weather_data_str = form_data_no_weather.get('weather_data', '').strip()
                if weather_data_str:
                    print("Processing weather data...")
                else:
                    print("No weather data provided - this is expected")
                
                db.session.commit()
                print(f"Entry without weather created: ID {entry_no_weather.id}")
                
            except Exception as e:
                db.session.rollback()
                print(f"Error creating entry without weather: {e}")
            
            # Test 3: Check what's actually in the database
            print("\n=== Test 3: Database verification ===")
            
            user_entries = JournalEntry.query.filter_by(user_id=test_user.id).all()
            print(f"User has {len(user_entries)} entries:")
            
            for entry in user_entries:
                if entry.weather_id:
                    weather = WeatherData.query.get(entry.weather_id)
                    if weather:
                        print(f"  Entry {entry.id}: '{entry.content[:30]}...' -> Weather {weather.id}: {weather.temperature}°C, {weather.weather_condition}")
                    else:
                        print(f"  Entry {entry.id}: '{entry.content[:30]}...' -> Weather ID {entry.weather_id} (NOT FOUND)")
                else:
                    print(f"  Entry {entry.id}: '{entry.content[:30]}...' -> No weather")
            
            # Cleanup 
            print("\n=== Cleanup ===")
            for entry in user_entries:
                if entry.weather_id:
                    weather = db.session.get(WeatherData, entry.weather_id)
                    if weather:
                        weather.journal_entry_id = None  # Clear the foreign key
                        db.session.delete(weather)
                db.session.delete(entry)
            
            db.session.delete(test_user)
            db.session.commit()
            print("Cleanup complete")

if __name__ == '__main__':
    test_form_weather_submission()