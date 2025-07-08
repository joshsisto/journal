#!/usr/bin/env python3
"""
Check specific user entry and how it displays weather/location
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, JournalEntry, WeatherData, Location, User

def check_user_entry():
    app = create_app()
    
    with app.app_context():
        # Look for the josh user's recent entry
        josh_user = User.query.filter_by(username='josh').first()
        if not josh_user:
            print("Josh user not found!")
            return
        
        print(f"Found user: {josh_user.username} (ID: {josh_user.id})")
        
        # Get his recent entries
        recent_entries = JournalEntry.query.filter_by(
            user_id=josh_user.id
        ).order_by(JournalEntry.created_at.desc()).limit(5).all()
        
        print(f"\nRecent entries for {josh_user.username}:")
        print("=" * 60)
        
        for entry in recent_entries:
            print(f"Entry {entry.id} - {entry.created_at}")
            print(f"  Content: {entry.content}")
            print(f"  Type: {entry.entry_type}")
            
            # Check weather data
            if entry.weather_id:
                weather = db.session.get(WeatherData, entry.weather_id)
                if weather:
                    print(f"  🌤️  Weather: {weather.temperature}°C, {weather.weather_condition}")
                    print(f"     Humidity: {weather.humidity}%")
                    print(f"     Weather summary: {weather.get_display_summary()}")
                else:
                    print(f"  ❌ Weather ID {entry.weather_id} not found!")
            else:
                print(f"  ⚪ No weather data")
            
            # Check location data
            if entry.location_id:
                location = db.session.get(Location, entry.location_id)
                if location:
                    print(f"  📍 Location: {location.latitude}, {location.longitude}")
                    print(f"     Address: {location.address}")
                    print(f"     Display name: {location.get_display_name()}")
                else:
                    print(f"  ❌ Location ID {entry.location_id} not found!")
            else:
                print(f"  ⚪ No location data")
            
            print("-" * 40)
        
        # Test what the frontend would see by checking template rendering data
        print("\nFrontend display test:")
        if recent_entries:
            entry = recent_entries[0]  # Most recent entry
            print(f"Testing entry {entry.id}:")
            
            # Test weather display
            if entry.weather_id and entry.weather:
                print(f"Weather object available: {entry.weather}")
                print(f"Weather display summary: {entry.weather.get_display_summary()}")
            
            # Test location display
            if entry.location_id and entry.location:
                print(f"Location object available: {entry.location}")
                print(f"Location display name: {entry.location.get_display_name()}")

if __name__ == '__main__':
    check_user_entry()