#!/usr/bin/env python3
"""
Service control script for journal-app that works without sudo password prompts.
This script provides systemctl operations that Claude can use.
"""

import subprocess
import sys
import time
from typing import Tuple, Optional


class ServiceController:
    """Controls the journal-app systemd service."""
    
    def __init__(self, service_name: str = "journal-app.service"):
        self.service_name = service_name
    
    def _run_systemctl(self, action: str, capture_output: bool = True) -> Tuple[bool, str]:
        """
        Run systemctl command.
        
        Args:
            action: systemctl action (start, stop, restart, status, etc.)
            capture_output: Whether to capture output
            
        Returns:
            Tuple of (success, output/error)
        """
        cmd = ["sudo", "systemctl", action, self.service_name]
        
        if action == "status":
            cmd.extend(["--no-pager", "-l"])
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                return result.returncode == 0, result.stdout + result.stderr
            else:
                result = subprocess.run(cmd, timeout=30)
                return result.returncode == 0, ""
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Error running command: {e}"
    
    def is_active(self) -> bool:
        """Check if service is active."""
        success, _ = self._run_systemctl("is-active")
        return success
    
    def status(self) -> Tuple[bool, str]:
        """Get service status."""
        return self._run_systemctl("status")
    
    def start(self) -> bool:
        """Start the service."""
        print("🚀 Starting journal-app.service...")
        success, output = self._run_systemctl("start")
        
        if success:
            time.sleep(3)  # Wait for service to start
            if self.is_active():
                print("✅ Service started successfully")
                return True
            else:
                print("❌ Service failed to start properly")
                return False
        else:
            print(f"❌ Failed to start service: {output}")
            return False
    
    def stop(self) -> bool:
        """Stop the service."""
        print("🛑 Stopping journal-app.service...")
        success, output = self._run_systemctl("stop")
        
        if success:
            time.sleep(2)  # Wait for service to stop
            if not self.is_active():
                print("✅ Service stopped successfully")
                return True
            else:
                print("❌ Service failed to stop properly")
                return False
        else:
            print(f"❌ Failed to stop service: {output}")
            return False
    
    def restart(self) -> bool:
        """Restart the service."""
        print("🔄 Restarting journal-app.service...")
        success, output = self._run_systemctl("restart")
        
        if success:
            time.sleep(3)  # Wait for service to restart
            if self.is_active():
                print("✅ Service restarted successfully")
                return True
            else:
                print("❌ Service failed to restart properly")
                return False
        else:
            print(f"❌ Failed to restart service: {output}")
            return False
    
    def reload_code(self) -> bool:
        """
        Reload code changes by restarting the service.
        This is the main method Claude should use after making code changes.
        """
        print("📥 Reloading code changes...")
        return self.restart()
    
    def show_status(self) -> None:
        """Show detailed service status."""
        if self.is_active():
            print("✅ journal-app.service is running")
        else:
            print("❌ journal-app.service is not running")
        
        success, output = self.status()
        if success or output:  # Show output even if command failed
            print("\nService details:")
            print(output)
    
    def follow_logs(self) -> None:
        """Follow service logs (blocking)."""
        print("📋 Following journal-app.service logs (Ctrl+C to exit)...")
        try:
            subprocess.run([
                "sudo", "journalctl", "-u", self.service_name, "-f"
            ])
        except KeyboardInterrupt:
            print("\n✅ Stopped following logs")
        except Exception as e:
            print(f"❌ Error following logs: {e}")


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Usage: python3 service_control.py [start|stop|restart|status|logs|reload]")
        print("")
        print("Commands:")
        print("  start    - Start the journal-app service")
        print("  stop     - Stop the journal-app service") 
        print("  restart  - Restart the journal-app service")
        print("  reload   - Reload code changes (same as restart)")
        print("  status   - Show service status")
        print("  logs     - Follow service logs")
        print("")
        print("Examples:")
        print("  python3 service_control.py reload    # Reload code after changes")
        print("  python3 service_control.py status    # Check if running")
        print("  python3 service_control.py logs      # View logs")
        return
    
    action = sys.argv[1].lower()
    controller = ServiceController()
    
    if action == "start":
        success = controller.start()
        sys.exit(0 if success else 1)
        
    elif action == "stop":
        success = controller.stop()
        sys.exit(0 if success else 1)
        
    elif action in ["restart", "reload"]:
        success = controller.restart()
        sys.exit(0 if success else 1)
        
    elif action == "status":
        controller.show_status()
        
    elif action == "logs":
        controller.follow_logs()
        
    else:
        print(f"Unknown action: {action}")
        print("Use: start, stop, restart, reload, status, or logs")
        sys.exit(1)


if __name__ == "__main__":
    main()