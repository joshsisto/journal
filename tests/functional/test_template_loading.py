"""
Functional tests for template loading and selection functionality.

Tests the JavaScript-based template loading system and user interactions.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException


class TestTemplateLoadingFunctional:
    """Functional tests for template loading interface."""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """Set up browser for functional testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless for CI
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            yield driver
        except WebDriverException:
            pytest.skip("Chrome browser not available for functional testing")
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def login_user(self, browser, base_url, username="testuser", password="TestPassword123!"):
        """Helper to log in a user."""
        browser.get(f"{base_url}/login")
        
        username_field = browser.find_element(By.NAME, "username")
        password_field = browser.find_element(By.NAME, "password")
        
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        login_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for redirect after login
        WebDriverWait(browser, 10).until(
            EC.url_contains("/dashboard")
        )
    
    def test_template_selector_appears(self, browser, app, custom_template_with_questions, user):
        """Test that template selector appears on guided journal page."""
        base_url = "http://localhost:5000"  # Assuming test server runs on this port
        
        # Note: This test requires a running server, so we'll mock the behavior
        # In a real scenario, you'd start the Flask test server
        pytest.skip("Requires running Flask server for Selenium tests")
        
        self.login_user(browser, base_url)
        
        # Navigate to guided journal
        browser.get(f"{base_url}/journal/guided")
        
        # Check that template selector exists
        template_select = browser.find_element(By.ID, "templateSelect")
        assert template_select is not None
        
        # Check that load button exists
        load_button = browser.find_element(By.ID, "loadTemplateBtn")
        assert load_button is not None
        assert "Load" in load_button.text
    
    def test_template_selection_changes_button_text(self, browser, app, custom_template_with_questions, user):
        """Test that selecting a template changes the button text."""
        pytest.skip("Requires running Flask server for Selenium tests")
        
        base_url = "http://localhost:5000"
        self.login_user(browser, base_url)
        
        browser.get(f"{base_url}/journal/guided")
        
        template_select = Select(browser.find_element(By.ID, "templateSelect"))
        load_button = browser.find_element(By.ID, "loadTemplateBtn")
        
        # Initially should show "Load Default"
        assert "Default" in load_button.text
        
        # Select a template
        template_select.select_by_visible_text(custom_template_with_questions.name)
        
        # Wait for button text to update
        WebDriverWait(browser, 5).until(
            lambda driver: custom_template_with_questions.name in load_button.text
        )
        
        assert custom_template_with_questions.name in load_button.text
    
    def test_load_template_button_functionality(self, browser, app, custom_template_with_questions, user):
        """Test that clicking load template button redirects with template parameter."""
        pytest.skip("Requires running Flask server for Selenium tests")
        
        base_url = "http://localhost:5000"
        self.login_user(browser, base_url)
        
        browser.get(f"{base_url}/journal/guided")
        
        template_select = Select(browser.find_element(By.ID, "templateSelect"))
        load_button = browser.find_element(By.ID, "loadTemplateBtn")
        
        # Select template
        template_select.select_by_visible_text(custom_template_with_questions.name)
        
        # Click load button
        load_button.click()
        
        # Wait for page to load with template parameter
        WebDriverWait(browser, 10).until(
            lambda driver: f"template_id={custom_template_with_questions.id}" in driver.current_url
        )
        
        assert f"template_id={custom_template_with_questions.id}" in browser.current_url
    
    def test_template_questions_appear_after_loading(self, browser, app, custom_template_with_questions, user):
        """Test that template questions appear after loading template."""
        pytest.skip("Requires running Flask server for Selenium tests")
        
        base_url = "http://localhost:5000"
        self.login_user(browser, base_url)
        
        # Navigate directly to guided journal with template
        browser.get(f"{base_url}/journal/guided?template_id={custom_template_with_questions.id}")
        
        # Check that template questions appear
        questions = browser.find_elements(By.CSS_SELECTOR, ".card-title")
        
        # Should have template questions, not default ones
        question_texts = [q.text for q in questions]
        assert "How would you rate your day?" in question_texts
        assert "What was the highlight of your day?" in question_texts
    
    def test_template_preview_shows_selected_template(self, browser, app, custom_template_with_questions, user):
        """Test that template preview area shows selected template info."""
        pytest.skip("Requires running Flask server for Selenium tests")
        
        base_url = "http://localhost:5000"
        self.login_user(browser, base_url)
        
        browser.get(f"{base_url}/journal/guided?template_id={custom_template_with_questions.id}")
        
        # Check template preview area
        preview = browser.find_element(By.ID, "templatePreview")
        assert custom_template_with_questions.name in preview.text
        
        # Should show active template indicator
        assert "Active Template" in preview.text
    
    def test_submit_template_based_entry(self, browser, app, custom_template_with_questions, user):
        """Test submitting a journal entry using template questions."""
        pytest.skip("Requires running Flask server for Selenium tests")
        
        base_url = "http://localhost:5000"
        self.login_user(browser, base_url)
        
        browser.get(f"{base_url}/journal/guided?template_id={custom_template_with_questions.id}")
        
        # Fill out template questions
        # Number question (rating slider)
        rating_slider = browser.find_element(By.CSS_SELECTOR, "input[type='range']")
        browser.execute_script("arguments[0].value = 8; arguments[0].dispatchEvent(new Event('input'));", rating_slider)
        
        # Text question
        text_areas = browser.find_elements(By.CSS_SELECTOR, "textarea")
        if text_areas:
            text_areas[0].send_keys("This was a great day!")
        
        # Boolean question (Yes/No radio)
        yes_radio = browser.find_element(By.CSS_SELECTOR, "input[type='radio'][value='Yes']")
        yes_radio.click()
        
        # Submit the form
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for success message
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success"))
        )
        
        success_message = browser.find_element(By.CSS_SELECTOR, ".alert-success")
        assert "success" in success_message.text.lower()


