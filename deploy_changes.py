#!/usr/bin/env python3
"""
Deployment script that automatically restarts the service and checks app health.
This should be used whenever making changes that require a service restart.
"""

import subprocess
import sys
import time

def restart_service():
    """Restart the journal app service."""
    try:
        print("🔄 Restarting journal-app.service...")
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'journal-app.service'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Service restarted successfully")
            time.sleep(5)  # Wait for service to fully start
            return True
        else:
            print(f"❌ Service restart failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error restarting service: {e}")
        return False

def run_health_check():
    """Run the health check script."""
    try:
        print("🏥 Running health check...")
        result = subprocess.run(['python3', 'check_app_health.py'], 
                              capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running health check: {e}")
        return False

def main():
    """Deploy changes and verify app health."""
    print("🚀 Deploying Changes")
    print("=" * 30)
    
    # Step 1: Restart service
    if not restart_service():
        print("❌ Deployment failed at service restart")
        return False
    
    # Step 2: Health check
    if not run_health_check():
        print("❌ Deployment failed - app health check failed")
        return False
    
    print("\n🎉 Deployment completed successfully!")
    print("✅ App is running and healthy")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)