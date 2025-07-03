"""
Unit tests for location and weather functionality.

Tests location tagging, weather integration, and related features.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from models import db, Location, WeatherData, JournalEntry, User
from services.weather_service import WeatherService


class TestLocationModel:
    """Test Location model functionality."""
    
    def test_location_creation_basic(self, app, db_session):
        """Test creating a basic location."""
        location = Location(
            name='Test Location',
            city='Test City',
            state='Test State',
            country='Test Country'
        )
        db_session.add(location)
        db_session.commit()
        
        assert location.id is not None
        assert location.name == 'Test Location'
        assert location.get_display_name() == 'Test Location'
    
    def test_location_with_coordinates(self, app, db_session):
        """Test creating location with GPS coordinates."""
        location = Location(
            name='GPS Location',
            latitude=40.7128,
            longitude=-74.0060,
            location_type='gps'
        )
        db_session.add(location)
        db_session.commit()
        
        coordinates = location.get_coordinates()
        assert coordinates == (40.7128, -74.0060)
        assert location.location_type == 'gps'
    
    def test_location_display_name_fallbacks(self, app, db_session):
        """Test location display name with various data combinations."""
        # Test with city, state, country
        location1 = Location(city='New York', state='NY', country='USA')
        assert 'New York, NY, USA' in location1.get_display_name()
        
        # Test with coordinates only
        location2 = Location(latitude=40.7128, longitude=-74.0060)
        display_name = location2.get_display_name()
        assert '40.7128' in display_name and '-74.0060' in display_name
        
        # Test with no data
        location3 = Location()
        assert location3.get_display_name() == 'Unknown Location'
    
    def test_location_to_dict(self, app, db_session):
        """Test location to_dict method."""
        location = Location(
            name='Test Location',
            latitude=40.7128,
            longitude=-74.0060,
            city='New York',
            state='NY',
            country='USA'
        )
        
        location_dict = location.to_dict()
        
        assert location_dict['name'] == 'Test Location'
        assert location_dict['latitude'] == 40.7128
        assert location_dict['longitude'] == -74.0060
        assert location_dict['city'] == 'New York'
        assert 'display_name' in location_dict


class TestWeatherModel:
    """Test WeatherData model functionality."""
    
    def test_weather_creation_basic(self, app, db_session):
        """Test creating basic weather data."""
        weather = WeatherData(
            temperature=22.5,
            temperature_unit='celsius',
            weather_condition='Sunny',
            humidity=65
        )
        db_session.add(weather)
        db_session.commit()
        
        assert weather.id is not None
        assert weather.temperature == 22.5
        assert weather.weather_condition == 'Sunny'
        assert weather.humidity == 65
    
    def test_weather_temperature_conversion(self, app, db_session):
        """Test temperature unit conversion methods."""
        # Test Celsius to Fahrenheit
        weather_c = WeatherData(temperature=20.0, temperature_unit='celsius')
        fahrenheit = weather_c.get_temperature_fahrenheit()
        assert fahrenheit == 68.0
        
        # Test Fahrenheit to Celsius
        weather_f = WeatherData(temperature=68.0, temperature_unit='fahrenheit')
        celsius = weather_f.get_temperature_celsius()
        assert celsius == 20.0
    
    def test_weather_display_summary(self, app, db_session):
        """Test weather display summary generation."""
        weather = WeatherData(
            temperature=22.0,
            temperature_unit='celsius',
            weather_condition='Partly Cloudy',
            humidity=70,
            wind_speed=5.5
        )
        
        summary = weather.get_display_summary()
        
        assert '22°C' in summary
        assert 'Partly Cloudy' in summary
        assert '70% humidity' in summary
        assert '6 mph wind' in summary  # Rounded wind speed
    
    def test_weather_to_dict(self, app, db_session):
        """Test weather to_dict method."""
        weather = WeatherData(
            temperature=25.0,
            weather_condition='Clear',
            humidity=60,
            wind_speed=3.2
        )
        
        weather_dict = weather.to_dict()
        
        assert weather_dict['temperature'] == 25.0
        assert weather_dict['weather_condition'] == 'Clear'
        assert weather_dict['humidity'] == 60
        assert 'display_summary' in weather_dict


class TestWeatherService:
    """Test WeatherService functionality."""
    
    def test_weather_service_init(self):
        """Test weather service initialization."""
        service = WeatherService()
        assert service.base_url == "http://api.openweathermap.org/data/2.5"
        assert service.geo_url == "http://api.openweathermap.org/geo/1.0"
        assert service.cache_duration.total_seconds() == 30 * 60  # 30 minutes
    
    @patch('services.weather_service.requests.get')
    def test_geocode_location_success(self, mock_get):
        """Test successful location geocoding."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{
            'lat': 40.7128,
            'lon': -74.0060,
            'name': 'New York'
        }]
        mock_get.return_value = mock_response
        
        service = WeatherService()
        service.api_key = 'test_key'
        
        coordinates = service.geocode_location('New York, NY')
        
        assert coordinates == (40.7128, -74.0060)
        mock_get.assert_called_once()
    
    @patch('services.weather_service.requests.get')
    def test_reverse_geocode_success(self, mock_get):
        """Test successful reverse geocoding."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{
            'name': 'New York',
            'state': 'NY',
            'country': 'US'
        }]
        mock_get.return_value = mock_response
        
        service = WeatherService()
        service.api_key = 'test_key'
        
        location_info = service.reverse_geocode(40.7128, -74.0060)
        
        assert location_info['name'] == 'New York'
        assert location_info['state'] == 'NY'
        assert location_info['country'] == 'US'
    
    def test_create_location_from_coordinates(self, app, db_session):
        """Test creating location from coordinates."""
        service = WeatherService()
        
        with patch.object(service, 'reverse_geocode') as mock_reverse:
            mock_reverse.return_value = {
                'name': 'Test City',
                'city': 'Test City',
                'state': 'TS',
                'country': 'TC'
            }
            
            location = service.create_location_from_coordinates(40.7128, -74.0060, 'Custom Name')
            
            assert location is not None
            assert location.name == 'Custom Name'
            assert location.latitude == 40.7128
            assert location.longitude == -74.0060
            assert location.location_type == 'gps'
    
    def test_get_user_recent_locations(self, app, db_session, user):
        """Test getting user's recent locations."""
        # Create test locations and entries
        location1 = Location(name='Location 1', latitude=40.7128, longitude=-74.0060)
        location2 = Location(name='Location 2', latitude=34.0522, longitude=-118.2437)
        db_session.add(location1)
        db_session.add(location2)
        db_session.flush()
        
        entry1 = JournalEntry(user_id=user.id, content='Test 1', entry_type='quick', location_id=location1.id)
        entry2 = JournalEntry(user_id=user.id, content='Test 2', entry_type='quick', location_id=location2.id)
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()
        
        service = WeatherService()
        recent_locations = service.get_user_recent_locations(user.id, limit=5)
        
        assert len(recent_locations) == 2
        assert recent_locations[0].name in ['Location 1', 'Location 2']


