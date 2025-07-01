#!/usr/bin/env python3
"""
Test runner script for journal application.

This script provides easy ways to run tests with proper configuration.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode == 0


def main():
    """Main test runner function."""
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("Journal Application Test Runner")
    print("="*40)
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✓ pytest {pytest.__version__} is available")
    except ImportError:
        print("✗ pytest is not installed. Run: pip install -r requirements-dev.txt")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path('pytest.ini').exists():
        print("✗ pytest.ini not found. Make sure you're in the project root.")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "quick"
    
    success = True
    
    if test_type == "quick":
        print("\nRunning quick tests (configuration and basic functionality)...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_csrf.py::TestCSRFConfiguration -v",
            "CSRF Configuration Tests"
        )
        success &= run_command(
            "python3 -m pytest tests/unit/test_csrf.py::TestCSRFTokenGeneration -v",
            "CSRF Token Generation Tests"
        )
        success &= run_command(
            "python3 -m pytest tests/unit/test_auth.py::TestRegistration::test_registration_page_loads -v",
            "Basic Page Load Test"
        )
        
    elif test_type == "auth":
        print("\nRunning authentication tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_auth.py -v",
            "All Authentication Tests"
        )
        
    elif test_type == "csrf":
        print("\nRunning CSRF protection tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_csrf.py -v",
            "All CSRF Tests"
        )
        
    elif test_type == "email":
        print("\nRunning email functionality tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_email.py -v",
            "All Email Tests"
        )
        
    elif test_type == "mfa":
        print("\nRunning MFA tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_mfa.py -v",
            "All MFA Tests"
        )
        
    elif test_type == "journal":
        print("\nRunning journal entry tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_journal_entries.py -v",
            "All Journal Entry Tests"
        )
        
    elif test_type == "ai":
        print("\nRunning AI feature tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/test_ai_features.py -v",
            "All AI Feature Tests"
        )
        
    elif test_type == "all":
        print("\nRunning all unit tests...")
        success &= run_command(
            "python3 -m pytest tests/unit/ -v",
            "All Unit Tests"
        )
        
    elif test_type == "coverage":
        print("\nRunning tests with coverage report...")
        success &= run_command(
            "python3 -m pytest tests/unit/ --cov=. --cov-report=html --cov-report=term",
            "Tests with Coverage"
        )
        
    elif test_type == "help":
        print_help()
        return
        
    else:
        print(f"Unknown test type: {test_type}")
        print_help()
        sys.exit(1)
    
    # Print results
    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check the output above.")
        sys.exit(1)


def print_help():
    """Print help information."""
    print("""
Usage: python3 run_tests.py [test_type]

Test types:
  quick      - Run quick tests (default)
  auth       - Run authentication tests
  csrf       - Run CSRF protection tests  
  email      - Run email functionality tests
  mfa        - Run MFA tests
  journal    - Run journal entry tests
  ai         - Run AI feature tests
  all        - Run all unit tests
  coverage   - Run tests with coverage report
  help       - Show this help

Examples:
  python3 run_tests.py quick
  python3 run_tests.py auth
  python3 run_tests.py coverage
""")


if __name__ == "__main__":
    main()