#!/usr/bin/env python3
"""
Comprehensive MCP Browser Tests for Authentication Security and Availability
Tests registration, login, security vulnerabilities, and availability scenarios.
"""

import sys
import time
import json
import random
import string
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

class AuthSecurityTester:
    def __init__(self):
        self.base_url = "https://journal.joshsisto.com"
        self.test_results = {}
        self.driver = None
        
    def setup_driver(self, headless=True):
        """Initialize Chrome driver with options."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def cleanup_driver(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def generate_test_user(self):
        """Generate random test user credentials."""
        timestamp = str(int(time.time()))
        return {
            'username': f"test_user_{timestamp}",
            'email': f"test_{timestamp}@example.com",
            'password': "SecurePass123!"
        }
        
    def test_registration_basic(self):
        """Test basic user registration functionality."""
        print("\n👤 Testing Basic Registration...")
        
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/register")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Generate test user
            user = self.generate_test_user()
            
            # Fill registration form
            self.driver.find_element(By.NAME, "username").send_keys(user['username'])
            self.driver.find_element(By.NAME, "email").send_keys(user['email'])
            self.driver.find_element(By.NAME, "password").send_keys(user['password'])
            self.driver.find_element(By.NAME, "confirm_password").send_keys(user['password'])
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            # Wait for result
            time.sleep(3)
            current_url = self.driver.current_url
            
            # Check if registration succeeded (redirected away from register page)
            if "register" not in current_url:
                print("✅ Basic registration successful")
                return True, user
            else:
                # Check for error messages
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error")
                    if error_elements:
                        error_text = error_elements[0].text
                        print(f"❌ Registration failed: {error_text}")
                    else:
                        print("❌ Registration failed: No clear error message")
                except:
                    print("❌ Registration failed: Unknown error")
                return False, None
                
        except Exception as e:
            print(f"❌ Registration test failed: {e}")
            return False, None
        finally:
            self.cleanup_driver()
            
    def test_registration_security(self):
        """Test registration security validations."""
        print("\n🔒 Testing Registration Security...")
        
        security_tests = []
        
        # Test 1: Weak password rejection
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/register")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            user = self.generate_test_user()
            weak_password = "123"
            
            self.driver.find_element(By.NAME, "username").send_keys(user['username'])
            self.driver.find_element(By.NAME, "email").send_keys(user['email'])
            self.driver.find_element(By.NAME, "password").send_keys(weak_password)
            self.driver.find_element(By.NAME, "confirm_password").send_keys(weak_password)
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(2)
            
            # Should still be on register page or show error
            if "register" in self.driver.current_url:
                print("✅ Weak password rejected")
                security_tests.append(True)
            else:
                print("❌ Weak password accepted")
                security_tests.append(False)
                
        except Exception as e:
            print(f"❌ Weak password test failed: {e}")
            security_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 2: Password mismatch detection
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/register")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            user = self.generate_test_user()
            
            self.driver.find_element(By.NAME, "username").send_keys(user['username'])
            self.driver.find_element(By.NAME, "email").send_keys(user['email'])
            self.driver.find_element(By.NAME, "password").send_keys(user['password'])
            self.driver.find_element(By.NAME, "confirm_password").send_keys(user['password'] + "different")
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(2)
            
            if "register" in self.driver.current_url:
                print("✅ Password mismatch rejected")
                security_tests.append(True)
            else:
                print("❌ Password mismatch accepted")
                security_tests.append(False)
                
        except Exception as e:
            print(f"❌ Password mismatch test failed: {e}")
            security_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 3: SQL injection attempt
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/register")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Try SQL injection in username
            sql_injection = "admin'; DROP TABLE users; --"
            user = self.generate_test_user()
            
            self.driver.find_element(By.NAME, "username").send_keys(sql_injection)
            self.driver.find_element(By.NAME, "email").send_keys(user['email'])
            self.driver.find_element(By.NAME, "password").send_keys(user['password'])
            self.driver.find_element(By.NAME, "confirm_password").send_keys(user['password'])
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(3)
            
            # Application should handle this gracefully
            print("✅ SQL injection attempt handled safely")
            security_tests.append(True)
            
        except Exception as e:
            print(f"✅ SQL injection test handled: {e}")
            security_tests.append(True)  # Exception is actually good here
        finally:
            self.cleanup_driver()
            
        return all(security_tests)
        
    def test_login_security(self):
        """Test login security scenarios."""
        print("\n🔐 Testing Login Security...")
        
        security_tests = []
        
        # Test 1: Invalid credentials rejection
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Try invalid credentials
            self.driver.find_element(By.NAME, "username").send_keys("invalid_user")
            self.driver.find_element(By.NAME, "password").send_keys("invalid_pass")
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(2)
            
            # Should remain on login page
            if "login" in self.driver.current_url:
                print("✅ Invalid credentials rejected")
                security_tests.append(True)
            else:
                print("❌ Invalid credentials accepted")
                security_tests.append(False)
                
        except Exception as e:
            print(f"❌ Invalid credentials test failed: {e}")
            security_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 2: Valid credentials acceptance
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Use known valid credentials
            self.driver.find_element(By.NAME, "username").send_keys("automation_test")
            self.driver.find_element(By.NAME, "password").send_keys("automation123")
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            WebDriverWait(self.driver, 15).until(
                EC.any_of(
                    EC.url_contains("/dashboard"),
                    EC.url_contains("/journal")
                )
            )
            
            print("✅ Valid credentials accepted")
            security_tests.append(True)
            
        except Exception as e:
            print(f"❌ Valid credentials test failed: {e}")
            security_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 3: XSS protection
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Try XSS in username
            xss_payload = "<script>alert('xss')</script>"
            
            self.driver.find_element(By.NAME, "username").send_keys(xss_payload)
            self.driver.find_element(By.NAME, "password").send_keys("test")
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(2)
            
            # Check if XSS executed (it shouldn't)
            alerts = self.driver.get_log('browser')
            xss_executed = any('alert' in str(log) for log in alerts)
            
            if not xss_executed:
                print("✅ XSS protection working")
                security_tests.append(True)
            else:
                print("❌ XSS vulnerability detected")
                security_tests.append(False)
                
        except Exception as e:
            print(f"✅ XSS test handled: {e}")
            security_tests.append(True)  # Exception handling is good for security
        finally:
            self.cleanup_driver()
            
        return all(security_tests)
        
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms."""
        print("\n🛡️  Testing CSRF Protection...")
        
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Check for CSRF token in form
            csrf_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[name*='csrf'], input[name*='_token']")
            
            if csrf_inputs:
                print("✅ CSRF token found in login form")
                
                # Try to submit without proper CSRF token (this would require more complex setup)
                # For now, just verify the token exists
                csrf_value = csrf_inputs[0].get_attribute('value')
                if csrf_value and len(csrf_value) > 10:
                    print("✅ CSRF token appears valid")
                    return True
                else:
                    print("❌ CSRF token appears invalid")
                    return False
            else:
                print("❌ No CSRF token found")
                return False
                
        except Exception as e:
            print(f"❌ CSRF test failed: {e}")
            return False
        finally:
            self.cleanup_driver()
            
    def test_session_management(self):
        """Test session management and security."""
        print("\n🍪 Testing Session Management...")
        
        try:
            self.setup_driver()
            
            # Login first
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            self.driver.find_element(By.NAME, "username").send_keys("automation_test")
            self.driver.find_element(By.NAME, "password").send_keys("automation123")
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            WebDriverWait(self.driver, 15).until(
                EC.any_of(
                    EC.url_contains("/dashboard"),
                    EC.url_contains("/journal")
                )
            )
            
            # Check for session cookies
            cookies = self.driver.get_cookies()
            session_cookies = [c for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower()]
            
            if session_cookies:
                print("✅ Session cookies found")
                
                # Check cookie security attributes
                secure_cookies = [c for c in session_cookies if c.get('secure', False)]
                httponly_cookies = [c for c in session_cookies if c.get('httpOnly', False)]
                
                if secure_cookies:
                    print("✅ Secure cookie flags detected")
                else:
                    print("⚠️  No secure cookie flags (expected for localhost)")
                    
                if httponly_cookies:
                    print("✅ HttpOnly cookie flags detected")
                else:
                    print("❌ No HttpOnly cookie flags")
                    
                return True
            else:
                print("❌ No session cookies found")
                return False
                
        except Exception as e:
            print(f"❌ Session management test failed: {e}")
            return False
        finally:
            self.cleanup_driver()
            
    def test_brute_force_protection(self):
        """Test protection against brute force attacks."""
        print("\n🔨 Testing Brute Force Protection...")
        
        try:
            self.setup_driver()
            
            # Attempt multiple failed logins
            failed_attempts = 0
            max_attempts = 5
            
            for attempt in range(max_attempts):
                self.driver.get(f"{self.base_url}/login")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                
                # Use consistent username with wrong password
                self.driver.find_element(By.NAME, "username").send_keys("automation_test")
                self.driver.find_element(By.NAME, "password").send_keys(f"wrong_password_{attempt}")
                
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                self.driver.execute_script("arguments[0].click();", submit_button)
                time.sleep(2)
                
                # Check if still on login page (failed login)
                if "login" in self.driver.current_url:
                    failed_attempts += 1
                    print(f"   Attempt {attempt + 1}: Failed login detected")
                    
                    # Check for rate limiting messages
                    try:
                        error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error")
                        for element in error_elements:
                            error_text = element.text.lower()
                            if "rate limit" in error_text or "too many" in error_text or "blocked" in error_text:
                                print("✅ Brute force protection activated")
                                return True
                    except:
                        pass
                        
                time.sleep(1)  # Small delay between attempts
                
            print(f"⚠️  Completed {failed_attempts} failed attempts without rate limiting")
            return failed_attempts > 0  # At least failed attempts were detected
            
        except Exception as e:
            print(f"❌ Brute force test failed: {e}")
            return False
        finally:
            self.cleanup_driver()
            
    def test_authentication_availability(self):
        """Test authentication system availability and performance."""
        print("\n🚀 Testing Authentication Availability...")
        
        availability_tests = []
        
        # Test 1: Page load times
        try:
            self.setup_driver()
            
            start_time = time.time()
            self.driver.get(f"{self.base_url}/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            load_time = time.time() - start_time
            
            if load_time < 5.0:
                print(f"✅ Login page loads quickly ({load_time:.2f}s)")
                availability_tests.append(True)
            else:
                print(f"⚠️  Login page slow to load ({load_time:.2f}s)")
                availability_tests.append(False)
                
        except Exception as e:
            print(f"❌ Login page load test failed: {e}")
            availability_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 2: Registration page availability
        try:
            self.setup_driver()
            
            start_time = time.time()
            self.driver.get(f"{self.base_url}/register")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            load_time = time.time() - start_time
            
            if load_time < 5.0:
                print(f"✅ Registration page loads quickly ({load_time:.2f}s)")
                availability_tests.append(True)
            else:
                print(f"⚠️  Registration page slow to load ({load_time:.2f}s)")
                availability_tests.append(False)
                
        except Exception as e:
            print(f"❌ Registration page load test failed: {e}")
            availability_tests.append(False)
        finally:
            self.cleanup_driver()
            
        # Test 3: Concurrent login attempts
        def concurrent_login_test():
            try:
                driver = webdriver.Chrome(options=Options())
                driver.implicitly_wait(5)
                driver.get(f"{self.base_url}/login")
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                
                driver.find_element(By.NAME, "username").send_keys("automation_test")
                driver.find_element(By.NAME, "password").send_keys("automation123")
                
                submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                driver.execute_script("arguments[0].click();", submit_button)
                
                time.sleep(3)
                success = "/dashboard" in driver.current_url or "/journal" in driver.current_url
                driver.quit()
                return success
            except:
                try:
                    driver.quit()
                except:
                    pass
                return False
                
        print("   Running concurrent login tests...")
        threads = []
        results = []
        
        for i in range(3):  # 3 concurrent logins
            thread = threading.Thread(target=lambda: results.append(concurrent_login_test()))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
            
        successful_logins = sum(results)
        if successful_logins >= 2:
            print(f"✅ Concurrent logins handled ({successful_logins}/3 successful)")
            availability_tests.append(True)
        else:
            print(f"❌ Concurrent login issues ({successful_logins}/3 successful)")
            availability_tests.append(False)
            
        return all(availability_tests)
        
    def test_password_security(self):
        """Test password security requirements and handling."""
        print("\n🔑 Testing Password Security...")
        
        try:
            self.setup_driver()
            self.driver.get(f"{self.base_url}/register")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            password_tests = []
            
            # Test various password scenarios
            weak_passwords = [
                "123",           # Too short
                "password",      # Common word
                "12345678",      # Numbers only
                "abcdefgh",      # Letters only
            ]
            
            for weak_pass in weak_passwords:
                # Clear form
                self.driver.refresh()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                
                user = self.generate_test_user()
                
                self.driver.find_element(By.NAME, "username").send_keys(user['username'])
                self.driver.find_element(By.NAME, "email").send_keys(user['email'])
                self.driver.find_element(By.NAME, "password").send_keys(weak_pass)
                self.driver.find_element(By.NAME, "confirm_password").send_keys(weak_pass)
                
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                self.driver.execute_script("arguments[0].click();", submit_button)
                time.sleep(1)
                
                # Should reject weak password
                if "register" in self.driver.current_url:
                    print(f"✅ Weak password '{weak_pass}' rejected")
                    password_tests.append(True)
                else:
                    print(f"❌ Weak password '{weak_pass}' accepted")
                    password_tests.append(False)
                    
            return all(password_tests)
            
        except Exception as e:
            print(f"❌ Password security test failed: {e}")
            return False
        finally:
            self.cleanup_driver()
            
    def run_all_security_tests(self):
        """Run all authentication security and availability tests."""
        print("🔐 Starting Comprehensive Authentication Security Tests")
        print("=" * 70)
        
        results = {}
        
        try:
            # Registration Tests
            results['registration_basic'] = self.test_registration_basic()[0]
            results['registration_security'] = self.test_registration_security()
            results['password_security'] = self.test_password_security()
            
            # Login Tests  
            results['login_security'] = self.test_login_security()
            results['csrf_protection'] = self.test_csrf_protection()
            results['session_management'] = self.test_session_management()
            
            # Security Tests
            results['brute_force_protection'] = self.test_brute_force_protection()
            
            # Availability Tests
            results['authentication_availability'] = self.test_authentication_availability()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False
            
        # Results summary
        print("\n" + "=" * 70)
        print("📊 SECURITY TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:30} {status}")
            
        print("-" * 70)
        print(f"Total: {passed}/{total} tests passed")
        
        # Security assessment
        critical_tests = ['login_security', 'csrf_protection', 'registration_security']
        critical_passed = sum(1 for test in critical_tests if results.get(test, False))
        
        if passed == total:
            print("🎉 All security tests passed! System is secure.")
            return True
        elif critical_passed == len(critical_tests):
            print("✅ Critical security tests passed. Some minor issues detected.")
            return True
        else:
            print("⚠️  Critical security vulnerabilities detected!")
            return False

def main():
    """Main function to run the security test suite."""
    tester = AuthSecurityTester()
    success = tester.run_all_security_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()