class TestLocationWeatherJournalIntegration:
    """Test integration of location and weather with journal entries."""
    
    def test_journal_entry_with_location(self, app, db_session, user):
        """Test creating journal entry with location."""
        location = Location(name='Test Location', city='Test City')
        db_session.add(location)
        db_session.flush()
        
        entry = JournalEntry(
            user_id=user.id,
            content='Test entry',
            entry_type='quick',
            location_id=location.id
        )
        db_session.add(entry)
        db_session.commit()
        
        assert entry.location is not None
        assert entry.location.name == 'Test Location'
        assert location in entry.location.journal_entries
    
    def test_journal_entry_with_weather(self, app, db_session, user):
        """Test creating journal entry with weather data."""
        weather = WeatherData(
            temperature=20.0,
            weather_condition='Sunny',
            humidity=65
        )
        db_session.add(weather)
        db_session.flush()
        
        entry = JournalEntry(
            user_id=user.id,
            content='Beautiful day!',
            entry_type='quick',
            weather_id=weather.id
        )
        db_session.add(entry)
        db_session.commit()
        
        assert entry.weather is not None
        assert entry.weather.weather_condition == 'Sunny'
        assert weather in entry.weather.journal_entries
    
    def test_journal_entry_with_location_and_weather(self, app, db_session, user):
        """Test creating journal entry with both location and weather."""
        location = Location(name='Park', latitude=40.7128, longitude=-74.0060)
        weather = WeatherData(temperature=22.0, weather_condition='Partly Cloudy')
        
        db_session.add(location)
        db_session.add(weather)
        db_session.flush()
        
        entry = JournalEntry(
            user_id=user.id,
            content='Nice walk in the park',
            entry_type='quick',
            location_id=location.id,
            weather_id=weather.id
        )
        db_session.add(entry)
        db_session.commit()
        
        assert entry.location.name == 'Park'
        assert entry.weather.weather_condition == 'Partly Cloudy'


