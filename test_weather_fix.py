#!/usr/bin/env python3
"""
Test the weather saving fix.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, JournalEntry, WeatherData, GuidedResponse
from werkzeug.security import generate_password_hash

def test_weather_fix():
    """Test that weather saving works correctly after the fix."""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Create a test user
            test_user = User.query.filter_by(username='testweatherfix').first()
            if not test_user:
                test_user = User(
                    username='testweatherfix',
                    email='testweatherfix@example.com',
                    password_hash=generate_password_hash('testpass123')
                )
                db.session.add(test_user)
                db.session.commit()
            
            print(f"Testing with user: {test_user.username} (ID: {test_user.id})")
            
            # Test 1: Guided journal submission with weather data (like the frontend sends)
            print("\n=== Test 1: Guided journal with consolidated weather data ===")
            
            # Simulate what the frontend now sends after the fix
            weather_data = {
                'temperature': 24.5,
                'condition': 'Clear',
                'humidity': 65,
                'wind_speed': 3.2
            }
            
            form_data = {
                'feeling_scale': '8',
                'feeling_reason': 'Great weather today!',
                'weather_data': json.dumps(weather_data),  # This is what the fix provides
                '_csrf_token': ''
            }
            
            print(f"Submitting guided journal with weather: {weather_data}")
            
            # Count before
            entries_before = JournalEntry.query.filter_by(user_id=test_user.id).count()
            weather_before = WeatherData.query.count()
            
            print(f"Before: {entries_before} entries, {weather_before} weather records")
            
            # Submit via the guided journal route
            response = client.post('/journal/guided', data=form_data, follow_redirects=True)
            
            print(f"Response status: {response.status_code}")
            
            # Count after
            entries_after = JournalEntry.query.filter_by(user_id=test_user.id).count()
            weather_after = WeatherData.query.count()
            
            print(f"After: {entries_after} entries, {weather_after} weather records")
            
            if entries_after > entries_before:
                # Get the new entry
                new_entry = JournalEntry.query.filter_by(user_id=test_user.id).order_by(JournalEntry.created_at.desc()).first()
                print(f"✅ New entry created: ID {new_entry.id}")
                
                if new_entry.weather_id:
                    weather_record = WeatherData.query.get(new_entry.weather_id)
                    if weather_record:
                        print(f"✅ Weather saved: {weather_record.temperature}°C, {weather_record.weather_condition}")
                        print(f"✅ Weather linked to entry: journal_entry_id={weather_record.journal_entry_id}")
                    else:
                        print(f"❌ Weather record not found for ID {new_entry.weather_id}")
                else:
                    print("❌ No weather_id set on entry")
                
                # Check guided responses
                responses = GuidedResponse.query.filter_by(journal_entry_id=new_entry.id).all()
                print(f"✅ {len(responses)} guided responses saved")
                
            else:
                print("❌ No new entry created")
            
            # Test 2: Quick entry with weather data  
            print("\n=== Test 2: Quick journal with weather data ===")
            
            weather_data_2 = {
                'temperature': 18.0,
                'condition': 'Rainy',
                'humidity': 85
            }
            
            form_data_2 = {
                'entry_type': 'quick',
                'content': 'Rainy day journal entry',
                'weather_data': json.dumps(weather_data_2),
                '_csrf_token': ''
            }
            
            print(f"Submitting quick entry with weather: {weather_data_2}")
            
            entries_before_2 = JournalEntry.query.filter_by(user_id=test_user.id).count()
            
            response_2 = client.post('/dashboard', data=form_data_2, follow_redirects=True)
            
            entries_after_2 = JournalEntry.query.filter_by(user_id=test_user.id).count()
            
            if entries_after_2 > entries_before_2:
                new_entry_2 = JournalEntry.query.filter_by(user_id=test_user.id).order_by(JournalEntry.created_at.desc()).first()
                print(f"✅ Quick entry created: ID {new_entry_2.id}")
                
                if new_entry_2.weather_id:
                    weather_record_2 = WeatherData.query.get(new_entry_2.weather_id)
                    if weather_record_2:
                        print(f"✅ Weather saved: {weather_record_2.temperature}°C, {weather_record_2.weather_condition}")
                    else:
                        print(f"❌ Weather record not found")
                else:
                    print("❌ No weather_id set on quick entry")
            else:
                print("❌ No quick entry created")
            
            # Test 3: Verify database state
            print("\n=== Test 3: Database verification ===")
            
            user_entries = JournalEntry.query.filter_by(user_id=test_user.id).all()
            print(f"User has {len(user_entries)} total entries:")
            
            weather_with_entries = 0
            for entry in user_entries:
                if entry.weather_id:
                    weather = WeatherData.query.get(entry.weather_id)
                    if weather:
                        print(f"  ✅ Entry {entry.id} ({entry.entry_type}): Weather {weather.id} = {weather.temperature}°C, {weather.weather_condition}")
                        weather_with_entries += 1
                    else:
                        print(f"  ❌ Entry {entry.id}: Invalid weather ID {entry.weather_id}")
                else:
                    print(f"  ➖ Entry {entry.id} ({entry.entry_type}): No weather")
            
            print(f"Summary: {weather_with_entries} entries have weather data")
            
            # Test 4: Verify relationships work both ways
            print("\n=== Test 4: Relationship verification ===")
            
            for entry in user_entries:
                if entry.weather:
                    print(f"  ✅ Entry {entry.id} -> Weather relationship works")
                    if entry.weather.journal_entry_id == entry.id:
                        print(f"  ✅ Weather {entry.weather.id} -> Entry backref works")
                    else:
                        print(f"  ❌ Weather backref broken: {entry.weather.journal_entry_id} != {entry.id}")
            
            # Cleanup
            print("\n=== Cleanup ===")
            for entry in user_entries:
                # Clear guided responses first
                guided_responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
                for response in guided_responses:
                    db.session.delete(response)
                
                # Clear weather relationship and delete weather
                if entry.weather_id:
                    weather = db.session.get(WeatherData, entry.weather_id)
                    if weather:
                        weather.journal_entry_id = None
                        db.session.delete(weather)
                
                db.session.delete(entry)
            
            db.session.delete(test_user)
            db.session.commit()
            print("Cleanup complete")

if __name__ == '__main__':
    test_weather_fix()