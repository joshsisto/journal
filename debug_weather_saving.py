#!/usr/bin/env python3
"""
Debug script to test weather and location saving directly
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, JournalEntry, WeatherData, Location, User
from flask_login import login_user

def test_weather_saving():
    app = create_app()
    
    with app.app_context():
        # Create test user
        test_user = User.query.filter_by(username='admin').first()
        if not test_user:
            test_user = User(username='testuser', email='test@example.com')
            test_user.set_password('testpass')
            db.session.add(test_user)
            db.session.commit()
        
        print(f"Using test user: {test_user.username} (ID: {test_user.id})")
        
        # Test data
        location_data = {
            "latitude": 40.7589,
            "longitude": -73.9851,
            "address": "New York, NY"
        }
        
        weather_data = {
            "temperature": 22.5,
            "condition": "Partly Cloudy",
            "humidity": 65
        }
        
        print(f"Location data: {json.dumps(location_data)}")
        print(f"Weather data: {json.dumps(weather_data)}")
        
        # Test 1: Direct creation via models
        print("\n=== Test 1: Direct model creation ===")
        try:
            # Create location
            location = Location(
                latitude=location_data['latitude'],
                longitude=location_data['longitude'],
                address=location_data['address'],
                city='New York',
                state='NY'
            )
            db.session.add(location)
            db.session.flush()
            print(f"✅ Location created: ID {location.id}")
            
            # Create weather
            weather = WeatherData(
                temperature=weather_data['temperature'],
                weather_condition=weather_data['condition'],
                humidity=weather_data['humidity'],
                location_id=location.id
            )
            db.session.add(weather)
            db.session.flush()
            print(f"✅ Weather created: ID {weather.id}")
            
            # Create journal entry
            entry = JournalEntry(
                user_id=test_user.id,
                content='Test entry for weather debugging',
                entry_type='quick',
                location_id=location.id,
                weather_id=weather.id
            )
            db.session.add(entry)
            
            # Link weather back to entry
            weather.journal_entry_id = entry.id
            
            db.session.commit()
            print(f"✅ Journal entry created: ID {entry.id}")
            print(f"   Location ID: {entry.location_id}")
            print(f"   Weather ID: {entry.weather_id}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
        
        # Test 2: Simulate dashboard POST route logic
        print("\n=== Test 2: Dashboard route logic simulation ===")
        try:
            # Simulate the exact logic from routes.py dashboard_post
            location_data_json = json.dumps(location_data)
            weather_data_json = json.dumps(weather_data)
            
            entry = JournalEntry(
                user_id=test_user.id,
                content='Test quick entry via dashboard logic',
                entry_type='quick'
            )
            db.session.add(entry)
            db.session.flush()
            print(f"✅ Entry created: ID {entry.id}")
            
            # Handle location data (copying exact logic from routes.py)
            if location_data_json:
                try:
                    loc_data = json.loads(location_data_json)
                    print(f"Parsed location data: {loc_data}")
                    location_record = Location(
                        latitude=loc_data.get('latitude'),
                        longitude=loc_data.get('longitude'),
                        address=loc_data.get('address', ''),
                        city='Unknown',  # This matches routes.py
                        state='Unknown'
                    )
                    db.session.add(location_record)
                    db.session.flush()
                    entry.location_id = location_record.id
                    print(f"✅ Location record created: ID {location_record.id}")
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"❌ Location error: {e}")
            
            # Handle weather data (copying exact logic from routes.py)
            if weather_data_json:
                try:
                    weather_info = json.loads(weather_data_json)
                    print(f"Parsed weather data: {weather_info}")
                    weather_record = WeatherData(
                        temperature=weather_info.get('temperature'),
                        weather_condition=weather_info.get('condition', ''),
                        humidity=weather_info.get('humidity'),
                        journal_entry_id=entry.id
                    )
                    db.session.add(weather_record)
                    db.session.flush()
                    entry.weather_id = weather_record.id
                    print(f"✅ Weather record created: ID {weather_record.id}")
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"❌ Weather error: {e}")
            
            db.session.commit()
            print(f"✅ Final entry state:")
            print(f"   Location ID: {entry.location_id}")
            print(f"   Weather ID: {entry.weather_id}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
        
        # Test 3: Verify data in database
        print("\n=== Test 3: Database verification ===")
        entries = JournalEntry.query.filter_by(user_id=test_user.id).order_by(JournalEntry.created_at.desc()).limit(5).all()
        print(f"Recent entries for user {test_user.username}:")
        for entry in entries:
            print(f"  Entry {entry.id}: {entry.content[:50]}...")
            print(f"    Location ID: {entry.location_id}")
            print(f"    Weather ID: {entry.weather_id}")
            if entry.location_id:
                loc = db.session.get(Location, entry.location_id)
                print(f"    Location: {loc.latitude}, {loc.longitude} - {loc.address}")
            if entry.weather_id:
                weather = db.session.get(WeatherData, entry.weather_id)
                print(f"    Weather: {weather.temperature}°C, {weather.weather_condition}")
        
        # Clean up test entries
        print("\n=== Cleanup ===")
        test_entries = JournalEntry.query.filter(
            JournalEntry.content.like('%Test%')
        ).all()
        
        for entry in test_entries:
            if entry.weather_id:
                weather = db.session.get(WeatherData, entry.weather_id)
                if weather:
                    db.session.delete(weather)
            if entry.location_id:
                location = db.session.get(Location, entry.location_id)
                if location:
                    db.session.delete(location)
            db.session.delete(entry)
        
        db.session.commit()
        print("✅ Cleanup complete")

if __name__ == '__main__':
    test_weather_saving()