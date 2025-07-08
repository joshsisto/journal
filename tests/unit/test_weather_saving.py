"""
Unit tests for weather saving functionality.

Tests the weather data processing and storage for journal entries.
"""

import pytest
import json
from unittest.mock import patch
from models import db, JournalEntry, WeatherData, GuidedResponse
from services.journal_service import create_quick_entry_simple, create_guided_entry_simple


class TestWeatherSaving:
    """Test weather data saving with journal entries."""
    
    def test_quick_entry_with_weather_json(self, app, db_session, user):
        """Test creating quick entry with weather data as JSON."""
        weather_data = {
            'temperature': 22.5,
            'condition': 'Sunny',
            'humidity': 65,
            'wind_speed': 3.2
        }
        
        # Simulate form data like what the frontend sends
        form_data = {
            'content': 'Beautiful sunny day!',
            'weather_data': json.dumps(weather_data)
        }
        
        # Create entry using the service (which calls the same logic as routes.py)
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry is not None
        assert entry.content == 'Beautiful sunny day!'
        assert entry.entry_type == 'quick'
        assert entry.user_id == user.id
        
        # Check weather was created and linked
        assert entry.weather_id is not None
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather is not None
        assert weather.temperature == 22.5
        assert weather.weather_condition == 'Sunny'
        assert weather.humidity == 65
        assert weather.journal_entry_id == entry.id
    
    def test_guided_entry_with_weather_json(self, app, db_session, user):
        """Test creating guided entry with weather data as JSON."""
        weather_data = {
            'temperature': 18.0,
            'condition': 'Rainy',
            'humidity': 85
        }
        
        # Simulate guided journal form data
        form_data = {
            'question_feeling_scale': '7',
            'question_feeling_reason': 'Cozy rainy day',
            'weather_data': json.dumps(weather_data)
        }
        
        # Create guided entry
        entry = create_guided_entry_simple(user.id, form_data)
        
        assert entry is not None
        assert entry.entry_type == 'guided'
        assert entry.user_id == user.id
        
        # Check weather was created and linked
        assert entry.weather_id is not None
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather is not None
        assert weather.temperature == 18.0
        assert weather.weather_condition == 'Rainy'
        assert weather.humidity == 85
        assert weather.journal_entry_id == entry.id
        
        # Check guided responses were created
        responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
        assert len(responses) > 0
        
        # Find the feeling_scale response
        feeling_response = next((r for r in responses if r.question_id == 'feeling_scale'), None)
        assert feeling_response is not None
        assert feeling_response.response == '7'
    
    def test_entry_without_weather_data(self, app, db_session, user):
        """Test creating entry without weather data."""
        form_data = {
            'content': 'Just a regular entry',
            'weather_data': ''  # Empty weather data
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry is not None
        assert entry.content == 'Just a regular entry'
        assert entry.weather_id is None  # No weather should be linked
    
    def test_entry_with_invalid_weather_json(self, app, db_session, user):
        """Test creating entry with malformed weather JSON."""
        form_data = {
            'content': 'Entry with bad weather data',
            'weather_data': 'invalid-json-data'  # Invalid JSON
        }
        
        # Should not raise an exception, just skip weather creation
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry is not None
        assert entry.content == 'Entry with bad weather data'
        assert entry.weather_id is None  # No weather due to invalid JSON
    
    def test_weather_with_partial_data(self, app, db_session, user):
        """Test weather creation with only some fields."""
        weather_data = {
            'temperature': 25.0,
            'condition': 'Clear'
            # Missing humidity, wind_speed, etc.
        }
        
        form_data = {
            'content': 'Entry with partial weather',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.weather_id is not None
        weather = db_session.get(WeatherData, entry.weather_id)
        assert weather.temperature == 25.0
        assert weather.weather_condition == 'Clear'
        assert weather.humidity is None  # Should handle missing fields gracefully
    
    def test_weather_relationship_integrity(self, app, db_session, user):
        """Test that weather-entry relationships maintain referential integrity."""
        weather_data = {
            'temperature': 20.0,
            'condition': 'Cloudy',
            'humidity': 70
        }
        
        form_data = {
            'content': 'Testing relationships',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        weather_id = entry.weather_id
        
        # Verify forward relationship (entry -> weather)
        assert entry.weather is not None
        assert entry.weather.id == weather_id
        
        # Verify backward relationship (weather -> entry)
        weather = db_session.get(WeatherData, weather_id)
        assert weather.journal_entry_id == entry.id
        
        # Test that deleting entry properly handles weather cleanup
        # Clear weather reference before deletion (as done in routes.py)
        if entry.weather_id:
            weather_record = db_session.get(WeatherData, entry.weather_id)
            if weather_record and weather_record.journal_entry_id == entry.id:
                weather_record.journal_entry_id = None
        
        # Clear any other weather records referencing this entry
        WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
        db_session.flush()
        
        # Delete the entry (should now work without foreign key issues)
        db_session.delete(entry)
        db_session.commit()
        
        # Weather record should still exist but not reference the deleted entry
        weather_after = db_session.get(WeatherData, weather_id)
        if weather_after:
            # Weather should exist but not reference the deleted entry
            assert weather_after.journal_entry_id is None
    
    def test_multiple_entries_different_weather(self, app, db_session, user):
        """Test creating multiple entries with different weather data."""
        weather_data_1 = {
            'temperature': 15.0,
            'condition': 'Snow',
            'humidity': 90
        }
        
        weather_data_2 = {
            'temperature': 30.0,
            'condition': 'Hot',
            'humidity': 40
        }
        
        form_data_1 = {
            'content': 'Snowy day',
            'weather_data': json.dumps(weather_data_1)
        }
        
        form_data_2 = {
            'content': 'Hot summer day',
            'weather_data': json.dumps(weather_data_2)
        }
        
        entry_1 = create_quick_entry_simple(user.id, form_data_1)
        entry_2 = create_quick_entry_simple(user.id, form_data_2)
        
        # Verify both entries have different weather
        assert entry_1.weather_id != entry_2.weather_id
        assert entry_1.weather.temperature == 15.0
        assert entry_1.weather.weather_condition == 'Snow'
        assert entry_2.weather.temperature == 30.0
        assert entry_2.weather.weather_condition == 'Hot'
    
    def test_weather_data_types_and_validation(self, app, db_session, user):
        """Test that weather data types are handled correctly."""
        weather_data = {
            'temperature': '24.5',  # String that should convert to float
            'condition': 'Partly Cloudy',
            'humidity': '75',  # String that should convert to int
            'wind_speed': 'invalid'  # Invalid data that should be skipped
        }
        
        form_data = {
            'content': 'Testing data type conversion',
            'weather_data': json.dumps(weather_data)
        }
        
        entry = create_quick_entry_simple(user.id, form_data)
        
        assert entry.weather_id is not None
        weather = db_session.get(WeatherData, entry.weather_id)
        
        # Should handle type conversion gracefully
        assert isinstance(weather.temperature, (int, float))
        assert weather.temperature == 24.5
        assert weather.humidity == 75
        assert weather.weather_condition == 'Partly Cloudy'