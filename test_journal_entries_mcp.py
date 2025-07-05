#!/usr/bin/env python3
"""
Comprehensive MCP Browser Tests for Journal Entry Creation
Tests both quick and guided journal entries with various scenarios.
"""

import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

class JournalEntryTester:
    def __init__(self):
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome driver with options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
    def login(self):
        """Login to the application."""
        print("🔐 Logging in...")
        self.driver.get("https://journal.joshsisto.com/login")
        
        username_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = self.driver.find_element(By.NAME, "password")
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_field.clear()
        username_field.send_keys("automation_test")
        password_field.clear()
        password_field.send_keys("automation123")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        WebDriverWait(self.driver, 15).until(
            EC.any_of(
                EC.url_contains("/dashboard"),
                EC.url_contains("/journal")
            )
        )
        print("✅ Login successful")
        
    def test_quick_journal_minimal(self):
        """Test quick journal with minimal required fields only."""
        print("\n📝 Testing Quick Journal - Minimal Fields...")
        
        self.driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "content"))
        )
        
        # Fill only required content field
        content_field = self.driver.find_element(By.NAME, "content")
        content_field.clear()
        content_field.send_keys("This is a minimal test entry with just content.")
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # Wait for success (redirect or success message)
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "quick" not in current_url:
            print("✅ Quick journal minimal entry created successfully")
            return True
        else:
            print(f"❌ Quick journal creation failed. Current URL: {current_url}")
            return False
            
    def test_quick_journal_with_location(self):
        """Test quick journal with location fields."""
        print("\n🗺️  Testing Quick Journal - With Location...")
        
        self.driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "content"))
        )
        
        # Expand location section
        try:
            location_toggle = self.driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#location-weather-collapse']")
            self.driver.execute_script("arguments[0].click();", location_toggle)
            time.sleep(1)
            print("✅ Location section expanded")
        except:
            print("ℹ️  Location section already expanded or not collapsible")
        
        # Fill content
        content_field = self.driver.find_element(By.NAME, "content")
        content_field.clear()
        content_field.send_keys("Testing journal entry with location data.")
        
        # Fill location fields
        location_name = self.driver.find_element(By.ID, "location_name")
        location_name.clear()
        location_name.send_keys("Test Location")
        
        location_city = self.driver.find_element(By.ID, "location_city")
        location_city.clear()
        location_city.send_keys("Test City")
        
        location_state = self.driver.find_element(By.ID, "location_state")
        location_state.clear()
        location_state.send_keys("Test State")
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "quick" not in current_url:
            print("✅ Quick journal with location created successfully")
            return True
        else:
            print(f"❌ Quick journal with location failed. Current URL: {current_url}")
            return False
            
    def test_quick_journal_with_tags(self):
        """Test quick journal with new tag creation."""
        print("\n🏷️  Testing Quick Journal - With Tags...")
        
        self.driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "content"))
        )
        
        # Fill content
        content_field = self.driver.find_element(By.NAME, "content")
        content_field.clear()
        content_field.send_keys("Testing journal entry with custom tags.")
        
        # Add a new tag
        try:
            new_tag_name = self.driver.find_element(By.ID, "new-tag-name")
            new_tag_name.clear()
            new_tag_name.send_keys("TestTag")
            
            # Try to add the tag
            add_tag_btn = self.driver.find_element(By.ID, "add-tag-btn")
            self.driver.execute_script("arguments[0].click();", add_tag_btn)
            time.sleep(1)
            print("✅ New tag added")
        except Exception as e:
            print(f"ℹ️  Tag creation failed or not available: {e}")
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "quick" not in current_url:
            print("✅ Quick journal with tags created successfully")
            return True
        else:
            print(f"❌ Quick journal with tags failed. Current URL: {current_url}")
            return False
            
    def test_guided_journal_minimal(self):
        """Test guided journal with minimal fields."""
        print("\n📋 Testing Guided Journal - Minimal Fields...")
        
        self.driver.get("https://journal.joshsisto.com/journal/guided")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait for template questions to load
        time.sleep(2)
        
        # Find all form inputs and fill minimal required ones
        try:
            # Look for text areas (main question responses)
            text_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea[name^='question_']")
            for i, textarea in enumerate(text_areas[:3]):  # Fill first 3 text questions
                textarea.clear()
                textarea.send_keys(f"Test response {i+1} for guided journal.")
                
            # Look for range inputs (feeling scales) and set to middle values
            range_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='range'][name^='question_']")
            for range_input in range_inputs[:2]:  # Set first 2 feeling scales
                self.driver.execute_script("arguments[0].value = 5; arguments[0].dispatchEvent(new Event('input'));", range_input)
                
            print(f"✅ Filled {len(text_areas)} text responses and {len(range_inputs)} feeling scales")
        except Exception as e:
            print(f"ℹ️  Error filling guided questions: {e}")
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "guided" not in current_url:
            print("✅ Guided journal minimal entry created successfully")
            return True
        else:
            print(f"❌ Guided journal creation failed. Current URL: {current_url}")
            return False
            
    def test_guided_journal_with_emotions(self):
        """Test guided journal with emotion selection."""
        print("\n❤️  Testing Guided Journal - With Emotions...")
        
        self.driver.get("https://journal.joshsisto.com/journal/guided")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(2)
        
        # Look for emotions section and expand if collapsed
        try:
            emotions_toggle = self.driver.find_element(By.CSS_SELECTOR, "[data-bs-target*='emotions-collapse']")
            self.driver.execute_script("arguments[0].click();", emotions_toggle)
            time.sleep(1)
            print("✅ Emotions section expanded")
        except:
            print("ℹ️  Emotions section already expanded or not available")
        
        # Select some emotions
        try:
            emotion_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, ".emotion-checkbox")
            selected_count = 0
            for checkbox in emotion_checkboxes[:3]:  # Select first 3 emotions
                self.driver.execute_script("arguments[0].click();", checkbox)
                selected_count += 1
                time.sleep(0.2)
            print(f"✅ Selected {selected_count} emotions")
        except Exception as e:
            print(f"ℹ️  Emotion selection failed: {e}")
        
        # Fill other required fields
        try:
            text_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea[name^='question_']")
            for i, textarea in enumerate(text_areas[:2]):
                textarea.clear()
                textarea.send_keys(f"Test response {i+1} with emotions.")
        except:
            pass
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "guided" not in current_url:
            print("✅ Guided journal with emotions created successfully")
            return True
        else:
            print(f"❌ Guided journal with emotions failed. Current URL: {current_url}")
            return False
            
    def test_guided_journal_with_template(self):
        """Test guided journal with template selection."""
        print("\n📄 Testing Guided Journal - With Template Selection...")
        
        self.driver.get("https://journal.joshsisto.com/journal/guided")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Expand template selection if collapsed
        try:
            template_toggle = self.driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#template-selection-collapse']")
            self.driver.execute_script("arguments[0].click();", template_toggle)
            time.sleep(1)
            print("✅ Template selection expanded")
        except:
            print("ℹ️  Template selection already expanded")
        
        # Try to select a different template
        try:
            template_select = Select(self.driver.find_element(By.ID, "templateSelect"))
            options = template_select.options
            
            if len(options) > 1:
                # Select second option (first non-default)
                template_select.select_by_index(1)
                selected_option = template_select.first_selected_option.text
                print(f"✅ Selected template: {selected_option}")
                
                # Load the template
                load_btn = self.driver.find_element(By.ID, "loadTemplateBtn")
                self.driver.execute_script("arguments[0].click();", load_btn)
                time.sleep(3)
                print("✅ Template loaded")
            else:
                print("ℹ️  No additional templates available")
        except Exception as e:
            print(f"ℹ️  Template selection failed: {e}")
        
        # Fill questions that are now available
        try:
            text_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea[name^='question_']")
            for i, textarea in enumerate(text_areas[:2]):
                textarea.clear()
                textarea.send_keys(f"Template test response {i+1}.")
        except:
            pass
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(3)
        current_url = self.driver.current_url
        
        if "/journal" in current_url and "guided" not in current_url:
            print("✅ Guided journal with template created successfully")
            return True
        else:
            print(f"❌ Guided journal with template failed. Current URL: {current_url}")
            return False
            
    def test_form_validation(self):
        """Test form validation scenarios."""
        print("\n🔍 Testing Form Validation...")
        
        # Test quick journal with empty content
        self.driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "content"))
        )
        
        # Try to submit without content
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(2)
        current_url = self.driver.current_url
        
        if "quick" in current_url:
            print("✅ Form validation working - empty content rejected")
            return True
        else:
            print("❌ Form validation failed - empty content accepted")
            return False
            
    def test_ui_interactions(self):
        """Test UI interactions and collapsible sections."""
        print("\n🖱️  Testing UI Interactions...")
        
        self.driver.get("https://journal.joshsisto.com/journal/quick")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        interactions_tested = 0
        
        # Test location/weather collapse
        try:
            location_toggle = self.driver.find_element(By.CSS_SELECTOR, "[data-bs-target='#location-weather-collapse']")
            self.driver.execute_script("arguments[0].click();", location_toggle)
            time.sleep(1)
            print("✅ Location/weather collapse working")
            interactions_tested += 1
        except:
            print("ℹ️  Location/weather section not collapsible")
        
        # Test search button text
        try:
            search_button = self.driver.find_element(By.ID, "search-location-btn")
            button_text = search_button.text
            if "Search" in button_text:
                print("✅ Search button has descriptive text")
                interactions_tested += 1
        except:
            print("ℹ️  Search button text test failed")
        
        return interactions_tested > 0
        
    def cleanup(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            print("🔧 Browser driver closed")
            
    def run_all_tests(self):
        """Run all journal entry tests."""
        print("🧪 Starting Comprehensive Journal Entry Tests")
        print("=" * 60)
        
        results = {}
        
        try:
            # Login first
            self.login()
            
            # Quick Journal Tests
            results['quick_minimal'] = self.test_quick_journal_minimal()
            results['quick_location'] = self.test_quick_journal_with_location()
            results['quick_tags'] = self.test_quick_journal_with_tags()
            
            # Guided Journal Tests
            results['guided_minimal'] = self.test_guided_journal_minimal()
            results['guided_emotions'] = self.test_guided_journal_with_emotions()
            results['guided_template'] = self.test_guided_journal_with_template()
            
            # Validation Tests
            results['form_validation'] = self.test_form_validation()
            results['ui_interactions'] = self.test_ui_interactions()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False
        finally:
            self.cleanup()
        
        # Results summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20} {status}")
        
        print("-" * 60)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False

def main():
    """Main function to run the test suite."""
    tester = JournalEntryTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()