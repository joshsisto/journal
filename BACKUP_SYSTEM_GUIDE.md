# Comprehensive Backup System Guide

## Overview

This guide covers the complete backup system for the journal application, including backup creation, scheduling, monitoring, restoration, and maintenance.

## System Components

### 1. Core Backup System (`backup_system.py`)
- **Purpose**: Main backup engine with PostgreSQL and SQLite support
- **Features**: 
  - Full, database-only, and codebase-only backups
  - Integrity verification with checksums
  - Automatic categorization (daily/weekly/monthly)
  - Compression and metadata storage
  - Retention policy management

### 2. Backup Scheduler (`backup_scheduler.py`)
- **Purpose**: Automated backup scheduling using systemd timers
- **Features**:
  - Daily database backups (02:00)
  - Weekly full backups (Sunday 03:00)
  - Monthly full backups with cleanup (1st 04:00)
  - Service management and monitoring

### 3. Backup Verification (`backup_verification.py`)
- **Purpose**: Comprehensive backup testing and validation
- **Features**:
  - Integrity checking
  - Restore procedure testing
  - System health validation
  - Performance testing
  - Report generation

### 4. Backup Restoration (`backup_restore.py`)
- **Purpose**: Safe backup restoration with rollback capability
- **Features**:
  - Safe restore procedures
  - Rollback on failure
  - Prerequisites validation
  - Test environment support
  - Service management

### 5. Backup Monitoring (`backup_monitor.py`)
- **Purpose**: Continuous monitoring and alerting
- **Features**:
  - Health monitoring
  - Email alerts
  - Disk usage monitoring
  - Service status checking
  - Comprehensive reporting

### 6. Shell Interface (`backup.sh`)
- **Purpose**: User-friendly shell interface
- **Features**:
  - Simple command interface
  - Service management
  - Pre-deployment backups
  - Emergency rollback

## Quick Start

### Initial Setup

1. **Install systemd timers for automated backups:**
   ```bash
   python3 backup_scheduler.py install
   ```

2. **Verify system is working:**
   ```bash
   python3 backup_verification.py verify
   ```

3. **Create your first backup:**
   ```bash
   ./backup.sh backup
   ```

### Daily Usage

```bash
# Check backup status
./backup.sh status

# List available backups
./backup.sh list

# Create manual backup
./backup.sh backup

# Monitor backup health
python3 backup_monitor.py check

# View backup statistics
python3 backup_system.py stats
```

## Detailed Command Reference

### Core Backup System (`backup_system.py`)

```bash
# Create full backup (database + codebase)
python3 backup_system.py backup

# Create database backup only
python3 backup_system.py backup --db-only

# Create codebase backup only
python3 backup_system.py backup --code-only

# List all backups
python3 backup_system.py list

# List backups with sizes
python3 backup_system.py list --size

# Verify backup integrity
python3 backup_system.py verify

# Verify specific backup
python3 backup_system.py verify --timestamp 20240708_143022

# Show backup statistics
python3 backup_system.py stats

# Clean up old backups
python3 backup_system.py cleanup

# Show what cleanup would remove
python3 backup_system.py cleanup --dry-run

# Remove specific backup
python3 backup_system.py remove 20240708_143022

# Restore from backup
python3 backup_system.py restore --timestamp 20240708_143022
```

### Backup Scheduler (`backup_scheduler.py`)

```bash
# Install automated backup schedules
python3 backup_scheduler.py install

# Uninstall backup schedules
python3 backup_scheduler.py uninstall

# Check scheduler status
python3 backup_scheduler.py status

# Run backup immediately
python3 backup_scheduler.py run --type daily
python3 backup_scheduler.py run --type weekly
python3 backup_scheduler.py run --type monthly

# Create monitoring script
python3 backup_scheduler.py monitor
```

### Backup Verification (`backup_verification.py`)

```bash
# Run comprehensive verification
python3 backup_verification.py verify

# Run specific test
python3 backup_verification.py test --test database
python3 backup_verification.py test --test integrity
python3 backup_verification.py test --test restore

# Generate detailed report
python3 backup_verification.py report
```

**Available Tests:**
- `executable` - Test backup system executable
- `database` - Test database connectivity
- `backup` - Test backup creation
- `integrity` - Test backup integrity
- `restore` - Test restore functionality
- `cleanup` - Test cleanup procedures
- `stats` - Test statistics generation
- `shell` - Test shell script interface
- `systemd` - Test systemd integration

### Backup Restoration (`backup_restore.py`)

```bash
# List available backups for restore
python3 backup_restore.py list

# Test restore prerequisites
python3 backup_restore.py test 20240708_143022

# Test with specific restore type
python3 backup_restore.py test 20240708_143022 --type database

# Perform safe restore (requires confirmation)
python3 backup_restore.py restore 20240708_143022 --confirm

# Restore specific component
python3 backup_restore.py restore 20240708_143022 --type database --confirm
python3 backup_restore.py restore 20240708_143022 --type codebase --confirm

# Restore to staging environment
python3 backup_restore.py restore 20240708_143022 --environment staging --confirm
```

