#!/usr/bin/env python3
"""
Manual test to reproduce the weather saving issue.
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

def test_weather_saving():
    """Test weather saving functionality manually."""
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Create a test user or use existing one
        test_user = User.query.filter_by(username='testweather').first()
        if not test_user:
            # Try to find by email to avoid conflicts
            test_user = User.query.filter_by(email='test@example.com').first()
            if not test_user:
                test_user = User(
                    username='testweather',
                    email='testweather@example.com',  # Unique email
                    password_hash=generate_password_hash('testpass123')
                )
                db.session.add(test_user)
                db.session.commit()
        
        print(f"Created test user: {test_user.username}")
        
        # Test 1: Create weather data directly
        print("\n=== Test 1: Direct WeatherData creation ===")
        weather_direct = WeatherData(
            temperature=22.5,
            temperature_unit='celsius',
            weather_condition='Sunny',
            humidity=65
        )
        db.session.add(weather_direct)
        db.session.commit()
        print(f"Direct weather creation successful: ID {weather_direct.id}")
        
        # Test 2: Create journal entry with weather
        print("\n=== Test 2: Journal entry with weather ===")
        entry = JournalEntry(
            user_id=test_user.id,
            content='Test entry with weather',
            entry_type='quick'
        )
        db.session.add(entry)
        db.session.flush()
        
        # Create weather and link to entry
        weather_linked = WeatherData(
            temperature=25.0,
            weather_condition='Clear',
            humidity=70,
            journal_entry_id=entry.id
        )
        db.session.add(weather_linked)
        db.session.flush()
        
        # Link weather to entry
        entry.weather_id = weather_linked.id
        db.session.commit()
        
        print(f"Entry created: ID {entry.id}")
        print(f"Weather linked: ID {weather_linked.id}")
        print(f"Entry weather_id: {entry.weather_id}")
        print(f"Weather journal_entry_id: {weather_linked.journal_entry_id}")
        
        # Test 3: Verify the relationship
        print("\n=== Test 3: Verify relationships ===")
        retrieved_entry = JournalEntry.query.get(entry.id)
        retrieved_weather = WeatherData.query.get(weather_linked.id)
        
        print(f"Retrieved entry weather: {retrieved_entry.weather}")
        print(f"Retrieved weather journal_entry_id: {retrieved_weather.journal_entry_id}")
        
        # Test 4: Test the form data parsing like in routes.py
        print("\n=== Test 4: Form data parsing simulation ===")
        
        # Simulate form data like what would come from the frontend
        test_weather_data = json.dumps({
            'temperature': 18.5,
            'condition': 'Partly Cloudy',
            'humidity': 75
        })
        
        print(f"Test weather data: {test_weather_data}")
        
        # Parse like in routes.py
        try:
            weather_info = json.loads(test_weather_data)
            weather_parsed = WeatherData(
                temperature=weather_info.get('temperature'),
                weather_condition=weather_info.get('condition', ''),
                humidity=weather_info.get('humidity')
            )
            
            # Create a new entry to test with
            entry_parsed = JournalEntry(
                user_id=test_user.id,
                content='Test entry with parsed weather',
                entry_type='quick'
            )
            db.session.add(entry_parsed)
            db.session.flush()
            
            # Set up the relationship
            weather_parsed.journal_entry_id = entry_parsed.id
            db.session.add(weather_parsed)
            db.session.flush()
            entry_parsed.weather_id = weather_parsed.id
            
            db.session.commit()
            
            print(f"Parsed weather creation successful: ID {weather_parsed.id}")
            print(f"Entry with parsed weather: ID {entry_parsed.id}")
            
        except Exception as e:
            print(f"Error parsing weather data: {e}")
        
        # Test 5: Check what's in the database
        print("\n=== Test 5: Database contents ===")
        all_weather = WeatherData.query.all()
        all_entries = JournalEntry.query.filter_by(user_id=test_user.id).all()
        
        print(f"Total weather records: {len(all_weather)}")
        for w in all_weather:
            print(f"  Weather {w.id}: {w.temperature}°C, {w.weather_condition}, entry_id={w.journal_entry_id}")
        
        print(f"Total entries for test user: {len(all_entries)}")
        for e in all_entries:
            print(f"  Entry {e.id}: {e.content[:30]}..., weather_id={e.weather_id}")
        
        # Cleanup
        print("\n=== Cleanup ===")
        for entry in all_entries:
            # Clear weather record references before deletion (like in routes.py)
            if entry.weather_id:
                weather_record = db.session.get(WeatherData, entry.weather_id)
                if weather_record and weather_record.journal_entry_id == entry.id:
                    weather_record.journal_entry_id = None

            # Clear any other weather records referencing this entry
            WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
            
        # Flush to ensure weather references are cleared before deleting entries
        db.session.flush()
        
        # Now delete entries safely
        for entry in all_entries:
            db.session.delete(entry)
        
        # Delete direct weather record
        if weather_direct:
            db.session.delete(weather_direct)
        
        db.session.delete(test_user)
        db.session.commit()
        print("Cleanup complete")

if __name__ == '__main__':
    test_weather_saving()