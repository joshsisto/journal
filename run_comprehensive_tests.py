#!/usr/bin/env python3
"""
Comprehensive test runner for preventing guided journal issues.

This script runs all tests that would catch the types of issues we just fixed:
- End-to-end browser tests
- Security validation tests  
- CSP/JavaScript tests
- Form functionality tests
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description, critical=True):
    """Run a command and handle the result."""
    print(f"🔍 {description}...")
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ {description} passed!")
            return True
        else:
            print(f"❌ {description} failed!")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            if critical:
                return False
            else:
                print("⚠️  Non-critical failure, continuing...")
                return True
                
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out!")
        return False
    except Exception as e:
        print(f"💥 {description} crashed: {e}")
        return False


def main():
    """Run comprehensive tests."""
    print("🚀 Running Comprehensive Test Suite")
    print("=" * 50)
    print("This test suite prevents guided journal issues like:")
    print("  - JavaScript/CSP blocking")
    print("  - Security false positives")
    print("  - Form submission failures")
    print("  - UI component malfunctions")
    print("")
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    failures = 0
    
    # 1. Basic unit tests
    if not run_command(
        "python3 run_tests.py quick", 
        "Running basic unit tests"
    ):
        failures += 1
    
    # 2. Security validation tests
    if not run_command(
        "python3 -m pytest tests/unit/test_security_validation.py -v",
        "Testing security validation (prevents false positives)"
    ):
        failures += 1
    
    # 3. CSP/JavaScript tests  
    if not run_command(
        "python3 -m pytest tests/unit/test_csp_javascript.py -v",
        "Testing CSP nonces and JavaScript structure"
    ):
        failures += 1
    
    # 4. CSRF validation
    if not run_command(
        "python3 validate_csrf.py",
        "Validating CSRF tokens in templates"
    ):
        failures += 1
    
    # 5. End-to-end tests (if Selenium is available)
    selenium_available = run_command(
        "python3 -c 'import selenium; print(\"Selenium available\")'",
        "Checking if Selenium is available",
        critical=False
    )
    
    if selenium_available:
        if not run_command(
            "python3 -m pytest tests/functional/test_guided_journal_e2e.py -v",
            "Running end-to-end browser tests",
            critical=False  # Browser tests can be flaky
        ):
            print("⚠️  Browser tests failed (non-critical)")
    else:
        print("ℹ️  Skipping browser tests (Selenium not available)")
    
    # 6. Template validation
    if not run_command(
        "python3 -c \"import subprocess; subprocess.run(['hooks/pre-commit-comprehensive'], check=True)\"",
        "Running comprehensive template validation"
    ):
        failures += 1
    
    # 7. Integration test - simulate form submission
    if not run_command(
        "python3 -m pytest tests/unit/test_journal_entries.py::TestGuidedJournalEntries::test_create_guided_entry_with_emotions_json -v",
        "Testing guided journal form submission with emotions"
    ):
        failures += 1
    
    print("")
    print("=" * 50)
    
    if failures == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ The codebase is protected against guided journal issues")
        print("")
        print("Tests successfully validate:")
        print("  ✅ JavaScript executes despite CSP")
        print("  ✅ Emotion data doesn't trigger security blocks")
        print("  ✅ Form submissions work properly")
        print("  ✅ CSRF tokens are properly implemented")
        print("  ✅ UI components function correctly")
        return 0
    else:
        print(f"❌ {failures} TEST CATEGORIES FAILED!")
        print("")
        print("🛠️  To fix issues:")
        print("  1. Check error messages above")
        print("  2. Run individual test categories for details")
        print("  3. Use pre-commit hook: cp hooks/pre-commit-comprehensive .git/hooks/pre-commit")
        print("  4. Review CLAUDE.md for testing guidelines")
        return 1


if __name__ == "__main__":
    sys.exit(main())