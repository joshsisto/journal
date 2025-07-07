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

## 🏥 App Health Monitoring
- **Deploy with health check**: `python3 deploy_changes.py` (recommended after code changes)
- **Manual health check**: `python3 check_app_health.py`
- **Service restart only**: `sudo systemctl restart journal-app.service`

**IMPORTANT**: Always use `deploy_changes.py` after making code changes to ensure the app is working correctly.

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

### 🏥 **AI Conversation Health Monitoring**
- **Full health check**: `./check_ai_health.sh` or `python3 ai_conversation_health_check.py`
- **Brief health check**: `./check_ai_health.sh brief` or `python3 ai_conversation_health_check.py --brief`
- **Purpose**: Prevents AI conversation breakdowns by monitoring templates, security, dependencies, and functionality
- **Automated**: Runs automatically in pre-commit and post-commit hooks

### 🔒 **Security & UI Testing**
- **Test security validation**: `python3 -m pytest tests/unit/test_security_validation.py -v`
- **Test CSP/JavaScript**: `python3 -m pytest tests/unit/test_csp_javascript.py -v`
- **Test guided journal E2E**: `python3 -m pytest tests/functional/test_guided_journal_e2e.py -v`
- **Validate CSRF tokens**: `python3 validate_csrf.py`

### 🚀 **MCP Browser Testing Framework** (Production Security Testing)
- **Setup framework**: `./deploy_mcp_testing.sh setup`
- **Run security scan**: `./deploy_mcp_testing.sh security https://journal.joshsisto.com 5`
- **Run comprehensive suite**: `./deploy_mcp_testing.sh all https://journal.joshsisto.com 8`
- **Run fuzz testing**: `./deploy_mcp_testing.sh fuzz https://journal.joshsisto.com 3`
- **Run concurrency tests**: `./deploy_mcp_testing.sh concurrency https://journal.joshsisto.com 10`
- **Run login flow tests**: `./deploy_mcp_testing.sh login https://journal.joshsisto.com 3`
- **Check framework status**: `./deploy_mcp_testing.sh status`
- **Python API**: `python3 run_mcp_tests.py --mode [security|fuzz|concurrency|login|all] --url [URL]`
- **Framework documentation**: See `README_MCP_TESTING.md` for complete usage guide
- **Purpose**: Multi-agent browser automation testing using MCP Task and WebFetch tools for comprehensive security analysis
- **Coverage**: OWASP Top 10, fuzz testing (1000+ payloads), concurrency testing, authentication flows
- **Automated**: Can be integrated into pre-commit hooks and CI/CD pipelines

## IMPORTANT: Development Workflow

### Code Changes & Testing
**🎯 COMPREHENSIVE TESTING WORKFLOW** (Prevents all guided journal issues):
1. **Before changes**: `python3 run_comprehensive_tests.py`
2. **During development**: `python3 run_tests.py [relevant-category]`
3. **Before committing**: Comprehensive pre-commit hook runs automatically
4. **For UI changes**: `python3 -m pytest tests/functional/ -v`
5. **Security testing**: `./deploy_mcp_testing.sh security https://journal.joshsisto.com 3` (for security-related changes)

**📋 Standard workflow:**
1. **Before changes**: `python3 run_tests.py quick`
2. **During development**: `python3 run_tests.py [relevant-category]`
3. **Before committing**: `python3 run_tests.py all`

**🚀 MCP Security Testing Workflow** (For production security validation):
1. **Pre-deployment**: `./deploy_mcp_testing.sh security https://journal.joshsisto.com 5`
2. **Post-deployment**: `./deploy_mcp_testing.sh all https://journal.joshsisto.com 8`
3. **Weekly comprehensive**: `./deploy_mcp_testing.sh all https://journal.joshsisto.com 10` (full security audit)
4. **Emergency security check**: `python3 run_mcp_tests.py --mode security --url https://journal.joshsisto.com`

### Service Restart
**🔥 CRITICAL: Service restart is AUTOMATIC via git hook** - the app runs as a systemd service and code changes require a restart to take effect:

**✅ AUTOMATIC RESTART**: A git post-commit hook automatically restarts the service when you commit changes.

**Manual restart options** (if needed):
```bash
sudo systemctl restart journal-app.service
# OR use the service control script:
python3 service_control.py reload
```

**⚠️ IMPORTANT FOR CLAUDE CODE**: After making code changes, you MUST:
1. **Use deployment script** (recommended) - run `python3 deploy_changes.py`
2. **Or manual process** - restart service then run health check
3. **Always verify** - check that the app is working before finishing

This prevents "Internal Server Error" situations and ensures changes work correctly.

This is critical for:
- Python code changes (routes.py, app.py, models.py, etc.)
- Template changes (HTML files)
- Configuration changes
- Any file modifications that affect the running application

**Git Hook Setup**:
- **Post-commit**: `hooks/post-commit` (automatic service restart + health check)
- **Pre-commit comprehensive**: `hooks/pre-commit-comprehensive` (prevents all issues + AI health check)
- **Pre-commit with MCP**: `hooks/pre-commit-comprehensive-mcp` (includes MCP security testing)
- **MCP security pre-commit**: `hooks/pre-commit-mcp-security` (MCP security testing only)
- **MCP security post-commit**: `hooks/post-commit-mcp-security` (comprehensive MCP validation)
- **Post-deploy health check**: `hooks/post-deploy-health-check` (standalone health validation)

**Hook Installation Options**:
- **🚀 Automated Installer** (Recommended): `./install_mcp_hooks.sh`
  - Interactive menu with options for different hook configurations
  - Automatic hook testing and status checking
  - Command-line options: `mcp`, `comprehensive`, `standard`, `remove`
