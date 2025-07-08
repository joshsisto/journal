#!/bin/bash

# MCP Browser Testing Framework Deployment Script
# ============================================
# This script deploys and manages the MCP browser testing framework
# for comprehensive testing of the journal application.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
LOG_FILE="$PROJECT_DIR/mcp_deployment.log"
TEST_RESULTS_DIR="$PROJECT_DIR/mcp_test_results"
BACKUP_DIR="$PROJECT_DIR/mcp_backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [$level] $message" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "$*"
    echo -e "${BLUE}[INFO]${NC} $*"
}

warn() {
    log "WARN" "$*"
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    log "ERROR" "$*"
    echo -e "${RED}[ERROR]${NC} $*"
}

success() {
    log "SUCCESS" "$*"
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Function to check dependencies
check_dependencies() {
    info "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    fi
    
    # Check required Python modules
    local python_modules=("concurrent.futures" "json" "logging" "threading" "dataclasses")
    for module in "${python_modules[@]}"; do
        if ! python3 -c "import $module" &> /dev/null; then
            missing_deps+=("python3-$module")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing dependencies: ${missing_deps[*]}"
        error "Please install missing dependencies and try again"
        exit 1
    fi
    
    success "All dependencies satisfied"
}

# Function to setup environment
setup_environment() {
    info "Setting up MCP testing environment..."
    
    # Create directories
    mkdir -p "$TEST_RESULTS_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$PROJECT_DIR/logs"
    
    # Create configuration file if it doesn't exist
    local config_file="$PROJECT_DIR/mcp_testing_config.json"
    if [ ! -f "$config_file" ]; then
        info "Creating default configuration file..."
        cat > "$config_file" << EOF
{
    "default_config": {
        "base_url": "https://journal.joshsisto.com",
        "local_url": "http://localhost:5000",
        "max_concurrent_tests": 10,
        "test_timeout": 300,
        "log_level": "INFO",
        "output_dir": "mcp_test_results",
        "generate_html_report": true
    },
    "test_users": [
        {
            "username": "testuser1",
            "password": "TestPass123!",
            "email": "testuser1@example.com"
        },
        {
            "username": "testuser2", 
            "password": "TestPass456!",
            "email": "testuser2@example.com"
        },
        {
            "username": "testuser3",
            "password": "TestPass789!",
            "email": "testuser3@example.com"
        }
    ],
    "security_config": {
        "enable_vulnerability_scanning": true,
        "enable_penetration_testing": true,
        "enable_compliance_checking": true,
        "severity_threshold": "medium"
    },
    "performance_config": {
        "load_test_duration": 300,
        "concurrent_users": 50,
        "ramp_up_time": 60,
        "think_time": 5
    }
}
EOF
        success "Configuration file created: $config_file"
    fi
    
    # Make scripts executable
    chmod +x "$PROJECT_DIR/mcp_browser_testing_framework.py"
    chmod +x "$PROJECT_DIR/mcp_testing_agents.py"
    chmod +x "$PROJECT_DIR/mcp_test_orchestrator.py"
    
    success "Environment setup complete"
}

# Function to validate framework files
validate_framework() {
    info "Validating MCP testing framework files..."
    
    local required_files=(
        "mcp_browser_testing_framework.py"
        "mcp_testing_agents.py"
        "mcp_test_orchestrator.py"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        error "Missing framework files: ${missing_files[*]}"
        exit 1
    fi
    
    # Validate Python syntax
    for file in "${required_files[@]}"; do
        if ! python3 -m py_compile "$PROJECT_DIR/$file"; then
            error "Syntax error in $file"
            exit 1
        fi
    done
    
    success "Framework validation complete"
}

# Function to run security tests
run_security_tests() {
    local target_url="${1:-https://journal.joshsisto.com}"
    local concurrent="${2:-5}"
    
    info "Running security tests against $target_url..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="$TEST_RESULTS_DIR/security_$timestamp"
    
    python3 "$PROJECT_DIR/mcp_test_orchestrator.py" \
        --url "$target_url" \
        --mode security \
        --concurrent "$concurrent" \
        --output "$output_dir" \
        --html \
        --log-level INFO
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Security tests completed successfully"
        info "Results saved to: $output_dir"
    else
        error "Security tests failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to run fuzz tests
run_fuzz_tests() {
    local target_url="${1:-https://journal.joshsisto.com}"
    local concurrent="${2:-3}"
    
    info "Running fuzz tests against $target_url..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="$TEST_RESULTS_DIR/fuzz_$timestamp"
    
    python3 "$PROJECT_DIR/mcp_test_orchestrator.py" \
        --url "$target_url" \
        --mode fuzz \
        --concurrent "$concurrent" \
        --output "$output_dir" \
        --timeout 600 \
        --html \
        --log-level INFO
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Fuzz tests completed successfully"
        info "Results saved to: $output_dir"
    else
        error "Fuzz tests failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to run concurrency tests
run_concurrency_tests() {
    local target_url="${1:-https://journal.joshsisto.com}"
    local concurrent="${2:-10}"
    
    info "Running concurrency tests against $target_url..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="$TEST_RESULTS_DIR/concurrency_$timestamp"
    
    python3 "$PROJECT_DIR/mcp_test_orchestrator.py" \
        --url "$target_url" \
        --mode concurrency \
        --concurrent "$concurrent" \
        --timeout 900 \
        --output "$output_dir" \
        --html \
        --log-level INFO
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Concurrency tests completed successfully"
        info "Results saved to: $output_dir"
    else
        error "Concurrency tests failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to run login flow tests
run_login_tests() {
    local target_url="${1:-https://journal.joshsisto.com}"
    local concurrent="${2:-3}"
    
    info "Running login flow tests against $target_url..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="$TEST_RESULTS_DIR/login_$timestamp"
    
    python3 "$PROJECT_DIR/mcp_test_orchestrator.py" \
        --url "$target_url" \
        --mode login \
        --concurrent "$concurrent" \
        --output "$output_dir" \
        --html \
        --log-level INFO
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Login flow tests completed successfully"
        info "Results saved to: $output_dir"
    else
        error "Login flow tests failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to run all tests
run_all_tests() {
    local target_url="${1:-https://journal.joshsisto.com}"
    local concurrent="${2:-8}"
    
    info "Running comprehensive test suite against $target_url..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="$TEST_RESULTS_DIR/comprehensive_$timestamp"
    
    python3 "$PROJECT_DIR/mcp_test_orchestrator.py" \
        --url "$target_url" \
        --mode all \
        --concurrent "$concurrent" \
        --timeout 1200 \
        --output "$output_dir" \
        --html \
        --log-level INFO
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Comprehensive test suite completed successfully"
        info "Results saved to: $output_dir"
        
        # Generate summary report
        generate_summary_report "$output_dir"
    else
        error "Comprehensive test suite failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to generate summary report
generate_summary_report() {
    local test_dir="$1"
    local summary_file="$test_dir/test_summary.txt"
    
    info "Generating test summary report..."
    
    cat > "$summary_file" << EOF
MCP Browser Testing Framework - Test Summary
==========================================

Test Execution Details:
- Timestamp: $(date)
- Test Directory: $test_dir
- Target URL: $target_url
- Framework Version: 1.0.0

Test Results:
EOF
    
    # Find and parse JSON report
    local json_report=$(find "$test_dir" -name "*.json" -type f | head -1)
    if [ -f "$json_report" ]; then
        echo "" >> "$summary_file"
        echo "Detailed Results (from $json_report):" >> "$summary_file"
        python3 -c "
import json
import sys
try:
    with open('$json_report', 'r') as f:
        data = json.load(f)
    
    summary = data.get('test_summary', {})
    security = data.get('vulnerability_assessment', {})
    
    print(f\"Total Tests: {summary.get('total_tests', 0)}\")
    print(f\"Passed Tests: {summary.get('passed_tests', 0)}\")
    print(f\"Failed Tests: {summary.get('failed_tests', 0)}\")
    print(f\"Pass Rate: {summary.get('pass_rate', 0):.1f}%\")
    print(f\"Security Score: {security.get('security_score', 0)}/100\")
    print(f\"Risk Level: {security.get('overall_risk_level', 'unknown').upper()}\")
    print(f\"Security Findings: {len(data.get('security_findings', []))}\")
    
except Exception as e:
    print(f\"Error parsing report: {e}\")
" >> "$summary_file"
    fi
    
    echo "" >> "$summary_file"
    echo "Files Generated:" >> "$summary_file"
    find "$test_dir" -type f -exec basename {} \; | sort >> "$summary_file"
    
    success "Summary report generated: $summary_file"
}

# Function to monitor test execution
monitor_tests() {
    local output_dir="$1"
    local check_interval="${2:-30}"
    
    info "Monitoring test execution in $output_dir..."
    info "Check interval: $check_interval seconds"
    
    while true; do
        sleep "$check_interval"
        
        # Check for new log files
        local log_files=$(find "$output_dir" -name "*.log" -type f 2>/dev/null | wc -l)
        local json_files=$(find "$output_dir" -name "*.json" -type f 2>/dev/null | wc -l)
        local html_files=$(find "$output_dir" -name "*.html" -type f 2>/dev/null | wc -l)
        
        info "Current status: $log_files logs, $json_files JSON reports, $html_files HTML reports"
        
        # Check if testing is complete (has final report)
        if [ -f "$output_dir/mcp_test_report_"*.json ]; then
            success "Test execution appears to be complete"
            break
        fi
    done
}

# Function to cleanup old results
cleanup_old_results() {
    local days="${1:-7}"
    
    info "Cleaning up test results older than $days days..."
    
    find "$TEST_RESULTS_DIR" -type d -mtime +$days -exec rm -rf {} + 2>/dev/null || true
    find "$BACKUP_DIR" -type f -mtime +$days -delete 2>/dev/null || true
    find "$PROJECT_DIR/logs" -type f -mtime +$days -delete 2>/dev/null || true
    
    success "Cleanup complete"
}

# Function to backup test results
backup_results() {
    local source_dir="$1"
    local backup_name="${2:-$(basename "$source_dir")_backup_$(date '+%Y%m%d_%H%M%S')}"
    
    info "Backing up test results from $source_dir..."
    
    tar -czf "$BACKUP_DIR/$backup_name.tar.gz" -C "$(dirname "$source_dir")" "$(basename "$source_dir")"
    
    success "Backup created: $BACKUP_DIR/$backup_name.tar.gz"
}

# Function to show usage
show_usage() {
    cat << EOF
MCP Browser Testing Framework Deployment Script
==============================================

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup                   Setup testing environment
    validate               Validate framework files
    security [URL] [CONC]  Run security tests
    fuzz [URL] [CONC]      Run fuzz tests  
    concurrency [URL] [CONC] Run concurrency tests
    login [URL] [CONC]     Run login flow tests
    all [URL] [CONC]       Run comprehensive test suite
    monitor [DIR] [INT]    Monitor test execution
    cleanup [DAYS]         Cleanup old results
    backup [DIR] [NAME]    Backup test results
    status                 Show framework status
    help                   Show this help message

Parameters:
    URL                    Target URL (default: https://journal.joshsisto.com)
    CONC                   Concurrent tests (default: varies by test type)
    DIR                    Directory to monitor/backup
    INT                    Monitor check interval in seconds (default: 30)
    DAYS                   Number of days for cleanup (default: 7)
    NAME                   Backup name (default: auto-generated)

Examples:
    $0 setup
    $0 security https://journal.joshsisto.com 5
    $0 all https://localhost:5000 3
    $0 monitor mcp_test_results/comprehensive_20240101_120000
    $0 cleanup 14
    $0 backup mcp_test_results/security_20240101_120000

EOF
}

# Function to show status
show_status() {
    info "MCP Browser Testing Framework Status"
    echo "====================================="
    
    echo "Framework Files:"
    for file in "mcp_browser_testing_framework.py" "mcp_testing_agents.py" "mcp_test_orchestrator.py"; do
        if [ -f "$PROJECT_DIR/$file" ]; then
            echo "  ✓ $file"
        else
            echo "  ✗ $file (missing)"
        fi
    done
    
    echo ""
    echo "Directories:"
    echo "  Test Results: $TEST_RESULTS_DIR ($(ls -1 "$TEST_RESULTS_DIR" 2>/dev/null | wc -l) items)"
    echo "  Backups: $BACKUP_DIR ($(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l) items)"
    echo "  Logs: $PROJECT_DIR/logs ($(ls -1 "$PROJECT_DIR/logs" 2>/dev/null | wc -l) items)"
    
    echo ""
    echo "Recent Test Results:"
    find "$TEST_RESULTS_DIR" -maxdepth 1 -type d -newer "$LOG_FILE" 2>/dev/null | head -5 | while read -r dir; do
        echo "  $(basename "$dir")"
    done || echo "  No recent results found"
    
    echo ""
    echo "Disk Usage:"
    echo "  Test Results: $(du -sh "$TEST_RESULTS_DIR" 2>/dev/null | cut -f1 || echo "0B")"
    echo "  Backups: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0B")"
    
    echo ""
    echo "Dependencies:"
    if command -v python3 &> /dev/null; then
        echo "  ✓ Python 3 ($(python3 --version 2>&1))"
    else
        echo "  ✗ Python 3 (missing)"
    fi
    
    if command -v pip3 &> /dev/null; then
        echo "  ✓ pip3"
    else
        echo "  ✗ pip3 (missing)"
    fi
}

# Main execution
main() {
    local command="${1:-help}"
    
    # Initialize logging
    touch "$LOG_FILE"
    
    case "$command" in
        setup)
            check_dependencies
            setup_environment
            validate_framework
            ;;
        validate)
            validate_framework
            ;;
        security)
            check_dependencies
            validate_framework
            run_security_tests "${2:-}" "${3:-}"
            ;;
        fuzz)
            check_dependencies
            validate_framework
            run_fuzz_tests "${2:-}" "${3:-}"
            ;;
        concurrency)
            check_dependencies
            validate_framework
            run_concurrency_tests "${2:-}" "${3:-}"
            ;;
        login)
            check_dependencies
            validate_framework
            run_login_tests "${2:-}" "${3:-}"
            ;;
        all)
            check_dependencies
            validate_framework
            run_all_tests "${2:-}" "${3:-}"
            ;;
        monitor)
            monitor_tests "${2:-$TEST_RESULTS_DIR}" "${3:-30}"
            ;;
        cleanup)
            cleanup_old_results "${2:-7}"
            ;;
        backup)
            backup_results "${2:-$TEST_RESULTS_DIR}" "${3:-}"
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"