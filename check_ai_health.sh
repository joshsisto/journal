#!/bin/bash
#
# AI Conversation Health Check - Convenient wrapper script
# This script provides easy access to AI conversation health monitoring
#

echo "🏥 AI Conversation Health Check Tool"
echo "===================================="
echo ""

# Check if health check script exists
if [ ! -f "ai_conversation_health_check.py" ]; then
    echo "❌ Error: ai_conversation_health_check.py not found"
    echo "   Make sure you're in the project root directory"
    exit 1
fi

# Parse command line arguments
case "${1:-full}" in
    "full")
        echo "🔍 Running full comprehensive health check..."
        echo ""
        python3 ai_conversation_health_check.py
        ;;
    "brief")
        echo "⚡ Running brief health check..."
        echo ""
        python3 ai_conversation_health_check.py --brief
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [full|brief|help]"
        echo ""
        echo "Commands:"
        echo "  full    - Run comprehensive health check (default)"
        echo "  brief   - Run quick health check for essential functionality"
        echo "  help    - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0            # Run full health check"
        echo "  $0 brief      # Run brief health check"
        echo "  $0 full       # Run full health check (explicit)"
        echo ""
        echo "This tool monitors AI conversation functionality to prevent breakdowns."
        ;;
    *)
        echo "❌ Invalid option: $1"
        echo "   Use '$0 help' for usage information"
        exit 1
        ;;
esac