# Development Workflow Details

This document contains detailed development workflow information for the journal application.

## Git Hook Setup

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

**Available Hooks**:
- **Post-commit**: `hooks/post-commit` (automatic service restart + health check)
- **Pre-commit comprehensive**: `hooks/pre-commit-comprehensive` (prevents all issues + AI health check)
- **Pre-commit with MCP**: `hooks/pre-commit-comprehensive-mcp` (includes MCP security testing)
- **MCP security pre-commit**: `hooks/pre-commit-mcp-security` (MCP security testing only)
- **MCP security post-commit**: `hooks/post-commit-mcp-security` (comprehensive MCP validation)
- **Post-deploy health check**: `hooks/post-deploy-health-check` (standalone health validation)

## Service Management

**🔥 CRITICAL: Service restart is AUTOMATIC via git hook** - the app runs as a systemd service and code changes require a restart to take effect.

**✅ AUTOMATIC RESTART**: A git post-commit hook automatically restarts the service when you commit changes.

**Manual restart options** (if needed):
```bash
sudo systemctl restart journal-app.service
# OR use the service control script:
python3 service_control.py reload
```

**⚠️ IMPORTANT FOR CLAUDE CODE**: After making code changes, you MUST:
1. **Create pre-deployment backup** - run `./backup.sh pre-deploy`
2. **Use deployment script** (recommended) - run `python3 deploy_changes.py`
3. **Or manual process** - restart service then run health check
4. **Verify backup system** - run `python3 backup_monitor.py check --brief`
5. **Always verify** - check that the app is working before finishing

This prevents "Internal Server Error" situations and ensures changes work correctly with backup safety.

This is critical for:
- Python code changes (routes.py, app.py, models.py, etc.)
- Template changes (HTML files)
- Configuration changes
- Any file modifications that affect the running application

## Testing Workflows

### 🎯 **Comprehensive Testing Workflow** (Prevents all guided journal issues)
1. **Before changes**: `python3 run_comprehensive_tests.py`
2. **Pre-deployment backup**: `./backup.sh pre-deploy`
3. **During development**: `python3 run_tests.py [relevant-category]`
4. **Before committing**: Comprehensive pre-commit hook runs automatically
5. **For UI changes**: `python3 -m pytest tests/functional/ -v`
6. **Security testing**: `./deploy_mcp_testing.sh security https://journal.joshsisto.com 3` (for security-related changes)
7. **Post-deployment**: `python3 backup_monitor.py check --brief`

### 📋 **Standard Testing Workflow**
1. **Before changes**: `python3 run_tests.py quick`
2. **Pre-deployment backup**: `./backup.sh pre-deploy`
3. **During development**: `python3 run_tests.py [relevant-category]`
4. **Before committing**: `python3 run_tests.py all`
5. **Post-deployment**: `python3 backup_monitor.py check --brief`

### 🚀 **MCP Security Testing Workflow** (For production security validation)
1. **Pre-deployment**: `./deploy_mcp_testing.sh security https://journal.joshsisto.com 5`
2. **Post-deployment**: `./deploy_mcp_testing.sh all https://journal.joshsisto.com 8`
3. **Weekly comprehensive**: `./deploy_mcp_testing.sh all https://journal.joshsisto.com 10` (full security audit)
4. **Emergency security check**: `python3 run_mcp_tests.py --mode security --url https://journal.joshsisto.com`

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