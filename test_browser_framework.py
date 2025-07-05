#!/usr/bin/env python3
"""
Test browser automation framework - verify it's working and can log in.
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def test_browser_framework():
    """Test that browser automation framework works and can log in."""
    
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
        print("🚀 Starting browser automation test...")
        
        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        print("✅ Browser driver initialized successfully")
        
        # Test 1: Can we reach the login page?
        print("🔍 Testing login page access...")
        driver.get("https://journal.joshsisto.com/login")
        
        # Check if page loads
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print(f"✅ Login page loaded: {driver.title}")
        
        # Test 2: Can we find login form elements?
        print("🔍 Testing login form elements...")
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        print("✅ Login form elements found")
        
        # Test 3: Can we log in with a test account?
        print("🔍 Testing login with automation_test account...")
        
        username_field.clear()
        username_field.send_keys("automation_test")
        
        password_field.clear()
        password_field.send_keys("automation123")
        
        # Use JavaScript to click the button to avoid interception
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Wait for login to complete
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.url_contains("/dashboard"),
                EC.url_contains("/journal"),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success"))
            )
        )
        
        print(f"✅ Login successful! Current URL: {driver.current_url}")
        
        # Test 4: Can we navigate to a protected page?
        print("🔍 Testing protected page access...")
        
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print(f"✅ Protected page loaded: {driver.title}")
        
        # Test 5: Check for any JavaScript errors
        print("🔍 Checking for JavaScript errors...")
        
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if js_errors:
            print(f"⚠️  Found JavaScript errors: {len(js_errors)}")
            for error in js_errors[:3]:  # Show first 3 errors
                print(f"   - {error['message']}")
        else:
            print("✅ No critical JavaScript errors found")
        
        print("\n🎉 Browser framework test completed successfully!")
        print("📊 Test Summary:")
        print("   ✅ Browser driver working")
        print("   ✅ Can load login page")
        print("   ✅ Can find form elements")
        print("   ✅ Can log in with test account")
        print("   ✅ Can access protected pages")
        print("   ✅ JavaScript execution working")
        
        return True
        
    except TimeoutException as e:
        print(f"❌ Timeout error: {e}")
        if driver:
            print(f"Current URL: {driver.current_url}")
            print(f"Page source length: {len(driver.page_source)}")
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
    success = test_browser_framework()
    sys.exit(0 if success else 1)