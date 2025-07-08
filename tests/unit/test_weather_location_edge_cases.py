"""
Additional unit tests for weather and location edge cases.

These tests specifically target edge cases that might occur in production
and ensure robust error handling for weather and location saving.
"""

import pytest
import json
from unittest.mock import patch
from models import db, JournalEntry, WeatherData, Location, GuidedResponse
from services.journal_service import create_quick_entry_simple, create_guided_entry_simple


class TestWeatherLocationEdgeCases:
    """Test edge cases for weather and location functionality."""
    
    def test_location_only_without_weather(self, app, db_session, user):
        """Test creating entry with location but no weather data."""
        form_data = {
            'content': 'Entry with location only',
            'location_name': 'Central Park',
            'location_city': 'New York',
            'location_state': 'NY',
            'location_latitude': '40.7851',
            'location_longitude': '-73.9683'
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.location_id is not None
        assert entry.weather_id is None
        
        location = db_session.get(Location, entry.location_id)
        assert location.name == 'Central Park'
        assert location.city == 'New York'
        assert location.latitude == 40.7851
        assert location.longitude == -73.9683
    
    def test_weather_only_without_location(self, app, db_session, user):
        """Test creating entry with weather but no location data."""
        weather_data = {
            'temperature': 18.5,
            'condition': 'Partly Cloudy',
            'humidity': 72
        }
        
        form_data = {
            'content': 'Entry with weather only',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.weather_id is not None
        assert entry.location_id is None
        
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather.temperature == 18.5
        assert weather.weather_condition == 'Partly Cloudy'
        assert weather.location_id is None
    
    def test_location_deduplication(self, app, db_session, user):
        """Test that similar locations are deduplicated."""
        # Create first entry with location
        form_data_1 = {
            'content': 'First entry',
            'location_name': 'Coffee Shop',
            'location_city': 'Seattle',
            'location_latitude': '47.6062',
            'location_longitude': '-122.3321'
        }
        
        entry_1 = create_quick_entry_simple(user.id, form_data_1)
        
        # Create second entry with very similar location (within 100m)
        form_data_2 = {
            'content': 'Second entry',
            'location_name': 'Coffee Shop',
            'location_city': 'Seattle',
            'location_latitude': '47.6063',  # Slightly different
            'location_longitude': '-122.3322'  # Slightly different
        }
        
        entry_2 = create_quick_entry_simple(user.id, form_data_2)
        
        # Should reuse the same location
        assert entry_1.location_id == entry_2.location_id
    
    def test_large_coordinate_values(self, app, db_session, user):
        """Test handling of extreme coordinate values."""
        form_data = {
            'content': 'Entry with extreme coordinates',
            'location_latitude': '89.9999',  # Near North Pole
            'location_longitude': '179.9999',  # Near International Date Line
            'location_name': 'Extreme Location'
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.location_id is not None
        location = db_session.get(Location, entry.location_id)
        assert abs(location.latitude - 89.9999) < 0.0001
        assert abs(location.longitude - 179.9999) < 0.0001
    
    def test_weather_with_extreme_values(self, app, db_session, user):
        """Test weather data with extreme but valid values."""
        weather_data = {
            'temperature': -40.0,  # Extreme cold
            'condition': 'Blizzard',
            'humidity': 100,  # Maximum humidity
            'wind_speed': 150.0,  # Hurricane-force winds
            'pressure': 870.0  # Extremely low pressure
        }
        
        form_data = {
            'content': 'Extreme weather conditions',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather.temperature == -40.0
        assert weather.weather_condition == 'Blizzard'
        assert weather.humidity == 100
        assert weather.wind_speed == 150.0
        assert weather.pressure == 870.0
    
    def test_empty_json_object(self, app, db_session, user):
        """Test handling of empty JSON object for weather."""
        form_data = {
            'content': 'Entry with empty weather JSON',
            'weather_data': '{}'  # Empty but valid JSON
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        # Should not create weather record for empty JSON
        assert entry.weather_id is None
    
    def test_partial_location_data(self, app, db_session, user):
        """Test handling of incomplete location data."""
        form_data = {
            'content': 'Entry with partial location',
            'location_city': 'Boston',
            # Missing other location fields
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.location_id is not None
        location = db_session.get(Location, entry.location_id)
        assert location.city == 'Boston'
        assert location.name is None
        assert location.latitude is None
    
    def test_unicode_location_names(self, app, db_session, user):
        """Test handling of Unicode characters in location names."""
        form_data = {
            'content': 'Entry with Unicode location',
            'location_name': 'Café München',
            'location_city': 'Zürich',
            'location_country': 'Schweiz'
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        location = db_session.get(Location, entry.location_id)
        assert location.name == 'Café München'
        assert location.city == 'Zürich'
        assert location.country == 'Schweiz'
    
    def test_weather_json_with_null_values(self, app, db_session, user):
        """Test handling of JSON with null values."""
        weather_data = {
            'temperature': 25.0,
            'condition': 'Sunny',
            'humidity': None,  # Null value
            'wind_speed': 0,   # Zero value
            'pressure': None   # Null value
        }
        
        form_data = {
            'content': 'Entry with null weather values',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather.temperature == 25.0
        assert weather.weather_condition == 'Sunny'
        assert weather.humidity is None
        assert weather.wind_speed is None  # 0 value gets converted to None due to logic
        assert weather.pressure is None
    
    def test_guided_entry_with_both_weather_and_location(self, app, db_session, user):
        """Test guided entry with both weather and location data."""
        weather_data = {
            'temperature': 22.0,
            'condition': 'Clear',
            'humidity': 60
        }
        
        form_data = {
            'question_feeling_scale': '8',
            'question_feeling_reason': 'Beautiful day outdoors',
            'weather_data': json.dumps(weather_data),
            'location_name': 'Hiking Trail',
            'location_latitude': '45.3311',
            'location_longitude': '-121.7113'
        }
        
        entry = create_guided_entry_simple(user.id, form_data)
        
        assert entry.weather_id is not None
        assert entry.location_id is not None
        
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather.temperature == 22.0
        assert weather.location_id == entry.location_id
        
        location = db_session.get(Location, entry.location_id)
        assert location.name == 'Hiking Trail'
        
        # Check that guided responses were created
        responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
        assert len(responses) >= 2
    
    def test_weather_location_relationship_consistency(self, app, db_session, user):
        """Test that weather and location are properly linked."""
        weather_data = {
            'temperature': 15.0,
            'condition': 'Rainy'
        }
        
        form_data = {
            'content': 'Testing weather-location link',
            'weather_data': json.dumps(weather_data),
            'location_name': 'Indoor Mall',
            'location_city': 'Portland'
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        weather = db_session.get(WeatherData, entry.weather_id)
        location = db_session.get(Location, entry.location_id)
        
        # Weather should reference the location
        assert weather.location_id == location.id
        
        # Weather should also reference the journal entry
        assert weather.journal_entry_id == entry.id
        
        # Entry should reference both
        assert entry.weather_id == weather.id
        assert entry.location_id == location.id
    
    def test_concurrent_entry_creation_simulation(self, app, db_session, user):
        """Test creating multiple entries quickly to simulate concurrent usage."""
        entries = []
        
        for i in range(5):
            weather_data = {
                'temperature': 20.0 + i,
                'condition': f'Condition {i}',
                'humidity': 50 + i * 5
            }
            
            form_data = {
                'content': f'Rapid entry {i}',
                'weather_data': json.dumps(weather_data),
                'location_name': f'Location {i}',
                'location_city': 'Test City'
            }
            
            entry = create_quick_entry_simple(user.id, form_data)
            entries.append(entry)
        
        # Verify all entries were created with unique weather and location records
        weather_ids = [e.weather_id for e in entries]
        location_ids = [e.location_id for e in entries]
        
        assert len(set(weather_ids)) == 5  # All different weather records
        assert len(set(location_ids)) == 5  # All different location records
        
        # Verify data integrity
        for i, entry in enumerate(entries):
            weather = db_session.get(WeatherData, entry.weather_id)
            location = db_session.get(Location, entry.location_id)
            
            assert weather.temperature == 20.0 + i
            assert weather.weather_condition == f'Condition {i}'
            assert location.name == f'Location {i}'
            assert weather.journal_entry_id == entry.id
    
    def test_deletion_with_orphaned_weather_cleanup(self, app, db_session, user):
        """Test that deleting entries properly handles weather cleanup."""
        weather_data = {
            'temperature': 25.0,
            'condition': 'Sunny',
            'humidity': 55
        }
        
        form_data = {
            'content': 'Entry to be deleted',
            'weather_data': json.dumps(weather_data),
            'location_name': 'Temporary Location'
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        weather_id = entry.weather_id
        location_id = entry.location_id
        
        # Simulate the deletion logic from routes.py
        if entry.weather_id:
            weather_record = db_session.get(WeatherData, entry.weather_id)
            if weather_record and weather_record.journal_entry_id == entry.id:
                weather_record.journal_entry_id = None
        
        WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
        db_session.flush()
        
        db_session.delete(entry)
        db_session.commit()
        
        # Weather and location should still exist but not reference the deleted entry
        weather = db_session.get(WeatherData, weather_id)
        location = db_session.get(Location, location_id)
        
        assert weather is not None
        assert location is not None
        assert weather.journal_entry_id is None
        assert weather.location_id == location_id  # Weather still linked to location