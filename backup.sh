#!/bin/bash

# Journal App Production Backup Script
# Usage: ./backup.sh [backup|restore|list] [options]

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKUP_SYSTEM="$PROJECT_ROOT/backup_system.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if app is running
check_app_running() {
    if sudo systemctl is-active --quiet journal-app.service; then
        return 0  # Service is running
    else
        return 1  # Service is not running
    fi
}

# Function to stop the application
stop_app() {
    print_status "Stopping journal-app service..."
    sudo systemctl stop journal-app.service
    sleep 2
    
    if ! check_app_running; then
        print_status "Service stopped successfully"
    else
        print_error "Failed to stop service"
        exit 1
    fi
}

# Function to start the application
start_app() {
    print_status "Starting journal-app service..."
    sudo systemctl start journal-app.service
    sleep 3
    
    if check_app_running; then
        print_status "Service started successfully"
    else
        print_error "Failed to start service"
        exit 1
    fi
}

# Function to restart the application
restart_app() {
    print_status "Restarting journal-app service..."
    sudo systemctl restart journal-app.service
    sleep 3
    
    if check_app_running; then
        print_status "Service restarted successfully"
    else
        print_error "Failed to restart service"
        exit 1
    fi
}

# Function to create pre-deployment backup
pre_deploy_backup() {
    print_status "Creating pre-deployment backup..."
    
    # Stop app for consistent backup
    if check_app_running; then
        stop_app
        APP_WAS_RUNNING=1
    else
        APP_WAS_RUNNING=0
    fi
    
    # Create backup
    python3 "$BACKUP_SYSTEM" backup
    
    # Restart app if it was running
    if [ "$APP_WAS_RUNNING" -eq 1 ]; then
        start_app
    fi
    
    print_status "Pre-deployment backup completed"
}

# Function to rollback to previous backup
rollback() {
    local timestamp="$1"
    
    if [ -z "$timestamp" ]; then
        print_error "No timestamp provided for rollback"
        echo "Available backups:"
        python3 "$BACKUP_SYSTEM" list
        exit 1
    fi
    
    print_warning "This will rollback both database and codebase to: $timestamp"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Rollback cancelled"
        exit 0
    fi
    
    # Stop application
    if check_app_running; then
        stop_app
    fi
    
    # Perform rollback
    print_status "Rolling back to: $timestamp"
    python3 "$BACKUP_SYSTEM" restore "$timestamp"
    
    # Start application
    start_app
    
    print_status "Rollback completed successfully"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Backup Commands:"
    echo "  backup              Create full backup (database + codebase)"
    echo "  backup --db-only    Create database backup only"
    echo "  backup --code-only  Create codebase backup only"
    echo "  list                List available backups"
    echo "  list --size         List backups with sizes"
    echo "  cleanup             Clean up old backups (keeps 7 daily, 4 weekly, 6 monthly)"
    echo "  cleanup --dry-run   Show what would be removed without removing"
    echo "  remove TIMESTAMP    Remove specific backup"
    echo "  size [TIMESTAMP]    Show backup sizes"
    echo "  restore TIMESTAMP   Restore from specific backup"
    echo "  rollback TIMESTAMP  Stop service, restore, restart service"
    echo "  pre-deploy          Create backup before deployment"
    echo ""
    echo "Service Commands:"
    echo "  restart             Restart journal-app.service"
    echo "  start               Start journal-app.service"
    echo "  stop                Stop journal-app.service"
    echo "  status              Show service status"
    echo "  logs                Follow service logs"
    echo ""
    echo "Examples:"
    echo "  $0 backup                    # Full backup"
    echo "  $0 pre-deploy                # Pre-deployment backup"
    echo "  $0 restart                   # Restart service (reload code)"
    echo "  $0 status                    # Check if service is running"
    echo "  $0 logs                      # Follow logs"
    echo "  $0 rollback 20240630_143022  # Emergency rollback"
}

# Main script logic
case "${1:-}" in
    "backup")
        shift
        if check_app_running; then
            print_warning "Application is running during backup"
            print_warning "For consistency, consider stopping the app first"
        fi
        python3 "$BACKUP_SYSTEM" backup "$@"
        ;;
    
    "list")
        shift
        python3 "$BACKUP_SYSTEM" list "$@"
        ;;
    
    "cleanup")
        shift
        python3 "$BACKUP_SYSTEM" cleanup "$@"
        ;;
    
    "remove")
        if [ -z "${2:-}" ]; then
            print_error "Timestamp required for remove"
            python3 "$BACKUP_SYSTEM" list
            exit 1
        fi
        shift
        python3 "$BACKUP_SYSTEM" remove "$@"
        ;;
    
    "size")
        shift
        python3 "$BACKUP_SYSTEM" size "$@"
        ;;
    
    "restore")
        if [ -z "${2:-}" ]; then
            print_error "Timestamp required for restore"
            python3 "$BACKUP_SYSTEM" list
            exit 1
        fi
        shift
        python3 "$BACKUP_SYSTEM" restore "$@"
        ;;
    
    "rollback")
        rollback "${2:-}"
        ;;
    
    "pre-deploy")
        pre_deploy_backup
        ;;
    
    "restart")
        restart_app
        ;;
    
    "start")
        start_app
        ;;
    
    "stop")
        stop_app
        ;;
    
    "status")
        if check_app_running; then
            print_status "journal-app.service is running"
            sudo systemctl status journal-app.service --no-pager -l
        else
            print_warning "journal-app.service is not running"
            sudo systemctl status journal-app.service --no-pager -l
        fi
        ;;
    
    "logs")
        print_status "Following journal-app.service logs (Ctrl+C to exit)..."
        sudo journalctl -u journal-app.service -f
        ;;
    
    "help"|"--help"|"-h")
        show_usage
        ;;
    
    *)
        show_usage
        exit 1
        ;;
esac