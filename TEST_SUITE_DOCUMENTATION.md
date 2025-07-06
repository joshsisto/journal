# Test Suite Documentation
**Journal Application - Comprehensive Testing Guide**  
**Date:** July 6, 2025

## Overview

This document provides complete instructions for running and understanding the journal application's test suite. The test suite uses pytest with PostgreSQL for database testing to match the production environment.

## Test Suite Structure

### Directory Layout
```
tests/
├── conftest.py              # Test configuration and fixtures
├── .env.test               # Test environment variables
├── unit/                   # Unit tests
│   ├── test_auth.py        # Authentication tests
│   ├── test_csrf.py        # CSRF protection tests
│   ├── test_email.py       # Email functionality tests
│   ├── test_journal_entries.py  # Journal entry tests
│   ├── test_security_validation.py  # Security tests
│   ├── test_ai_features.py # AI integration tests
│   ├── test_location_*.py  # Location/weather tests
│   └── test_*.py          # Additional unit tests
├── functional/             # End-to-end tests
│   ├── test_guided_journal_e2e.py
│   └── test_location_search_e2e.py
└── integration/            # Integration tests
```

### Test Categories
- **Unit Tests:** Individual component testing
- **Functional Tests:** End-to-end browser automation
- **Integration Tests:** Multi-component interaction testing
- **Security Tests:** CSRF, validation, and security feature testing

## Prerequisites

### 1. Environment Setup
Ensure you have the following installed:
- Python 3.10+
- PostgreSQL 14+ (running and accessible)
- All project dependencies: `pip install -r requirements.txt`

### 2. Database Configuration
The test suite uses PostgreSQL to match production. Ensure:
- PostgreSQL service is running
- Database user `journal_user` exists with password access
- Main database `journal_db` is accessible
- Test environment variables are configured

### 3. Environment Variables
Create or verify `.env.test` file exists with:
```bash
# Test Database Settings
TEST_DB_USER=journal_user
TEST_DB_PASSWORD=eNP*h^S%1U@KteLeOnFfFfwu
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=journal_db

# Test-specific settings
TESTING=true
WTF_CSRF_ENABLED=false
MAIL_SUPPRESS_SEND=true
```

## Running Tests

### Quick Start
```bash
# Navigate to project directory
cd /home/josh/Sync2/projects/journal

# Run the basic quick tests (recommended first run)
python3 run_tests.py quick

# Run all unit tests
python3 run_tests.py all

# Run comprehensive test suite (includes security and functional tests)
python3 run_comprehensive_tests.py
```

### Standard Test Commands

#### 1. Using the Test Runner Scripts
```bash
# Quick configuration tests only
python3 run_tests.py quick

# Run specific category
python3 run_tests.py auth      # Authentication tests
python3 run_tests.py email     # Email functionality tests  
python3 run_tests.py csrf      # CSRF protection tests
python3 run_tests.py journal   # Journal entry tests
python3 run_tests.py ai        # AI feature tests
python3 run_tests.py mfa       # Multi-factor authentication tests

# Run all unit tests
python3 run_tests.py all

# Run with coverage report
python3 run_tests.py coverage
```

#### 2. Using pytest Directly
```bash
# Run all unit tests
python3 -m pytest tests/unit/ -v

# Run specific test file
python3 -m pytest tests/unit/test_auth.py -v

# Run specific test class
python3 -m pytest tests/unit/test_auth.py::TestRegistration -v

# Run specific test method
python3 -m pytest tests/unit/test_auth.py::TestRegistration::test_registration_page_loads -v

# Run with minimal output
python3 -m pytest tests/unit/ -q --tb=no --disable-warnings

# Run with detailed failure information
python3 -m pytest tests/unit/test_auth.py -v --tb=short

# Run with coverage
python3 -m pytest tests/unit/ --cov=. --cov-report=html
```

#### 3. Comprehensive Testing
```bash
# Run the full comprehensive test suite (includes security validation)
python3 run_comprehensive_tests.py

# Run functional/browser tests
python3 -m pytest tests/functional/ -v

# Run security validation tests specifically
python3 -m pytest tests/unit/test_security_validation.py -v
python3 -m pytest tests/unit/test_csrf.py -v
```

### Test Filtering and Options

#### Running Tests by Category (using pytest marks)
```bash
# Run only unit tests
python3 -m pytest -m unit -v

# Run only email-related tests
python3 -m pytest -m email -v

# Run only CSRF tests
python3 -m pytest -m csrf -v

# Run only journal-related tests  
python3 -m pytest -m journal -v
```

#### Common pytest Options
```bash
# Verbose output with test names
python3 -m pytest tests/unit/ -v

# Quiet output (just dots)
python3 -m pytest tests/unit/ -q

# Stop on first failure
python3 -m pytest tests/unit/ -x

# Show only failing tests in output
python3 -m pytest tests/unit/ --tb=no -q

# Run tests in parallel (if pytest-xdist installed)
python3 -m pytest tests/unit/ -n 4

# Disable warnings
python3 -m pytest tests/unit/ --disable-warnings

# Show print statements
python3 -m pytest tests/unit/ -s
```

## Understanding Test Output

### Success Output Example
```
============================= test session starts ==============================
collected 169 items

tests/unit/test_auth.py::TestRegistration::test_registration_page_loads PASSED [ 1%]
tests/unit/test_csrf.py::TestCSRFConfiguration::test_csrf_configuration_values PASSED [ 2%]
...

======================== 169 passed, 6 warnings in 45.2s ======================
```