### Backup Monitoring (`backup_monitor.py`)

```bash
# Run health check
python3 backup_monitor.py check

# Brief health check
python3 backup_monitor.py check --brief

# Generate health report
python3 backup_monitor.py report

# Start continuous monitoring
python3 backup_monitor.py monitor

# Monitor with custom interval
python3 backup_monitor.py monitor --interval 30

# Show configuration
python3 backup_monitor.py config
```

### Shell Interface (`backup.sh`)

```bash
# Full backup
./backup.sh backup

# Database backup only
./backup.sh backup --db-only

# Codebase backup only
./backup.sh backup --code-only

# List backups
./backup.sh list
./backup.sh list --size

# Pre-deployment backup
./backup.sh pre-deploy

# Emergency rollback
./backup.sh rollback 20240708_143022

# Service management
./backup.sh restart
./backup.sh start
./backup.sh stop
./backup.sh status
./backup.sh logs

# Cleanup
./backup.sh cleanup
./backup.sh cleanup --dry-run

# Remove specific backup
./backup.sh remove 20240708_143022

# Show backup sizes
./backup.sh size
./backup.sh size 20240708_143022

# Help
./backup.sh help
```

## Automated Backup Schedules

The system creates three automated backup schedules:

### Daily Backup (02:00)
- **Type**: Database only
- **Frequency**: Every day at 2:00 AM
- **Retention**: 7 days
- **Purpose**: Regular data protection

### Weekly Backup (Sunday 03:00)
- **Type**: Full backup (database + codebase)
- **Frequency**: Every Sunday at 3:00 AM
- **Retention**: 4 weeks
- **Purpose**: Complete system backup

### Monthly Backup (1st 04:00)
- **Type**: Full backup + cleanup
- **Frequency**: 1st of each month at 4:00 AM
- **Retention**: 6 months
- **Purpose**: Long-term archive + maintenance

## Backup Directory Structure

```
backups/
├── daily/
│   ├── db_20240708_020000/
│   │   ├── postgresql_journal_db.dump
│   │   └── postgresql_journal_db.sql
│   └── manifest_20240708_020000.json
├── weekly/
│   ├── codebase_20240707_030000.tar.gz
│   ├── db_20240707_030000/
│   │   └── postgresql_journal_db.dump
│   └── manifest_20240707_030000.json
├── monthly/
│   └── ...
└── backup_monitor_config.json
```

## Backup Metadata

Each backup includes comprehensive metadata:

```json
{
  "metadata": {
    "timestamp": "20240708_143022",
    "backup_type": "full",
    "database_type": "postgresql",
    "created_at": "2024-07-08T14:30:22.123456",
    "git_commit": "a1b2c3d4",
    "git_branch": "main",
    "total_size": 12345678,
    "checksum": "sha256:abcd1234...",
    "files": {
      "database_postgresql": "/path/to/backup.dump",
      "codebase": "/path/to/codebase.tar.gz"
    }
  },
  "backup_results": {
    "database": {
      "postgresql": {
        "path": "/path/to/backup.dump",
        "checksum": "sha256:...",
        "type": "postgresql"
      }
    },
    "codebase": {
      "path": "/path/to/codebase.tar.gz",
      "checksum": "sha256:...",
      "type": "codebase"
    }
  }
}
```

## Monitoring and Alerting

### Health Checks

The monitoring system performs these checks:

1. **Backup Freshness**: Ensures backups are created within 26 hours
2. **Backup Integrity**: Verifies backup file checksums
3. **Backup Size**: Checks for unreasonably small backups
4. **Systemd Services**: Monitors timer and service status
5. **Disk Usage**: Monitors backup directory disk usage
6. **Database Connectivity**: Verifies database accessibility

### Alert Levels

- **INFO**: General information (backup completed)
- **WARNING**: Non-critical issues (old backup, high disk usage)
- **ERROR**: Serious issues (backup failed, integrity error)
- **CRITICAL**: System-threatening issues (no backups, database offline)

### Email Notifications

Configure email alerts by setting environment variables:

```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USERNAME=your-username
MAIL_PASSWORD=your-password
```

### Monitoring Configuration

Edit `backup_monitor_config.json` to customize monitoring:

```json
{
  "monitoring": {
    "max_backup_age_hours": 26,
    "min_backup_size_mb": 1,
    "check_interval_minutes": 60,
    "disk_usage_threshold": 85
  },
  "alerting": {
    "email_enabled": true,
    "email_recipients": ["admin@example.com"],
    "alert_cooldown_minutes": 60
  }
}
```

## Restoration Procedures

### Safe Restoration Process

1. **Prerequisites Check**: Validates system state before restore
2. **Safety Backup**: Creates backup of current state
3. **Service Stop**: Stops application service
4. **Restore Data**: Restores database and/or codebase
5. **Service Start**: Restarts application service
6. **Verification**: Verifies successful restoration
7. **Rollback**: Reverts to safety backup if verification fails

