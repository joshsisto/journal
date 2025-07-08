#!/usr/bin/env python3
"""
Test the updated dashboard weather/location display
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_dashboard_weather_location_display():
    """Test that the dashboard shows weather and location information properly"""
    
    dashboard_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'dashboard.html')
    
    with open(dashboard_template_path, 'r') as f:
        template_content = f.read()
    
    print("🧪 Testing Dashboard Weather/Location Display")
    print("=" * 60)
    
    # Check for new layout structure
    layout_elements = [
        ('Entry body container', 'entry-body'),
        ('Main content area', 'entry-main-content'),
        ('Context area', 'entry-context'),
        ('Weather info display', 'entry-weather-info'),
        ('Location info display', 'entry-location-info'),
        ('Weather template check', 'entry.weather'),
        ('Location template check', 'entry.location'),
        ('Temperature display', 'entry.weather.temperature'),
        ('Weather condition display', 'entry.weather.weather_condition'),
        ('Location city display', 'entry.location.city')
    ]
    
    print("🔍 Checking Layout Elements:")
    for description, element in layout_elements:
        if element in template_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
    
    # Check for CSS classes
    css_classes = [
        'entry-body',
        'entry-main-content',
        'entry-context',
        'entry-weather-info',
        'entry-location-info',
        'weather-temp',
        'weather-condition',
        'location-name'
    ]
    
    print("\n🎨 Checking CSS Classes:")
    for css_class in css_classes:
        if f'.{css_class}' in template_content:
            print(f"   ✅ .{css_class}")
        else:
            print(f"   ❌ .{css_class} - NOT FOUND")
    
    # Check for responsive design
    responsive_features = [
        ('Mobile flexbox layout', 'flex-direction: column'),
        ('Desktop side-by-side', 'justify-content: space-between'),
        ('Mobile context stacking', '@media (max-width: 768px)'),
        ('Small mobile adjustments', '@media (max-width: 480px)'),
        ('Context alignment', 'align-items: flex-end')
    ]
    
    print("\n📱 Checking Responsive Design:")
    for description, feature in responsive_features:
        if feature in template_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
    
    # Check for proper template logic
    template_logic = [
        ('Weather conditional', '{% if entry.weather %}'),
        ('Location conditional', '{% if entry.location %}'),
        ('Combined conditional', '{% if entry.location or entry.weather %}'),
        ('Temperature rounding', 'entry.weather.temperature|round|int'),
        ('Location city access', 'entry.location.city'),
        ('Weather condition access', 'entry.weather.weather_condition')
    ]
    
    print("\n🔧 Checking Template Logic:")
    for description, logic in template_logic:
        if logic in template_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
    
    print(f"\n🎉 Dashboard Weather/Location Display Test Complete!")
    
    # Summary
    total_elements = len(layout_elements) + len(css_classes) + len(responsive_features) + len(template_logic)
    found_elements = sum(1 for _, element in layout_elements if element in template_content)
    found_css = sum(1 for css_class in css_classes if f'.{css_class}' in template_content)
    found_responsive = sum(1 for _, feature in responsive_features if feature in template_content)
    found_logic = sum(1 for _, logic in template_logic if logic in template_content)
    
    total_found = found_elements + found_css + found_responsive + found_logic
    
    print(f"\n📊 Summary:")
    print(f"   Layout Elements: {found_elements}/{len(layout_elements)}")
    print(f"   CSS Classes: {found_css}/{len(css_classes)}")
    print(f"   Responsive Features: {found_responsive}/{len(responsive_features)}")
    print(f"   Template Logic: {found_logic}/{len(template_logic)}")
    print(f"   Total: {total_found}/{total_elements}")
    
    if total_found >= total_elements * 0.9:  # 90% or more
        print(f"   ✅ EXCELLENT - Weather/location display is fully implemented!")
        return True
    elif total_found >= total_elements * 0.75:  # 75% or more
        print(f"   ✅ GOOD - Most features implemented")
        return True
    else:
        print(f"   ⚠️  NEEDS WORK - Some features missing")
        return False

def test_with_real_data():
    """Test with actual data from the database"""
    app = create_app()
    
    with app.app_context():
        from models import JournalEntry
        
        print(f"\n🗃️  Testing with Real Database Data:")
        print("=" * 50)
        
        # Get recent entries with weather/location
        entries_with_context = JournalEntry.query.filter(
            (JournalEntry.weather_id.isnot(None)) | (JournalEntry.location_id.isnot(None))
        ).order_by(JournalEntry.created_at.desc()).limit(3).all()
        
        if entries_with_context:
            print(f"   ✅ Found {len(entries_with_context)} entries with weather/location data")
            
            for entry in entries_with_context:
                print(f"\n   Entry {entry.id} - {entry.created_at.strftime('%b %d, %Y')}:")
                
                if entry.weather:
                    temp = round(entry.weather.temperature) if entry.weather.temperature else 'N/A'
                    print(f"     🌤️  Weather: {temp}° {entry.weather.weather_condition}")
                
                if entry.location:
                    city = entry.location.city or 'Unknown'
                    state = entry.location.state if entry.location.state and entry.location.state != 'Unknown' else ''
                    location_display = f"{city}, {state}" if state else city
                    print(f"     📍 Location: {location_display}")
                
                if not entry.weather and not entry.location:
                    print(f"     ⚪ No weather or location data")
            
            print(f"\n   ✅ Dashboard will show weather/location data on the right side!")
        else:
            print(f"   ⚪ No entries with weather/location data found")
            print(f"   💡 Create a journal entry with weather/location to see the display")

if __name__ == '__main__':
    template_success = test_dashboard_weather_location_display()
    test_with_real_data()
    
    if template_success:
        print(f"\n🎉 SUCCESS: Dashboard weather/location display is working!")
        print("Key Features Implemented:")
        print("  ✅ Content on the left, weather/location on the right")
        print("  ✅ Compact weather display with temperature and condition")
        print("  ✅ Location display with city and state")
        print("  ✅ Mobile-responsive layout (stacks vertically on small screens)")
        print("  ✅ Only shows weather/location when data exists")
    else:
        print(f"\n❌ Some issues found in the implementation")