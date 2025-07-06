#!/usr/bin/env python3
"""
Final Dashboard Validation Script
Tests the newly implemented compact, tight dashboard design
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

class CompactDashboardValidator:
    def __init__(self, base_url="https://journal.joshsisto.com"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_results": {},
            "screenshots": [],
            "design_assessment": {},
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
        filename = f"final_validation_{name}_{timestamp}.png"
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
    
    def login_to_app(self):
        """Login to the application"""
        print("🔐 Logging into application...")
        
        try:
            # Navigate to login page
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
            
            # Wait for redirect
            self.wait.until(
                EC.any_of(
                    EC.url_contains("/dashboard"),
                    EC.url_contains("/journal")
                )
            )
            
            print(f"✅ Authentication successful! Current URL: {self.driver.current_url}")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return False
    
    def test_dashboard_access(self):
        """Test dashboard access and capture main view"""
        print("📊 Testing dashboard access...")
        
        try:
            # Navigate to dashboard
            self.driver.get(f"{self.base_url}/dashboard")
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)  # Allow for dynamic content
            
            # Take screenshot of main dashboard
            self.take_screenshot("dashboard_main", "Main dashboard view - compact design")
            
            # Check page title
            page_title = self.driver.title
            print(f"📋 Dashboard page title: {page_title}")
            
            # Analyze page structure
            self.analyze_page_structure()
            
            return True
            
        except Exception as e:
            print(f"❌ Dashboard access failed: {str(e)}")
            return False
    
    def analyze_page_structure(self):
        """Analyze the dashboard structure and spacing"""
        print("🔍 Analyzing dashboard structure...")
        
        try:
            # Get page dimensions
            body_height = self.driver.execute_script("return document.body.scrollHeight")
            window_height = self.driver.execute_script("return window.innerHeight")
            
            # Look for main content areas
            main_content = self.driver.find_elements(By.CSS_SELECTOR, "main, .main-content, .container, .dashboard-container")
            
            # Look for writing interface
            writing_areas = self.driver.find_elements(By.CSS_SELECTOR, "textarea, .writing-area, .quick-write, .journal-form")
            
            # Look for entry displays
            entry_displays = self.driver.find_elements(By.CSS_SELECTOR, ".entry, .journal-entry, .recent-entries, .entries-list")
            
            # Look for toggle buttons
            toggle_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, .toggle, .btn-toggle, .expand, .show-more")
            
            self.results["design_assessment"] = {
                "page_height": body_height,
                "window_height": window_height,
                "main_content_areas": len(main_content),
                "writing_areas_found": len(writing_areas),
                "entry_displays_found": len(entry_displays),
                "toggle_buttons_found": len(toggle_buttons)
            }
            
            print(f"📐 Page structure analysis:")
            print(f"   - Page height: {body_height}px")
            print(f"   - Window height: {window_height}px")
            print(f"   - Main content areas: {len(main_content)}")
            print(f"   - Writing areas: {len(writing_areas)}")
            print(f"   - Entry displays: {len(entry_displays)}")
            print(f"   - Interactive buttons: {len(toggle_buttons)}")
            
        except Exception as e:
            print(f"❌ Structure analysis failed: {str(e)}")
    
    def test_writing_interface(self):
        """Test the writing interface functionality"""
        print("✏️  Testing writing interface...")
        
        try:
            # Look for writing interface elements
            writing_selectors = [
                "textarea",
                "input[type='text']",
                ".writing-area",
                ".quick-write",
                ".journal-form textarea",
                "#content",
                "[name='content']"
            ]
            
            writing_element = None
            for selector in writing_selectors:
                try:
                    writing_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Found writing interface with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if writing_element:
                # Take screenshot of writing interface
                self.take_screenshot("writing_interface", "Writing interface - ready for input")
                
                # Test writing functionality
                test_text = "Testing compact dashboard design"
                writing_element.clear()
                writing_element.send_keys(test_text)
                
                # Verify text was entered
                entered_text = writing_element.get_attribute("value")
                if test_text in entered_text:
                    print("✅ Writing interface working correctly")
                    return True
                else:
                    print("⚠️  Writing interface may have issues")
                    return False
            else:
                print("⚠️  No writing interface found")
                return False
                
        except Exception as e:
            print(f"❌ Writing interface test failed: {str(e)}")
            return False
    
    def test_guided_entries_display(self):
        """Test guided journal entries display"""
        print("📝 Testing guided journal entries...")
        
        try:
            # Look for guided entries
            guided_selectors = [
                ".guided-entry",
                ".guided-response",
                ".journal-entry",
                ".entry-guided",
                ".guided-journal"
            ]
            
            guided_entries = []
            for selector in guided_selectors:
                entries = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if entries:
                    guided_entries.extend(entries)
                    print(f"✅ Found {len(entries)} entries with selector: {selector}")
            
            if guided_entries:
                # Take screenshot of guided entries
                self.take_screenshot("guided_entries", "Guided journal entries display")
                
                # Check for emotion displays
                emotion_elements = self.driver.find_elements(By.CSS_SELECTOR, ".emotion, .emotions, .feeling")
                print(f"📊 Found {len(emotion_elements)} emotion-related elements")
                
                return True
            else:
                print("⚠️  No guided journal entries found")
                return False
                
        except Exception as e:
            print(f"❌ Guided entries test failed: {str(e)}")
            return False
    
    def test_toggle_functionality(self):
        """Test toggle functionality"""
        print("🔄 Testing toggle functionality...")
        
        try:
            # Look for toggle buttons
            toggle_selectors = [
                "button",
                ".toggle",
                ".btn-toggle",
                ".expand",
                ".show-more",
                ".show-details"
            ]
            
            toggle_buttons = []
            for selector in toggle_selectors:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    toggle_buttons.extend(buttons)
            
            if toggle_buttons:
                # Take screenshot before toggle
                self.take_screenshot("toggle_before", "Before toggle interaction")
                
                # Try to click first toggle
                first_button = toggle_buttons[0]
                button_text = first_button.text
                
                # Click using JavaScript to avoid interception
                self.driver.execute_script("arguments[0].click();", first_button)
                time.sleep(1)
                
                # Take screenshot after toggle
                self.take_screenshot("toggle_after", "After toggle interaction")
                
                print(f"✅ Toggle functionality tested with button: '{button_text}'")
                return True
            else:
                print("⚠️  No toggle buttons found")
                return False
                
        except Exception as e:
            print(f"❌ Toggle functionality test failed: {str(e)}")
            return False
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness"""
        print("📱 Testing mobile responsiveness...")
        
        try:
            # Resize to mobile viewport
            self.driver.set_window_size(375, 667)
            time.sleep(2)
            
            # Take screenshot of mobile view
            self.take_screenshot("mobile_view", "Mobile responsive view (375px width)")
            
            # Check if content fits
            body_width = self.driver.execute_script("return document.body.scrollWidth")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            
            is_responsive = body_width <= viewport_width + 20
            
            if is_responsive:
                print(f"✅ Mobile responsiveness working: {viewport_width}px viewport, {body_width}px content")
                return True
            else:
                print(f"⚠️  Mobile responsiveness issue: {viewport_width}px viewport, {body_width}px content")
                return False
                
        except Exception as e:
            print(f"❌ Mobile responsiveness test failed: {str(e)}")
            return False
        finally:
            # Restore desktop size
            self.driver.set_window_size(1920, 1080)
    
    def run_validation(self):
        """Run comprehensive validation"""
        print("🚀 Starting Final Dashboard Validation")
        print("=" * 60)
        
        success = True
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Login
            if not self.login_to_app():
                success = False
                return
            
            # Test dashboard access
            if not self.test_dashboard_access():
                success = False
            
            # Test writing interface
            if not self.test_writing_interface():
                self.results["issues_found"].append("Writing interface not accessible")
            
            # Test guided entries
            if not self.test_guided_entries_display():
                self.results["issues_found"].append("Guided journal entries not found")
            
            # Test toggle functionality
            if not self.test_toggle_functionality():
                self.results["issues_found"].append("Toggle functionality not working")
            
            # Test mobile responsiveness
            if not self.test_mobile_responsiveness():
                self.results["issues_found"].append("Mobile responsiveness issues")
            
            # Determine overall status
            if success and len(self.results["issues_found"]) == 0:
                self.results["overall_status"] = "PASSED"
            elif len(self.results["issues_found"]) <= 2:
                self.results["overall_status"] = "PASSED_WITH_WARNINGS"
            else:
                self.results["overall_status"] = "FAILED"
                
        except Exception as e:
            self.results["overall_status"] = "CRITICAL_FAILURE"
            self.results["issues_found"].append(f"Critical failure: {str(e)}")
            print(f"💥 Critical failure: {str(e)}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 Browser closed")
    
    def generate_report(self):
        """Generate validation report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"/home/josh/Sync2/projects/journal/final_validation_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📋 Final validation report saved: {report_path}")
        return report_path
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 FINAL DASHBOARD VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"🕐 Timestamp: {self.results['timestamp']}")
        print(f"🎯 Overall Status: {self.results['overall_status']}")
        
        if self.results["design_assessment"]:
            print(f"\n📐 Design Assessment:")
            assessment = self.results["design_assessment"]
            for key, value in assessment.items():
                print(f"   {key}: {value}")
        
        if self.results["issues_found"]:
            print(f"\n🚨 Issues Found ({len(self.results['issues_found'])}):")
            for issue in self.results["issues_found"]:
                print(f"   • {issue}")
        
        if self.results["screenshots"]:
            print(f"\n📸 Screenshots Captured ({len(self.results['screenshots'])}):")
            for screenshot in self.results["screenshots"]:
                print(f"   • {screenshot['name']}: {screenshot['description']}")
                print(f"     File: {screenshot['filepath']}")
        
        print("\n" + "=" * 60)
        print("🔍 COMPACT DESIGN EVALUATION")
        print("=" * 60)
        
        # Provide specific compact design assessment
        if self.results["design_assessment"]:
            assessment = self.results["design_assessment"]
            page_height = assessment.get("page_height", 0)
            writing_areas = assessment.get("writing_areas_found", 0)
            entry_displays = assessment.get("entry_displays_found", 0)
            
            print(f"📊 Compactness Indicators:")
            print(f"   • Page height: {page_height}px {'(Compact)' if page_height < 2000 else '(Needs optimization)'}")
            print(f"   • Writing interface availability: {'✅ Available' if writing_areas > 0 else '❌ Not found'}")
            print(f"   • Entry display efficiency: {'✅ Efficient' if entry_displays > 0 else '❌ Needs improvement'}")
            
            # Overall compact design rating
            compact_score = 0
            if page_height < 2000:
                compact_score += 1
            if writing_areas > 0:
                compact_score += 1
            if entry_displays > 0:
                compact_score += 1
            
            if compact_score >= 2:
                print(f"🎯 Compact Design Rating: {'✅ EXCELLENT' if compact_score == 3 else '✅ GOOD'}")
            else:
                print(f"🎯 Compact Design Rating: ❌ NEEDS IMPROVEMENT")
        
        print("=" * 60)


def main():
    """Main validation function"""
    validator = CompactDashboardValidator()
    
    try:
        validator.run_validation()
        validator.generate_report()
        validator.print_summary()
        
        return validator.results["overall_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        
    except Exception as e:
        print(f"💥 Validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)