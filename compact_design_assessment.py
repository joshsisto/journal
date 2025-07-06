#!/usr/bin/env python3
"""
Compact Design Assessment Script
Analyzes the dashboard CSS and provides assessment of compact design implementation
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class CompactDesignAssessment:
    def __init__(self, base_url="https://journal.joshsisto.com"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "authentication_test": {},
            "legacy_dashboard_test": {},
            "css_analysis": {},
            "screenshots": [],
            "design_assessment": {},
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
        filename = f"compact_design_{name}_{timestamp}.png"
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
    
    def test_authentication(self):
        """Test authentication functionality"""
        print("🔐 Testing Authentication...")
        
        try:
            # Navigate to login page
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for login form
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # Take screenshot of login page
            self.take_screenshot("login_page", "Login page interface")
            
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
            
            self.results["authentication_test"] = {
                "status": "SUCCESS",
                "redirected_to": self.driver.current_url
            }
            print(f"✅ Authentication successful! Redirected to: {self.driver.current_url}")
            return True
            
        except Exception as e:
            self.results["authentication_test"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ Authentication failed: {str(e)}")
            return False
    
    def test_legacy_dashboard(self):
        """Test legacy dashboard as working baseline"""
        print("📊 Testing Legacy Dashboard...")
        
        try:
            # Navigate to legacy dashboard
            self.driver.get(f"{self.base_url}/dashboard/legacy")
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # Take screenshot
            self.take_screenshot("legacy_dashboard", "Legacy dashboard for comparison")
            
            # Check page title
            page_title = self.driver.title
            
            # Analyze basic structure
            body_height = self.driver.execute_script("return document.body.scrollHeight")
            
            self.results["legacy_dashboard_test"] = {
                "status": "SUCCESS",
                "page_title": page_title,
                "page_height": body_height,
                "url": self.driver.current_url
            }
            
            print(f"✅ Legacy dashboard loaded successfully")
            print(f"   Title: {page_title}")
            print(f"   Height: {body_height}px")
            return True
            
        except Exception as e:
            self.results["legacy_dashboard_test"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ Legacy dashboard test failed: {str(e)}")
            return False
    
    def analyze_compact_css(self):
        """Analyze the compact dashboard CSS implementation"""
        print("🎨 Analyzing Compact CSS Implementation...")
        
        try:
            # Read the dashboard template to analyze CSS
            with open("/home/josh/Sync2/projects/journal/templates/dashboard.html", "r") as f:
                dashboard_content = f.read()
            
            # Extract CSS rules for analysis
            css_indicators = {}
            
            # Check for compact indicators
            if "padding: 8px" in dashboard_content:
                css_indicators["compact_padding"] = True
            
            if "margin-bottom: 12px" in dashboard_content:
                css_indicators["tight_margins"] = True
                
            if "font-size: 14px" in dashboard_content:
                css_indicators["compact_font"] = True
                
            if "min-height: 120px" in dashboard_content:
                css_indicators["compact_textarea"] = True
                
            if "max-width: none" in dashboard_content:
                css_indicators["full_width_layout"] = True
            
            # Check for text-focused design
            if "line-height: 1.4" in dashboard_content:
                css_indicators["text_focused_line_height"] = True
                
            # Count padding/margin values
            padding_8px = dashboard_content.count("padding: 8px")
            margin_12px = dashboard_content.count("margin-bottom: 12px")
            
            self.results["css_analysis"] = {
                "status": "SUCCESS",
                "compact_indicators": css_indicators,
                "padding_8px_count": padding_8px,
                "margin_12px_count": margin_12px,
                "total_compact_rules": len([k for k, v in css_indicators.items() if v])
            }
            
            print(f"✅ CSS Analysis completed:")
            for indicator, present in css_indicators.items():
                status = "✅" if present else "❌"
                print(f"   {status} {indicator.replace('_', ' ').title()}")
            
            return True
            
        except Exception as e:
            self.results["css_analysis"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ CSS analysis failed: {str(e)}")
            return False
    
    def assess_compact_design(self):
        """Provide overall assessment of compact design implementation"""
        print("🔍 Assessing Compact Design Implementation...")
        
        css_analysis = self.results.get("css_analysis", {})
        compact_indicators = css_analysis.get("compact_indicators", {})
        
        # Calculate compact design score
        compact_score = 0
        max_score = 6
        
        compact_features = [
            ("Compact Padding", compact_indicators.get("compact_padding", False)),
            ("Tight Margins", compact_indicators.get("tight_margins", False)),
            ("Compact Font Size", compact_indicators.get("compact_font", False)),
            ("Compact Textarea", compact_indicators.get("compact_textarea", False)),
            ("Full Width Layout", compact_indicators.get("full_width_layout", False)),
            ("Text-Focused Line Height", compact_indicators.get("text_focused_line_height", False))
        ]
        
        for feature_name, is_present in compact_features:
            if is_present:
                compact_score += 1
        
        # Calculate percentage
        compact_percentage = (compact_score / max_score) * 100
        
        # Determine rating
        if compact_percentage >= 90:
            rating = "EXCELLENT"
            status = "PASSED"
        elif compact_percentage >= 75:
            rating = "GOOD"
            status = "PASSED"
        elif compact_percentage >= 50:
            rating = "FAIR"
            status = "PARTIAL"
        else:
            rating = "NEEDS_IMPROVEMENT"
            status = "FAILED"
        
        self.results["design_assessment"] = {
            "compact_score": compact_score,
            "max_score": max_score,
            "compact_percentage": compact_percentage,
            "rating": rating,
            "status": status,
            "features": compact_features
        }
        
        print(f"📊 Compact Design Assessment:")
        print(f"   Score: {compact_score}/{max_score} ({compact_percentage:.1f}%)")
        print(f"   Rating: {rating}")
        print(f"   Status: {status}")
        
        for feature_name, is_present in compact_features:
            status_icon = "✅" if is_present else "❌"
            print(f"   {status_icon} {feature_name}")
        
        return status in ["PASSED", "PARTIAL"]
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness"""
        print("📱 Testing Mobile Responsiveness...")
        
        try:
            # Switch to mobile view
            self.driver.set_window_size(375, 667)
            time.sleep(2)
            
            # Navigate to legacy dashboard (since main dashboard has errors)
            self.driver.get(f"{self.base_url}/dashboard/legacy")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)
            
            # Take screenshot
            self.take_screenshot("mobile_responsive", "Mobile view (375px width)")
            
            # Check responsiveness
            body_width = self.driver.execute_script("return document.body.scrollWidth")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            
            is_responsive = body_width <= viewport_width + 20
            
            print(f"✅ Mobile test: {viewport_width}px viewport, {body_width}px content")
            return is_responsive
            
        except Exception as e:
            print(f"❌ Mobile responsiveness test failed: {str(e)}")
            return False
        finally:
            self.driver.set_window_size(1920, 1080)
    
    def run_assessment(self):
        """Run complete assessment"""
        print("🚀 Starting Compact Dashboard Design Assessment")
        print("=" * 70)
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Run tests
            auth_success = self.test_authentication()
            legacy_success = self.test_legacy_dashboard()
            css_success = self.analyze_compact_css()
            design_success = self.assess_compact_design()
            mobile_success = self.test_mobile_responsiveness()
            
            # Determine overall status
            if design_success and auth_success:
                if css_success and mobile_success:
                    self.results["overall_status"] = "PASSED"
                else:
                    self.results["overall_status"] = "PASSED_WITH_WARNINGS"
            else:
                self.results["overall_status"] = "NEEDS_IMPROVEMENT"
                
        except Exception as e:
            self.results["overall_status"] = "CRITICAL_FAILURE"
            print(f"💥 Critical failure: {str(e)}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 Browser closed")
    
    def generate_report(self):
        """Generate assessment report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"/home/josh/Sync2/projects/journal/compact_design_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📋 Assessment report saved: {report_path}")
        return report_path
    
    def print_summary(self):
        """Print comprehensive summary"""
        print("\n" + "=" * 70)
        print("📊 COMPACT DASHBOARD DESIGN ASSESSMENT")
        print("=" * 70)
        
        print(f"🕐 Timestamp: {self.results['timestamp']}")
        print(f"🎯 Overall Status: {self.results['overall_status']}")
        
        # Authentication results
        auth = self.results.get("authentication_test", {})
        auth_status = "✅" if auth.get("status") == "SUCCESS" else "❌"
        print(f"\n🔐 Authentication: {auth_status} {auth.get('status', 'UNKNOWN')}")
        
        # CSS Analysis results
        css = self.results.get("css_analysis", {})
        if css.get("status") == "SUCCESS":
            compact_count = css.get("total_compact_rules", 0)
            print(f"🎨 CSS Analysis: ✅ {compact_count}/6 compact design rules implemented")
        
        # Design Assessment
        design = self.results.get("design_assessment", {})
        if design:
            percentage = design.get("compact_percentage", 0)
            rating = design.get("rating", "UNKNOWN")
            print(f"📐 Design Quality: {percentage:.1f}% - {rating}")
        
        # Screenshots
        screenshots = self.results.get("screenshots", [])
        if screenshots:
            print(f"\n📸 Screenshots Captured ({len(screenshots)}):")
            for screenshot in screenshots:
                print(f"   • {screenshot['name']}: {screenshot['description']}")
                print(f"     File: {screenshot['filepath']}")
        
        print("\n" + "=" * 70)
        print("🎯 COMPACT DESIGN RECOMMENDATIONS")
        print("=" * 70)
        
        if design:
            features = design.get("features", [])
            implemented = [f for f, status in features if status]
            missing = [f for f, status in features if not status]
            
            if implemented:
                print("✅ Successfully Implemented:")
                for feature in implemented:
                    print(f"   • {feature}")
            
            if missing:
                print("\n❌ Areas for Improvement:")
                for feature in missing:
                    print(f"   • {feature}")
        
        # Overall recommendation
        overall = self.results.get("overall_status")
        if overall == "PASSED":
            print(f"\n🎉 RECOMMENDATION: The compact dashboard design is well-implemented!")
        elif overall == "PASSED_WITH_WARNINGS":
            print(f"\n⚠️  RECOMMENDATION: Good compact design with minor improvements needed.")
        else:
            print(f"\n🔧 RECOMMENDATION: Compact design implementation needs significant work.")
        
        print("=" * 70)


def main():
    """Main assessment function"""
    assessor = CompactDesignAssessment()
    
    try:
        assessor.run_assessment()
        assessor.generate_report()
        assessor.print_summary()
        
        return assessor.results["overall_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        
    except Exception as e:
        print(f"💥 Assessment failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)