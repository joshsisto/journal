#!/usr/bin/env python3
"""
Comprehensive backup system for journal application.
Provides database and codebase backups with rollback capabilities.
"""

import os
import sys
import sqlite3
import shutil
import subprocess
import datetime
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BackupSystem:
    """Handles database and codebase backups with rollback functionality."""
    
    def __init__(self, project_root: str = None):
        """Initialize backup system."""
        self.project_root = Path(project_root or os.getcwd())
        self.backup_dir = self.project_root / "backups"
        self.db_paths = [
            self.project_root / "instance" / "journal.db",
            self.project_root / "journal.db",
            self.project_root / "admin" / "journal.db"
        ]
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_timestamp(self) -> str:
        """Get formatted timestamp for backup naming."""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def backup_database(self, timestamp: str = None) -> Dict[str, str]:
        """
        Create backup of all database files.
        
        Args:
            timestamp: Optional timestamp for backup naming
            
        Returns:
            Dict mapping original paths to backup paths
        """
        if not timestamp:
            timestamp = self.get_timestamp()
            
        db_backup_dir = self.backup_dir / f"db_{timestamp}"
        db_backup_dir.mkdir(exist_ok=True)
        
        backed_up = {}
        
        for db_path in self.db_paths:
            if db_path.exists() and db_path.stat().st_size > 0:
                # Create atomic backup using SQLite backup API
                backup_path = db_backup_dir / f"{db_path.parent.name}_{db_path.name}"
                
                try:
                    # Use SQLite's backup API for consistent snapshots
                    source_conn = sqlite3.connect(str(db_path))
                    backup_conn = sqlite3.connect(str(backup_path))
                    source_conn.backup(backup_conn)
                    source_conn.close()
                    backup_conn.close()
                    
                    backed_up[str(db_path)] = str(backup_path)
                    print(f"✓ Database backed up: {db_path} -> {backup_path}")
                    
                except Exception as e:
                    print(f"✗ Failed to backup {db_path}: {e}")
                    
        return backed_up
    
    def backup_codebase(self, timestamp: str = None) -> str:
        """
        Create git-based backup of codebase.
        
        Args:
            timestamp: Optional timestamp for backup naming
            
        Returns:
            Path to backup archive
        """
        if not timestamp:
            timestamp = self.get_timestamp()
            
        # Create git archive for consistent codebase snapshot
        archive_path = self.backup_dir / f"codebase_{timestamp}.tar.gz"
        
        try:
            # Check if we're in a git repository
            subprocess.run(
                ["git", "rev-parse", "--git-dir"], 
                cwd=self.project_root, 
                check=True, 
                capture_output=True
            )
            
            # Create archive of current commit + staged changes
            subprocess.run([
                "git", "archive", 
                "--format=tar.gz",
                f"--output={archive_path}",
                "HEAD"
            ], cwd=self.project_root, check=True)
            
            # Also backup any unstaged changes
            unstaged_path = self.backup_dir / f"unstaged_{timestamp}.tar.gz"
            subprocess.run([
                "tar", "-czf", str(unstaged_path),
                "--exclude=backups",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "--exclude=.git",
                "."
            ], cwd=self.project_root, check=True)
            
            print(f"✓ Codebase backed up: {archive_path}")
            print(f"✓ Unstaged changes backed up: {unstaged_path}")
            return str(archive_path)
            
        except subprocess.CalledProcessError:
            # Fallback to tar if not in git repo
            subprocess.run([
                "tar", "-czf", str(archive_path),
                "--exclude=backups",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "."
            ], cwd=self.project_root, check=True)
            
            print(f"✓ Codebase backed up (tar): {archive_path}")
            return str(archive_path)
    
    def create_backup_manifest(self, timestamp: str, db_backups: Dict[str, str], 
                             code_backup: str) -> str:
        """Create manifest file with backup details."""
        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        
        # Get current git info if available
        git_info = {}
        try:
            git_info["commit"] = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.project_root, 
                capture_output=True, 
                text=True, 
                check=True
            ).stdout.strip()
            
            git_info["branch"] = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                cwd=self.project_root, 
                capture_output=True, 
                text=True, 
                check=True
            ).stdout.strip()
        except subprocess.CalledProcessError:
            pass
        
        manifest = {
            "timestamp": timestamp,
            "created_at": datetime.datetime.now().isoformat(),
            "database_backups": db_backups,
            "codebase_backup": code_backup,
            "git_info": git_info,
            "project_root": str(self.project_root)
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        print(f"✓ Manifest created: {manifest_path}")
        return str(manifest_path)
    
    def full_backup(self) -> str:
        """
        Create complete backup of database and codebase.
        
        Returns:
            Timestamp of created backup
        """
        timestamp = self.get_timestamp()
        print(f"Creating full backup: {timestamp}")
        
        # Backup database
        db_backups = self.backup_database(timestamp)
        
        # Backup codebase
        code_backup = self.backup_codebase(timestamp)
        
        # Create manifest
        manifest_path = self.create_backup_manifest(timestamp, db_backups, code_backup)
        
        print(f"\n✓ Full backup complete: {timestamp}")
        print(f"  Manifest: {manifest_path}")
        return timestamp
    
    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []
        
        for manifest_file in self.backup_dir.glob("manifest_*.json"):
            try:
                with open(manifest_file) as f:
                    manifest = json.load(f)
                    backups.append(manifest)
            except Exception as e:
                print(f"Warning: Could not read {manifest_file}: {e}")
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
    
    def cleanup_old_backups(self, keep_daily: int = 7, keep_weekly: int = 4, 
                           keep_monthly: int = 6) -> List[str]:
        """
        Clean up old backups based on retention policy.
        
        Args:
            keep_daily: Number of daily backups to keep
            keep_weekly: Number of weekly backups to keep  
            keep_monthly: Number of monthly backups to keep
            
        Returns:
            List of removed backup timestamps
        """
        backups = self.list_backups()
        if not backups:
            return []
        
        now = datetime.datetime.now()
        removed = []
        
        # Group backups by age category
        daily_cutoff = now - datetime.timedelta(days=7)
        weekly_cutoff = now - datetime.timedelta(weeks=4) 
        monthly_cutoff = now - datetime.timedelta(days=30*6)
        
        daily_backups = []
        weekly_backups = []
        monthly_backups = []
        old_backups = []
        
        for backup in backups:
            backup_date = datetime.datetime.fromisoformat(backup["created_at"])
            
            if backup_date > daily_cutoff:
                daily_backups.append(backup)
            elif backup_date > weekly_cutoff:
                weekly_backups.append(backup)
            elif backup_date > monthly_cutoff:
                monthly_backups.append(backup)
            else:
                old_backups.append(backup)
        
        # Keep specified number of each category
        to_remove = []
        
        if len(daily_backups) > keep_daily:
            to_remove.extend(daily_backups[keep_daily:])
            
        if len(weekly_backups) > keep_weekly:
            to_remove.extend(weekly_backups[keep_weekly:])
            
        if len(monthly_backups) > keep_monthly:
            to_remove.extend(monthly_backups[keep_monthly:])
            
        # Remove all backups older than monthly retention
        to_remove.extend(old_backups)
        
        # Actually remove backup files
        for backup in to_remove:
            timestamp = backup["timestamp"]
            try:
                self.remove_backup(timestamp)
                removed.append(timestamp)
                print(f"✓ Removed old backup: {timestamp}")
            except Exception as e:
                print(f"✗ Failed to remove backup {timestamp}: {e}")
        
        if removed:
            print(f"✓ Cleaned up {len(removed)} old backups")
        else:
            print("✓ No old backups to clean up")
            
        return removed
    
    def remove_backup(self, timestamp: str) -> bool:
        """
        Remove a specific backup and all its files.
        
        Args:
            timestamp: Backup timestamp to remove
            
        Returns:
            True if successful
        """
        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        
        if not manifest_path.exists():
            print(f"✗ Backup manifest not found: {manifest_path}")
            return False
            
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            # Remove database backup directory
            db_backup_dir = self.backup_dir / f"db_{timestamp}"
            if db_backup_dir.exists():
                shutil.rmtree(db_backup_dir)
            
            # Remove codebase backup files
            code_backup = manifest.get("codebase_backup")
            if code_backup and os.path.exists(code_backup):
                os.remove(code_backup)
            
            # Remove unstaged backup if exists
            unstaged_backup = self.backup_dir / f"unstaged_{timestamp}.tar.gz"
            if unstaged_backup.exists():
                unstaged_backup.unlink()
            
            # Remove manifest
            manifest_path.unlink()
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to remove backup {timestamp}: {e}")
            return False
    
    def get_backup_size(self, timestamp: str = None) -> Dict[str, int]:
        """
        Get size information for backups.
        
        Args:
            timestamp: Specific backup timestamp, or None for all backups
            
        Returns:
            Dict with size information in bytes
        """
        if timestamp:
            # Get size for specific backup
            manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
            if not manifest_path.exists():
                return {}
                
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                
                total_size = 0
                
                # Database backup size
                db_backup_dir = self.backup_dir / f"db_{timestamp}"
                if db_backup_dir.exists():
                    for file_path in db_backup_dir.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                
                # Codebase backup size
                code_backup = manifest.get("codebase_backup")
                if code_backup and os.path.exists(code_backup):
                    total_size += os.path.getsize(code_backup)
                
                # Unstaged backup size
                unstaged_backup = self.backup_dir / f"unstaged_{timestamp}.tar.gz"
                if unstaged_backup.exists():
                    total_size += unstaged_backup.stat().st_size
                
                return {timestamp: total_size}
                
            except Exception as e:
                print(f"Warning: Could not calculate size for {timestamp}: {e}")
                return {}
        else:
            # Get total backup directory size
            total_size = 0
            for file_path in self.backup_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return {"total": total_size}
    
    def restore_database(self, timestamp: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            timestamp: Backup timestamp to restore from
            
        Returns:
            True if successful
        """
        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        
        if not manifest_path.exists():
            print(f"✗ Backup manifest not found: {manifest_path}")
            return False
            
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            db_backups = manifest["database_backups"]
            
            # Stop application first (user should handle this)
            print("⚠️  Make sure the application is stopped before restoring!")
            
            # Restore each database
            for original_path, backup_path in db_backups.items():
                if os.path.exists(backup_path):
                    # Create backup of current database
                    current_backup = f"{original_path}.pre_restore_{self.get_timestamp()}"
                    if os.path.exists(original_path):
                        shutil.copy2(original_path, current_backup)
                        print(f"✓ Current database backed up to: {current_backup}")
                    
                    # Restore from backup
                    shutil.copy2(backup_path, original_path)
                    print(f"✓ Database restored: {backup_path} -> {original_path}")
                else:
                    print(f"✗ Backup file missing: {backup_path}")
                    
            return True
            
        except Exception as e:
            print(f"✗ Database restore failed: {e}")
            return False
    
    def restore_codebase(self, timestamp: str) -> bool:
        """
        Restore codebase from backup.
        
        Args:
            timestamp: Backup timestamp to restore from
            
        Returns:
            True if successful
        """
        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        
        if not manifest_path.exists():
            print(f"✗ Backup manifest not found: {manifest_path}")
            return False
            
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            code_backup = manifest["codebase_backup"]
            
            if not os.path.exists(code_backup):
                print(f"✗ Codebase backup missing: {code_backup}")
                return False
            
            print("⚠️  Make sure the application is stopped before restoring!")
            print("⚠️  This will overwrite current codebase!")
            
            # Extract backup
            subprocess.run([
                "tar", "-xzf", code_backup, "-C", str(self.project_root)
            ], check=True)
            
            print(f"✓ Codebase restored from: {code_backup}")
            
            # If git info available, show what was restored
            git_info = manifest.get("git_info", {})
            if git_info:
                print(f"  Restored to commit: {git_info.get('commit', 'unknown')}")
                print(f"  Original branch: {git_info.get('branch', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"✗ Codebase restore failed: {e}")
            return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Journal App Backup System")
    parser.add_argument("--project-root", help="Project root directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create backup")
    backup_parser.add_argument("--db-only", action="store_true", help="Backup database only")
    backup_parser.add_argument("--code-only", action="store_true", help="Backup codebase only")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--size", action="store_true", help="Show backup sizes")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--keep-daily", type=int, default=7, help="Daily backups to keep (default: 7)")
    cleanup_parser.add_argument("--keep-weekly", type=int, default=4, help="Weekly backups to keep (default: 4)")
    cleanup_parser.add_argument("--keep-monthly", type=int, default=6, help="Monthly backups to keep (default: 6)")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove specific backup")
    remove_parser.add_argument("timestamp", help="Backup timestamp to remove")
    
    # Size command
    size_parser = subparsers.add_parser("size", help="Show backup sizes")
    size_parser.add_argument("timestamp", nargs="?", help="Specific backup timestamp")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("timestamp", help="Backup timestamp to restore")
    restore_parser.add_argument("--db-only", action="store_true", help="Restore database only")
    restore_parser.add_argument("--code-only", action="store_true", help="Restore codebase only")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup_system = BackupSystem(args.project_root)
    
    if args.command == "backup":
        if args.db_only:
            backup_system.backup_database()
        elif args.code_only:
            backup_system.backup_codebase()
        else:
            backup_system.full_backup()
            
    elif args.command == "list":
        backups = backup_system.list_backups()
        if not backups:
            print("No backups found")
        else:
            if args.size:
                print(f"{'Timestamp':<17} {'Created':<20} {'Size':<10} {'Commit':<10} {'Branch'}")
                print("-" * 80)
                for backup in backups:
                    git_info = backup.get("git_info", {})
                    commit = git_info.get("commit", "N/A")[:8]
                    branch = git_info.get("branch", "N/A")
                    created = backup["created_at"][:19].replace("T", " ")
                    
                    # Get backup size
                    size_info = backup_system.get_backup_size(backup["timestamp"])
                    size_bytes = size_info.get(backup["timestamp"], 0)
                    size_mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_mb:.1f}MB"
                    
                    print(f"{backup['timestamp']:<17} {created:<20} {size_str:<10} {commit:<10} {branch}")
            else:
                print(f"{'Timestamp':<17} {'Created':<20} {'Commit':<10} {'Branch'}")
                print("-" * 70)
                for backup in backups:
                    git_info = backup.get("git_info", {})
                    commit = git_info.get("commit", "N/A")[:8]
                    branch = git_info.get("branch", "N/A")
                    created = backup["created_at"][:19].replace("T", " ")
                    print(f"{backup['timestamp']:<17} {created:<20} {commit:<10} {branch}")
                    
    elif args.command == "cleanup":
        if args.dry_run:
            # Show what would be removed without actually removing
            backups = backup_system.list_backups()
            print("Dry run - showing what would be removed:")
            
            # Simulate the cleanup logic
            now = datetime.datetime.now()
            daily_cutoff = now - datetime.timedelta(days=7)
            weekly_cutoff = now - datetime.timedelta(weeks=4) 
            monthly_cutoff = now - datetime.timedelta(days=30*6)
            
            daily_backups = []
            weekly_backups = []
            monthly_backups = []
            old_backups = []
            
            for backup in backups:
                backup_date = datetime.datetime.fromisoformat(backup["created_at"])
                
                if backup_date > daily_cutoff:
                    daily_backups.append(backup)
                elif backup_date > weekly_cutoff:
                    weekly_backups.append(backup)
                elif backup_date > monthly_cutoff:
                    monthly_backups.append(backup)
                else:
                    old_backups.append(backup)
            
            to_remove = []
            if len(daily_backups) > args.keep_daily:
                to_remove.extend(daily_backups[args.keep_daily:])
            if len(weekly_backups) > args.keep_weekly:
                to_remove.extend(weekly_backups[args.keep_weekly:])
            if len(monthly_backups) > args.keep_monthly:
                to_remove.extend(monthly_backups[args.keep_monthly:])
            to_remove.extend(old_backups)
            
            if to_remove:
                print(f"Would remove {len(to_remove)} backups:")
                for backup in to_remove:
                    print(f"  - {backup['timestamp']} ({backup['created_at'][:19].replace('T', ' ')})")
            else:
                print("No backups would be removed")
        else:
            backup_system.cleanup_old_backups(args.keep_daily, args.keep_weekly, args.keep_monthly)
            
    elif args.command == "remove":
        success = backup_system.remove_backup(args.timestamp)
        if success:
            print(f"✓ Backup {args.timestamp} removed successfully")
        else:
            print(f"✗ Failed to remove backup {args.timestamp}")
            
    elif args.command == "size":
        if args.timestamp:
            size_info = backup_system.get_backup_size(args.timestamp)
            if size_info:
                size_bytes = list(size_info.values())[0]
                size_mb = size_bytes / (1024 * 1024)
                print(f"Backup {args.timestamp}: {size_mb:.1f}MB ({size_bytes:,} bytes)")
            else:
                print(f"Backup {args.timestamp} not found")
        else:
            size_info = backup_system.get_backup_size()
            total_bytes = size_info.get("total", 0)
            total_mb = total_bytes / (1024 * 1024)
            print(f"Total backup size: {total_mb:.1f}MB ({total_bytes:,} bytes)")
            
            # Show individual backup sizes
            backups = backup_system.list_backups()
            if backups:
                print(f"\nIndividual backup sizes:")
                for backup in backups:
                    individual_size = backup_system.get_backup_size(backup["timestamp"])
                    if individual_size:
                        size_bytes = list(individual_size.values())[0]
                        size_mb = size_bytes / (1024 * 1024)
                        print(f"  {backup['timestamp']}: {size_mb:.1f}MB")
                
    elif args.command == "restore":
        if args.db_only:
            backup_system.restore_database(args.timestamp)
        elif args.code_only:
            backup_system.restore_codebase(args.timestamp)
        else:
            print("Restoring database...")
            backup_system.restore_database(args.timestamp)
            print("\nRestoring codebase...")
            backup_system.restore_codebase(args.timestamp)


if __name__ == "__main__":
    main()