### Restore Types

- **Full Restore**: Database + codebase
- **Database Only**: Database restoration only
- **Codebase Only**: Application code restoration only

### Target Environments

- **Production**: Live system restoration
- **Staging**: Staging environment restoration
- **Test**: Test environment restoration

## Maintenance Tasks

### Daily Maintenance

```bash
# Check backup health
python3 backup_monitor.py check --brief

# Verify recent backups
python3 backup_verification.py test --test integrity
```

### Weekly Maintenance

```bash
# Run comprehensive verification
python3 backup_verification.py verify

# Generate health report
python3 backup_monitor.py report

# Check disk usage
python3 backup_system.py stats
```

### Monthly Maintenance

```bash
# Clean up old backups
python3 backup_system.py cleanup

# Run comprehensive restore test
python3 backup_restore.py test $(python3 backup_system.py list | head -1 | cut -d'|' -f1)

# Review and update monitoring configuration
python3 backup_monitor.py config
```

## Troubleshooting

### Common Issues

#### Backup Creation Fails

1. **Check database connectivity:**
   ```bash
   python3 backup_verification.py test --test database
   ```

2. **Check disk space:**
   ```bash
   df -h /path/to/backups
   ```

3. **Check service status:**
   ```bash
   sudo systemctl status journal-app.service
   ```

#### Backup Integrity Fails

1. **Verify specific backup:**
   ```bash
   python3 backup_system.py verify --timestamp 20240708_143022
   ```

2. **Check backup files:**
   ```bash
   ls -la backups/daily/db_20240708_143022/
   ```

#### Systemd Timers Not Running

1. **Check timer status:**
   ```bash
   sudo systemctl list-timers journal-backup-*
   ```

2. **Check service logs:**
   ```bash
   sudo journalctl -u journal-backup-daily.service
   ```

3. **Reinstall timers:**
   ```bash
   python3 backup_scheduler.py uninstall
   python3 backup_scheduler.py install
   ```

#### Restoration Fails

1. **Check prerequisites:**
   ```bash
   python3 backup_restore.py test 20240708_143022
   ```

2. **Check backup integrity:**
   ```bash
   python3 backup_system.py verify --timestamp 20240708_143022
   ```

3. **Check service status:**
   ```bash
   sudo systemctl status journal-app.service
   ```

### Debug Mode

For detailed debugging, set environment variable:

```bash
export DEBUG=1
python3 backup_system.py backup
```

### Log Files

- **Application logs**: `sudo journalctl -u journal-app.service`
- **Backup logs**: `backup.log`
- **Alert logs**: `backup_alerts.log`
- **Health reports**: `backup_health_report_*.json`
- **Verification reports**: `backup_verification_report_*.json`

## Security Considerations

### Database Security

- PostgreSQL password stored in `.env` file (not in git)
- Database connections use encrypted connections when available
- Backup files include sensitive data - protect access

### File Permissions

```bash
# Set appropriate permissions
chmod 600 .env
chmod 755 backup_system.py
chmod 755 backup.sh
chmod 700 backups/
```

### Access Control

- Backup files contain sensitive application data
- Restrict access to backup directory
- Use appropriate file permissions
- Consider encrypting backup files for long-term storage

## Performance Optimization

### Backup Performance

- Use PostgreSQL custom format for better compression
- Exclude unnecessary files from codebase backups
- Use compression for all backup archives
- Schedule backups during low-usage hours

### Storage Optimization

- Regular cleanup of old backups
- Monitor disk usage
- Use appropriate retention policies
- Consider offsite backup storage

## Integration with Existing Systems

### Git Integration

- Backup metadata includes git commit and branch information
- Codebase backups exclude `.git` directory
- Backup timing can be coordinated with deployments

### Monitoring Integration

- Health checks can be integrated with external monitoring
- Alerts can be sent to external systems
- Metrics can be exported for analysis

## Best Practices

1. **Regular Testing**: Test restoration procedures monthly
2. **Monitor Health**: Check backup health daily
3. **Verify Integrity**: Verify backup integrity weekly
4. **Update Configuration**: Review configuration quarterly
5. **Document Changes**: Document any configuration changes
6. **Offsite Storage**: Consider offsite backup storage
7. **Encryption**: Encrypt sensitive backup data
8. **Access Control**: Restrict backup access to authorized personnel

## Support and Maintenance

### Getting Help

For issues with the backup system:

1. Check this guide first
2. Review log files for error messages
3. Run diagnostic commands
4. Check system resources (disk, memory)
5. Verify configuration settings

### Updating the System

To update the backup system:

1. Test changes in staging environment
2. Create backup before updating
3. Update scripts and configuration
4. Verify functionality after update
5. Update documentation as needed

### Contact Information

For system administration support:
- Email: admin@journal.joshsisto.com
- Documentation: This guide
- Log files: `/home/josh/Sync2/projects/journal/`

---

*Last updated: July 8, 2024*
*Version: 1.0.0*