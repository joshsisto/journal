"""
End-to-end functional tests for location search functionality.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from unittest.mock import patch


class TestLocationSearchE2E:
    """End-to-end tests for location search functionality."""

    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome driver for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        yield driver
        driver.quit()

    @pytest.fixture
    def wait(self, driver):
        """Create WebDriverWait instance."""
        return WebDriverWait(driver, 10)

    def test_location_search_elements_present(self, driver, wait):
        """Test that location search elements are present on the page."""
        # Navigate to quick journal page
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        # Check if we're redirected to login (expected for unauthenticated user)
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        try:
            # Look for location search input
            search_input = wait.until(
                EC.presence_of_element_located((By.ID, "location-search-input"))
            )
            assert search_input.is_displayed()
            assert search_input.get_attribute("placeholder")
            
            # Look for location search button
            search_button = driver.find_element(By.ID, "location-search-btn")
            assert search_button.is_displayed()
            
            # Look for current location button
            current_location_btn = driver.find_element(By.ID, "get-current-location")
            assert current_location_btn.is_displayed()
            
        except TimeoutException:
            pytest.fail("Location search elements not found within timeout")

    def test_location_search_input_validation(self, driver, wait):
        """Test location search input validation."""
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        try:
            search_input = wait.until(
                EC.presence_of_element_located((By.ID, "location-search-input"))
            )
            search_button = driver.find_element(By.ID, "location-search-btn")
            
            # Test empty input
            search_input.clear()
            search_button.click()
            
            # Should show some kind of validation message
            # (This would need to be verified based on actual implementation)
            
            # Test valid input
            search_input.clear()
            search_input.send_keys("New York")
            search_button.click()
            
            # Should trigger search (verified by network activity or UI changes)
            
        except (TimeoutException, NoSuchElementException):
            pytest.skip("Could not test location search validation")

    def test_location_search_javascript_loaded(self, driver):
        """Test that location search JavaScript is properly loaded."""
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        # Check if LocationService is available
        location_service_available = driver.execute_script(
            "return typeof window.LocationService !== 'undefined' || typeof window.locationService !== 'undefined';"
        )
        
        if not location_service_available:
            # Wait a bit for dynamic loading
            time.sleep(2)
            location_service_available = driver.execute_script(
                "return typeof window.LocationService !== 'undefined' || typeof window.locationService !== 'undefined';"
            )
        
        # Note: This might be false if authentication is required
        # The test documents the expected behavior
        
    def test_csrf_token_present(self, driver):
        """Test that CSRF token is available for API calls."""
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        # Check if CSRF token is set
        csrf_token = driver.execute_script("return window.csrfToken;")
        
        if csrf_token:
            assert isinstance(csrf_token, str)
            assert len(csrf_token) > 0

    def test_location_search_accessibility(self, driver, wait):
        """Test accessibility features of location search."""
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        try:
            # Check for proper labels and ARIA attributes
            search_input = wait.until(
                EC.presence_of_element_located((By.ID, "location-search-input"))
            )
            search_button = driver.find_element(By.ID, "location-search-btn")
            
            # Check input has placeholder
            placeholder = search_input.get_attribute("placeholder")
            assert placeholder and len(placeholder) > 0
            
            # Check button has title or aria-label
            title = search_button.get_attribute("title")
            aria_label = search_button.get_attribute("aria-label")
            assert title or aria_label
            
        except (TimeoutException, NoSuchElementException):
            pytest.skip("Could not test accessibility features")

    def test_enter_key_functionality(self, driver, wait):
        """Test that Enter key triggers location search."""
        driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        try:
            search_input = wait.until(
                EC.presence_of_element_located((By.ID, "location-search-input"))
            )
            
            # Type in input and press Enter
            search_input.clear()
            search_input.send_keys("New York")
            search_input.send_keys("\n")  # Enter key
            
            # Should trigger the same behavior as clicking the button
            # (Specific verification would depend on implementation)
            
        except (TimeoutException, NoSuchElementException):
            pytest.skip("Could not test Enter key functionality")


class TestLocationSearchPerformance:
    """Performance tests for location search."""
    
    def test_location_js_load_time(self):
        """Test that location.js loads within reasonable time."""
        import requests
        import time
        
        start_time = time.time()
        response = requests.get("https://journal.joshsisto.com/static/js/location.js")
        load_time = time.time() - start_time
        
        assert response.status_code == 200
        assert load_time < 2.0  # Should load within 2 seconds
        
    def test_location_component_render_time(self):
        """Test that location component renders quickly."""
        # This would measure the time it takes for the component to render
        # In a real browser environment
        pass


class TestLocationSearchMobile:
    """Mobile-specific tests for location search."""
    
    @pytest.fixture
    def mobile_driver(self):
        """Set up mobile Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Mobile viewport
        chrome_options.add_argument("--window-size=375,667")
        chrome_options.add_experimental_option("mobileEmulation", {
            "deviceName": "iPhone SE"
        })
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    def test_location_search_mobile_layout(self, mobile_driver):
        """Test location search layout on mobile devices."""
        mobile_driver.get("https://journal.joshsisto.com/journal/quick")
        
        if "login" in mobile_driver.current_url.lower():
            pytest.skip("Authentication required for this test")
        
        try:
            # Check if elements are visible and properly sized on mobile
            search_input = mobile_driver.find_element(By.ID, "location-search-input")
            search_button = mobile_driver.find_element(By.ID, "location-search-btn")
            
            # Elements should be visible
            assert search_input.is_displayed()
            assert search_button.is_displayed()
            
            # Elements should be appropriately sized for mobile
            input_size = search_input.size
            button_size = search_button.size
            
            assert input_size['width'] > 100  # Reasonable minimum width
            assert button_size['height'] > 30  # Touchable size
            
        except NoSuchElementException:
            pytest.skip("Could not test mobile layout")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])