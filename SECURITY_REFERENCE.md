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

## Security Testing Commands

```bash
# Validate CSRF tokens
python3 validate_csrf.py

# Test security validation
python3 -m pytest tests/unit/test_security_validation.py -v

# Test CSP/JavaScript
python3 -m pytest tests/unit/test_csp_javascript.py -v
```

## Database Security

### **PostgreSQL Security Configuration**
- **Secure Password**: 24-character cryptographically generated password
- **Local Access Only**: Database configured for localhost connections only
- **Least Privilege**: Database user has only necessary permissions for journal app
- **Environment Protection**: All credentials in `.env` file (gitignored)