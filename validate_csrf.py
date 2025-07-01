#!/usr/bin/env python3
"""
CSRF Token Validation Script

This script checks all HTML templates for incorrect CSRF token usage.
Run this before commits to catch CSRF misconfigurations.

Usage: python validate_csrf.py
"""

import os
import re
import sys
from pathlib import Path

def find_csrf_issues():
    """Find CSRF token issues in templates."""
    issues = []
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        return []
    
    # Pattern to find incorrect csrf_token usage (without parentheses)
    # This will match {{ csrf_token }} but not {{ csrf_token() }}
    incorrect_pattern = re.compile(r'\{\{\s*csrf_token\s*\}\}')
    
    # Pattern to find correct csrf_token usage (with parentheses)
    correct_pattern = re.compile(r'\{\{\s*csrf_token\(\)\s*\}\}')
    
    print("🔍 Scanning templates for CSRF token issues...")
    print("-" * 50)
    
    for template_file in templates_dir.rglob("*.html"):
        with open(template_file, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                lines = content.split('\n')
                
                # Check each line for issues
                for line_num, line in enumerate(lines, 1):
                    # Check for incorrect usage
                    if incorrect_pattern.search(line):
                        issues.append({
                            'file': str(template_file),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'incorrect_usage'
                        })
                        
            except Exception as e:
                print(f"⚠️  Error reading {template_file}: {e}")
    
    return issues

def main():
    """Main validation function."""
    print("CSRF Token Validation")
    print("=" * 50)
    
    issues = find_csrf_issues()
    
    if not issues:
        print("✅ No CSRF token issues found!")
        print("\n💡 All templates are using correct CSRF token syntax: {{ csrf_token() }}")
        return 0
    
    print(f"❌ Found {len(issues)} CSRF token issue(s):")
    print()
    
    for issue in issues:
        print(f"📁 File: {issue['file']}")
        print(f"📍 Line {issue['line']}: {issue['content']}")
        print(f"🔧 Fix: Change '{{ csrf_token }}' to '{{ csrf_token() }}'")
        print("-" * 40)
    
    print(f"\n💡 To fix all issues at once, run:")
    print(f"   find templates/ -name '*.html' -exec sed -i 's/{{{{ csrf_token }}}}/{{{{ csrf_token() }}}}/g' {{}} \\;")
    
    return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)