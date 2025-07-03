/**
 * Location services for journal entries.
 * Handles GPS location detection, manual location entry, and location management.
 */

class LocationService {
    constructor() {
        this.currentLocation = null;
        this.watchId = null;
        this.isGettingLocation = false;
    }

    /**
     * Get user's current location using GPS
     */
    async getCurrentLocation() {
        if (this.isGettingLocation) {
            return;
        }

        if (!navigator.geolocation) {
            this.showLocationError('Geolocation is not supported by this browser.');
            return;
        }

        this.isGettingLocation = true;
        this.showLocationStatus('Getting your location...', 'info');

        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000 // Cache for 1 minute
        };

        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, options);
            });

            const location = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy
            };

            this.currentLocation = location;
            this.onLocationReceived(location);
            this.showLocationStatus('Location detected successfully!', 'success');

        } catch (error) {
            this.handleLocationError(error);
        } finally {
            this.isGettingLocation = false;
        }
    }

    /**
     * Handle location detection errors
     */
    handleLocationError(error) {
        let message = 'Unable to get your location. ';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message += 'Location access was denied. Please enable location services and refresh the page.';
                break;
            case error.POSITION_UNAVAILABLE:
                message += 'Location information is unavailable.';
                break;
            case error.TIMEOUT:
                message += 'Location request timed out. Please try again.';
                break;
            default:
                message += 'An unknown error occurred.';
                break;
        }

        this.showLocationError(message);
    }

    /**
     * Called when location is successfully received
     */
    onLocationReceived(location) {
        // Update latitude/longitude fields
        const latField = document.getElementById('location_latitude');
        const lonField = document.getElementById('location_longitude');
        
        if (latField && lonField) {
            latField.value = location.latitude.toFixed(6);
            lonField.value = location.longitude.toFixed(6);
        }

        // Update location display
        this.updateLocationDisplay(location);

        // Try to get address information
        this.reverseGeocode(location.latitude, location.longitude);

        // Fetch weather data for this location
        this.fetchWeatherData(location.latitude, location.longitude);
    }

    /**
     * Reverse geocode coordinates to get address
     */
    async reverseGeocode(latitude, longitude) {
        try {
            const response = await fetch('/api/location/reverse-geocode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': window.csrfToken
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                })
            });

            if (response.ok) {
                const locationData = await response.json();
                this.updateLocationFields(locationData);
            }
        } catch (error) {
            console.log('Reverse geocoding failed:', error);
        }
    }

    /**
     * Fetch weather data for location
     */
    async fetchWeatherData(latitude, longitude) {
        try {
            const response = await fetch('/api/weather/current', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': window.csrfToken
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                })
            });

            if (response.ok) {
                const weatherData = await response.json();
                this.updateWeatherDisplay(weatherData);
            }
        } catch (error) {
            console.log('Weather fetch failed:', error);
        }
    }

    /**
     * Update location form fields with geocoded data
     */
    updateLocationFields(locationData) {
        const fields = {
            'location_name': locationData.name,
            'location_city': locationData.city,
            'location_state': locationData.state,
            'location_country': locationData.country,
            'location_address': locationData.address
        };

        Object.entries(fields).forEach(([fieldId, value]) => {
            const field = document.getElementById(fieldId);
            if (field && value) {
                field.value = value;
            }
        });

        // Update the location preview
        this.updateLocationPreview(locationData);
    }

    /**
     * Update weather display with fetched data
     */
    updateWeatherDisplay(weatherData) {
        const weatherContainer = document.getElementById('weather-info');
        if (!weatherContainer) return;

        const weatherHtml = `
            <div class="weather-summary">
                <i class="fas fa-cloud-sun text-primary me-2"></i>
                <span class="weather-temp">${Math.round(weatherData.temperature)}°C</span>
                <span class="weather-condition ms-2">${weatherData.weather_condition}</span>
            </div>
            <div class="weather-details mt-2">
                <small class="text-muted">
                    ${weatherData.humidity}% humidity • ${weatherData.wind_speed} m/s wind
                </small>
            </div>
        `;

        weatherContainer.innerHTML = weatherHtml;
        weatherContainer.style.display = 'block';

        // Store weather data in hidden fields
        this.updateWeatherFields(weatherData);
    }

    /**
     * Update hidden weather form fields
     */
    updateWeatherFields(weatherData) {
        const fields = {
            'weather_temperature': weatherData.temperature,
            'weather_condition': weatherData.weather_condition,
            'weather_description': weatherData.weather_description,
            'weather_humidity': weatherData.humidity,
            'weather_wind_speed': weatherData.wind_speed,
            'weather_pressure': weatherData.pressure
        };

        Object.entries(fields).forEach(([fieldId, value]) => {
            const field = document.getElementById(fieldId);
            if (field && value !== undefined && value !== null) {
                field.value = value;
            }
        });
    }

    /**
     * Update location display/preview
     */
    updateLocationDisplay(location) {
        const locationDisplay = document.getElementById('location-display');
        if (!locationDisplay) return;

        const displayHtml = `
            <div class="location-preview">
                <i class="fas fa-map-marker-alt text-primary me-2"></i>
                <span class="location-coords">
                    ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}
                </span>
                <small class="text-muted ms-2">(±${Math.round(location.accuracy)}m accuracy)</small>
            </div>
        `;

        locationDisplay.innerHTML = displayHtml;
        locationDisplay.style.display = 'block';
    }

    /**
     * Update location preview with address information
     */
    updateLocationPreview(locationData) {
        const locationDisplay = document.getElementById('location-display');
        if (!locationDisplay) return;

        const displayName = locationData.name || 
                           `${locationData.city}, ${locationData.state}` ||
                           'Current Location';

        const displayHtml = `
            <div class="location-preview">
                <i class="fas fa-map-marker-alt text-primary me-2"></i>
                <span class="location-name">${displayName}</span>
                ${locationData.address ? `<small class="text-muted d-block">${locationData.address}</small>` : ''}
            </div>
        `;

        locationDisplay.innerHTML = displayHtml;
    }

    /**
     * Show location status message
     */
    showLocationStatus(message, type = 'info') {
        const statusContainer = document.getElementById('location-status');
        if (!statusContainer) return;

        const alertClass = {
            'info': 'alert-info',
            'success': 'alert-success',
            'error': 'alert-danger'
        }[type] || 'alert-info';

        statusContainer.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Auto-dismiss success messages
        if (type === 'success') {
            setTimeout(() => {
                const alert = statusContainer.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 3000);
        }
    }

    /**
     * Show location error message
     */
    showLocationError(message) {
        this.showLocationStatus(message, 'error');
    }

    /**
     * Clear current location data
     */
    clearLocation() {
        this.currentLocation = null;
        
        // Clear form fields
        const locationFields = [
            'location_latitude', 'location_longitude', 'location_name',
            'location_city', 'location_state', 'location_country', 'location_address'
        ];
        
        locationFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.value = '';
            }
        });

        // Clear display
        const locationDisplay = document.getElementById('location-display');
        if (locationDisplay) {
            locationDisplay.style.display = 'none';
        }

        // Clear weather
        const weatherContainer = document.getElementById('weather-info');
        if (weatherContainer) {
            weatherContainer.style.display = 'none';
        }

        this.showLocationStatus('Location cleared', 'info');
    }

    /**
     * Search for a location by name
     */
    async searchLocation(locationName) {
        console.log('Location search called with:', locationName);
        
        if (!locationName.trim()) {
            this.showLocationError('Please enter a location name');
            return;
        }

        this.showLocationStatus('Searching for location...', 'info');
        console.log('Making API request to /api/location/search');

        try {
            const response = await fetch('/api/location/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': window.csrfToken
                },
                body: JSON.stringify({
                    location_name: locationName
                })
            });

            console.log('API response status:', response.status);
            console.log('API response headers:', response.headers);

            if (response.ok) {
                const locationData = await response.json();
                console.log('Location data received:', locationData);
                
                if (locationData.latitude && locationData.longitude) {
                    const location = {
                        latitude: locationData.latitude,
                        longitude: locationData.longitude,
                        accuracy: 1000 // Estimated accuracy for searched locations
                    };

                    this.currentLocation = location;
                    this.onLocationReceived(location);
                    this.updateLocationFields(locationData);
                    this.showLocationStatus('Location found successfully!', 'success');
                } else {
                    this.showLocationError('Location not found. Please try a different search term.');
                }
            } else {
                const errorData = await response.text();
                console.error('API error response:', errorData);
                this.showLocationError(`Failed to search for location: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            console.error('Location search error:', error);
            this.showLocationError('Error searching for location. Please check your connection.');
        }
    }
}

// Initialize location service when page loads
let locationService;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing LocationService...');
    locationService = new LocationService();
    console.log('LocationService initialized:', !!locationService);

    // Get current location button
    const getCurrentLocationBtn = document.getElementById('get-current-location');
    if (getCurrentLocationBtn) {
        getCurrentLocationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            locationService.getCurrentLocation();
        });
    }

    // Clear location button
    const clearLocationBtn = document.getElementById('clear-location');
    if (clearLocationBtn) {
        clearLocationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            locationService.clearLocation();
        });
    }

    // Location search button
    const searchLocationBtn = document.getElementById('location-search-btn');
    const locationInput = document.getElementById('location-search-input');
    
    console.log('Location search elements found:', {
        button: !!searchLocationBtn,
        input: !!locationInput
    });
    
    if (searchLocationBtn && locationInput) {
        console.log('Setting up location search event handlers');
        
        // Handle search button click
        searchLocationBtn.addEventListener('click', function(e) {
            console.log('Location search button clicked');
            e.preventDefault();
            e.stopPropagation();
            locationService.searchLocation(locationInput.value);
        });
        
        // Handle Enter key in search input
        locationInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                console.log('Enter key pressed in location search input');
                e.preventDefault();
                e.stopPropagation();
                locationService.searchLocation(locationInput.value);
            }
        });
    } else {
        console.error('Location search elements not found!');
    }

    // Toggle advanced location options
    const toggleAdvancedBtn = document.getElementById('toggle-advanced-location');
    if (toggleAdvancedBtn) {
        toggleAdvancedBtn.addEventListener('click', function() {
            const coordsSection = document.getElementById('coordinates-section');
            
            if (coordsSection.style.display === 'none') {
                coordsSection.style.display = '';
                toggleAdvancedBtn.innerHTML = '<i class="fas fa-cog me-1"></i>Hide Advanced Options';
            } else {
                coordsSection.style.display = 'none';
                toggleAdvancedBtn.innerHTML = '<i class="fas fa-cog me-1"></i>Show Advanced Options';
            }
        });
    }

    // Debug test button
    const testBtn = document.getElementById('test-location-search');
    if (testBtn) {
        testBtn.style.display = 'block'; // Show debug button
        testBtn.addEventListener('click', function() {
            console.log('Test button clicked - testing location search');
            console.log('CSRF Token available:', !!window.csrfToken);
            console.log('LocationService available:', !!locationService);
            
            // Test with a simple location
            if (locationService) {
                locationService.searchLocation('New York');
            } else {
                console.error('LocationService not available!');
            }
        });
    }

    // Recent locations selection
    const recentLocationSelect = document.getElementById('recent-locations');
    if (recentLocationSelect) {
        recentLocationSelect.addEventListener('change', function(e) {
            if (e.target.value) {
                // Load selected recent location
                loadRecentLocation(e.target.value);
            }
        });
    }
});

/**
 * Load a recent location by ID
 */
async function loadRecentLocation(locationId) {
    try {
        const response = await fetch(`/api/location/${locationId}`, {
            headers: {
                'X-CSRF-Token': window.csrfToken
            }
        });

        if (response.ok) {
            const locationData = await response.json();
            
            // Update form fields
            locationService.updateLocationFields(locationData);
            
            // Update display
            if (locationData.latitude && locationData.longitude) {
                const location = {
                    latitude: locationData.latitude,
                    longitude: locationData.longitude,
                    accuracy: 1000
                };
                
                locationService.updateLocationDisplay(location);
                locationService.fetchWeatherData(locationData.latitude, locationData.longitude);
            }
            
            locationService.showLocationStatus('Location loaded successfully', 'success');
        }
    } catch (error) {
        locationService.showLocationError('Failed to load location');
    }
}