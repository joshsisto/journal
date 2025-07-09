#!/usr/bin/env python3
"""
Comprehensive backup monitoring and alerting system for journal application.
Monitors backup health, sends alerts, and provides detailed reporting.
"""

import os
import sys
import json
import subprocess
import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class BackupAlert:
    """Backup alert structure."""
    level: AlertLevel
    title: str
    message: str
    timestamp: str
    details: Dict[str, Any]

class BackupMonitor:
    """Comprehensive backup monitoring and alerting system."""
    
    def __init__(self, project_root: str = None):
        """Initialize backup monitor."""
        self.project_root = Path(project_root or os.getcwd())
        self.backup_system = self.project_root / "backup_system.py"
        self.backup_dir = self.project_root / "backups"
        self.monitor_config_file = self.project_root / "backup_monitor_config.json"
        self.alerts_log = self.project_root / "backup_alerts.log"
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize alerts
        self.alerts = []
        
        print(f"Backup monitor initialized. Project: {self.project_root}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration."""
        default_config = {
            "monitoring": {
                "max_backup_age_hours": 26,  # Alert if no backup in 26 hours
                "min_backup_size_mb": 0.1,   # Alert if backup smaller than 0.1MB
                "max_failed_backups": 3,     # Alert after 3 consecutive failures
                "check_interval_minutes": 60, # Check every hour
                "retention_check": True,      # Check retention policy compliance
                "integrity_check": True,      # Verify backup integrity
                "service_check": True,       # Check systemd service status
                "disk_usage_threshold": 85   # Alert if disk usage > 85%
            },
            "alerting": {
                "email_enabled": True,
                "email_recipients": ["admin@journal.joshsisto.com"],
                "email_from": "backup-monitor@journal.joshsisto.com",
                "log_enabled": True,
                "console_enabled": True,
                "alert_cooldown_minutes": 60  # Don't repeat same alert for 60 minutes
            },
            "notifications": {
                "backup_success": False,      # Don't notify on successful backups
                "backup_failure": True,       # Notify on backup failures
                "system_issues": True,        # Notify on system issues
                "weekly_report": True,        # Send weekly summary
                "monthly_report": True       # Send monthly summary
            }
        }
        
        if self.monitor_config_file.exists():
            try:
                with open(self.monitor_config_file) as f:
                    user_config = json.load(f)
                
                # Merge with defaults
                config = default_config.copy()
                for section, values in user_config.items():
                    if section in config:
                        config[section].update(values)
                    else:
                        config[section] = values
                
                return config
            except Exception as e:
                print(f"⚠️  Error loading config, using defaults: {e}")
        
        # Save default config
        with open(self.monitor_config_file, 'w') as f:
            json.dump(default_config, indent=2, fp=f)
        
        return default_config
    
    def add_alert(self, level: AlertLevel, title: str, message: str, details: Dict[str, Any] = None):
        """Add alert to the system."""
        alert = BackupAlert(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.datetime.now().isoformat(),
            details=details or {}
        )
        
        self.alerts.append(alert)
        
        # Log alert
        if self.config["alerting"]["log_enabled"]:
            self._log_alert(alert)
        
        # Console output
        if self.config["alerting"]["console_enabled"]:
            self._console_alert(alert)
        
        # Email alert for high severity
        if (self.config["alerting"]["email_enabled"] and 
            level in [AlertLevel.ERROR, AlertLevel.CRITICAL]):
            self._email_alert(alert)
    
    def _log_alert(self, alert: BackupAlert):
        """Log alert to file."""
        log_entry = {
            "timestamp": alert.timestamp,
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details
        }
        
        with open(self.alerts_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _console_alert(self, alert: BackupAlert):
        """Output alert to console."""
        level_symbols = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }
        
        symbol = level_symbols.get(alert.level, "📋")
        print(f"{symbol} [{alert.level.value.upper()}] {alert.title}")
        print(f"   {alert.message}")
        
        if alert.details:
            for key, value in alert.details.items():
                print(f"   {key}: {value}")
    
    def _email_alert(self, alert: BackupAlert):
        """Send email alert."""
        try:
            # Load email configuration from environment
            from dotenv import load_dotenv
            load_dotenv()
            
            smtp_server = os.environ.get('MAIL_SERVER', 'smtp.mailgun.org')
            smtp_port = int(os.environ.get('MAIL_PORT', 587))
            smtp_user = os.environ.get('MAIL_USERNAME')
            smtp_password = os.environ.get('MAIL_PASSWORD')
            from_email = self.config["alerting"]["email_from"]
            
            if not all([smtp_user, smtp_password]):
                print("⚠️  Email credentials not configured")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(self.config["alerting"]["email_recipients"])
            msg['Subject'] = f"Journal Backup Alert: {alert.title}"
            
            body = f"""
Backup Alert: {alert.title}

Level: {alert.level.value.upper()}
Time: {alert.timestamp}
Message: {alert.message}

Details:
{json.dumps(alert.details, indent=2)}

---
Journal Backup Monitor
{self.project_root}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email alert sent for: {alert.title}")
            
        except Exception as e:
            print(f"❌ Failed to send email alert: {e}")
    
    def check_backup_freshness(self) -> bool:
        """Check if backups are recent enough."""
        try:
            # Get backup list
            result = subprocess.run([
                sys.executable, str(self.backup_system), "list"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            
            if result.returncode != 0:
                self.add_alert(
                    AlertLevel.ERROR,
                    "Backup System Error",
                    "Failed to list backups",
                    {"stderr": result.stderr}
                )
                return False
            
            if "No backups found" in result.stdout:
                self.add_alert(
                    AlertLevel.CRITICAL,
                    "No Backups Found",
                    "No backups exist in the system",
                    {}
                )
                return False
            
            # Parse backup list to find most recent
            lines = result.stdout.strip().split('\n')
            backup_lines = [line for line in lines if '|' in line and line.strip()]
            
            if not backup_lines:
                self.add_alert(
                    AlertLevel.ERROR,
                    "Backup Parsing Error",
                    "Unable to parse backup list",
                    {"output": result.stdout}
                )
                return False
            
            # Get first backup (most recent)
            first_backup = backup_lines[0]
            timestamp_str = first_backup.split('|')[0].strip()
            
            try:
                backup_time = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                age_hours = (datetime.datetime.now() - backup_time).total_seconds() / 3600
                
                max_age = self.config["monitoring"]["max_backup_age_hours"]
                
                if age_hours > max_age:
                    self.add_alert(
                        AlertLevel.WARNING,
                        "Backup Age Warning",
                        f"Most recent backup is {age_hours:.1f} hours old",
                        {
                            "backup_timestamp": timestamp_str,
                            "age_hours": age_hours,
                            "max_age_hours": max_age
                        }
                    )
                    return False
                
                return True
                
            except ValueError:
                self.add_alert(
                    AlertLevel.ERROR,
                    "Backup Timestamp Error",
                    f"Unable to parse backup timestamp: {timestamp_str}",
                    {"timestamp": timestamp_str}
                )
                return False
        
        except subprocess.TimeoutExpired:
            self.add_alert(
                AlertLevel.ERROR,
                "Backup System Timeout",
                "Backup system command timed out",
                {}
            )
            return False
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Backup Freshness Check Error",
                f"Error checking backup freshness: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def check_backup_integrity(self) -> bool:
        """Check backup integrity."""
        if not self.config["monitoring"]["integrity_check"]:
            return True
        
        try:
            result = subprocess.run([
                sys.executable, str(self.backup_system), "verify"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=120)
            
            if result.returncode != 0:
                self.add_alert(
                    AlertLevel.ERROR,
                    "Backup Integrity Check Failed",
                    "Backup verification command failed",
                    {"stderr": result.stderr}
                )
                return False
            
            # Check for failure indicators (but not "Failed: 0" which indicates success)
            if "Failed:" in result.stdout and "Failed: 0" not in result.stdout:
                failed_count = result.stdout.count("Failed:")
                self.add_alert(
                    AlertLevel.WARNING,
                    "Backup Integrity Issues",
                    f"{failed_count} backup(s) failed integrity check",
                    {"output": result.stdout}
                )
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.add_alert(
                AlertLevel.ERROR,
                "Backup Integrity Check Timeout",
                "Backup integrity check timed out",
                {}
            )
            return False
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Backup Integrity Check Error",
                f"Error checking backup integrity: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def check_backup_size(self) -> bool:
        """Check backup sizes are reasonable."""
        try:
            result = subprocess.run([
                sys.executable, str(self.backup_system), "list", "--size"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            
            if result.returncode != 0:
                return False
            
            lines = result.stdout.strip().split('\n')
            backup_lines = [line for line in lines if '|' in line and 'MB' in line]
            
            min_size_mb = self.config["monitoring"]["min_backup_size_mb"]
            small_backups = []
            
            for line in backup_lines:
                try:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        size_str = parts[4].strip()
                        if 'MB' in size_str:
                            size_mb = float(size_str.replace('MB', '').strip())
                            if size_mb < min_size_mb:
                                small_backups.append({
                                    'timestamp': parts[0].strip(),
                                    'size_mb': size_mb
                                })
                except (ValueError, IndexError):
                    continue
            
            if small_backups:
                self.add_alert(
                    AlertLevel.WARNING,
                    "Small Backup Warning",
                    f"Found {len(small_backups)} backup(s) smaller than {min_size_mb}MB",
                    {"small_backups": small_backups}
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Backup Size Check Error",
                f"Error checking backup sizes: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def check_systemd_services(self) -> bool:
        """Check systemd backup service status."""
        if not self.config["monitoring"]["service_check"]:
            return True
        
        try:
            # Check backup timers (try user timers first, then system timers)
            try:
                result = subprocess.run([
                    'systemctl', '--user', 'list-timers', 'journal-backup-*', '--no-pager'
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode != 0:
                    # Try system timers with sudo
                    result = subprocess.run([
                        'sudo', 'systemctl', 'list-timers', 'journal-backup-*', '--no-pager'
                    ], capture_output=True, text=True, timeout=15)
                    
                    if result.returncode != 0:
                        self.add_alert(
                            AlertLevel.WARNING,
                            "Systemd Timer Check Failed",
                            "Unable to check systemd backup timers",
                            {"stderr": result.stderr}
                        )
                        return False
            except:
                # If both fail, just skip the check
                return True
            
            if "journal-backup-" not in result.stdout:
                self.add_alert(
                    AlertLevel.WARNING,
                    "No Backup Timers",
                    "No systemd backup timers found",
                    {"output": result.stdout}
                )
                return False
            
            # Check for failed services
            failed_services = []
            for service_type in ['daily', 'weekly', 'monthly']:
                service_name = f"journal-backup-{service_type}.service"
                
                status_result = subprocess.run([
                    'sudo', 'systemctl', 'is-failed', service_name
                ], capture_output=True, text=True)
                
                if status_result.returncode == 0:  # Service is failed
                    failed_services.append(service_name)
            
            if failed_services:
                self.add_alert(
                    AlertLevel.ERROR,
                    "Failed Backup Services",
                    f"Found {len(failed_services)} failed backup service(s)",
                    {"failed_services": failed_services}
                )
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.add_alert(
                AlertLevel.ERROR,
                "Systemd Service Check Timeout",
                "Systemd service check timed out",
                {}
            )
            return False
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Systemd Service Check Error",
                f"Error checking systemd services: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def check_disk_usage(self) -> bool:
        """Check disk usage for backup directory."""
        try:
            # Get disk usage for backup directory
            statvfs = os.statvfs(self.backup_dir)
            total_space = statvfs.f_blocks * statvfs.f_frsize
            available_space = statvfs.f_bavail * statvfs.f_frsize
            used_space = total_space - available_space
            usage_percent = (used_space / total_space) * 100
            
            threshold = self.config["monitoring"]["disk_usage_threshold"]
            
            if usage_percent > threshold:
                self.add_alert(
                    AlertLevel.WARNING,
                    "High Disk Usage",
                    f"Backup directory disk usage is {usage_percent:.1f}%",
                    {
                        "usage_percent": usage_percent,
                        "threshold": threshold,
                        "total_gb": total_space / (1024**3),
                        "available_gb": available_space / (1024**3),
                        "backup_dir": str(self.backup_dir)
                    }
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Disk Usage Check Error",
                f"Error checking disk usage: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def check_database_connectivity(self) -> bool:
        """Check database connectivity."""
        try:
            # Load database configuration
            from dotenv import load_dotenv
            load_dotenv()
            
            use_postgresql = os.environ.get('USE_POSTGRESQL', '').lower() == 'true'
            
            if use_postgresql:
                # Check PostgreSQL connectivity
                pg_config = {
                    'host': os.environ.get('DB_HOST', 'localhost'),
                    'port': os.environ.get('DB_PORT', '5432'),
                    'database': os.environ.get('DB_NAME', 'journal_db'),
                    'user': os.environ.get('DB_USER', 'journal_user'),
                    'password': os.environ.get('DB_PASSWORD')
                }
                
                if not pg_config['password']:
                    self.add_alert(
                        AlertLevel.ERROR,
                        "Database Configuration Error",
                        "PostgreSQL password not configured",
                        {}
                    )
                    return False
                
                env = os.environ.copy()
                env['PGPASSWORD'] = pg_config['password']
                
                result = subprocess.run([
                    'psql',
                    '-h', pg_config['host'],
                    '-p', pg_config['port'],
                    '-U', pg_config['user'],
                    '-d', pg_config['database'],
                    '-c', 'SELECT 1;'
                ], capture_output=True, text=True, env=env, timeout=10)
                
                if result.returncode != 0:
                    self.add_alert(
                        AlertLevel.ERROR,
                        "Database Connectivity Error",
                        "Unable to connect to PostgreSQL database",
                        {"stderr": result.stderr}
                    )
                    return False
            
            else:
                # Check SQLite connectivity
                import sqlite3
                
                sqlite_paths = [
                    self.project_root / "instance" / "journal.db",
                    self.project_root / "journal.db"
                ]
                
                found_db = False
                for db_path in sqlite_paths:
                    if db_path.exists():
                        try:
                            conn = sqlite3.connect(str(db_path))
                            conn.execute("SELECT 1")
                            conn.close()
                            found_db = True
                            break
                        except sqlite3.Error as e:
                            self.add_alert(
                                AlertLevel.ERROR,
                                "SQLite Database Error",
                                f"Error accessing SQLite database: {str(e)}",
                                {"database_path": str(db_path)}
                            )
                            return False
                
                if not found_db:
                    self.add_alert(
                        AlertLevel.ERROR,
                        "SQLite Database Missing",
                        "No SQLite database files found",
                        {"searched_paths": [str(p) for p in sqlite_paths]}
                    )
                    return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.add_alert(
                AlertLevel.ERROR,
                "Database Connectivity Timeout",
                "Database connectivity check timed out",
                {}
            )
            return False
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "Database Connectivity Check Error",
                f"Error checking database connectivity: {str(e)}",
                {"exception": str(e)}
            )
            return False
    
    def run_comprehensive_check(self) -> Dict[str, bool]:
        """Run comprehensive backup health check."""
        print("Starting comprehensive backup health check...")
        print("=" * 50)
        
        checks = [
            ("Backup Freshness", self.check_backup_freshness),
            ("Backup Integrity", self.check_backup_integrity),
            ("Backup Size", self.check_backup_size),
            ("Systemd Services", self.check_systemd_services),
            ("Disk Usage", self.check_disk_usage),
            ("Database Connectivity", self.check_database_connectivity)
        ]
        
        results = {}
        passed = 0
        failed = 0
        
        for check_name, check_func in checks:
            print(f"Running: {check_name}")
            try:
                result = check_func()
                results[check_name] = result
                
                if result:
                    passed += 1
                    print(f"✅ {check_name}: PASSED")
                else:
                    failed += 1
                    print(f"❌ {check_name}: FAILED")
                    
            except Exception as e:
                failed += 1
                results[check_name] = False
                print(f"❌ {check_name}: ERROR - {str(e)}")
                
                self.add_alert(
                    AlertLevel.ERROR,
                    f"{check_name} Check Error",
                    f"Check failed with exception: {str(e)}",
                    {"exception": str(e)}
                )
        
        # Summary
        print("\n" + "=" * 50)
        print("BACKUP HEALTH CHECK SUMMARY")
        print("=" * 50)
        print(f"Total checks: {len(checks)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Health score: {(passed/len(checks)*100):.1f}%")
        
        # Overall health alert
        if failed == 0:
            self.add_alert(
                AlertLevel.INFO,
                "Backup Health Check Passed",
                "All backup health checks passed",
                {"total_checks": len(checks), "passed": passed}
            )
        elif failed <= 2:
            self.add_alert(
                AlertLevel.WARNING,
                "Backup Health Issues",
                f"{failed} backup health check(s) failed",
                {"total_checks": len(checks), "passed": passed, "failed": failed}
            )
        else:
            self.add_alert(
                AlertLevel.CRITICAL,
                "Backup System Unhealthy",
                f"Multiple backup health checks failed ({failed}/{len(checks)})",
                {"total_checks": len(checks), "passed": passed, "failed": failed}
            )
        
        return results
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        # Run health checks
        check_results = self.run_comprehensive_check()
        
        # Get backup statistics
        try:
            stats_result = subprocess.run([
                sys.executable, str(self.backup_system), "stats"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            
            backup_stats = {}
            if stats_result.returncode == 0:
                for line in stats_result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        backup_stats[key.strip()] = value.strip()
        except Exception:
            backup_stats = {"error": "Unable to retrieve backup statistics"}
        
        # Create report
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "health_score": sum(check_results.values()) / len(check_results) * 100,
            "check_results": check_results,
            "backup_statistics": backup_stats,
            "alerts": [
                {
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "details": alert.details
                }
                for alert in self.alerts
            ],
            "configuration": self.config
        }
        
        return report
    
    def save_health_report(self, report: Dict[str, Any]) -> str:
        """Save health report to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.project_root / f"backup_health_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Health report saved: {report_file}")
        return str(report_file)
    
    def continuous_monitoring(self, interval_minutes: int = None):
        """Run continuous monitoring."""
        if interval_minutes is None:
            interval_minutes = self.config["monitoring"]["check_interval_minutes"]
        
        print(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        try:
            while True:
                print(f"\n[{datetime.datetime.now().isoformat()}] Running health check...")
                
                # Clear previous alerts
                self.alerts = []
                
                # Run health check
                self.run_comprehensive_check()
                
                # Sleep until next check
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup monitoring system")
    parser.add_argument('action', choices=[
        'check', 'monitor', 'report', 'config'
    ], help='Action to perform')
    parser.add_argument('--brief', action='store_true', help='Brief output')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Monitoring interval in minutes')
    
    args = parser.parse_args()
    
    monitor = BackupMonitor()
    
    if args.action == 'check':
        results = monitor.run_comprehensive_check()
        
        if args.brief:
            failed_count = sum(1 for passed in results.values() if not passed)
            if failed_count == 0:
                print("✅ All backup health checks passed")
                sys.exit(0)
            else:
                print(f"❌ {failed_count} backup health check(s) failed")
                sys.exit(1)
        else:
            # Detailed output already printed by run_comprehensive_check()
            failed_count = sum(1 for passed in results.values() if not passed)
            sys.exit(0 if failed_count == 0 else 1)
    
    elif args.action == 'monitor':
        monitor.continuous_monitoring(args.interval)
    
    elif args.action == 'report':
        report = monitor.generate_health_report()
        report_file = monitor.save_health_report(report)
        
        if args.brief:
            print(f"Health score: {report['health_score']:.1f}%")
            print(f"Report: {report_file}")
        else:
            print(f"Health report generated: {report_file}")
            print(f"Health score: {report['health_score']:.1f}%")
            print(f"Alerts: {len(report['alerts'])}")
    
    elif args.action == 'config':
        print(f"Configuration file: {monitor.monitor_config_file}")
        print(json.dumps(monitor.config, indent=2))


if __name__ == "__main__":
    main()