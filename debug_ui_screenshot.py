#!/usr/bin/env python3
"""
Debug UI by taking screenshots and examining elements.
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def debug_ui():
    """Take screenshots and debug UI elements."""
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    driver = None
    try:
        print("🔍 Debugging UI elements...")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        # Login
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
        
        # Go to quick journal
        driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Take screenshot
        driver.save_screenshot("quick_journal_debug.png")
        print("✅ Screenshot saved: quick_journal_debug.png")
        
        # Check search button
        try:
            search_button = driver.find_element(By.ID, "search-location-btn")
            print(f"Search button found. Text: '{search_button.text}'")
            print(f"Search button HTML: {search_button.get_attribute('outerHTML')}")
        except Exception as e:
            print(f"Search button not found: {e}")
        
        # Check location weather section
        try:
            location_weather = driver.find_elements(By.CSS_SELECTOR, "[data-bs-target='#location-weather-collapse']")
            print(f"Location/weather toggles found: {len(location_weather)}")
            for i, element in enumerate(location_weather):
                print(f"  Toggle {i}: {element.get_attribute('outerHTML')[:100]}...")
        except Exception as e:
            print(f"Location/weather check failed: {e}")
        
        # Check page source for location component
        page_source = driver.page_source
        if "location-weather-collapse" in page_source:
            print("✅ Location-weather-collapse found in page source")
        else:
            print("❌ Location-weather-collapse NOT found in page source")
        
        if "search-location-btn" in page_source:
            print("✅ search-location-btn found in page source")
        else:
            print("❌ search-location-btn NOT found in page source")
        
        # Check guided journal too
        driver.get("https://journal.joshsisto.com/journal/guided")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        driver.save_screenshot("guided_journal_debug.png")
        print("✅ Screenshot saved: guided_journal_debug.png")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    debug_ui()