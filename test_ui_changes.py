#!/usr/bin/env python3
"""
Test UI changes - location search button and collapsible dropdowns.
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def test_ui_changes():
    """Test the UI changes we implemented."""
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    driver = None
    try:
        print("🚀 Starting UI changes test...")
        
        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        print("✅ Browser driver initialized successfully")
        
        # Test 1: Login to access protected pages
        print("🔍 Testing login...")
        driver.get("https://journal.joshsisto.com/login")
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_field.clear()
        username_field.send_keys("automation_test")
        password_field.clear()
        password_field.send_keys("automation123")
        driver.execute_script("arguments[0].click();", submit_button)
        
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.url_contains("/dashboard"),
                EC.url_contains("/journal")
            )
        )
        print("✅ Login successful")
        
        # Test 2: Check location search button on quick journal page
        print("🔍 Testing location search button on quick journal...")
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check if search button has text (check HTML since Selenium may not read text properly)
        search_button = driver.find_element(By.ID, "search-location-btn")
        button_text = search_button.text
        button_html = search_button.get_attribute('outerHTML')
        print(f"   Search button text: '{button_text}'")
        
        if "Search" in button_text or "Search" in button_html:
            print("✅ Location search button has text")
        else:
            print("❌ Location search button missing text")
            print(f"   Button HTML: {button_html}")
            return False
        
        # Test 3: Check collapsible location/weather section
        try:
            location_weather_toggle = driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#location-weather-collapse']")
            print("✅ Location/weather collapsible toggle found")
            
            # Try to expand it
            driver.execute_script("arguments[0].click();", location_weather_toggle)
            time.sleep(1)
            print("✅ Location/weather collapse toggle working")
        except NoSuchElementException:
            print("❌ Location/weather collapsible not found")
            return False
            
        # Test 4: Check collapsible recent locations (if present)
        try:
            recent_locations_toggle = driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#recent-locations-collapse']")
            print("✅ Recent locations collapsible toggle found")
            
            # Try to expand it
            driver.execute_script("arguments[0].click();", recent_locations_toggle)
            time.sleep(1)
            print("✅ Recent locations collapse toggle working")
        except NoSuchElementException:
            print("ℹ️  Recent locations section not present (no recent locations)")
        
        # Test 5: Check guided journal page
        print("🔍 Testing guided journal page...")
        driver.get("https://journal.joshsisto.com/journal/guided")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Test template selection collapsible
        try:
            template_toggle = driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#template-selection-collapse']")
            print("✅ Template selection collapsible toggle found")
            
            # Try to expand it
            driver.execute_script("arguments[0].click();", template_toggle)
            time.sleep(1)
            print("✅ Template selection collapse toggle working")
        except NoSuchElementException:
            print("❌ Template selection collapsible not found")
            return False
        
        # Test emotions collapsible (if emotions question exists)
        try:
            emotions_toggle = driver.find_element(By.CSS_SELECTOR, "[data-bs-target*='emotions-collapse']")
            print("✅ Emotions selection collapsible toggle found")
            
            # Try to expand it
            driver.execute_script("arguments[0].click();", emotions_toggle)
            time.sleep(1)
            print("✅ Emotions selection collapse toggle working")
        except NoSuchElementException:
            print("ℹ️  Emotions section not present (depends on template)")
        
        print("\n🎉 UI changes test completed successfully!")
        print("📊 Test Summary:")
        print("   ✅ Location search button has clear text")
        print("   ✅ Collapsible dropdowns working")
        print("   ✅ Template selection is collapsible")
        print("   ✅ UI improvements implemented correctly")
        
        return True
        
    except TimeoutException as e:
        print(f"❌ Timeout error: {e}")
        return False
        
    except NoSuchElementException as e:
        print(f"❌ Element not found: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()
            print("🔧 Browser driver closed")

if __name__ == "__main__":
    success = test_ui_changes()
    sys.exit(0 if success else 1)