- **Manual Installation**:
  - **Standard comprehensive**: `cp hooks/pre-commit-comprehensive .git/hooks/pre-commit`
  - **Enhanced with MCP security**: `cp hooks/pre-commit-comprehensive-mcp .git/hooks/pre-commit`
  - **MCP security only**: `cp hooks/pre-commit-mcp-security .git/hooks/pre-commit`
  - **MCP post-commit**: `cp hooks/post-commit-mcp-security .git/hooks/post-commit`

**Hook Management Commands**:
- **Install MCP security hooks**: `./install_mcp_hooks.sh mcp`
- **Install comprehensive + MCP**: `./install_mcp_hooks.sh comprehensive`
- **Check hook status**: `./install_mcp_hooks.sh status`
- **Test hooks**: `./install_mcp_hooks.sh test`
- **Remove all hooks**: `./install_mcp_hooks.sh remove`

## 🚀 MCP Security Testing Integration

**NEW**: The journal application now includes a comprehensive MCP Browser Testing Framework for production security validation:

### **MCP Testing Framework Components**:
- **Security Testing Agent** - CSRF, SQL injection, XSS, authentication security analysis
- **Fuzz Testing Agent** - 1000+ malicious payloads, form input validation, API fuzzing
- **Concurrency Testing Agent** - Race conditions, resource exhaustion, multi-user load testing
- **Login Flow Testing Agent** - Authentication flows, session management, password security

### **Integration with Git Hooks**:
- **Pre-commit Security**: Automatically runs MCP security tests for security-related file changes
- **Post-commit Validation**: Comprehensive security analysis after successful commits
- **Targeted Testing**: Smart detection of changed files to run relevant security tests
- **Report Generation**: Automated security reports and scoring (0-100 scale)

### **When MCP Tests Run Automatically**:
- **Pre-commit**: Security tests for changes to `routes.py`, `app.py`, `models.py`, templates
- **Post-commit**: Comprehensive security validation on main/master branch
- **Targeted**: Login flow tests for auth changes, UI tests for template changes
- **Scheduled**: Weekly comprehensive security audits (configurable)

### **MCP Test Results**:
- **Security Scoring**: Quantitative assessment (85+ recommended for production)
- **Vulnerability Detection**: OWASP Top 10 coverage, custom security checks
- **Performance Metrics**: Response times, concurrency handling, resource usage
- **Compliance Reporting**: Security standards validation and audit trails

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

## 🗄️ Database Configuration

### **PostgreSQL Migration (Completed July 2025)**
**The application has been successfully migrated from SQLite to PostgreSQL.**

#### **Current Database Setup**
- **Database Engine**: PostgreSQL 14.18
- **Database Name**: `journal_db`
- **Database User**: `journal_user`
- **Host**: `localhost` (local connections only)
- **Port**: `5432` (default PostgreSQL port)
- **Password**: Stored securely in `.env` file (24-character secure password)

#### **Migration Summary**
- **Date Completed**: July 5, 2025
- **Records Migrated**: 241 total records across 12 tables
  - 21 users with authentication data
  - 32 journal entries with content
  - 113 guided responses with Q&A data
  - 17 weather records with conditions
  - 9 locations with GPS coordinates
  - Additional data: photos, templates, tags, exercise logs
- **Data Integrity**: 100% - Zero data loss during migration
- **Downtime**: Minimal - Service-based migration approach

#### **Configuration Files**
- **Environment**: Database credentials in `.env` (excluded from git)
- **Config**: `config.py` handles PostgreSQL vs SQLite with URL encoding for special characters
- **Models**: All SQLAlchemy models compatible with PostgreSQL data types

#### **Key Migration Fixes Applied**
1. **Boolean Data Type Conversion**: SQLite integers (0/1) → PostgreSQL boolean values
2. **Foreign Key Constraints**: Proper handling of circular references between journal entries and weather data
3. **URL Encoding**: Password special characters properly encoded in connection strings
4. **Cascade Relationships**: Proper CASCADE DELETE configured for related data

#### **Database Security**
- **Secure Password**: 24-character cryptographically generated password
- **Local Access Only**: Database configured for localhost connections only
- **Least Privilege**: Database user has only necessary permissions for journal app
- **Environment Protection**: All credentials in `.env` file (gitignored)

#### **Rollback Capability** 
- **SQLite Backup**: Original SQLite database preserved in `instance/` directory
- **Rollback Process**: Change `USE_POSTGRESQL=false` in `.env` and restart service
- **Migration Archive**: All migration scripts archived in `migration_archive/`

#### **Critical Fix - Journal Entry Deletion**
**Issue**: Foreign key constraint violations when deleting journal entries
**Cause**: Circular foreign key relationships between journal entries and weather data
**Solution**: Enhanced deletion logic in `routes.py:delete_entry()` that:
- Clears weather record references before deletion
- Handles bidirectional relationships properly
- Uses proper transaction rollback on errors
- Provides detailed logging for troubleshooting

```python
# Before deleting journal entry, clear weather references
if entry.weather_id:
    weather_record = db.session.get(WeatherData, entry.weather_id)
    if weather_record and weather_record.journal_entry_id == entry.id:
        weather_record.journal_entry_id = None

# Clear any other weather records referencing this entry
WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
```

## Backup System
- **PostgreSQL Backups**: Use `pg_dump` for professional database backups
- **Create backup**: `./backup.sh backup` or `./backup.sh pre-deploy`
- **List backups**: `./backup.sh list --size`
- **Cleanup old backups**: `./backup.sh cleanup`
- **Emergency rollback**: `./backup.sh rollback TIMESTAMP`
- **PostgreSQL-specific**: `backup_system_postgresql.py` available in migration archive

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