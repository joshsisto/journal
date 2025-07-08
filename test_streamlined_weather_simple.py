#!/usr/bin/env python3
"""
Simple test to validate the streamlined weather UI exists in the template
"""

import os

def test_streamlined_weather_ui_in_template():
    """Test that the streamlined weather UI elements are present in the dashboard template"""
    
    dashboard_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'dashboard.html')
    
    with open(dashboard_template_path, 'r') as f:
        template_content = f.read()
    
    print("🧪 Testing Streamlined Weather UI Elements")
    print("=" * 60)
    
    # Check for new UI elements
    ui_elements = [
        ('Auto-detect button', 'autoDetectBtn'),
        ('Clear button', 'clearWeatherBtn'),
        ('Search button', 'searchLocationBtn'),
        ('Weather section title', '📍 Weather & Location'),
        ('Auto button text', '🎯 Auto'),
        ('Clear button text', '🗑️ Clear'),
        ('Search button text', '🔍 Search'),
        ('Location search container', 'location-search-container'),
        ('Weather actions container', 'weather-actions'),
        ('Weather header container', 'weather-header')
    ]
    
    print("🔍 Checking UI Elements:")
    for description, element in ui_elements:
        if element in template_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
    
    # Check for JavaScript functions
    js_functions = [
        'autoDetectLocation',
        'clearWeatherData',
        'searchLocation',
        'showWeatherData',
        'showWeatherLoading',
        'showWeatherError',
        'updateFormFields',
        'fetchWeatherForLocation'
    ]
    
    print("\n🔧 Checking JavaScript Functions:")
    for func in js_functions:
        if f'function {func}(' in template_content:
            print(f"   ✅ {func}()")
        else:
            print(f"   ❌ {func}() - NOT FOUND")
    
    # Check for CSS classes
    css_classes = [
        'weather-btn',
        'clear-btn',
        'search-btn',
        'weather-loading',
        'weather-info',
        'weather-temp',
        'weather-condition',
        'location-info'
    ]
    
    print("\n🎨 Checking CSS Classes:")
    for css_class in css_classes:
        if f'.{css_class}' in template_content:
            print(f"   ✅ .{css_class}")
        else:
            print(f"   ❌ .{css_class} - NOT FOUND")
    
    # Check for key functionality
    features = [
        ('Auto-detect on weather toggle open', 'autoDetectLocation();'),
        ('Enter key search support', 'if (e.key === \'Enter\')'),
        ('Clear functionality', 'clearWeatherData()'),
        ('Loading states', 'weather-loading'),
        ('Error handling', 'showWeatherError'),
        ('Form field updates', 'updateFormFields()')
    ]
    
    print("\n⚡ Checking Key Features:")
    for description, feature in features:
        if feature in template_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
    
    print(f"\n🎉 Streamlined Weather UI Template Validation Complete!")
    
    # Summary
    total_elements = len(ui_elements) + len(js_functions) + len(css_classes) + len(features)
    found_elements = sum(1 for _, element in ui_elements if element in template_content)
    found_js = sum(1 for func in js_functions if f'function {func}(' in template_content)
    found_css = sum(1 for css_class in css_classes if f'.{css_class}' in template_content)
    found_features = sum(1 for _, feature in features if feature in template_content)
    
    total_found = found_elements + found_js + found_css + found_features
    
    print(f"\n📊 Summary:")
    print(f"   UI Elements: {found_elements}/{len(ui_elements)}")
    print(f"   JS Functions: {found_js}/{len(js_functions)}")
    print(f"   CSS Classes: {found_css}/{len(css_classes)}")
    print(f"   Features: {found_features}/{len(features)}")
    print(f"   Total: {total_found}/{total_elements}")
    
    if total_found >= total_elements * 0.9:  # 90% or more
        print(f"   ✅ EXCELLENT - Streamlined UI is fully implemented!")
    elif total_found >= total_elements * 0.75:  # 75% or more
        print(f"   ✅ GOOD - Most features implemented")
    else:
        print(f"   ⚠️  NEEDS WORK - Some features missing")

if __name__ == '__main__':
    test_streamlined_weather_ui_in_template()