### Failure Output Example
```
tests/unit/test_auth.py::TestRegistration::test_registration_invalid_email FAILED [ 5%]

=================================== FAILURES ===================================
________________________ test_registration_invalid_email ________________________

    def test_registration_invalid_email(self):
>       assert response.status_code == 400
E       assert 200 == 400

tests/unit/test_auth.py:123: AssertionError
```

### Current Test Status (as of July 6, 2025)
```
Total Tests: 317
✅ Passing: 169 (53%)
❌ Failing: 141 (45%)  
🔴 Errors: 6 (2%)
⏭️ Skipped: 1 (0%)
```

## Test Configuration Details

### Database Setup
The test suite uses PostgreSQL with transaction isolation:
- Each test runs in its own transaction
- All changes are rolled back after each test
- Unique test data generated using UUIDs to prevent conflicts
- Savepoint-based nested transactions for complex scenarios

### Mock Services
Standard mock fixtures are available:
- `mock_mail` - Email sending functionality
- `mock_email_service` - Email service functions
- `mock_ai_service` - AI response generation
- `mock_weather_service` - Weather API calls
- `mock_geocoding_service` - Location geocoding

### Test Data Generation
- User fixtures automatically generate unique usernames/emails
- Test data uses UUID suffixes to prevent unique constraint violations
- Fixtures are scoped to function level for proper isolation

## Debugging Test Failures

### Common Issues and Solutions

#### 1. Database Connection Errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database access
PGPASSWORD='eNP*h^S%1U@KteLeOnFfFfwu' psql -U journal_user -h localhost -d journal_db -c "SELECT 1;"
```

#### 2. Import Errors
```bash
# Verify Python path and dependencies
python3 -c "import flask, sqlalchemy, pytest; print('Dependencies OK')"

# Check for circular imports
python3 -c "from app import create_app; print('App import OK')"
```

#### 3. Unique Constraint Violations
- Tests should use the provided fixtures that generate unique data
- If seeing "duplicate key value" errors, check fixture usage

#### 4. Session/Transaction Issues
- Tests may fail when run in groups but pass individually
- This indicates session isolation issues - check db_session fixture usage

### Debug Specific Test Categories

#### Authentication Tests
```bash
# Run with verbose output to see exact failure points
python3 -m pytest tests/unit/test_auth.py -v -s

# Test specific registration scenario
python3 -m pytest tests/unit/test_auth.py::TestRegistration::test_successful_registration_with_email -v
```

#### CSRF Tests
```bash
# Validate CSRF token handling
python3 validate_csrf.py

# Run CSRF tests with output
python3 -m pytest tests/unit/test_csrf.py -v
```

#### Email Tests
```bash
# Test email functionality (many tests require mocking)
python3 -m pytest tests/unit/test_email.py -v

# Run individual email test to avoid isolation issues
python3 -m pytest tests/unit/test_email.py::TestResendVerification::test_resend_verification_no_email -v
```

## Test Performance

### Typical Run Times
- **Quick tests:** ~30 seconds (3 basic configuration tests)
- **Category tests:** ~1-3 minutes per category
- **All unit tests:** ~60-90 seconds (317 tests)
- **Comprehensive suite:** ~3-5 minutes (includes functional tests)

### Performance Optimization
- PostgreSQL adds overhead compared to SQLite but provides production accuracy
- Parallel execution can be enabled with pytest-xdist
- Transaction isolation ensures test independence but increases time

## Continuous Integration

### Pre-commit Testing
```bash
# Install comprehensive pre-commit hook
cp hooks/pre-commit-comprehensive .git/hooks/pre-commit

# Manual pre-commit check
python3 run_comprehensive_tests.py
```

### Health Checks
```bash
# Application health check
python3 check_app_health.py

# AI conversation health check  
python3 ai_conversation_health_check.py

# Deploy with health verification
python3 deploy_changes.py
```

## Maintenance

### Adding New Tests
1. Place unit tests in `tests/unit/test_<category>.py`
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_<functionality>_<scenario>`
4. Add appropriate pytest marks for categorization

### Updating Test Configuration
- Modify `tests/conftest.py` for fixture changes
- Update `.env.test` for environment variables
- Modify `pytest.ini` for pytest configuration

### Test Data Management
- Use provided fixtures that generate unique data
- Avoid hardcoded test data that might conflict
- Leverage mock fixtures for external services

## Troubleshooting

### Getting Help
```bash
# Check pytest help
python3 -m pytest --help

# Check available fixtures
python3 -m pytest --fixtures

# Check available marks
python3 -m pytest --markers
```

### Common Error Patterns
1. **Import Errors:** Check Python path and dependencies
2. **Database Errors:** Verify PostgreSQL connection and permissions
3. **Unique Constraints:** Use provided fixtures with UUID generation
4. **Session Issues:** Check proper usage of db_session fixture
5. **Mock Errors:** Verify mock fixture usage and patch targets

### Performance Issues
- Use `-q` flag for quieter output
- Consider running specific categories instead of full suite
- Check database performance if tests are unusually slow

---

**Last Updated:** July 6, 2025  
**Test Suite Version:** PostgreSQL-aligned with comprehensive infrastructure fixes  
**Success Rate:** 53% (169/317 tests passing)