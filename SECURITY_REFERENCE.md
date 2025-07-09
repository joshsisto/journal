# Security Reference Guide

Complete security configuration and validation information for the journal application.

## CSRF Protection Configuration

**CRITICAL**: This app uses Flask-WTF for CSRF protection. Follow these rules strictly:

### CSRF Settings (app.py)
Current configuration:
```python
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow CSRF for proxied SSL
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']
app.config['WTF_CSRF_CHECK_HEADERS'] = False  # Skip referrer check for proxy environments
```

### Template Usage Rules

**ALWAYS use `{{ csrf_token() }}` with parentheses - NEVER `{{ csrf_token }}`**

✅ **CORRECT**:
```html
<!-- For AJAX requests -->
'X-CSRF-Token': '{{ csrf_token() }}'

<!-- For forms -->
<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
```

❌ **WRONG** (causes function reference errors):
```html
'X-CSRF-Token': '{{ csrf_token }}'
<input type="hidden" name="_csrf_token" value="{{ csrf_token }}">
```

### Prevention Steps
1. **Always call the function**: Use `csrf_token()` not `csrf_token`
2. **Test AJAX requests**: Check browser network tab for CSRF token value (not function reference)
3. **Check logs**: CSRF failures show as "400 Bad Request: The CSRF token is invalid/missing"
4. **Automated validation**: Run `python3 validate_csrf.py` before commits
5. **Git pre-commit hook**: Automatically installed - prevents commits with CSRF issues
6. **Manual check**: Search codebase: `grep -r "csrf_token[^()]" templates/`

### Validation Tools
- **Script**: `validate_csrf.py` - Scans all templates for CSRF issues
- **Pre-commit hook**: `.git/hooks/pre-commit` - Prevents committing CSRF issues
- **Quick fix**: `find templates/ -name '*.html' -exec sed -i 's/{{ csrf_token }}/{{ csrf_token() }}/g' {} \;`

### Common CSRF Error Messages
- "The CSRF token is invalid" → Token mismatch (usually function reference issue)
- "The CSRF session token is missing" → Token not sent in request
- "CSRF validation failed" → General CSRF protection triggered

## MCP Security Testing Integration

**NEW**: The journal application includes a comprehensive MCP Browser Testing Framework for production security validation:

### **MCP Testing Framework Components**
- **Security Testing Agent** - CSRF, SQL injection, XSS, authentication security analysis
- **Fuzz Testing Agent** - 1000+ malicious payloads, form input validation, API fuzzing
- **Concurrency Testing Agent** - Race conditions, resource exhaustion, multi-user load testing
- **Login Flow Testing Agent** - Authentication flows, session management, password security

### **Integration with Git Hooks**
- **Pre-commit Security**: Automatically runs MCP security tests for security-related file changes
- **Post-commit Validation**: Comprehensive security analysis after successful commits
- **Targeted Testing**: Smart detection of changed files to run relevant security tests
- **Report Generation**: Automated security reports and scoring (0-100 scale)

### **When MCP Tests Run Automatically**
- **Pre-commit**: Security tests for changes to `routes.py`, `app.py`, `models.py`, templates
- **Post-commit**: Comprehensive security validation on main/master branch
- **Targeted**: Login flow tests for auth changes, UI tests for template changes
- **Scheduled**: Weekly comprehensive security audits (configurable)

### **MCP Test Results**
- **Security Scoring**: Quantitative assessment (85+ recommended for production)
- **Vulnerability Detection**: OWASP Top 10 coverage, custom security checks
- **Performance Metrics**: Response times, concurrency handling, resource usage
- **Compliance Reporting**: Security standards validation and audit trails

### **📖 Detailed MCP Documentation**
- **[MCP_INTEGRATION_SUMMARY.md](MCP_INTEGRATION_SUMMARY.md)** - Complete MCP framework implementation details

## Security Testing Commands

```bash
# Validate CSRF tokens
python3 validate_csrf.py

# Test security validation
python3 -m pytest tests/unit/test_security_validation.py -v

# Test CSP/JavaScript
python3 -m pytest tests/unit/test_csp_javascript.py -v

# MCP security scan
./deploy_mcp_testing.sh security https://journal.joshsisto.com 5

# MCP comprehensive suite
./deploy_mcp_testing.sh all https://journal.joshsisto.com 8
```

## Database Security

### **PostgreSQL Security Configuration**
- **Secure Password**: 24-character cryptographically generated password
- **Local Access Only**: Database configured for localhost connections only
- **Least Privilege**: Database user has only necessary permissions for journal app
- **Environment Protection**: All credentials in `.env` file (gitignored)