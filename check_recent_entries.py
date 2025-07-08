#!/usr/bin/env python3
"""
Check recent journal entries for weather/location data
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, JournalEntry, WeatherData, Location, User

def check_recent_entries():
    app = create_app()
    
    with app.app_context():
        # Check entries from last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        recent_entries = JournalEntry.query.filter(
            JournalEntry.created_at >= since
        ).order_by(JournalEntry.created_at.desc()).limit(20).all()
        
        print(f"Recent journal entries (last 24 hours): {len(recent_entries)}")
        print("=" * 80)
        
        for entry in recent_entries:
            user = db.session.get(User, entry.user_id)
            print(f"Entry {entry.id} by {user.username if user else 'Unknown'} at {entry.created_at}")
            print(f"  Content: {entry.content[:100]}...")
            print(f"  Type: {entry.entry_type}")
            print(f"  Location ID: {entry.location_id}")
            print(f"  Weather ID: {entry.weather_id}")
            
            if entry.location_id:
                location = db.session.get(Location, entry.location_id)
                if location:
                    print(f"  📍 Location: {location.latitude}, {location.longitude}")
                    print(f"     Address: {location.address}")
                else:
                    print(f"  ❌ Location record not found!")
            
            if entry.weather_id:
                weather = db.session.get(WeatherData, entry.weather_id)
                if weather:
                    print(f"  🌤️  Weather: {weather.temperature}°C, {weather.weather_condition}")
                    print(f"     Humidity: {weather.humidity}%")
                else:
                    print(f"  ❌ Weather record not found!")
            
            print("-" * 40)
        
        # Check for orphaned weather/location records
        print("\nOrphaned weather records (no journal_entry_id):")
        orphaned_weather = WeatherData.query.filter(
            WeatherData.journal_entry_id.is_(None),
            WeatherData.recorded_at >= since
        ).limit(10).all()
        
        for weather in orphaned_weather:
            print(f"  Weather {weather.id}: {weather.temperature}°C, {weather.weather_condition}")
        
        print(f"\nOrphaned location records (recent):")
        orphaned_locations = Location.query.filter(
            Location.created_at >= since
        ).limit(10).all()
        
        for location in orphaned_locations:
            # Check if this location is referenced by any entries
            referenced = JournalEntry.query.filter_by(location_id=location.id).first()
            if not referenced:
                print(f"  Location {location.id}: {location.latitude}, {location.longitude} - {location.address}")

if __name__ == '__main__':
    check_recent_entries()