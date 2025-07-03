#!/usr/bin/env python3
"""
App health checker - verifies the journal app is running correctly.
This should be run after any code changes to ensure the app is working.
"""

import subprocess
import requests
import time
import sys

def check_service_status():
    """Check if the systemd service is running."""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'is-active', 'journal-app.service'], 
                              capture_output=True, text=True, timeout=10)
        return result.stdout.strip() == 'active'
    except Exception as e:
        print(f"❌ Error checking service status: {e}")
        return False

def check_service_logs():
    """Check recent service logs for errors."""
    try:
        result = subprocess.run(['sudo', 'journalctl', '-u', 'journal-app.service', 
                               '--since', '2 minutes ago', '--no-pager'], 
                              capture_output=True, text=True, timeout=15)
        
        logs = result.stdout
        
        # Check for common error patterns
        error_patterns = [
            'Error',
            'Exception',
            'Traceback',
            'CRITICAL',
            'FATAL',
            'failed',
            'OperationalError',
            'ImportError',
            'SyntaxError'
        ]
        
        errors_found = []
        for line in logs.split('\n'):
            for pattern in error_patterns:
                if pattern in line and 'journal-app.service' in line:
                    errors_found.append(line.strip())
        
        return errors_found
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return [f"Log check failed: {e}"]

def check_app_response():
    """Check if the app responds to HTTP requests."""
    try:
        # Try to connect to the app
        response = requests.get('https://127.0.0.1:5000/', 
                              timeout=10, verify=False)
        
        # We expect a redirect for the root URL (to login or dashboard)
        return response.status_code in [200, 302, 401]
    except Exception as e:
        print(f"❌ Error checking app response: {e}")
        return False

def restart_service_if_needed():
    """Restart the service if it's not working."""
    try:
        print("🔄 Restarting journal-app.service...")
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'journal-app.service'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Service restarted successfully")
            time.sleep(5)  # Wait for service to start
            return True
        else:
            print(f"❌ Service restart failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error restarting service: {e}")
        return False

def main():
    """Run complete app health check."""
    print("🏥 Journal App Health Check")
    print("=" * 40)
    
    all_checks_passed = True
    
    # 1. Check service status
    print("1. Checking service status...")
    if check_service_status():
        print("   ✅ Service is active")
    else:
        print("   ❌ Service is not active")
        all_checks_passed = False
        
        # Try to restart
        if restart_service_if_needed():
            if check_service_status():
                print("   ✅ Service recovered after restart")
            else:
                print("   ❌ Service still not working after restart")
                return False
        else:
            return False
    
    # 2. Check for errors in logs
    print("2. Checking recent logs...")
    errors = check_service_logs()
    if not errors:
        print("   ✅ No errors in recent logs")
    else:
        print(f"   ❌ Found {len(errors)} errors in logs:")
        for error in errors[:3]:  # Show first 3 errors
            print(f"     - {error}")
        all_checks_passed = False
    
    # 3. Check app response
    print("3. Checking app response...")
    if check_app_response():
        print("   ✅ App responds to HTTP requests")
    else:
        print("   ❌ App not responding to HTTP requests")
        all_checks_passed = False
        
        # Try restart if not responding
        if restart_service_if_needed():
            time.sleep(3)
            if check_app_response():
                print("   ✅ App recovered after restart")
            else:
                print("   ❌ App still not responding after restart")
                return False
        else:
            return False
    
    # Final result
    print("\n" + "=" * 40)
    if all_checks_passed:
        print("🎉 All health checks passed!")
        print("✅ Journal app is running correctly")
        return True
    else:
        print("⚠️  Some health checks failed")
        print("🔧 Manual intervention may be required")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)