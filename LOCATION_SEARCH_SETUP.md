# Location Search Setup Guide

## Issue Description

The location search functionality might not work if the OpenWeatherMap API key is not properly configured. When users try to search for locations, they may get form submission errors or no response.

## Root Cause Analysis

1. **Missing API Key**: The `OPENWEATHER_API_KEY` is not set in the `.env` file
2. **Form Submission Conflict**: Location search button might trigger journal form submission instead of search
3. **JavaScript Errors**: Console errors preventing proper API calls

## Solution Steps

### Step 1: Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap API](https://openweathermap.org/api)
2. Sign up for a free account
3. Navigate to API Keys section
4. Copy your API key

### Step 2: Configure the API Key in .env File

**Configuration Method: Edit .env file**

1. Edit the `.env` file in the project root:
```bash
nano .env
```

2. Add or update the OpenWeatherMap API key:
```bash
# Weather API
OPENWEATHER_API_KEY=your_api_key_here
```

3. Restart the journal service:
```bash
sudo systemctl restart journal-app.service
```

**Note**: All sensitive configuration (API keys, database passwords, etc.) is stored in the `.env` file, not as system environment variables.

### Step 3: Verify Configuration

1. Test the API configuration:
```bash
python3 test_weather_api.py
```

2. Check service status:
```bash
sudo systemctl status journal-app.service
```

3. Monitor logs:
```bash
sudo journalctl -u journal-app.service -f
```

## Testing the Fix

1. **Open your journal app** in a browser
2. **Create a new journal entry**
3. **Try searching for a location** in the location search field
4. **Verify the search works** and populates location data

## Technical Details

### API Endpoints Used
- **Location Search**: `/api/location/search` - Geocodes location names to coordinates
- **Weather Data**: `/api/weather/current` - Fetches current weather for coordinates
- **Reverse Geocoding**: `/api/location/reverse-geocode` - Converts coordinates to addresses

### JavaScript Integration
- **Location Service**: `static/js/location.js` handles frontend location functionality
- **API Calls**: Uses fetch() with CSRF tokens for authenticated requests
- **Error Handling**: Provides user feedback for failed searches

### Security Considerations
- API key is stored as environment variable (not in code)
- All API endpoints require user authentication
- Rate limiting prevents API abuse
- Input validation prevents malicious requests

## Troubleshooting

### Common Issues

1. **"Nothing happens when searching"**
   - Check API key configuration
   - Verify service has restarted
   - Check browser console for errors

2. **"API key invalid" error**
   - Verify API key is correct
   - Check OpenWeatherMap account status
   - Ensure API key has geocoding permissions

3. **"Location not found" responses**
   - Try different search terms
   - Check if location exists in OpenWeatherMap database
   - Verify network connectivity

### Debug Commands

```bash
# Check environment variables
sudo systemctl show journal-app.service | grep Environment

# Test API connectivity
curl "http://api.openweathermap.org/data/2.5/weather?lat=40.7128&lon=-74.0060&appid=YOUR_API_KEY"

# Monitor service logs
sudo journalctl -u journal-app.service --since "5 minutes ago"
```

## API Usage and Limits

- **Free Tier**: 1,000 calls/day, 60 calls/minute
- **Required APIs**: Current Weather Data API, Geocoding API
- **Rate Limiting**: Built-in rate limiting prevents quota exhaustion
- **Caching**: Weather data is cached for 30 minutes to reduce API calls

## Backup Location Entry

If location search is not working, users can still:
1. **Use GPS location** via "Use Current Location" button
2. **Manually enter location data** in the form fields
3. **Select from recent locations** if available

This ensures journal entry creation isn't blocked by location search issues.

## Monitoring and Maintenance

- **Monitor API usage** in OpenWeatherMap dashboard
- **Check service logs** regularly for API errors
- **Update API key** before expiration
- **Monitor rate limits** and upgrade plan if needed

## Testing Location Search

### Automated Testing
```bash
# Run location search specific tests
python3 run_tests.py location

# Run comprehensive tests including location functionality  
python3 run_comprehensive_tests.py
```

### Manual Testing
1. **Basic Functionality**:
   - Navigate to Quick Journal or Guided Journal
   - Enter a location name (e.g., "New York, NY")  
   - Click Search button or press Enter
   - Verify location data and weather information appear

2. **GPS Location**:
   - Click "Use Current Location" button
   - Allow location permissions
   - Verify coordinates and weather data are populated

3. **Error Handling**:
   - Test with invalid location names
   - Test without internet connection
   - Verify appropriate error messages are shown

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use .env files** for sensitive configuration
3. **Implement rate limiting** to prevent abuse
4. **Validate all input** before API calls
5. **Handle errors gracefully** with user feedback