#!/usr/bin/env python3
"""
Comprehensive backup system for the journal application.
Supports PostgreSQL and SQLite databases with full backup, restore, and monitoring capabilities.
"""

import os
import sys
import shutil
import subprocess
import datetime
import json
import argparse
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Backup type enumeration."""
    FULL = "full"
    DATABASE = "database"
    CODEBASE = "codebase"

@dataclass
class BackupMetadata:
    """Backup metadata structure."""
    timestamp: str
    backup_type: BackupType
    database_type: str
    created_at: str
    git_commit: str
    git_branch: str
    total_size: int
    checksum: str
    files: Dict[str, str]

class ComprehensiveBackupSystem:
    """Comprehensive backup system with PostgreSQL and SQLite support."""
    
    def __init__(self, project_root: str = None):
        """Initialize backup system."""
        self.project_root = Path(project_root or os.getcwd())
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.backup_dir / "daily").mkdir(exist_ok=True)
        (self.backup_dir / "weekly").mkdir(exist_ok=True)
        (self.backup_dir / "monthly").mkdir(exist_ok=True)
        
        # SQLite database paths
        self.sqlite_paths = [
            self.project_root / "instance" / "journal.db",
            self.project_root / "journal.db",
            self.project_root / "admin" / "journal.db"
        ]
        
        # Load database configuration
        self._load_db_config()
        
        # Backup retention settings
        self.retention_policy = {
            "daily": 7,    # Keep 7 daily backups
            "weekly": 4,   # Keep 4 weekly backups
            "monthly": 6   # Keep 6 monthly backups
        }
        
        logger.info(f"Backup system initialized. Database type: {'PostgreSQL' if self.use_postgresql else 'SQLite'}")
    
    def _load_db_config(self):
        """Load database configuration from environment."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv not available, using environment variables only")
        
        self.use_postgresql = os.environ.get('USE_POSTGRESQL', '').lower() == 'true'
        
        if self.use_postgresql:
            self.pg_config = {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'port': os.environ.get('DB_PORT', '5432'),
                'database': os.environ.get('DB_NAME', 'journal_db'),
                'user': os.environ.get('DB_USER', 'journal_user'),
                'password': os.environ.get('DB_PASSWORD')
            }
            
            if not self.pg_config['password']:
                logger.error("PostgreSQL password not found in environment")
                raise ValueError("DB_PASSWORD environment variable required for PostgreSQL")
        else:
            self.pg_config = None
    
    def get_timestamp(self) -> str:
        """Get formatted timestamp for backup naming."""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_backup_category(self, timestamp: str = None) -> str:
        """Determine backup category based on timestamp."""
        if not timestamp:
            timestamp = self.get_timestamp()
        
        dt = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        
        # Monthly backup on 1st of month
        if dt.day == 1:
            return "monthly"
        # Weekly backup on Sundays
        elif dt.weekday() == 6:
            return "weekly"
        else:
            return "daily"
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def verify_backup_integrity(self, backup_path: str, expected_checksum: str) -> bool:
        """Verify backup file integrity using checksum."""
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        actual_checksum = self.calculate_checksum(backup_path)
        if actual_checksum != expected_checksum:
            logger.error(f"Checksum mismatch for {backup_path}")
            logger.error(f"Expected: {expected_checksum}")
            logger.error(f"Actual: {actual_checksum}")
            return False
        
        logger.info(f"Backup integrity verified: {backup_path}")
        return True
    
    def backup_postgresql(self, timestamp: str = None) -> Optional[Tuple[str, str]]:
        """
        Create PostgreSQL database backup using pg_dump.
        
        Returns:
            Tuple of (backup_file_path, checksum) or None if failed
        """
        if not self.use_postgresql or not self.pg_config:
            logger.error("PostgreSQL not configured")
            return None
        
        if not timestamp:
            timestamp = self.get_timestamp()
        
        category = self.get_backup_category(timestamp)
        db_backup_dir = self.backup_dir / category / f"db_{timestamp}"
        db_backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = db_backup_dir / f"postgresql_{self.pg_config['database']}.sql"
        
        try:
            logger.info(f"Creating PostgreSQL backup: {self.pg_config['database']}")
            
            # Set password for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = self.pg_config['password']
            
            # Create pg_dump command with comprehensive options
            cmd = [
                'pg_dump',
                '-h', self.pg_config['host'],
                '-p', self.pg_config['port'],
                '-U', self.pg_config['user'],
                '-d', self.pg_config['database'],
                '--verbose',
                '--no-password',
                '--create',           # Include CREATE DATABASE statement
                '--clean',            # Include DROP statements
                '--if-exists',        # Use IF EXISTS for drops
                '--format=custom',    # Use custom format for better compression
                '--compress=9'        # Maximum compression
            ]
            
            # Use custom format for better compression and features
            custom_backup_file = db_backup_dir / f"postgresql_{self.pg_config['database']}.dump"
            cmd.extend(['-f', str(custom_backup_file)])
            
            # Run pg_dump
            result = subprocess.run(
                cmd,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                file_size = custom_backup_file.stat().st_size
                checksum = self.calculate_checksum(str(custom_backup_file))
                
                # Also create a plain SQL backup for easier inspection
                sql_cmd = cmd[:-2] + ['--format=plain', '-f', str(backup_file)]
                subprocess.run(sql_cmd, env=env, timeout=600)
                
                logger.info(f"PostgreSQL backup created: {custom_backup_file} ({file_size:,} bytes)")
                return str(custom_backup_file), checksum
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("PostgreSQL backup timed out")
            return None
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            return None
    
    def backup_sqlite(self, timestamp: str = None) -> Dict[str, Tuple[str, str]]:
        """
        Create backup of SQLite database files.
        
        Returns:
            Dict mapping original paths to (backup_path, checksum) tuples
        """
        if not timestamp:
            timestamp = self.get_timestamp()
        
        category = self.get_backup_category(timestamp)
        db_backup_dir = self.backup_dir / category / f"db_{timestamp}"
        db_backup_dir.mkdir(parents=True, exist_ok=True)
        
        backups = {}
        
        for db_path in self.sqlite_paths:
            if db_path.exists():
                try:
                    # Create backup filename
                    backup_name = f"{db_path.parent.name}_{db_path.name}"
                    backup_path = db_backup_dir / backup_name
                    
                    # Create vacuum backup for better consistency
                    self._vacuum_sqlite_backup(str(db_path), str(backup_path))
                    
                    file_size = backup_path.stat().st_size
                    checksum = self.calculate_checksum(str(backup_path))
                    
                    backups[str(db_path)] = (str(backup_path), checksum)
                    
                    logger.info(f"SQLite backup: {db_path} -> {backup_path} ({file_size:,} bytes)")
                    
                except Exception as e:
                    logger.error(f"Failed to backup {db_path}: {e}")
        
        return backups
    
    def _vacuum_sqlite_backup(self, source_db: str, backup_path: str):
        """Create a vacuum backup of SQLite database for consistency."""
        try:
            # Connect to source database
            conn = sqlite3.connect(source_db)
            
            # Create backup with vacuum
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            
            # Vacuum the backup for optimal storage
            backup_conn.execute('VACUUM;')
            
            # Close connections
            backup_conn.close()
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"SQLite vacuum backup failed: {e}")
            # Fall back to simple copy
            shutil.copy2(source_db, backup_path)
    
    def backup_database(self, timestamp: str = None) -> Dict[str, Any]:
        """
        Backup database (PostgreSQL or SQLite based on configuration).
        
        Returns:
            Dict with backup information
        """
        if not timestamp:
            timestamp = self.get_timestamp()
        
        backups = {}
        
        if self.use_postgresql:
            pg_backup = self.backup_postgresql(timestamp)
            if pg_backup:
                backups['postgresql'] = {
                    'path': pg_backup[0],
                    'checksum': pg_backup[1],
                    'type': 'postgresql'
                }
        else:
            sqlite_backups = self.backup_sqlite(timestamp)
            for original_path, (backup_path, checksum) in sqlite_backups.items():
                backups[original_path] = {
                    'path': backup_path,
                    'checksum': checksum,
                    'type': 'sqlite'
                }
        
        return backups
    
    def backup_codebase(self, timestamp: str = None) -> Optional[Tuple[str, str]]:
        """
        Create backup of the entire codebase.
        
        Returns:
            Tuple of (backup_file_path, checksum) or None if failed
        """
        if not timestamp:
            timestamp = self.get_timestamp()
        
        category = self.get_backup_category(timestamp)
        backup_file = self.backup_dir / category / f"codebase_{timestamp}.tar.gz"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info("Creating codebase backup...")
            
            # Comprehensive exclude patterns
            exclude_patterns = [
                '--exclude=backups',
                '--exclude=__pycache__',
                '--exclude=*.pyc',
                '--exclude=*.pyo',
                '--exclude=.git',
                '--exclude=.env',
                '--exclude=.env.local',
                '--exclude=venv',
                '--exclude=.venv',
                '--exclude=env',
                '--exclude=node_modules',
                '--exclude=uploads',
                '--exclude=*.log',
                '--exclude=.pytest_cache',
                '--exclude=.coverage',
                '--exclude=htmlcov',
                '--exclude=.tox',
                '--exclude=.mypy_cache',
                '--exclude=.DS_Store',
                '--exclude=Thumbs.db',
                '--exclude=*.tmp',
                '--exclude=*.swp',
                '--exclude=*.swo',
                '--exclude=*~'
            ]
            
            # Create tar command
            cmd = [
                'tar', 'czf', str(backup_file)
            ] + exclude_patterns + [
                '-C', str(self.project_root.parent),
                self.project_root.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 minute timeout
            
            if result.returncode == 0:
                file_size = backup_file.stat().st_size
                checksum = self.calculate_checksum(str(backup_file))
                
                logger.info(f"Codebase backup created: {backup_file} ({file_size:,} bytes)")
                return str(backup_file), checksum
            else:
                logger.error(f"Codebase backup failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Codebase backup timed out")
            return None
        except Exception as e:
            logger.error(f"Codebase backup failed: {e}")
            return None
    
    def create_full_backup(self, backup_type: BackupType = BackupType.FULL) -> bool:
        """Create full backup (database + codebase)."""
        timestamp = self.get_timestamp()
        
        logger.info(f"Creating {backup_type.value} backup: {timestamp}")
        logger.info("=" * 50)
        
        backup_results = {}
        
        # Backup database
        if backup_type in [BackupType.FULL, BackupType.DATABASE]:
            db_backups = self.backup_database(timestamp)
            backup_results['database'] = db_backups
        
        # Backup codebase
        if backup_type in [BackupType.FULL, BackupType.CODEBASE]:
            codebase_backup = self.backup_codebase(timestamp)
            if codebase_backup:
                backup_results['codebase'] = {
                    'path': codebase_backup[0],
                    'checksum': codebase_backup[1],
                    'type': 'codebase'
                }
        
        # Create comprehensive metadata
        metadata = BackupMetadata(
            timestamp=timestamp,
            backup_type=backup_type,
            database_type='postgresql' if self.use_postgresql else 'sqlite',
            created_at=datetime.datetime.now().isoformat(),
            git_commit=self._get_git_info()['commit'],
            git_branch=self._get_git_info()['branch'],
            total_size=self._calculate_total_size(backup_results),
            checksum=self._calculate_combined_checksum(backup_results),
            files=self._extract_file_paths(backup_results)
        )
        
        # Save metadata
        category = self.get_backup_category(timestamp)
        manifest_file = self.backup_dir / category / f"manifest_{timestamp}.json"
        
        manifest_data = {
            "metadata": metadata.__dict__,
            "backup_results": backup_results,
            "git_info": self._get_git_info(),
            "project_root": str(self.project_root),
            "retention_policy": self.retention_policy
        }
        
        # Convert enum to string for JSON serialization
        manifest_data["metadata"]["backup_type"] = backup_type.value
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        logger.info(f"Backup manifest: {manifest_file}")
        
        # Verify backup integrity
        if self._verify_backup_integrity(manifest_data):
            logger.info("✅ Backup integrity verified")
        else:
            logger.warning("⚠️  Backup integrity verification failed")
        
        success = bool(backup_results)
        if success:
            logger.info("✅ Backup completed successfully")
        else:
            logger.error("❌ Backup failed")
        
        return success
    
    def _calculate_total_size(self, backup_results: Dict[str, Any]) -> int:
        """Calculate total size of all backup files."""
        total_size = 0
        
        for category, backups in backup_results.items():
            if category == 'database':
                for backup_info in backups.values():
                    if os.path.exists(backup_info['path']):
                        total_size += os.path.getsize(backup_info['path'])
            elif category == 'codebase':
                if os.path.exists(backups['path']):
                    total_size += os.path.getsize(backups['path'])
        
        return total_size
    
    def _calculate_combined_checksum(self, backup_results: Dict[str, Any]) -> str:
        """Calculate combined checksum of all backup files."""
        all_checksums = []
        
        for category, backups in backup_results.items():
            if category == 'database':
                for backup_info in backups.values():
                    all_checksums.append(backup_info['checksum'])
            elif category == 'codebase':
                all_checksums.append(backups['checksum'])
        
        combined = "".join(sorted(all_checksums))
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _extract_file_paths(self, backup_results: Dict[str, Any]) -> Dict[str, str]:
        """Extract file paths from backup results."""
        files = {}
        
        for category, backups in backup_results.items():
            if category == 'database':
                for original_path, backup_info in backups.items():
                    files[f"database_{original_path}"] = backup_info['path']
            elif category == 'codebase':
                files['codebase'] = backups['path']
        
        return files
    
    def _verify_backup_integrity(self, manifest_data: Dict[str, Any]) -> bool:
        """Verify integrity of all backup files."""
        backup_results = manifest_data.get('backup_results', {})
        
        for category, backups in backup_results.items():
            if category == 'database':
                for backup_info in backups.values():
                    if not self.verify_backup_integrity(backup_info['path'], backup_info['checksum']):
                        return False
            elif category == 'codebase':
                if not self.verify_backup_integrity(backups['path'], backups['checksum']):
                    return False
        
        return True
    
    def _get_git_info(self) -> Dict[str, str]:
        """Get current git information."""
        try:
            # Get current commit hash
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            commit = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get current branch
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get status
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            is_clean = len(result.stdout.strip()) == 0 if result.returncode == 0 else False
            
            return {
                "commit": commit,
                "branch": branch,
                "is_clean": is_clean
            }
        except Exception as e:
            logger.error(f"Failed to get git info: {e}")
            return {"commit": "unknown", "branch": "unknown", "is_clean": False}
    
    def restore_postgresql(self, backup_file: str) -> bool:
        """
        Restore PostgreSQL database from backup file.
        
        Args:
            backup_file: Path to backup file (can be .sql or .dump)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_postgresql or not self.pg_config:
            logger.error("PostgreSQL not configured")
            return False
        
        if not os.path.exists(backup_file):
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        try:
            logger.info(f"Restoring PostgreSQL database from: {backup_file}")
            
            # Set password for psql/pg_restore
            env = os.environ.copy()
            env['PGPASSWORD'] = self.pg_config['password']
            
            # Drop and recreate database
            logger.info("Dropping and recreating database...")
            
            # Connect to postgres database to drop and recreate
            drop_cmd = [
                'psql',
                '-h', self.pg_config['host'],
                '-p', self.pg_config['port'],
                '-U', self.pg_config['user'],
                '-d', 'postgres',
                '-c', f"DROP DATABASE IF EXISTS {self.pg_config['database']}"
            ]
            
            result = subprocess.run(drop_cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to drop database: {result.stderr}")
                return False
            
            # Create new database
            create_cmd = [
                'psql',
                '-h', self.pg_config['host'],
                '-p', self.pg_config['port'],
                '-U', self.pg_config['user'],
                '-d', 'postgres',
                '-c', f"CREATE DATABASE {self.pg_config['database']}"
            ]
            
            result = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to create database: {result.stderr}")
                return False
            
            # Restore from backup
            logger.info("Restoring data...")
            
            # Determine restore command based on file extension
            if backup_file.endswith('.dump'):
                # Custom format backup
                restore_cmd = [
                    'pg_restore',
                    '-h', self.pg_config['host'],
                    '-p', self.pg_config['port'],
                    '-U', self.pg_config['user'],
                    '-d', self.pg_config['database'],
                    '--verbose',
                    '--clean',
                    '--if-exists',
                    backup_file
                ]
            else:
                # Plain SQL backup
                restore_cmd = [
                    'psql',
                    '-h', self.pg_config['host'],
                    '-p', self.pg_config['port'],
                    '-U', self.pg_config['user'],
                    '-d', self.pg_config['database'],
                    '-f', backup_file
                ]
            
            result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ PostgreSQL database restored successfully")
                return True
            else:
                logger.error(f"Failed to restore database: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"PostgreSQL restore failed: {e}")
            return False
    
    def restore_sqlite(self, backup_files: Dict[str, str]) -> bool:
        """
        Restore SQLite database files from backup.
        
        Args:
            backup_files: Dict mapping original paths to backup paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Restoring SQLite databases...")
            
            for original_path, backup_path in backup_files.items():
                if not os.path.exists(backup_path):
                    logger.error(f"Backup file not found: {backup_path}")
                    continue
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                
                # Copy backup to original location
                shutil.copy2(backup_path, original_path)
                logger.info(f"Restored: {backup_path} -> {original_path}")
            
            logger.info("✅ SQLite databases restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"SQLite restore failed: {e}")
            return False
    
    def restore_codebase(self, backup_file: str) -> bool:
        """
        Restore codebase from backup archive.
        
        Args:
            backup_file: Path to codebase backup archive
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(backup_file):
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        try:
            logger.info(f"Restoring codebase from: {backup_file}")
            
            # Create temporary directory for extraction
            temp_dir = self.project_root.parent / f"temp_restore_{self.get_timestamp()}"
            temp_dir.mkdir(exist_ok=True)
            
            # Extract archive
            cmd = ['tar', 'xzf', backup_file, '-C', str(temp_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to extract backup: {result.stderr}")
                shutil.rmtree(temp_dir)
                return False
            
            # Find extracted project directory
            extracted_dir = temp_dir / self.project_root.name
            if not extracted_dir.exists():
                logger.error(f"Extracted directory not found: {extracted_dir}")
                shutil.rmtree(temp_dir)
                return False
            
            # Backup current codebase
            current_backup = self.project_root.parent / f"current_backup_{self.get_timestamp()}"
            shutil.move(str(self.project_root), str(current_backup))
            
            # Move extracted codebase to original location
            shutil.move(str(extracted_dir), str(self.project_root))
            
            # Clean up
            shutil.rmtree(temp_dir)
            
            logger.info("✅ Codebase restored successfully")
            logger.info(f"Previous codebase backed up to: {current_backup}")
            
            return True
            
        except Exception as e:
            logger.error(f"Codebase restore failed: {e}")
            return False
    
    def list_backups(self, show_sizes: bool = False) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        
        # Search in all categories
        for category in ['daily', 'weekly', 'monthly', '.']:
            category_dir = self.backup_dir / category if category != '.' else self.backup_dir
            
            for manifest_file in sorted(category_dir.glob("manifest_*.json")):
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                    
                    # Handle both new and old manifest formats
                    metadata = manifest.get('metadata', {})
                    
                    # If no metadata section, it's an old format
                    if not metadata:
                        # Old format - extract info directly from manifest
                        backup_info = {
                            "timestamp": manifest.get("timestamp", "unknown"),
                            "created_at": manifest.get("created_at", "unknown"),
                            "backup_type": "full" if manifest.get("codebase_backup") else "database",
                            "database_type": "sqlite",  # Old format was SQLite
                            "git_commit": manifest.get("git_info", {}).get("commit", "unknown")[:8],
                            "git_branch": manifest.get("git_info", {}).get("branch", "unknown"),
                            "category": category,
                            "manifest_file": str(manifest_file)
                        }
                        
                        if show_sizes:
                            # Calculate size from old format
                            total_size = 0
                            # Database backups
                            for backup_path in manifest.get("database_backups", {}).values():
                                if os.path.exists(backup_path):
                                    total_size += os.path.getsize(backup_path)
                            # Codebase backup
                            codebase_backup = manifest.get("codebase_backup")
                            if codebase_backup and os.path.exists(codebase_backup):
                                total_size += os.path.getsize(codebase_backup)
                            backup_info["total_size"] = total_size
                    else:
                        # New format
                        backup_info = {
                            "timestamp": metadata.get("timestamp", "unknown"),
                            "created_at": metadata.get("created_at", "unknown"),
                            "backup_type": metadata.get("backup_type", "unknown"),
                            "database_type": metadata.get("database_type", "unknown"),
                            "git_commit": metadata.get("git_commit", "unknown")[:8],
                            "git_branch": metadata.get("git_branch", "unknown"),
                            "category": category,
                            "manifest_file": str(manifest_file)
                        }
                        
                        if show_sizes:
                            backup_info["total_size"] = metadata.get("total_size", 0)
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    logger.warning(f"Error reading manifest {manifest_file}: {e}")
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def cleanup_old_backups(self, dry_run: bool = False) -> Dict[str, int]:
        """Clean up old backups according to retention policy."""
        logger.info("Cleaning up old backups...")
        
        cleanup_stats = {"daily": 0, "weekly": 0, "monthly": 0}
        
        for category, keep_count in self.retention_policy.items():
            category_dir = self.backup_dir / category
            if not category_dir.exists():
                continue
            
            # Get all manifests in this category
            manifests = sorted(category_dir.glob("manifest_*.json"), reverse=True)
            
            # Keep only the most recent backups
            to_remove = manifests[keep_count:]
            
            for manifest_file in to_remove:
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                    
                    timestamp = manifest.get('metadata', {}).get('timestamp', 'unknown')
                    
                    if dry_run:
                        logger.info(f"Would remove {category} backup: {timestamp}")
                    else:
                        # Remove all files associated with this backup
                        self._remove_backup_files(manifest)
                        logger.info(f"Removed {category} backup: {timestamp}")
                    
                    cleanup_stats[category] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {manifest_file}: {e}")
        
        action = "Would remove" if dry_run else "Removed"
        logger.info(f"{action} {sum(cleanup_stats.values())} old backups")
        
        return cleanup_stats
    
    def _remove_backup_files(self, manifest: Dict[str, Any]):
        """Remove all files associated with a backup."""
        backup_results = manifest.get('backup_results', {})
        
        # Remove database backups
        for category, backups in backup_results.items():
            if category == 'database':
                for backup_info in backups.values():
                    backup_path = backup_info['path']
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        # Remove parent directory if empty
                        try:
                            os.rmdir(os.path.dirname(backup_path))
                        except OSError:
                            pass  # Directory not empty
            elif category == 'codebase':
                backup_path = backups['path']
                if os.path.exists(backup_path):
                    os.remove(backup_path)
        
        # Remove manifest file
        manifest_file = manifest.get('metadata', {}).get('manifest_file')
        if manifest_file and os.path.exists(manifest_file):
            os.remove(manifest_file)
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get comprehensive backup statistics."""
        backups = self.list_backups(show_sizes=True)
        
        stats = {
            "total_backups": len(backups),
            "total_size": sum(b.get("total_size", 0) for b in backups),
            "by_category": {"daily": 0, "weekly": 0, "monthly": 0, "other": 0},
            "by_type": {"full": 0, "database": 0, "codebase": 0},
            "oldest_backup": None,
            "newest_backup": None,
            "database_type": "postgresql" if self.use_postgresql else "sqlite"
        }
        
        for backup in backups:
            # Count by category
            category = backup.get("category", "other")
            if category in stats["by_category"]:
                stats["by_category"][category] += 1
            else:
                stats["by_category"]["other"] += 1
            
            # Count by type
            backup_type = backup.get("backup_type", "unknown")
            if backup_type in stats["by_type"]:
                stats["by_type"][backup_type] += 1
        
        if backups:
            stats["oldest_backup"] = backups[-1]["timestamp"]
            stats["newest_backup"] = backups[0]["timestamp"]
        
        return stats


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Comprehensive backup system for journal application")
    parser.add_argument('action', choices=[
        'backup', 'list', 'restore', 'cleanup', 'stats', 'verify', 'remove', 'size'
    ], help='Action to perform')
    
    parser.add_argument('timestamp', nargs='?', help='Timestamp for restore/remove operations')
    parser.add_argument('--db-only', action='store_true', help='Database backup only')
    parser.add_argument('--code-only', action='store_true', help='Codebase backup only')
    parser.add_argument('--size', action='store_true', help='Show backup sizes')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
    
    args = parser.parse_args()
    
    try:
        backup_system = ComprehensiveBackupSystem()
        
        if args.action == 'backup':
            if args.db_only:
                backup_system.create_full_backup(BackupType.DATABASE)
            elif args.code_only:
                backup_system.create_full_backup(BackupType.CODEBASE)
            else:
                backup_system.create_full_backup(BackupType.FULL)
        
        elif args.action == 'list':
            backups = backup_system.list_backups(show_sizes=args.size)
            
            if not backups:
                print("No backups found")
                return
            
            print("Available backups:")
            print("-" * 80)
            
            for backup in backups:
                timestamp = backup['timestamp']
                created_at = backup['created_at']
                backup_type = backup['backup_type']
                category = backup['category']
                git_info = f"{backup['git_branch']}:{backup['git_commit']}"
                
                if args.size and 'total_size' in backup:
                    size_mb = backup['total_size'] / (1024 * 1024)
                    print(f"{timestamp} | {backup_type:8} | {category:7} | {git_info:15} | {size_mb:6.1f} MB")
                else:
                    print(f"{timestamp} | {backup_type:8} | {category:7} | {git_info:15} | {created_at}")
        
        elif args.action == 'restore':
            if not args.timestamp:
                print("❌ Timestamp required for restore")
                return
            
            # Find backup manifest
            manifest_file = None
            for category in ['daily', 'weekly', 'monthly', '.']:
                category_dir = backup_system.backup_dir / category if category != '.' else backup_system.backup_dir
                potential_file = category_dir / f"manifest_{args.timestamp}.json"
                if potential_file.exists():
                    manifest_file = potential_file
                    break
            
            if not manifest_file:
                print(f"❌ Backup not found: {args.timestamp}")
                return
            
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            backup_results = manifest.get('backup_results', {})
            
            # Restore database
            if 'database' in backup_results:
                if backup_system.use_postgresql:
                    pg_backup = backup_results['database'].get('postgresql', {}).get('path')
                    if pg_backup:
                        backup_system.restore_postgresql(pg_backup)
                else:
                    sqlite_backups = {k: v['path'] for k, v in backup_results['database'].items()}
                    backup_system.restore_sqlite(sqlite_backups)
            
            # Restore codebase
            if 'codebase' in backup_results:
                codebase_backup = backup_results['codebase'].get('path')
                if codebase_backup:
                    backup_system.restore_codebase(codebase_backup)
        
        elif args.action == 'cleanup':
            backup_system.cleanup_old_backups(dry_run=args.dry_run)
        
        elif args.action == 'stats':
            stats = backup_system.get_backup_stats()
            print("Backup Statistics:")
            print("=" * 40)
            print(f"Total backups: {stats['total_backups']}")
            print(f"Total size: {stats['total_size'] / (1024*1024*1024):.2f} GB")
            print(f"Database type: {stats['database_type']}")
            print(f"Newest backup: {stats['newest_backup']}")
            print(f"Oldest backup: {stats['oldest_backup']}")
            print("\nBy category:")
            for category, count in stats['by_category'].items():
                print(f"  {category}: {count}")
            print("\nBy type:")
            for backup_type, count in stats['by_type'].items():
                print(f"  {backup_type}: {count}")
        
        elif args.action == 'remove':
            if not args.timestamp:
                print("❌ Timestamp required for remove")
                return
            
            # Find and remove backup
            manifest_file = None
            for category in ['daily', 'weekly', 'monthly', '.']:
                category_dir = backup_system.backup_dir / category if category != '.' else backup_system.backup_dir
                potential_file = category_dir / f"manifest_{args.timestamp}.json"
                if potential_file.exists():
                    manifest_file = potential_file
                    break
            
            if not manifest_file:
                print(f"❌ Backup not found: {args.timestamp}")
                return
            
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            backup_system._remove_backup_files(manifest)
            print(f"✅ Removed backup: {args.timestamp}")
        
        elif args.action == 'verify':
            if args.timestamp:
                # Verify specific backup
                manifest_file = None
                for category in ['daily', 'weekly', 'monthly', '.']:
                    category_dir = backup_system.backup_dir / category if category != '.' else backup_system.backup_dir
                    potential_file = category_dir / f"manifest_{args.timestamp}.json"
                    if potential_file.exists():
                        manifest_file = potential_file
                        break
                
                if not manifest_file:
                    print(f"❌ Backup not found: {args.timestamp}")
                    return
                
                with open(manifest_file) as f:
                    manifest = json.load(f)
                
                if backup_system._verify_backup_integrity(manifest):
                    print(f"✅ Backup {args.timestamp} integrity verified")
                else:
                    print(f"❌ Backup {args.timestamp} integrity check failed")
            else:
                # Verify all backups
                backups = backup_system.list_backups()
                verified = 0
                failed = 0
                
                for backup in backups:
                    manifest_file = backup['manifest_file']
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                    
                    if backup_system._verify_backup_integrity(manifest):
                        verified += 1
                    else:
                        failed += 1
                        print(f"❌ Failed: {backup['timestamp']}")
                
                print(f"Verified: {verified}, Failed: {failed}")
        
        elif args.action == 'size':
            if args.timestamp:
                # Show size of specific backup
                manifest_file = None
                for category in ['daily', 'weekly', 'monthly', '.']:
                    category_dir = backup_system.backup_dir / category if category != '.' else backup_system.backup_dir
                    potential_file = category_dir / f"manifest_{args.timestamp}.json"
                    if potential_file.exists():
                        manifest_file = potential_file
                        break
                
                if not manifest_file:
                    print(f"❌ Backup not found: {args.timestamp}")
                    return
                
                with open(manifest_file) as f:
                    manifest = json.load(f)
                
                metadata = manifest.get('metadata', {})
                size_mb = metadata.get('total_size', 0) / (1024 * 1024)
                print(f"Backup {args.timestamp}: {size_mb:.1f} MB")
            else:
                # Show total size of all backups
                stats = backup_system.get_backup_stats()
                size_gb = stats['total_size'] / (1024 * 1024 * 1024)
                print(f"Total backup size: {size_gb:.2f} GB")
    
    except Exception as e:
        logger.error(f"Backup system error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()