#!/usr/bin/env python3
"""
Direct test script for AI conversation.
This bypasses the Flask app to test the AI directly.
"""

import os
import sys
import json
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

def main():
    """Run a direct test of the AI conversation functionality."""
    try:
        from ai_utils import get_ai_response
        
        # Simple test entry
        entries = [{
            "id": 1,
            "date": "2025-04-10",
            "entry_type": "quick",
            "content": "Today was a great day. I felt really happy and productive."
        }]
        
        # Test question
        question = "How am I feeling based on this entry?"
        
        print(f"Testing AI with {len(entries)} entries and question: '{question}'")
        print("-" * 50)
        
        # Get response
        response = get_ai_response(entries, question)
        
        print("-" * 50)
        print("AI Response:")
        print(response)
        print("-" * 50)
        
        print("Test completed successfully!")
        return 0
    except Exception as e:
        print(f"Error in direct test: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())