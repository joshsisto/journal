"""
Integration tests for weather and location form submissions.

These tests simulate real browser form submissions to catch issues
that unit tests miss, like security validation blocking legitimate data.
"""

import pytest
import json
from flask import url_for
from models import db, JournalEntry, WeatherData, Location


class TestWeatherFormSubmission:
    """Integration tests for weather form submission endpoints."""

    @pytest.fixture
    def logged_in_user(self, client, user):
        """Log in a user for testing."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        return user

    def test_quick_journal_with_weather_json_submission(self, client, logged_in_user):
        """Test submitting quick journal with weather JSON data (real form submission)."""
        # Get CSRF token first
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Extract CSRF token from the response
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Real weather data that was failing in production
        weather_data = {
            "temperature": 72,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "location": "33.4528, -112.0685"
        }
        
        location_data = {
            "latitude": 33.4528292,
            "longitude": -112.0685027,
            "address": "33.4528, -112.0685"
        }
        
        # Submit form exactly like the browser does
        form_data = {
            '_csrf_token': csrf_token,
            'content': 'Testing weather submission with coordinates',
            'weather_data': json.dumps(weather_data),
            'location_data': json.dumps(location_data),
            'entry_type': 'quick'
        }
        
        response = client.post('/dashboard', data=form_data, follow_redirects=True)
        
        # Should not get 400 error (malicious input detected)
        assert response.status_code == 200
        assert b'Malicious input detected' not in response.data
        assert b'form submission failed' not in response.data.lower()
        
        # Verify entry was created
        entry = JournalEntry.query.filter_by(
            user_id=logged_in_user.id,
            content='Testing weather submission with coordinates'
        ).first()
        
        assert entry is not None
        assert entry.weather_id is not None
        assert entry.location_id is not None
        
        # Verify weather data
        weather = db.session.get(WeatherData, entry.weather_id)
        assert weather.temperature == 72
        assert weather.weather_condition == "Partly Cloudy"
        assert weather.humidity == 65
        
        # Verify location data
        location = db.session.get(Location, entry.location_id)
        assert abs(location.latitude - 33.4528292) < 0.0001
        assert abs(location.longitude - -112.0685027) < 0.0001

    def test_guided_journal_with_weather_submission(self, client, logged_in_user):
        """Test submitting guided journal with weather data."""
        response = client.get('/journal/guided')
        assert response.status_code == 200
        
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Complex weather data with potential SQL-like patterns
        weather_data = {
            "temperature": 18.5,
            "condition": "Partly Cloudy & Windy",
            "humidity": 85,
            "pressure": 1013.25,
            "wind_speed": 12.5,
            "description": "Light clouds with 15-20 mph winds"
        }
        
        form_data = {
            '_csrf_token': csrf_token,
            'question_feeling_scale': '8',
            'question_feeling_reason': 'Great weather for outdoor activities!',
            'question_about_day': 'Had a wonderful day outside enjoying the weather',
            'weather_data': json.dumps(weather_data),
            'location_data': json.dumps({
                "name": "Central Park",
                "city": "New York",
                "latitude": 40.7851,
                "longitude": -73.9683
            })
        }
        
        response = client.post('/journal/guided', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Malicious input detected' not in response.data
        
        # Verify guided entry was created
        entry = JournalEntry.query.filter_by(
            user_id=logged_in_user.id,
            entry_type='guided'
        ).order_by(JournalEntry.created_at.desc()).first()
        
        assert entry is not None
        assert entry.weather_id is not None
        assert entry.location_id is not None

    def test_extreme_coordinate_values_not_blocked(self, client, logged_in_user):
        """Test that extreme but valid coordinates don't trigger security alerts."""
        response = client.get('/dashboard')
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Extreme coordinates that might look suspicious
        location_data = {
            "latitude": 89.9999,  # Near North Pole
            "longitude": 179.9999,  # Near International Date Line
            "address": "Research Station Alpha"
        }
        
        weather_data = {
            "temperature": -40.0,  # Extreme cold
            "condition": "Blizzard",
            "humidity": 100,
            "wind_speed": 150.0,  # Hurricane force
            "pressure": 870.0  # Extremely low pressure
        }
        
        form_data = {
            '_csrf_token': csrf_token,
            'content': 'Arctic research station log entry',
            'weather_data': json.dumps(weather_data),
            'location_data': json.dumps(location_data)
        }
        
        response = client.post('/dashboard', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Malicious input detected' not in response.data

    def test_numeric_patterns_in_weather_not_flagged_as_sql_injection(self, client, logged_in_user):
        """Test that numeric patterns in weather data don't trigger SQL injection detection."""
        response = client.get('/dashboard')
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Weather data with patterns that might trigger false positives
        weather_data = {
            "temperature": 21.1,  # Could be mistaken for "1=1"
            "condition": "Clear & Sunny",  # Ampersand
            "humidity": 50,
            "description": "Temperature steady at 21.1°F, conditions 1 of 5 possible",
            "uv_index": 7.5,
            "visibility": 10.0
        }
        
        location_data = {
            "latitude": 11.1111,  # Repeating 1s
            "longitude": -111.1111,  # More repeating 1s
            "address": "123 Main St, Apt 1-1"
        }
        
        form_data = {
            '_csrf_token': csrf_token,
            'content': 'Weather contains numeric patterns that should not trigger security alerts',
            'weather_data': json.dumps(weather_data),
            'location_data': json.dumps(location_data)
        }
        
        response = client.post('/dashboard', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Malicious input detected' not in response.data
        assert b'SQL injection attempt blocked' not in response.data

    def test_special_characters_in_location_names(self, client, logged_in_user):
        """Test that special characters in location names don't cause issues."""
        response = client.get('/dashboard')
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Location names with special characters
        location_data = {
            "name": "Café München's & Restaurant",
            "city": "St. John's",
            "address": "123 O'Brien St, Apt #2-B",
            "latitude": 47.5615,
            "longitude": -52.7126
        }
        
        weather_data = {
            "temperature": 15.5,
            "condition": "Light Rain & Fog",
            "description": "Overcast with 5-10mm rain expected"
        }
        
        form_data = {
            '_csrf_token': csrf_token,
            'content': 'Entry from location with special characters in name',
            'weather_data': json.dumps(weather_data),
            'location_data': json.dumps(location_data)
        }
        
        response = client.post('/dashboard', data=form_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Malicious input detected' not in response.data

    def test_malicious_input_still_blocked(self, client, logged_in_user):
        """Ensure that actually malicious input is still blocked."""
        response = client.get('/dashboard')
        csrf_token = self._extract_csrf_token(response.data.decode())
        
        # Actually malicious content should still be blocked
        form_data = {
            '_csrf_token': csrf_token,
            'content': 'Normal content',
            'malicious_field': "'; DROP TABLE users; --",  # SQL injection
            'another_field': '<script>alert("xss")</script>'  # XSS
        }
        
        response = client.post('/dashboard', data=form_data, follow_redirects=True)
        
        # This should still trigger security blocking
        assert response.status_code in [400, 302]  # Either blocked or redirected with error

    def _extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML response."""
        import re
        # Look for CSRF token in meta tag or hidden input
        csrf_pattern = r'name=["\']csrf_token["\'][^>]*content=["\']([^"\']+)["\']'
        match = re.search(csrf_pattern, html_content)
        if match:
            return match.group(1)
        
        # Alternative pattern for hidden input
        csrf_pattern = r'name=["\']_csrf_token["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(csrf_pattern, html_content)
        if match:
            return match.group(1)
        
        # If not found, try to extract from any token field
        token_pattern = r'value=["\']([a-f0-9]{40,})["\']'
        match = re.search(token_pattern, html_content)
        if match:
            return match.group(1)
            
        raise ValueError("Could not extract CSRF token from response")