"""
Weather service for fetching weather data from external APIs.

This service handles:
1. Fetching weather data from OpenWeatherMap API
2. Geocoding locations to coordinates
3. Reverse geocoding coordinates to locations
4. Caching weather data to avoid excessive API calls
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from models import db, Location, WeatherData

logger = logging.getLogger(__name__)

class WeatherService:
    """Service for handling weather data and location services."""
    
    def __init__(self):
        # OpenWeatherMap API configuration
        self.api_key = os.environ.get('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.geo_url = "http://api.openweathermap.org/geo/1.0"
        
        # Cache duration for weather data (30 minutes)
        self.cache_duration = timedelta(minutes=30)
        
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not found. Weather features will use manual input only.")
    
    def get_weather_by_coordinates(self, latitude: float, longitude: float, 
                                 use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get current weather data for given coordinates.
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            use_cache (bool): Whether to use cached data if available
            
        Returns:
            Dict containing weather data or None if unavailable
        """
        if not self.api_key:
            logger.warning("No API key available for weather data")
            return None
        
        # Check cache first if requested
        if use_cache:
            cached_weather = self._get_cached_weather(latitude, longitude)
            if cached_weather:
                return cached_weather.to_dict()
        
        try:
            # Fetch current weather
            weather_url = f"{self.base_url}/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric'  # Celsius
            }
            
            response = requests.get(weather_url, params=params, timeout=10)
            response.raise_for_status()
            weather_data = response.json()
            
            # Parse and save weather data
            parsed_weather = self._parse_weather_response(weather_data)
            weather_record = self._save_weather_data(parsed_weather, latitude, longitude)
            
            return weather_record.to_dict() if weather_record else parsed_weather
            
        except requests.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in weather service: {e}")
            return None
    
    def get_weather_by_location_name(self, location_name: str, 
                                   use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get weather data for a named location.
        
        Args:
            location_name (str): Name of the location
            use_cache (bool): Whether to use cached data
            
        Returns:
            Dict containing weather data or None if unavailable
        """
        # First, geocode the location name to coordinates
        coordinates = self.geocode_location(location_name)
        if not coordinates:
            return None
        
        latitude, longitude = coordinates
        return self.get_weather_by_coordinates(latitude, longitude, use_cache)
    
    def geocode_location(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Convert location name to coordinates using geocoding.
        
        Args:
            location_name (str): Name of the location to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not self.api_key:
            return None
        
        try:
            geocode_url = f"{self.geo_url}/direct"
            params = {
                'q': location_name,
                'limit': 1,
                'appid': self.api_key
            }
            
            response = requests.get(geocode_url, params=params, timeout=10)
            response.raise_for_status()
            geo_data = response.json()
            
            if geo_data:
                location = geo_data[0]
                return (location['lat'], location['lon'])
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error geocoding location '{location_name}': {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, str]]:
        """
        Convert coordinates to location information.
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            
        Returns:
            Dict with location information or None if unavailable
        """
        if not self.api_key:
            return None
        
        try:
            reverse_url = f"{self.geo_url}/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'limit': 1,
                'appid': self.api_key
            }
            
            response = requests.get(reverse_url, params=params, timeout=10)
            response.raise_for_status()
            geo_data = response.json()
            
            if geo_data:
                location = geo_data[0]
                return {
                    'name': location.get('name', ''),
                    'city': location.get('name', ''),
                    'state': location.get('state', ''),
                    'country': location.get('country', ''),
                    'address': f"{location.get('name', '')}, {location.get('state', '')}, {location.get('country', '')}"
                }
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error reverse geocoding coordinates ({latitude}, {longitude}): {e}")
            return None
    
    def create_location_from_coordinates(self, latitude: float, longitude: float, 
                                       name: Optional[str] = None) -> Optional[Location]:
        """
        Create a Location record from coordinates, with optional reverse geocoding.
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            name (str, optional): Custom name for the location
            
        Returns:
            Location object or None if creation failed
        """
        try:
            # Try to get location information via reverse geocoding
            location_info = self.reverse_geocode(latitude, longitude)
            
            location = Location(
                name=name,
                latitude=latitude,
                longitude=longitude,
                location_type='gps'
            )
            
            if location_info:
                location.city = location_info.get('city')
                location.state = location_info.get('state')
                location.country = location_info.get('country')
                location.address = location_info.get('address')
                if not name:
                    location.name = location_info.get('name')
            
            db.session.add(location)
            db.session.commit()
            
            return location
            
        except Exception as e:
            logger.error(f"Error creating location from coordinates: {e}")
            db.session.rollback()
            return None
    
    def create_location_from_name(self, location_name: str) -> Optional[Location]:
        """
        Create a Location record from a location name using geocoding.
        
        Args:
            location_name (str): Name of the location
            
        Returns:
            Location object or None if creation failed
        """
        try:
            coordinates = self.geocode_location(location_name)
            if not coordinates:
                # Create location with just the name (manual entry)
                location = Location(
                    name=location_name,
                    location_type='manual'
                )
                db.session.add(location)
                db.session.commit()
                return location
            
            latitude, longitude = coordinates
            return self.create_location_from_coordinates(latitude, longitude, location_name)
            
        except Exception as e:
            logger.error(f"Error creating location from name '{location_name}': {e}")
            db.session.rollback()
            return None
    
    def _get_cached_weather(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        """Get cached weather data for coordinates if recent enough."""
        cutoff_time = datetime.utcnow() - self.cache_duration
        
        # Find location within a small radius (approximately 1km)
        lat_range = 0.009  # About 1km in latitude degrees
        lon_range = 0.009  # About 1km in longitude degrees
        
        location = Location.query.filter(
            Location.latitude.between(latitude - lat_range, latitude + lat_range),
            Location.longitude.between(longitude - lon_range, longitude + lon_range)
        ).first()
        
        if not location:
            return None
        
        # Find recent weather data for this location
        weather = WeatherData.query.filter(
            WeatherData.location_id == location.id,
            WeatherData.recorded_at > cutoff_time
        ).order_by(WeatherData.recorded_at.desc()).first()
        
        return weather
    
    def _parse_weather_response(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenWeatherMap API response into our format."""
        main = weather_data.get('main', {})
        weather = weather_data.get('weather', [{}])[0]
        wind = weather_data.get('wind', {})
        
        return {
            'temperature': main.get('temp'),
            'temperature_unit': 'celsius',
            'humidity': main.get('humidity'),
            'pressure': main.get('pressure'),
            'weather_condition': weather.get('main'),
            'weather_description': weather.get('description'),
            'wind_speed': wind.get('speed'),
            'wind_direction': wind.get('deg'),
            'visibility': weather_data.get('visibility', 0) / 1000 if weather_data.get('visibility') else None,  # Convert m to km
            'weather_source': 'openweathermap'
        }
    
    def _save_weather_data(self, weather_dict: Dict[str, Any], 
                          latitude: float, longitude: float) -> Optional[WeatherData]:
        """Save weather data to database."""
        try:
            # Find or create location
            location = Location.query.filter(
                Location.latitude == latitude,
                Location.longitude == longitude
            ).first()
            
            if not location:
                location = self.create_location_from_coordinates(latitude, longitude)
            
            if not location:
                return None
            
            # Create weather record
            weather = WeatherData(
                location_id=location.id,
                **weather_dict
            )
            
            db.session.add(weather)
            db.session.commit()
            
            return weather
            
        except Exception as e:
            logger.error(f"Error saving weather data: {e}")
            db.session.rollback()
            return None
    
    def get_user_recent_locations(self, user_id: int, limit: int = 10) -> list:
        """
        Get user's recent locations for quick selection.
        
        Args:
            user_id (int): User ID
            limit (int): Maximum number of locations to return
            
        Returns:
            List of Location objects
        """
        from models import JournalEntry
        
        # Get locations from user's recent entries
        recent_entries = db.session.query(JournalEntry.location_id).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.location_id.isnot(None)
        ).order_by(JournalEntry.created_at.desc()).limit(limit * 2).all()
        
        if not recent_entries:
            return []
        
        location_ids = list(set([entry.location_id for entry in recent_entries if entry.location_id]))
        
        locations = Location.query.filter(
            Location.id.in_(location_ids)
        ).order_by(Location.updated_at.desc()).limit(limit).all()
        
        return locations


# Global weather service instance
weather_service = WeatherService()