class TestTemplateLoadingUnit:
    """Unit tests for template loading JavaScript functionality."""
    
    def test_template_loading_javascript_structure(self, client, logged_in_user, custom_template):
        """Test that template loading JavaScript is properly structured."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check for required JavaScript functions
        assert 'loadSelectedTemplate' in content
        assert 'changeTemplate' in content
        assert 'updateLoadButtonText' in content
        
        # Check for required DOM elements
        assert 'id="templateSelect"' in content
        assert 'id="loadTemplateBtn"' in content
        assert 'onclick="loadSelectedTemplate()"' in content
    
    def test_template_loading_url_construction(self, client, logged_in_user, custom_template):
        """Test that JavaScript constructs URLs correctly."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check URL construction logic
        assert 'window.location.origin' in content
        assert 'window.location.pathname' in content
        assert 'template_id' in content
    
    def test_template_options_rendered_correctly(self, client, logged_in_user, custom_template, system_template):
        """Test that template options are rendered in select dropdown."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check that templates appear in select options
        assert custom_template.name in content
        assert system_template.name in content
        
        # Check for optgroups
        assert 'System Templates' in content
        assert 'My Templates' in content
    
    def test_template_loading_with_invalid_id(self, client, logged_in_user):
        """Test template loading with invalid template ID."""
        response = client.get('/journal/guided?template_id=99999')
        
        # Should fallback to default questions gracefully
        assert response.status_code == 200
        assert b'guided' in response.data.lower()
    
    def test_template_loading_preserves_form_state(self, client, logged_in_user, custom_template):
        """Test that template loading preserves CSRF tokens and form state."""
        response = client.get(f'/journal/guided?template_id={custom_template.id}')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check CSRF token is present
        assert 'csrf_token' in content
        assert '_csrf_token' in content
        
        # Check template_id is preserved in hidden field
        assert f'value="{custom_template.id}"' in content
    
    def test_template_loading_console_logging(self, client, logged_in_user):
        """Test that JavaScript includes proper console logging for debugging."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check for console.log statements
        assert 'console.log' in content
        assert 'Loading template' in content or 'Redirecting to' in content
    
    def test_template_loading_error_handling(self, client, logged_in_user):
        """Test that template loading includes error handling."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Should include basic error handling for missing elements
        assert 'getElementById' in content
        # JavaScript should check if elements exist before using them
        assert 'loadBtn' in content
    
    def test_template_loading_accessibility(self, client, logged_in_user, custom_template):
        """Test that template loading interface is accessible."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        content = response.data.decode()
        
        # Check for proper labels
        assert 'for="templateSelect"' in content
        assert 'Select Template' in content
        
        # Check for helpful instructions
        assert 'Load Template' in content
        
        # Check for proper button structure
        assert 'btn' in content and 'button' in content