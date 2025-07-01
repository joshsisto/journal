# Testing Guide for Journal Application

This guide explains how to integrate testing into your development workflow.

## Quick Reference

### Essential Commands
```bash
# Run tests before making changes
python3 run_tests.py quick

# Run tests after making changes
python3 run_tests.py auth      # If working on authentication
python3 run_tests.py journal   # If working on journal features
python3 run_tests.py ai        # If working on AI features

# Run all tests before committing
python3 run_tests.py all

# Run tests with coverage report
python3 run_tests.py coverage
```

### Test Categories
- **quick** - Basic configuration and page load tests (fast, always run)
- **auth** - Authentication, registration, login, logout tests
- **email** - Email verification, password reset tests
- **mfa** - Multi-factor authentication tests
- **journal** - Journal entry creation, editing, viewing tests
- **ai** - AI conversation and feature tests
- **csrf** - CSRF protection and security tests
- **all** - Complete test suite

## Development Workflow Integration

### 1. Before Starting Work
```bash
# Ensure tests are passing before you begin
python3 run_tests.py quick
```

### 2. While Developing
```bash
# Test the specific area you're working on
python3 run_tests.py auth       # For auth changes
python3 run_tests.py journal    # For journal changes
python3 run_tests.py ai         # For AI changes

# For quick feedback on specific tests
python3 -m pytest tests/unit/test_auth.py::TestLogin -v
```

### 3. Before Committing
```bash
# Run all tests to ensure nothing is broken
python3 run_tests.py all

# If tests pass, proceed with git workflow
git add .
git commit -m "Your commit message"
git push origin main
```

### 4. Production Deployment
```bash
# Full testing workflow before production
python3 run_tests.py coverage    # Generate coverage report
python3 run_tests.py all         # Ensure all tests pass
./backup.sh pre-deploy           # Create backup before deployment
python3 service_control.py reload # Restart production service
```

## Test-Driven Development (TDD)

### When Adding New Features
1. **Write test first** (if feature is complex)
2. **Run test** (should fail initially)
3. **Implement feature**
4. **Run test** (should pass)
5. **Refactor if needed**

### Example: Adding New Authentication Feature
```bash
# 1. Add test to tests/unit/test_auth.py
# 2. Run specific test to see it fail
python3 -m pytest tests/unit/test_auth.py::TestNewFeature::test_new_feature -v

# 3. Implement feature in routes.py or models.py
# 4. Run test again to see it pass
python3 -m pytest tests/unit/test_auth.py::TestNewFeature::test_new_feature -v

# 5. Run related tests to ensure no regressions
python3 run_tests.py auth
```

## Continuous Integration Setup

### Git Pre-commit Hook
The project already has a pre-commit hook for CSRF validation. You can add test running:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run CSRF validation (already existing)
python3 validate_csrf.py || exit 1

# Run quick tests before commit
echo "Running quick tests before commit..."
python3 run_tests.py quick || {
    echo "Tests failed! Please fix before committing."
    exit 1
}

echo "All tests passed!"
```

### GitHub Actions (Optional)
You could add `.github/workflows/tests.yml`:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: python3 run_tests.py all
```

## When Tests Fail

### 1. Identify the Scope
```bash
# Check which area is affected
python3 run_tests.py quick      # Basic infrastructure
python3 run_tests.py auth       # Authentication issues
python3 run_tests.py journal    # Journal functionality
```

### 2. Run Specific Tests for Details
```bash
# Get detailed output for failing tests
python3 -m pytest tests/unit/test_auth.py::TestLogin::test_failed_test -vvs
```

### 3. Common Failure Patterns

**CSRF Token Issues:**
- Check if you added new forms without CSRF tokens
- Run: `python3 validate_csrf.py`

**Database Issues:**
- Check if you changed models without updating tests
- Look for missing test data or fixtures

**Import Issues:**
- Check if you moved or renamed files
- Update import statements in test files

**Permission Issues:**
- Check if you changed authentication logic
- Update test expectations accordingly

## Performance and Coverage

### Test Performance
```bash
# Show test execution times
python3 -m pytest tests/unit/ --durations=10

# Run tests in parallel (faster)
python3 -m pytest tests/unit/ -n auto
```

### Coverage Reports
```bash
# Generate HTML coverage report
python3 run_tests.py coverage

# View coverage report
open htmlcov/index.html  # or navigate to file in browser
```

### Coverage Goals
- **Overall coverage**: Aim for 80%+
- **Critical paths**: Authentication, data handling should be 90%+
- **New features**: All new code should have tests

## Testing Best Practices

### 1. Test Organization
- **Unit tests**: Test individual functions/methods (`tests/unit/`)
- **Integration tests**: Test component interactions (future: `tests/integration/`)
- **Test naming**: Use descriptive names (`test_user_login_with_valid_credentials`)

### 2. Test Data
- Use fixtures for common test data (`conftest.py`)
- Keep tests independent (each test should work alone)
- Clean up after tests (handled automatically by fixtures)

### 3. Test Scope
- **Test one thing**: Each test should verify one behavior
- **Test edge cases**: Empty inputs, invalid data, boundary conditions
- **Test error conditions**: What happens when things go wrong

### 4. Mocking
- Mock external services (email, AI APIs)
- Mock slow operations
- Don't mock the code you're testing

## Troubleshooting

### Common Issues

**Tests hang or timeout:**
```bash
# Run with timeout
python3 -m pytest tests/unit/ --timeout=30
```

**Database connection errors:**
```bash
# Clean up test database
rm -f test_journal.db
python3 run_tests.py quick
```

**Import errors:**
```bash
# Check Python path
export PYTHONPATH=/home/josh/Sync2/projects/journal:$PYTHONPATH
python3 run_tests.py quick
```

**Rate limiting in tests:**
- Tests should automatically disable rate limiting
- If not, check `RATELIMIT_ENABLED = False` in test config

### Getting Help

1. **Check test output**: Always read the full error message
2. **Run single test**: Isolate the problem with `-k test_name`
3. **Check fixtures**: Ensure test data is set up correctly
4. **Verify imports**: Make sure all required modules are available

## Integration with Your Workflow

### Daily Development
```bash
# Morning routine
git pull origin main
python3 run_tests.py quick

# During development (after each logical change)
python3 run_tests.py [relevant-category]

# Before lunch/end of day
python3 run_tests.py all
```

### Feature Development
```bash
# Starting new feature
git checkout -b feature/new-feature
python3 run_tests.py all  # Ensure clean start

# During development
python3 run_tests.py [category]  # Test relevant area

# Before merging
python3 run_tests.py all
git merge main  # or create PR
```

### Production Deployment
```bash
# Full pre-deployment check
python3 run_tests.py coverage
./backup.sh pre-deploy
# Only deploy if all tests pass
python3 service_control.py reload
```

This testing workflow will help you catch issues early, maintain code quality, and deploy with confidence!