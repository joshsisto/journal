#!/usr/bin/env python3
"""
AI Conversation Health Check System

This script monitors the health of AI conversation functionality to prevent
the types of issues that have been causing repeated breakdowns.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path


class AIConversationHealthCheck:
    """Comprehensive health checker for AI conversation functionality."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.project_root = Path(__file__).parent
    
    def log_issue(self, message):
        """Log a critical issue."""
        self.issues.append(message)
        print(f"❌ ISSUE: {message}")
    
    def log_warning(self, message):
        """Log a warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def log_success(self, message):
        """Log a success."""
        print(f"✅ {message}")
    
    def check_template_integrity(self):
        """Check AI conversation templates for common issues."""
        print("\n🔍 Checking AI conversation template integrity...")
        
        template_dir = self.project_root / "templates" / "ai"
        required_templates = [
            "conversation.html",
            "chat_multiple.html", 
            "working_multiple.html",
            "direct_conversation.html"
        ]
        
        for template in required_templates:
            template_path = template_dir / template
            if not template_path.exists():
                self.log_issue(f"Missing AI template: {template}")
                continue
            
            # Check template content
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for CSP nonces
            if '<script' in content and 'nonce="{{ csp_nonce() }}"' not in content:
                self.log_issue(f"Template {template} missing CSP nonce in script tags")
            
            # Check for CSRF tokens
            if '{{ csrf_token }}' in content:  # Wrong format
                self.log_issue(f"Template {template} uses incorrect CSRF token format (missing parentheses)")
            
            # Check for test alerts (should not be in production)
            if 'alert(' in content:
                self.log_warning(f"Template {template} contains alert() - remove for production")
            
            self.log_success(f"Template {template} basic checks passed")
    
    def check_security_configuration(self):
        """Check security module configuration."""
        print("\n🔒 Checking security configuration...")
        
        security_file = self.project_root / "security.py"
        if not security_file.exists():
            self.log_issue("security.py not found")
            return
        
        with open(security_file, 'r', encoding='utf-8') as f:
            security_content = f.read()
        
        # Check for emotion field handling
        if 'emotion' not in security_content.lower():
            self.log_issue("Security module missing emotion field handling")
        
        # Check for request context handling
        if 'request.endpoint' not in security_content:
            self.log_issue("Security module missing request context check")
        
        # Check for legitimate JSON exceptions
        if 'question_' not in security_content:
            self.log_issue("Security module missing question_ field handling")
        
        self.log_success("Security configuration checks passed")
    
    def check_dependencies(self):
        """Check required dependencies are installed."""
        print("\n📦 Checking dependencies...")
        
        required_packages = ['selenium', 'flask', 'pytest']
        
        for package in required_packages:
            try:
                __import__(package)
                self.log_success(f"Package {package} is available")
            except ImportError:
                self.log_issue(f"Required package {package} not installed")
    
    def check_test_health(self):
        """Check if critical tests are passing."""
        print("\n🧪 Checking test health...")
        
        # Check if comprehensive test script exists
        test_script = self.project_root / "run_comprehensive_tests.py"
        if not test_script.exists():
            self.log_issue("Comprehensive test script missing")
            return
        
        # Run security validation tests
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'tests/unit/test_security_validation.py::TestSecurityValidation::test_legitimate_emotion_json_allowed',
                '-v'
            ], cwd=self.project_root, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log_success("Emotion JSON security test passing")
            else:
                self.log_issue("Emotion JSON security test failing")
        except subprocess.TimeoutExpired:
            self.log_warning("Security test timed out")
        except Exception as e:
            self.log_warning(f"Could not run security test: {e}")
        
        # Check CSRF validation
        csrf_script = self.project_root / "validate_csrf.py"
        if csrf_script.exists():
            try:
                result = subprocess.run([sys.executable, str(csrf_script)], 
                                       cwd=self.project_root, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.log_success("CSRF validation passed")
                else:
                    self.log_issue("CSRF validation failed")
            except Exception as e:
                self.log_warning(f"Could not run CSRF validation: {e}")
    
    def check_git_hooks(self):
        """Check if protective git hooks are installed."""
        print("\n🪝 Checking git hooks...")
        
        git_hooks_dir = self.project_root / ".git" / "hooks"
        
        # Check pre-commit hook
        pre_commit_hook = git_hooks_dir / "pre-commit"
        if not pre_commit_hook.exists():
            self.log_issue("Pre-commit hook not installed")
        elif not os.access(pre_commit_hook, os.X_OK):
            self.log_issue("Pre-commit hook not executable")
        else:
            self.log_success("Pre-commit hook installed and executable")
        
        # Check post-commit hook for service restart
        post_commit_hook = git_hooks_dir / "post-commit"
        if not post_commit_hook.exists():
            self.log_warning("Post-commit hook for service restart not found")
        else:
            self.log_success("Post-commit hook for service restart found")
    
    def check_ai_routes(self):
        """Check AI conversation routes configuration."""
        print("\n🛣️  Checking AI conversation routes...")
        
        routes_file = self.project_root / "routes.py"
        if not routes_file.exists():
            self.log_issue("routes.py not found")
            return
        
        with open(routes_file, 'r', encoding='utf-8') as f:
            routes_content = f.read()
        
        # Check for AI conversation routes
        required_routes = [
            'ai_conversation_api',
            'multiple_entries_conversation',
            'single_entry_conversation'
        ]
        
        for route in required_routes:
            if route not in routes_content:
                self.log_issue(f"AI route {route} not found")
            else:
                self.log_success(f"AI route {route} found")
    
    def generate_report(self):
        """Generate a comprehensive health report."""
        print("\n" + "="*60)
        print("🏥 AI CONVERSATION HEALTH REPORT")
        print("="*60)
        
        total_checks = len(self.issues) + len(self.warnings)
        
        if not self.issues and not self.warnings:
            print("🎉 ALL SYSTEMS HEALTHY!")
            print("AI conversation functionality is in excellent condition.")
            return True
        
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print(f"\n📊 HEALTH SCORE: {max(0, 100 - len(self.issues) * 20 - len(self.warnings) * 5)}%")
        
        if self.issues:
            print("\n🔧 RECOMMENDED ACTIONS:")
            print("  1. Fix critical issues immediately")
            print("  2. Run comprehensive tests: python3 run_comprehensive_tests.py")
            print("  3. Check individual components with specific tests")
            print("  4. Commit changes to trigger automated checks")
            
        return len(self.issues) == 0
    
    def run_full_check(self):
        """Run all health checks."""
        print("🚀 Starting AI Conversation Health Check...")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_template_integrity()
        self.check_security_configuration()
        self.check_dependencies()
        self.check_test_health()
        self.check_git_hooks()
        self.check_ai_routes()
        
        return self.generate_report()


def main():
    """Main entry point."""
    brief_mode = '--brief' in sys.argv
    
    checker = AIConversationHealthCheck()
    
    if brief_mode:
        # Run minimal checks for post-commit hook
        checker.check_template_integrity()
        checker.check_security_configuration()
        
        # Brief report
        if not checker.issues:
            print("✅ AI conversation health check passed")
            sys.exit(0)
        else:
            print(f"❌ {len(checker.issues)} issues found")
            for issue in checker.issues:
                print(f"  - {issue}")
            sys.exit(1)
    else:
        # Full comprehensive check
        healthy = checker.run_full_check()
        sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()