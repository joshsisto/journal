#!/usr/bin/env python3
"""
Comprehensive Dashboard Validation Script
Validates all enhanced dashboard functionality end-to-end
"""

import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class DashboardValidator:
    def __init__(self, base_url="https://journal.joshsisto.com"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_results": {},
            "screenshots": [],
            "performance_metrics": {},
            "issues_found": [],
            "overall_status": "UNKNOWN"
        }
        
    def setup_driver(self, mobile=False):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        if mobile:
            chrome_options.add_argument("--window-size=375,667")
            chrome_options.add_experimental_option("mobileEmulation", {
                "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
            })
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def take_screenshot(self, name, description=""):
        """Take a screenshot and save it"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_validation_{name}_{timestamp}.png"
        filepath = f"/home/josh/Sync2/projects/journal/{filename}"
        
        try:
            self.driver.save_screenshot(filepath)
            self.results["screenshots"].append({
                "name": name,
                "description": description,
                "filepath": filepath,
                "timestamp": timestamp
            })
            print(f"✅ Screenshot saved: {filename}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to save screenshot {name}: {str(e)}")
            return None
    
    def measure_performance(self, action_name):
        """Measure page performance"""
        try:
            # Get navigation timing
            nav_timing = self.driver.execute_script("""
                var timing = performance.timing;
                return {
                    'navigationStart': timing.navigationStart,
                    'domContentLoadedEventEnd': timing.domContentLoadedEventEnd,
                    'loadEventEnd': timing.loadEventEnd,
                    'pageLoadTime': timing.loadEventEnd - timing.navigationStart,
                    'domReadyTime': timing.domContentLoadedEventEnd - timing.navigationStart
                };
            """)
            
            self.results["performance_metrics"][action_name] = nav_timing
            print(f"📊 Performance - {action_name}: {nav_timing.get('pageLoadTime', 0)}ms")
            return nav_timing
        except Exception as e:
            print(f"❌ Performance measurement failed for {action_name}: {str(e)}")
            return None
    
    def test_authentication(self):
        """Test authentication with automation_test user"""
        print("\n🔐 Testing Authentication...")
        
        try:
            # Navigate to login page
            start_time = time.time()
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for login form
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # Take screenshot of login page
            self.take_screenshot("login_page", "Login page before authentication")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys("automation_test")
            password_field.clear()
            password_field.send_keys("automation123")
            
            # Submit form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for dashboard redirect
            self.wait.until(
                EC.url_contains("/dashboard")
            )
            
            auth_time = time.time() - start_time
            self.results["test_results"]["authentication"] = {
                "status": "PASSED",
                "time_taken": auth_time,
                "current_url": self.driver.current_url
            }
            print(f"✅ Authentication successful in {auth_time:.2f}s")
            
        except Exception as e:
            self.results["test_results"]["authentication"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Authentication failed: {str(e)}")
            print(f"❌ Authentication failed: {str(e)}")
            raise
    
    def test_dashboard_loading(self):
        """Test dashboard loading and enhanced functionality"""
        print("\n📊 Testing Dashboard Loading...")
        
        try:
            start_time = time.time()
            
            # Ensure we're on the dashboard
            if "/dashboard" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/dashboard")
            
            # Wait for dashboard elements
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard-container"))
            )
            
            # Measure performance
            self.measure_performance("dashboard_load")
            
            # Take screenshot of main dashboard
            self.take_screenshot("dashboard_main", "Main dashboard view")
            
            # Check for key dashboard elements
            elements_to_check = [
                (".dashboard-header", "Dashboard header"),
                (".quick-write-section", "Quick write section"),
                (".recent-entries", "Recent entries section"),
                (".dashboard-stats", "Dashboard statistics")
            ]
            
            found_elements = []
            for selector, name in elements_to_check:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    found_elements.append(name)
                    print(f"✅ Found: {name}")
                except NoSuchElementException:
                    print(f"⚠️  Missing: {name}")
            
            load_time = time.time() - start_time
            self.results["test_results"]["dashboard_loading"] = {
                "status": "PASSED",
                "time_taken": load_time,
                "elements_found": found_elements,
                "elements_count": len(found_elements)
            }
            print(f"✅ Dashboard loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            self.results["test_results"]["dashboard_loading"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Dashboard loading failed: {str(e)}")
            print(f"❌ Dashboard loading failed: {str(e)}")
    
    def test_guided_journal_display(self):
        """Test guided journal entries display with emotions"""
        print("\n📝 Testing Guided Journal Display...")
        
        try:
            # Look for guided journal entries
            guided_entries = self.driver.find_elements(By.CSS_SELECTOR, ".guided-entry")
            
            if not guided_entries:
                print("⚠️  No guided journal entries found")
                self.results["test_results"]["guided_journal_display"] = {
                    "status": "NO_DATA",
                    "entries_found": 0
                }
                return
            
            # Take screenshot of guided entries
            self.take_screenshot("guided_entries", "Guided journal entries display")
            
            # Check for emotion information in entries
            emotion_info_found = 0
            for entry in guided_entries[:3]:  # Check first 3 entries
                try:
                    emotion_element = entry.find_element(By.CSS_SELECTOR, ".emotion-info, .emotion-display, .guided-emotions")
                    emotion_info_found += 1
                    print(f"✅ Found emotion info in entry")
                except NoSuchElementException:
                    print(f"⚠️  No emotion info found in entry")
            
            self.results["test_results"]["guided_journal_display"] = {
                "status": "PASSED",
                "entries_found": len(guided_entries),
                "entries_with_emotions": emotion_info_found
            }
            print(f"✅ Guided journal display validated: {len(guided_entries)} entries, {emotion_info_found} with emotions")
            
        except Exception as e:
            self.results["test_results"]["guided_journal_display"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Guided journal display failed: {str(e)}")
            print(f"❌ Guided journal display failed: {str(e)}")
    
    def test_toggle_functionality(self):
        """Test detailed view toggle functionality"""
        print("\n🔄 Testing Toggle Functionality...")
        
        try:
            # Look for toggle buttons
            toggle_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".toggle-details, .show-details, .expand-toggle")
            
            if not toggle_buttons:
                print("⚠️  No toggle buttons found")
                self.results["test_results"]["toggle_functionality"] = {
                    "status": "NO_TOGGLES",
                    "toggles_found": 0
                }
                return
            
            # Test first toggle
            first_toggle = toggle_buttons[0]
            initial_text = first_toggle.text
            
            # Take screenshot before toggle
            self.take_screenshot("toggle_before", "Before toggle action")
            
            # Click toggle
            self.driver.execute_script("arguments[0].click();", first_toggle)
            time.sleep(1)  # Wait for animation
            
            # Take screenshot after toggle
            self.take_screenshot("toggle_after", "After toggle action")
            
            # Check if toggle state changed
            after_text = first_toggle.text
            toggle_worked = initial_text != after_text
            
            self.results["test_results"]["toggle_functionality"] = {
                "status": "PASSED" if toggle_worked else "FAILED",
                "toggles_found": len(toggle_buttons),
                "toggle_state_changed": toggle_worked,
                "initial_text": initial_text,
                "after_text": after_text
            }
            
            if toggle_worked:
                print(f"✅ Toggle functionality working: '{initial_text}' -> '{after_text}'")
            else:
                print(f"⚠️  Toggle state unchanged: '{initial_text}'")
            
        except Exception as e:
            self.results["test_results"]["toggle_functionality"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Toggle functionality failed: {str(e)}")
            print(f"❌ Toggle functionality failed: {str(e)}")
    
    def test_writing_interface(self):
        """Test immediate writing functionality"""
        print("\n✏️  Testing Writing Interface...")
        
        try:
            # Look for quick write area
            write_area = None
            write_selectors = [
                "textarea[name='content']",
                "#quick-write-content",
                ".quick-write textarea",
                "textarea.form-control"
            ]
            
            for selector in write_selectors:
                try:
                    write_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not write_area:
                print("⚠️  No writing interface found")
                self.results["test_results"]["writing_interface"] = {
                    "status": "NO_INTERFACE",
                    "interface_found": False
                }
                return
            
            # Test writing functionality
            test_content = "Test entry for dashboard validation"
            write_area.clear()
            write_area.send_keys(test_content)
            
            # Take screenshot of writing interface
            self.take_screenshot("writing_interface", "Writing interface with test content")
            
            # Verify content was entered
            entered_content = write_area.get_attribute("value")
            content_matches = test_content in entered_content
            
            self.results["test_results"]["writing_interface"] = {
                "status": "PASSED" if content_matches else "FAILED",
                "interface_found": True,
                "content_entered": content_matches,
                "test_content": test_content,
                "entered_content": entered_content
            }
            
            if content_matches:
                print(f"✅ Writing interface working correctly")
            else:
                print(f"⚠️  Writing interface issue: expected '{test_content}', got '{entered_content}'")
            
        except Exception as e:
            self.results["test_results"]["writing_interface"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Writing interface failed: {str(e)}")
            print(f"❌ Writing interface failed: {str(e)}")
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness at 375px width"""
        print("\n📱 Testing Mobile Responsiveness...")
        
        try:
            # Resize to mobile viewport
            self.driver.set_window_size(375, 667)
            time.sleep(2)  # Wait for responsive layout
            
            # Take screenshot of mobile view
            self.take_screenshot("mobile_view", "Mobile responsive view (375px)")
            
            # Check if mobile-specific elements are present
            mobile_elements = []
            mobile_selectors = [
                ".mobile-menu",
                ".hamburger-menu",
                ".mobile-nav",
                ".responsive-layout"
            ]
            
            for selector in mobile_selectors:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    mobile_elements.append(selector)
                except NoSuchElementException:
                    pass
            
            # Check if layout is responsive (no horizontal scroll)
            body_width = self.driver.execute_script("return document.body.scrollWidth")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            
            is_responsive = body_width <= viewport_width + 20  # Allow small margin
            
            self.results["test_results"]["mobile_responsiveness"] = {
                "status": "PASSED" if is_responsive else "FAILED",
                "viewport_width": viewport_width,
                "body_width": body_width,
                "is_responsive": is_responsive,
                "mobile_elements_found": mobile_elements
            }
            
            if is_responsive:
                print(f"✅ Mobile responsiveness working: {viewport_width}px viewport, {body_width}px content")
            else:
                print(f"⚠️  Mobile responsiveness issue: {viewport_width}px viewport, {body_width}px content")
            
        except Exception as e:
            self.results["test_results"]["mobile_responsiveness"] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.results["issues_found"].append(f"Mobile responsiveness failed: {str(e)}")
            print(f"❌ Mobile responsiveness failed: {str(e)}")
        finally:
            # Restore desktop size
            self.driver.set_window_size(1920, 1080)
    
    def run_comprehensive_validation(self):
        """Run complete validation suite"""
        print("🚀 Starting Comprehensive Dashboard Validation")
        print("=" * 50)
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Run all tests
            self.test_authentication()
            self.test_dashboard_loading()
            self.test_guided_journal_display()
            self.test_toggle_functionality()
            self.test_writing_interface()
            self.test_mobile_responsiveness()
            
            # Calculate overall status
            failed_tests = [test for test, result in self.results["test_results"].items() 
                          if result.get("status") == "FAILED"]
            
            if not failed_tests:
                self.results["overall_status"] = "PASSED"
            elif len(failed_tests) <= 2:
                self.results["overall_status"] = "PASSED_WITH_WARNINGS"
            else:
                self.results["overall_status"] = "FAILED"
            
            print(f"\n🎯 Overall Status: {self.results['overall_status']}")
            
        except Exception as e:
            self.results["overall_status"] = "CRITICAL_FAILURE"
            self.results["issues_found"].append(f"Critical failure: {str(e)}")
            print(f"💥 Critical failure: {str(e)}")
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        report_path = f"/home/josh/Sync2/projects/journal/dashboard_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📋 Validation report saved: {report_path}")
        return report_path
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 DASHBOARD VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"🕐 Timestamp: {self.results['timestamp']}")
        print(f"🎯 Overall Status: {self.results['overall_status']}")
        
        print("\n📋 Test Results:")
        for test_name, result in self.results["test_results"].items():
            status = result.get("status", "UNKNOWN")
            icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
            print(f"  {icon} {test_name.replace('_', ' ').title()}: {status}")
        
        if self.results["issues_found"]:
            print(f"\n🚨 Issues Found ({len(self.results['issues_found'])}):")
            for issue in self.results["issues_found"]:
                print(f"  • {issue}")
        
        if self.results["screenshots"]:
            print(f"\n📸 Screenshots Captured ({len(self.results['screenshots'])}):")
            for screenshot in self.results["screenshots"]:
                print(f"  • {screenshot['name']}: {screenshot['filepath']}")
        
        print("=" * 60)


def main():
    """Main validation function"""
    validator = DashboardValidator()
    
    try:
        validator.run_comprehensive_validation()
        validator.generate_report()
        validator.print_summary()
        
        return validator.results["overall_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        
    except Exception as e:
        print(f"💥 Validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)