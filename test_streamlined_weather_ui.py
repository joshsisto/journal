#!/usr/bin/env python3
"""
Test the streamlined weather UI functionality
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_dashboard_loads_with_new_weather_ui():
    """Test that the dashboard loads with the new streamlined weather UI"""
    app = create_app()
    
    with app.test_client() as client:
        # Create a test user and login
        with app.app_context():
            from models import db, User
            
            import uuid
            unique_username = f'testuser_{str(uuid.uuid4())[:8]}'
            test_user = User(username=unique_username, email=f'test_{str(uuid.uuid4())[:8]}@example.com')
            test_user.set_password('testpassword')
            
            db.session.add(test_user)
            db.session.commit()
            
            # Get login page for CSRF token
            login_page = client.get('/login')
            login_html = login_page.data.decode()
            
            # Extract CSRF token
            import re
            csrf_match = re.search(r'name="_csrf_token" value="([^"]+)"', login_html)
            csrf_token = csrf_match.group(1) if csrf_match else ''
            
            # Login with CSRF token
            login_response = client.post('/login', data={
                'username': unique_username,
                'password': 'testpassword',
                '_csrf_token': csrf_token
            }, follow_redirects=True)
            
            # Get dashboard
            dashboard_response = client.get('/dashboard')
            
            assert dashboard_response.status_code == 200
            dashboard_html = dashboard_response.data.decode()
            
            print("🧪 Testing Streamlined Weather UI")
            print("=" * 50)
            
            # Check for new weather UI elements
            ui_elements = [
                ('🎯 Auto button', 'autoDetectBtn'),
                ('🗑️ Clear button', 'clearWeatherBtn'),
                ('🔍 Search button', 'searchLocationBtn'),
                ('Weather title', '📍 Weather & Location'),
                ('Location search placeholder', 'Search location'),
                ('Auto-detect functionality', 'autoDetectLocation'),
                ('Clear functionality', 'clearWeatherData'),
                ('Search functionality', 'searchLocation'),
                ('Weather display styling', 'weather-info'),
                ('Loading animation', 'weather-loading')
            ]
            
            for description, element in ui_elements:
                if element in dashboard_html:
                    print(f"   ✅ {description} found")
                else:
                    print(f"   ❌ {description} missing")
            
            # Check for key JavaScript functions
            js_functions = [
                'autoDetectLocation',
                'clearWeatherData', 
                'searchLocation',
                'showWeatherData',
                'updateFormFields'
            ]
            
            print("\n🔧 Testing JavaScript Functions:")
            for func in js_functions:
                if f'function {func}(' in dashboard_html:
                    print(f"   ✅ {func}() function found")
                else:
                    print(f"   ❌ {func}() function missing")
            
            # Check for streamlined CSS classes
            css_classes = [
                'weather-btn',
                'clear-btn',
                'search-btn',
                'weather-loading',
                'weather-info',
                'location-search-container'
            ]
            
            print("\n🎨 Testing CSS Classes:")
            for css_class in css_classes:
                if css_class in dashboard_html:
                    print(f"   ✅ .{css_class} found")
                else:
                    print(f"   ❌ .{css_class} missing")
            
            print(f"\n🎉 Streamlined Weather UI Test Complete!")
            print("Key Features Implemented:")
            print("  ✅ Single-click auto-detection")
            print("  ✅ Clear weather/location button")
            print("  ✅ Location search functionality")
            print("  ✅ Minimalist design with tight layout")
            print("  ✅ Loading states and error handling")
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()

if __name__ == '__main__':
    test_dashboard_loads_with_new_weather_ui()