class TestLocationWeatherAPI:
    """Test location and weather API endpoints."""
    
    @patch('services.weather_service.weather_service.geocode_location')
    def test_api_location_search_success(self, mock_geocode, client, logged_in_user):
        """Test successful location search API."""
        mock_geocode.return_value = (40.7128, -74.0060)
        
        with patch('services.weather_service.weather_service.reverse_geocode') as mock_reverse:
            mock_reverse.return_value = {
                'name': 'New York',
                'city': 'New York',
                'state': 'NY',
                'country': 'US',
                'address': 'New York, NY, US'
            }
            
            response = client.post('/api/location/search', 
                                 json={'location_name': 'New York'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['latitude'] == 40.7128
            assert data['longitude'] == -74.0060
            assert data['name'] == 'New York'
    
    def test_api_location_search_empty_name(self, client, logged_in_user):
        """Test location search with empty name."""
        response = client.post('/api/location/search',
                             json={'location_name': ''},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    @patch('services.weather_service.weather_service.reverse_geocode')
    def test_api_reverse_geocode_success(self, mock_reverse, client, logged_in_user):
        """Test successful reverse geocoding API."""
        mock_reverse.return_value = {
            'name': 'Central Park',
            'city': 'New York',
            'state': 'NY',
            'country': 'US'
        }
        
        response = client.post('/api/location/reverse-geocode',
                             json={'latitude': 40.7829, 'longitude': -73.9654},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['name'] == 'Central Park'
    
    def test_api_reverse_geocode_invalid_coordinates(self, client, logged_in_user):
        """Test reverse geocoding with invalid coordinates."""
        response = client.post('/api/location/reverse-geocode',
                             json={'latitude': 91, 'longitude': 181},  # Invalid ranges
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    @patch('services.weather_service.weather_service.get_weather_by_coordinates')
    def test_api_weather_current_success(self, mock_weather, client, logged_in_user):
        """Test successful current weather API."""
        mock_weather.return_value = {
            'temperature': 22.5,
            'temperature_unit': 'celsius',
            'weather_condition': 'Clear',
            'humidity': 65,
            'wind_speed': 5.2
        }
        
        response = client.post('/api/weather/current',
                             json={'latitude': 40.7128, 'longitude': -74.0060},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['temperature'] == 22.5
        assert data['weather_condition'] == 'Clear'


class TestLocationWeatherForms:
    """Test location and weather form integration."""
    
    def test_quick_journal_with_location_data(self, client, logged_in_user, user):
        """Test creating quick journal entry with location data."""
        form_data = {
            'content': 'Test entry with location',
            'location_name': 'Test Location',
            'location_city': 'Test City',
            'location_latitude': '40.7128',
            'location_longitude': '-74.0060',
            'weather_temperature': '22.5',
            'weather_condition': 'Sunny',
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/quick', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check that entry was created with location and weather
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.location is not None
        assert entry.location.name == 'Test Location'
        assert entry.weather is not None
        assert entry.weather.temperature == 22.5
    
    def test_guided_journal_with_location_data(self, client, logged_in_user, user):
        """Test creating guided journal entry with location data."""
        form_data = {
            'feeling_scale': '8',
            'feeling_reason': 'Great day!',
            'location_name': 'Central Park',
            'location_city': 'New York',
            'weather_temperature': '25.0',
            'weather_condition': 'Clear',
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check that entry was created with location and weather
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.location is not None
        assert entry.location.name == 'Central Park'
        assert entry.weather is not None
        assert entry.weather.temperature == 25.0


class TestLocationWeatherSecurity:
    """Test security aspects of location and weather features."""
    
    def test_location_api_requires_authentication(self, client):
        """Test that location API requires authentication."""
        response = client.post('/api/location/search',
                             json={'location_name': 'Test'})
        assert response.status_code == 302  # Redirect to login
    
    def test_weather_api_requires_authentication(self, client):
        """Test that weather API requires authentication."""
        response = client.post('/api/weather/current',
                             json={'latitude': 40, 'longitude': -74})
        assert response.status_code == 302  # Redirect to login
    
    def test_coordinate_validation(self, client, logged_in_user):
        """Test coordinate validation in APIs."""
        # Test invalid latitude
        response = client.post('/api/location/reverse-geocode',
                             json={'latitude': 91, 'longitude': 0},
                             headers={'Content-Type': 'application/json'})
        assert response.status_code == 400
        
        # Test invalid longitude
        response = client.post('/api/location/reverse-geocode',
                             json={'latitude': 0, 'longitude': 181},
                             headers={'Content-Type': 'application/json'})
        assert response.status_code == 400


class TestLocationWeatherEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_location_with_no_data(self, app, db_session):
        """Test creating location with minimal data."""
        location = Location()
        db_session.add(location)
        db_session.commit()
        
        assert location.id is not None
        assert location.get_display_name() == 'Unknown Location'
    
    def test_weather_with_null_values(self, app, db_session):
        """Test weather data with null values."""
        weather = WeatherData(
            temperature=None,
            weather_condition=None,
            humidity=None
        )
        db_session.add(weather)
        db_session.commit()
        
        summary = weather.get_display_summary()
        assert 'Weather data available' in summary
    
    def test_location_deduplication(self, app, db_session):
        """Test that similar locations are deduplicated."""
        from services.journal_service import _handle_location_and_weather
        
        # Create two entries with similar GPS coordinates
        form_data1 = {
            'location_latitude': '40.7128',
            'location_longitude': '-74.0060',
            'location_name': 'Location 1'
        }
        
        form_data2 = {
            'location_latitude': '40.7129',  # Very close coordinates
            'location_longitude': '-74.0061',
            'location_name': 'Location 2'
        }
        
        location_id1, _ = _handle_location_and_weather(form_data1)
        db_session.commit()
        
        location_id2, _ = _handle_location_and_weather(form_data2)
        db_session.commit()
        
        # Should reuse the same location for nearby coordinates
        assert location_id1 == location_id2
    
    def test_weather_service_without_api_key(self):
        """Test weather service behavior without API key."""
        service = WeatherService()
        service.api_key = None
        
        # Should return None gracefully
        coordinates = service.geocode_location('Test Location')
        assert coordinates is None
        
        weather_data = service.get_weather_by_coordinates(40.7128, -74.0060)
        assert weather_data is None
    
    def test_malformed_coordinates_in_form(self, app, db_session):
        """Test handling malformed coordinates in form data."""
        from services.journal_service import _handle_location_and_weather
        
        form_data = {
            'location_latitude': 'invalid',
            'location_longitude': 'also_invalid',
            'location_name': 'Test Location'
        }
        
        # Should not crash and should create location without coordinates
        location_id, weather_id = _handle_location_and_weather(form_data)
        db_session.commit()
        
        if location_id:
            location = Location.query.get(location_id)
            assert location.latitude is None
            assert location.longitude is None
            assert location.location_type == 'manual'