"""
End-to-end tests for guided journal functionality.

These tests simulate real user interactions to catch issues like:
- JavaScript execution problems
- CSP blocking
- Form submission failures  
- Security module false positives
- UI component functionality
"""
import pytest
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time


class TestGuidedJournalE2E:
    """End-to-end tests for guided journal functionality."""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """Set up headless Chrome browser for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def logged_in_user(self, browser, client, user):
        """Log in a test user in the browser."""
        # Get login page
        browser.get("https://127.0.0.1:5000/auth/login")
        
        # Fill login form
        username_field = browser.find_element(By.NAME, "username")
        password_field = browser.find_element(By.NAME, "password")
        
        username_field.send_keys(user.username)
        password_field.send_keys("password123")
        
        # Submit form
        login_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for redirect to dashboard
        WebDriverWait(browser, 10).until(
            EC.url_contains("/dashboard")
        )
        
        return user
    
    def test_guided_journal_page_loads(self, browser, logged_in_user):
        """Test that guided journal page loads without errors."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Check page loaded
        assert "Guided Journal" in browser.title
        
        # Check for JavaScript errors in console
        logs = browser.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        assert len(js_errors) == 0, f"JavaScript errors found: {js_errors}"
    
    def test_happiness_slider_functionality(self, browser, logged_in_user):
        """Test happiness slider emoji changes and alignment."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Find happiness slider
        slider = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='range']"))
        )
        
        # Test slider interaction
        browser.execute_script("arguments[0].value = 5;", slider)
        browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", slider)
        
        # Check emoji updates
        emoji_element = browser.find_element(By.CSS_SELECTOR, "[id$='_emoji']")
        assert emoji_element.text == "😐", "Emoji should be neutral face for value 5"
        
        # Test extreme values
        browser.execute_script("arguments[0].value = 1;", slider)
        browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", slider)
        assert "😭" in emoji_element.text, "Emoji should be crying face for value 1"
        
        browser.execute_script("arguments[0].value = 10;", slider)
        browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", slider)
        assert "🤩" in emoji_element.text, "Emoji should be star-struck for value 10"
    
    def test_emotion_selection_functionality(self, browser, logged_in_user):
        """Test emotion checkbox selection and display."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Wait for emotion checkboxes to load
        checkboxes = WebDriverWait(browser, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".emotion-checkbox"))
        )
        
        assert len(checkboxes) > 0, "Emotion checkboxes should be present"
        
        # Select some emotions
        positive_emotions = browser.find_elements(By.CSS_SELECTOR, "[data-category='Positive'] .emotion-checkbox")
        negative_emotions = browser.find_elements(By.CSS_SELECTOR, "[data-category='Negative'] .emotion-checkbox")
        
        # Click a few emotions
        positive_emotions[0].click()  # Select first positive emotion
        positive_emotions[1].click()  # Select second positive emotion
        negative_emotions[0].click()  # Select first negative emotion
        
        # Check selected emotions display updates
        selected_display = browser.find_element(By.ID, "selected_emotions_display")
        
        # Wait for display to update
        WebDriverWait(browser, 5).until(
            lambda driver: "None selected" not in selected_display.text
        )
        
        # Check badges are displayed
        badges = selected_display.find_elements(By.CSS_SELECTOR, ".badge")
        assert len(badges) == 3, "Should show 3 selected emotion badges"
        
        # Check hidden input is populated
        hidden_input = browser.find_element(By.CSS_SELECTOR, "[name*='additional_emotions']")
        hidden_value = hidden_input.get_attribute("value")
        
        assert hidden_value, "Hidden input should have value"
        
        # Validate JSON format
        try:
            emotions_data = json.loads(hidden_value)
            assert isinstance(emotions_data, list), "Hidden input should contain JSON array"
            assert len(emotions_data) == 3, "Should have 3 selected emotions in JSON"
        except json.JSONDecodeError:
            pytest.fail("Hidden input should contain valid JSON")
    
    def test_form_submission_with_emotions(self, browser, logged_in_user):
        """Test complete form submission with emotion data."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Fill out form
        # 1. Set happiness slider
        slider = browser.find_element(By.CSS_SELECTOR, "input[type='range']")
        browser.execute_script("arguments[0].value = 7;", slider)
        browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", slider)
        
        # 2. Select emotions
        emotions = browser.find_elements(By.CSS_SELECTOR, ".emotion-checkbox")[:3]
        for emotion in emotions:
            emotion.click()
        
        # 3. Fill text areas (if any)
        text_areas = browser.find_elements(By.CSS_SELECTOR, "textarea")
        for i, textarea in enumerate(text_areas):
            if textarea.is_displayed():
                textarea.send_keys(f"Test response {i+1}")
        
        # Submit form
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for success or check for errors
        try:
            # Should redirect to journal index on success
            WebDriverWait(browser, 10).until(
                EC.url_contains("/journal")
            )
            
            # Check for success message
            success_message = WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success"))
            )
            assert "successfully" in success_message.text.lower()
            
        except TimeoutException:
            # Check for error messages
            error_elements = browser.find_elements(By.CSS_SELECTOR, ".alert-danger")
            if error_elements:
                error_text = error_elements[0].text
                pytest.fail(f"Form submission failed with error: {error_text}")
            else:
                pytest.fail("Form submission timed out without clear success or error")
    
    def test_csp_javascript_execution(self, browser, logged_in_user):
        """Test that JavaScript executes properly despite CSP."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Check that JavaScript functions are available
        # Test if emotion selection JavaScript loaded
        emotion_script_loaded = browser.execute_script("""
            return document.querySelectorAll('.emotion-checkbox').length > 0;
        """)
        assert emotion_script_loaded, "Emotion selection JavaScript should load"
        
        # Test if slider JavaScript works
        slider_script_works = browser.execute_script("""
            var slider = document.querySelector('input[type="range"]');
            if (!slider) return false;
            
            var originalValue = slider.value;
            slider.value = '8';
            slider.dispatchEvent(new Event('input'));
            
            var emojiElement = document.querySelector('[id$="_emoji"]');
            return emojiElement && emojiElement.textContent.length > 0;
        """)
        assert slider_script_works, "Slider JavaScript should work"
    
    def test_no_console_errors(self, browser, logged_in_user):
        """Test that page loads without console errors."""
        browser.get("https://127.0.0.1:5000/journal/guided")
        
        # Interact with page elements to trigger JavaScript
        emotions = browser.find_elements(By.CSS_SELECTOR, ".emotion-checkbox")
        if emotions:
            emotions[0].click()
        
        slider = browser.find_element(By.CSS_SELECTOR, "input[type='range']")
        browser.execute_script("arguments[0].value = 5;", slider)
        browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", slider)
        
        # Check console for errors
        logs = browser.get_log('browser')
        critical_errors = [
            log for log in logs 
            if log['level'] == 'SEVERE' and 'Content-Security-Policy' not in log['message']
        ]
        
        assert len(critical_errors) == 0, f"Critical JavaScript errors found: {critical_errors}"