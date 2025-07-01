#!/usr/bin/env python3
"""
Development workflow helper script for journal application.

This script provides easy commands for common development tasks.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description="", check=True):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    if description:
        print(f"🔄 {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, check=check)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        return False


def test_and_deploy():
    """Run full test suite and deploy if successful."""
    print("🚀 Starting test and deploy workflow...")
    
    # Run all tests
    if not run_command("python3 run_tests.py all", "Running all tests"):
        print("❌ Tests failed! Deployment aborted.")
        return False
    
    # Create backup
    if not run_command("./backup.sh pre-deploy", "Creating pre-deployment backup"):
        print("⚠️  Backup failed, but continuing...")
    
    # Restart service
    if not run_command("python3 service_control.py reload", "Restarting production service"):
        print("❌ Service restart failed!")
        return False
    
    print("\n🎉 Deployment successful!")
    return True


def quick_check():
    """Run quick tests and checks."""
    print("⚡ Running quick development checks...")
    
    # CSRF validation
    if not run_command("python3 validate_csrf.py", "Validating CSRF tokens"):
        return False
    
    # Quick tests
    if not run_command("python3 run_tests.py quick", "Running quick tests"):
        return False
    
    print("\n✅ All quick checks passed!")
    return True


def test_category(category):
    """Run tests for a specific category."""
    valid_categories = ['auth', 'email', 'mfa', 'journal', 'ai', 'csrf', 'all', 'quick', 'coverage']
    
    if category not in valid_categories:
        print(f"❌ Invalid category: {category}")
        print(f"Valid categories: {', '.join(valid_categories)}")
        return False
    
    return run_command(f"python3 run_tests.py {category}", f"Running {category} tests")


def commit_workflow():
    """Run pre-commit workflow."""
    print("📝 Running pre-commit workflow...")
    
    # Check git status
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        print("📋 No changes to commit.")
        return True
    
    print("📋 Changes detected:")
    run_command("git status --short", "")
    
    # Run quick checks
    if not quick_check():
        print("❌ Pre-commit checks failed!")
        return False
    
    # Ask for commit message
    commit_msg = input("\n💬 Enter commit message (or 'cancel' to abort): ").strip()
    if commit_msg.lower() == 'cancel' or not commit_msg:
        print("🚫 Commit cancelled.")
        return False
    
    # Stage and commit
    if not run_command("git add .", "Staging changes"):
        return False
    
    # Use heredoc format for commit message
    commit_cmd = f"""git commit -m "$(cat <<'EOF'
{commit_msg}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" """
    
    if not run_command(commit_cmd, "Creating commit"):
        return False
    
    # Ask about pushing
    push = input("\n📤 Push to GitHub? (y/N): ").strip().lower()
    if push in ['y', 'yes']:
        run_command("git push origin main", "Pushing to GitHub")
    
    print("\n✅ Commit workflow completed!")
    return True


def coverage_report():
    """Generate and open coverage report."""
    print("📊 Generating coverage report...")
    
    if not run_command("python3 run_tests.py coverage", "Running tests with coverage"):
        return False
    
    # Try to open coverage report
    coverage_path = "htmlcov/index.html"
    if os.path.exists(coverage_path):
        print(f"\n📊 Coverage report generated: {coverage_path}")
        open_cmd = {
            'darwin': 'open',  # macOS
            'linux': 'xdg-open',  # Linux
            'win32': 'start'  # Windows
        }.get(sys.platform, 'xdg-open')
        
        try:
            subprocess.run([open_cmd, coverage_path], check=False)
            print("📖 Coverage report opened in browser.")
        except:
            print("💡 Please open htmlcov/index.html in your browser to view the report.")
    
    return True


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Development workflow helper for journal application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 dev.py check          # Run quick checks
  python3 dev.py test auth      # Run authentication tests
  python3 dev.py commit         # Guided commit workflow
  python3 dev.py deploy         # Test and deploy
  python3 dev.py coverage       # Generate coverage report
        """
    )
    
    parser.add_argument('command', nargs='?', default='help',
                       choices=['check', 'test', 'commit', 'deploy', 'coverage', 'help'],
                       help='Development command to run')
    
    parser.add_argument('category', nargs='?',
                       help='Test category for test command')
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🛠️  Journal Development Workflow Helper")
    print("="*40)
    
    if args.command == 'help':
        parser.print_help()
        return
    
    elif args.command == 'check':
        success = quick_check()
    
    elif args.command == 'test':
        if not args.category:
            print("❌ Please specify a test category.")
            print("Usage: python3 dev.py test [auth|email|mfa|journal|ai|csrf|all|quick|coverage]")
            return
        success = test_category(args.category)
    
    elif args.command == 'commit':
        success = commit_workflow()
    
    elif args.command == 'deploy':
        success = test_and_deploy()
    
    elif args.command == 'coverage':
        success = coverage_report()
    
    else:
        parser.print_help()
        return
    
    if success:
        print(f"\n🎉 '{args.command}' completed successfully!")
    else:
        print(f"\n❌ '{args.command}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()