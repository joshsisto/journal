# Testing Reference Guide

Complete testing commands and workflows for the journal application.

## Quick Test Commands

### 🎯 **Comprehensive Testing** (Prevents Guided Journal Issues)
```bash
# Run all protection tests
python3 run_comprehensive_tests.py

# Test backup system
python3 backup_verification.py verify

# Install comprehensive pre-commit hook (one-time setup)
cp hooks/pre-commit-comprehensive .git/hooks/pre-commit
```

### 📋 **Standard Testing**
```bash
# Run quick tests
python3 run_tests.py quick

# Run category tests
python3 run_tests.py [auth|email|mfa|journal|ai|csrf]

# Run all tests
python3 run_tests.py all

# Run with coverage
python3 run_tests.py coverage

# Test specific file
python3 -m pytest tests/unit/test_auth.py -v
```

### 🏥 **Health Monitoring**
```bash
# AI conversation health check
./check_ai_health.sh
python3 ai_conversation_health_check.py

# Brief health check
./check_ai_health.sh brief
python3 ai_conversation_health_check.py --brief

# App health check
python3 check_app_health.py

# Backup system health
python3 backup_monitor.py check --brief
```

### 🔒 **Security & UI Testing**
```bash
# Test security validation
python3 -m pytest tests/unit/test_security_validation.py -v

# Test CSP/JavaScript
python3 -m pytest tests/unit/test_csp_javascript.py -v

# Test guided journal E2E
python3 -m pytest tests/functional/test_guided_journal_e2e.py -v

# Validate CSRF tokens
python3 validate_csrf.py
```

### 🚀 **MCP Browser Testing Framework** (Production Security Testing)
```bash
# Setup framework
./deploy_mcp_testing.sh setup

# Run security scan
./deploy_mcp_testing.sh security https://journal.joshsisto.com 5

# Run comprehensive suite
./deploy_mcp_testing.sh all https://journal.joshsisto.com 8

# Run fuzz testing
./deploy_mcp_testing.sh fuzz https://journal.joshsisto.com 3

# Run concurrency tests
./deploy_mcp_testing.sh concurrency https://journal.joshsisto.com 10

# Run login flow tests
./deploy_mcp_testing.sh login https://journal.joshsisto.com 3

# Check framework status
./deploy_mcp_testing.sh status

# Python API
python3 run_mcp_tests.py --mode [security|fuzz|concurrency|login|all] --url [URL]
```

## MCP Testing Framework Details

**Purpose**: Multi-agent browser automation testing using MCP Task and WebFetch tools for comprehensive security analysis

**Coverage**: OWASP Top 10, fuzz testing (1000+ payloads), concurrency testing, authentication flows

**Automated**: Can be integrated into pre-commit hooks and CI/CD pipelines

**Framework documentation**: See `README_MCP_TESTING.md` for complete usage guide

## Preventing Guided Journal Issues

**CRITICAL**: Use comprehensive testing to prevent the types of issues that broke guided journal functionality:

### ⚡ **Quick Prevention**
```bash
# Before making any changes to guided journal or similar UI features:
python3 run_comprehensive_tests.py

# Install comprehensive pre-commit hook (one-time setup):
cp hooks/pre-commit-comprehensive .git/hooks/pre-commit
```

### 🔍 **Issue Types Prevented**
1. **JavaScript/CSP Issues**: Scripts blocked by Content Security Policy
2. **Security False Positives**: Legitimate JSON data flagged as malicious  
3. **Form Submission Failures**: Data rejected by security validation
4. **UI Component Malfunctions**: Checkboxes, sliders, form interactions
5. **Template Errors**: Missing nonces, incorrect CSRF tokens

### 🛡️ **Automated Protection**
- **Pre-commit hook**: Validates CSP nonces, CSRF tokens, JavaScript syntax
- **Security tests**: Ensures legitimate data (emotions, JSON) isn't blocked
- **E2E tests**: Browser automation tests actual user interactions
- **Integration tests**: Full form submission with emotion data
- **Template validation**: Checks form elements and script structure

### 📋 **For New Features**
When adding new UI features with JavaScript/forms:
1. **Add CSP nonces**: `<script nonce="{{ csp_nonce() }}">`
2. **Update security.py**: Add field exceptions if using JSON data
3. **Write tests**: Add to `tests/functional/` for complex UI interactions
4. **Run comprehensive tests**: `python3 run_comprehensive_tests.py`

## Route Testing

### AI-Enhanced Route Testing
```bash
# Test new routes work (prevents 500 errors)
python3 test_routes.py

# AI route validation
python3 AI_AUTOMATION_IMPLEMENTATION.py code-review --files routes.py
```

**Purpose**: Verifies new routes actually work and prevents deployment of broken routes.