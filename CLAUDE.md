# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Production Environment
- **Hosting**: Ubuntu server running as systemd service
- **Service Name**: `journal-app.service`
- **Service Status**: `sudo systemctl status journal-app.service`
- **Service Control**: 
  - Restart: `sudo systemctl restart journal-app.service`
  - Stop: `sudo systemctl stop journal-app.service` 
  - Start: `sudo systemctl start journal-app.service`
- **Process**: `/home/josh/Sync2/projects/journal/.venv/bin/python app.py` (PID varies)
- **Domain**: https://journal.joshsisto.com/ (behind Cloudflare)
- **Logs**: Use `sudo journalctl -u journal-app.service -f` to follow logs

## Build & Run Commands
- **Production**: Service runs automatically via systemd
- **Development**: `python app.py` (for local testing)
- **Create DB tables**: `python recreate_db.py`
- **Run DB updates**: `python add_tag_tables.py`, `python add_timezone_column.py`, etc.
- **Restart production service**: `python3 service_control.py reload`

## Testing Commands

### 🎯 **Comprehensive Testing** (Prevents Guided Journal Issues)
- **Run all protection tests**: `python3 run_comprehensive_tests.py`
- **Use comprehensive pre-commit**: `cp hooks/pre-commit-comprehensive .git/hooks/pre-commit`

### 📋 **Standard Testing**
- **Run quick tests**: `python3 run_tests.py quick`
- **Run category tests**: `python3 run_tests.py [auth|email|mfa|journal|ai|csrf]`
- **Run all tests**: `python3 run_tests.py all`
- **Run with coverage**: `python3 run_tests.py coverage`
- **Test specific file**: `python3 -m pytest tests/unit/test_auth.py -v`

### 🔒 **Security & UI Testing**
- **Test security validation**: `python3 -m pytest tests/unit/test_security_validation.py -v`
- **Test CSP/JavaScript**: `python3 -m pytest tests/unit/test_csp_javascript.py -v`
- **Test guided journal E2E**: `python3 -m pytest tests/functional/test_guided_journal_e2e.py -v`
- **Validate CSRF tokens**: `python3 validate_csrf.py`

## IMPORTANT: Development Workflow

### Code Changes & Testing
**🎯 COMPREHENSIVE TESTING WORKFLOW** (Prevents all guided journal issues):
1. **Before changes**: `python3 run_comprehensive_tests.py`
2. **During development**: `python3 run_tests.py [relevant-category]`
3. **Before committing**: Comprehensive pre-commit hook runs automatically
4. **For UI changes**: `python3 -m pytest tests/functional/ -v`

**📋 Standard workflow:**
1. **Before changes**: `python3 run_tests.py quick`
2. **During development**: `python3 run_tests.py [relevant-category]`
3. **Before committing**: `python3 run_tests.py all`

### Service Restart
**🔥 CRITICAL: Service restart is AUTOMATIC via git hook** - the app runs as a systemd service and code changes require a restart to take effect:

**✅ AUTOMATIC RESTART**: A git post-commit hook automatically restarts the service when you commit changes.

**Manual restart options** (if needed):
```bash
sudo systemctl restart journal-app.service
# OR use the service control script:
python3 service_control.py reload
```

**⚠️ IMPORTANT FOR CLAUDE CODE**: After making code changes, you MUST either:
1. **Commit your changes** (recommended) - triggers automatic restart
2. **Manual restart** - run `sudo systemctl restart journal-app.service`

This is critical for:
- Python code changes (routes.py, app.py, models.py, etc.)
- Template changes (HTML files)
- Configuration changes
- Any file modifications that affect the running application

**Git Hook Setup**:
- **Post-commit**: `hooks/post-commit` (automatic service restart)
- **Pre-commit comprehensive**: `hooks/pre-commit-comprehensive` (prevents all issues)
- **Install comprehensive hook**: `cp hooks/pre-commit-comprehensive .git/hooks/pre-commit`
- **Standard hooks**: Already installed automatically

## 🎯 Preventing Guided Journal Issues

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

## Backup System
- **Create backup**: `./backup.sh backup` or `./backup.sh pre-deploy`
- **List backups**: `./backup.sh list --size`
- **Cleanup old backups**: `./backup.sh cleanup`
- **Emergency rollback**: `./backup.sh rollback TIMESTAMP`

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

## Code Style Guidelines
- **Imports**: Group imports: 1) standard library, 2) third-party, 3) local modules
- **Docstrings**: Use Google-style docstrings with Args/Returns sections
- **Error Handling**: Use try/except blocks with specific exceptions
- **Naming**: 
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPER_CASE
- **Type Hints**: Optional but recommended for function parameters and returns
- **Models**: Define relationships clearly with backref and lazy loading options
- **Routes**: Group related routes in blueprints
- **Database**: Use SQLAlchemy models with descriptive __repr__ methods
- **Templates**: Keep template logic minimal; use Jinja2 filters for formatting