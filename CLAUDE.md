# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 **Quick Start - Most Important Commands**

### **For ALL New Features (REQUIRED)**
```bash
# 1. AI Feature Generation & Review
python3 AI_AUTOMATION_IMPLEMENTATION.py generate-feature --feature "description"
python3 AI_AUTOMATION_IMPLEMENTATION.py code-review --files routes.py
python3 test_routes.py

# 2. Safe Deployment
./backup.sh pre-deploy
python3 deploy_changes.py
python3 backup_monitor.py check --brief
```

### **Daily Health Checks**
```bash
# App health
python3 check_app_health.py

# Backup health  
python3 backup_monitor.py check --brief

# Quick tests
python3 run_tests.py quick
```

### **Before Code Changes**
```bash
# Comprehensive testing (prevents all issues)
python3 run_comprehensive_tests.py

# Standard testing
python3 run_tests.py quick
```

## 📚 **Complete Documentation Index**

**Core References:**
- **[README.md](README.md)** - Project overview and getting started
- **[TESTING_REFERENCE.md](TESTING_REFERENCE.md)** - All testing commands and workflows
- **[SECURITY_REFERENCE.md](SECURITY_REFERENCE.md)** - CSRF, MCP testing, security validation
- **[DEVELOPMENT_WORKFLOW_DETAILS.md](DEVELOPMENT_WORKFLOW_DETAILS.md)** - Git hooks, service management, code style

**Backup System:**
- **[BACKUP_SYSTEM_GUIDE.md](BACKUP_SYSTEM_GUIDE.md)** - Complete backup commands and procedures
- **[BACKUP_SYSTEM_SUMMARY.md](BACKUP_SYSTEM_SUMMARY.md)** - Quick reference
- **[BACKUP_TROUBLESHOOTING_SUMMARY.md](BACKUP_TROUBLESHOOTING_SUMMARY.md)** - Issue resolution

**Workflow Enhancements:**
- **[IMMEDIATE_WORKFLOW_IMPROVEMENTS.md](IMMEDIATE_WORKFLOW_IMPROVEMENTS.md)** - Quick wins (30 min setup)
- **[ENTERPRISE_WORKFLOW_IMPROVEMENTS.md](ENTERPRISE_WORKFLOW_IMPROVEMENTS.md)** - Long-term roadmap
- **[WORKFLOW_ENHANCEMENT_SUMMARY.md](WORKFLOW_ENHANCEMENT_SUMMARY.md)** - Complete overview

**Advanced Features:**
- **[MCP_INTEGRATION_SUMMARY.md](MCP_INTEGRATION_SUMMARY.md)** - MCP security testing framework

## 🏥 **Production Environment**

- **Hosting**: Ubuntu server running as systemd service
- **Service**: `journal-app.service`
- **Domain**: https://journal.joshsisto.com/ (behind Cloudflare)
- **Logs**: `sudo journalctl -u journal-app.service -f`

**Service Control:**
```bash
# Status
sudo systemctl status journal-app.service

# Manual restart (automatic via git hooks)
sudo systemctl restart journal-app.service
python3 service_control.py reload
```

## 🤖 **AI-Enhanced Feature Development Workflow**

**CRITICAL: Use this workflow for ALL new feature development to prevent deployment issues.**

### **Required 5-Step Workflow**

When the user requests a new feature, ALWAYS follow this exact workflow:

#### **Step 1: AI Feature Generation**
```bash
python3 AI_AUTOMATION_IMPLEMENTATION.py generate-feature --feature "feature description"
```
**Purpose**: Generates complete implementation following project patterns

#### **Step 2: AI Code Review** 
```bash
python3 AI_AUTOMATION_IMPLEMENTATION.py code-review --files routes.py templates/new_feature.html
```
**Purpose**: Catches issues before deployment (imports, routes, security)

#### **Step 3: AI Risk Assessment**
```bash
python3 AI_AUTOMATION_IMPLEMENTATION.py risk-assessment --changes routes.py models.py
```
**Purpose**: Determines deployment complexity and required safety actions

#### **Step 4: Route Testing** 
```bash
python3 test_routes.py
```
**Purpose**: Verifies new routes actually work (prevents 500 errors)

#### **Step 5: Enhanced Deployment**
```bash
./deploy_with_ai.sh
```
**Purpose**: Full AI-enhanced deployment with health checks

### **Why This Workflow is Critical**

Prevents:
- **500 errors** (missing imports, undefined routes)
- **Security vulnerabilities** (missing CSRF, CSP)
- **Pattern violations** (inconsistent with project standards)
- **Deployment failures** (broken routes, template errors)

### **Manual Override**

Only skip this workflow for:
- Documentation-only changes
- Minor CSS/styling adjustments
- Emergency hotfixes (still run AI review after)

**For ALL feature development: Use the AI workflow to ensure quality and prevent issues.**

## 💾 **Database Configuration**

### **PostgreSQL Setup (Current)**
- **Engine**: PostgreSQL 14.18
- **Database**: `journal_db`
- **User**: `journal_user`
- **Host**: `localhost:5432`
- **Credentials**: Stored in `.env` file

### **Migration Summary**
- **Completed**: July 5, 2025
- **Records**: 241 total across 12 tables
- **Data Integrity**: 100% - Zero data loss
- **Rollback**: Change `USE_POSTGRESQL=false` in `.env`

## 🕒 **Timezone Handling**

- **Default**: All users set to `America/Los_Angeles` (Pacific Time)
- **Storage**: UTC in database, converted for display
- **Templates**: Use `{{ format_datetime(entry.created_at, '%b %d, %Y at %I:%M %p') }}`
- **Fix users**: `python3 fix_user_timezone.py`

## 🔥 **Critical Development Rules**

### **Always Before Deployment**
1. **Create backup**: `./backup.sh pre-deploy`
2. **Use deployment script**: `python3 deploy_changes.py` 
3. **Verify backup system**: `python3 backup_monitor.py check --brief`

### **CSRF Protection (CRITICAL)**
- **Always use**: `{{ csrf_token() }}` with parentheses
- **Never use**: `{{ csrf_token }}` (causes errors)
- **Validate**: `python3 validate_csrf.py`

### **Service Restart**
- **Automatic**: Git post-commit hook restarts service
- **Manual**: `sudo systemctl restart journal-app.service`

### **For UI Changes**
- **Add CSP nonces**: `<script nonce="{{ csp_nonce() }}">`
- **Test comprehensively**: `python3 run_comprehensive_tests.py`

## 📋 **Quick Reference Commands**

### **AI Development (Use for all features)**
```bash
python3 AI_AUTOMATION_IMPLEMENTATION.py generate-feature --feature "description"
python3 AI_AUTOMATION_IMPLEMENTATION.py code-review --files routes.py
python3 test_routes.py
./deploy_with_ai.sh
```

### **Health & Monitoring**
```bash
python3 check_app_health.py
python3 backup_monitor.py check --brief
```

### **Testing**
```bash
python3 run_comprehensive_tests.py  # Prevents all issues
python3 run_tests.py quick          # Standard testing
python3 validate_csrf.py            # Security validation
```

### **Backup Operations**
```bash
./backup.sh pre-deploy             # Before deployment
./backup.sh backup                 # Manual backup
./backup.sh list --size            # List backups
```

### **Database Operations**
```bash
python3 recreate_db.py             # Create tables
python3 fix_user_timezone.py       # Update timezones
```

---

**📖 For detailed information, see the documentation files listed in the Complete Documentation Index above.**