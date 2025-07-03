#!/usr/bin/env python3

"""
Add question_text column to guided_responses table.

This script adds a new column to store the actual question text alongside the response,
which is essential for template questions where the question text is dynamic.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db
from app import create_app

def add_question_text_column():
    """Add question_text column to guided_responses table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Add the question_text column
            with db.engine.connect() as connection:
                connection.execute(db.text("""
                    ALTER TABLE guided_responses 
                    ADD COLUMN question_text TEXT NULL
                """))
                connection.commit()
            
            print("✅ Successfully added question_text column to guided_responses table")
            
        except Exception as e:
            print(f"❌ Error adding question_text column: {e}")
            # Check if column already exists
            try:
                with db.engine.connect() as connection:
                    result = connection.execute(db.text("""
                        PRAGMA table_info(guided_responses)
                    """))
                    columns = [row[1] for row in result.fetchall()]
                    if 'question_text' in columns:
                        print("✅ Column question_text already exists in guided_responses table")
                    else:
                        print(f"❌ Column does not exist and failed to create: {e}")
            except Exception as check_error:
                print(f"❌ Error checking column existence: {check_error}")

if __name__ == '__main__':
    add_question_text_column()