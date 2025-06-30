# Production Deployment Guide

## Safe Deployment Workflow

### Before Deployment
```bash
# 1. Create pre-deployment backup
./backup.sh pre-deploy

# 2. Test changes locally
python app.py
# Test functionality

# 3. Commit changes
git add .
git commit -m "Your changes"
```

### Deployment
```bash
# 4. Deploy changes (git pull, restart services, etc.)
git pull origin main

# 5. Run database migrations if needed
python recreate_db.py  # Only if schema changed
```

### If Something Goes Wrong
```bash
# Quick rollback to previous backup
./backup.sh list                    # Find backup timestamp
./backup.sh rollback TIMESTAMP      # Replace with actual timestamp
```

## Backup System Usage

### Create Backups
```bash
./backup.sh backup              # Full backup (recommended)
./backup.sh backup --db-only    # Database only
./backup.sh backup --code-only  # Codebase only
```

### List Backups
```bash
./backup.sh list
```

### Restore from Backup
```bash
# Stop application first
./backup.sh rollback TIMESTAMP
# OR manually:
./backup.sh restore TIMESTAMP
```

## Backup Strategy

### Automatic Backups
Add to crontab for automatic backups:
```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily backup at 2 AM
0 2 * * * cd /path/to/journal && ./backup.sh backup --db-only >> logs/backup.log 2>&1

# Weekly full backup on Sunday at 3 AM  
0 3 * * 0 cd /path/to/journal && ./backup.sh backup >> logs/backup.log 2>&1
```

### Manual Backups
- Before any major deployment: `./backup.sh pre-deploy`
- Before database migrations: `./backup.sh backup`
- Before major code changes: `./backup.sh backup`

## Database Corruption Prevention

The backup system uses SQLite's atomic backup API to prevent corruption:

1. **Consistent Snapshots**: Uses SQLite's backup API for atomic copies
2. **Pre-restore Backups**: Creates backup of current DB before restore
3. **Application Stopping**: Ensures app is stopped during critical operations
4. **Manifest Files**: Tracks what was backed up and when

## Emergency Recovery

If database is corrupted:
```bash
# 1. Stop application
pkill -f "python.*app.py"

# 2. List available backups
./backup.sh list

# 3. Restore from most recent good backup
./backup.sh restore TIMESTAMP

# 4. Start application
python app.py
```

## Monitoring

Check backup logs:
```bash
tail -f logs/backup.log  
```

Verify backup integrity:
```bash
# Test that backed up database can be opened
sqlite3 backups/db_TIMESTAMP/instance_journal.db ".tables"
```