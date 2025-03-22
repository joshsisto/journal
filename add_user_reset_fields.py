"""
Add password reset and email change fields to User model.

This script adds new columns to the users table to support password
reset and email change functionality.
"""
import sqlite3
import os
from app import create_app
from flask import current_app

def add_columns():
    """Add new columns to users table for password reset and email change."""
    # Create app context
    app = create_app()
    
    # Get database path from app config
    with app.app_context():
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Handle SQLite connection
        if db_uri.startswith('sqlite:///'):
            # For absolute path
            db_path = db_uri.replace('sqlite:///', '')
            
            # If it's a relative path, combine with instance folder
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.instance_path, db_path)
                
            print(f"Using database at: {db_path}")
        else:
            raise ValueError(f"Unsupported database URI: {db_uri}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not cursor.fetchone():
        print("Error: 'users' table not found in the database.")
        print("Make sure you've run the application at least once to create the tables.")
        conn.close()
        return
    
    # Add reset_token column
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN reset_token TEXT;')
        print("Added reset_token column")
    except sqlite3.OperationalError as e:
        print(f"Error adding reset_token column: {e}")
    
    # Add reset_token_expiry column
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP;')
        print("Added reset_token_expiry column")
    except sqlite3.OperationalError as e:
        print(f"Error adding reset_token_expiry column: {e}")
    
    # Add email_change_token column
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN email_change_token TEXT;')
        print("Added email_change_token column")
    except sqlite3.OperationalError as e:
        print(f"Error adding email_change_token column: {e}")
    
    # Add email_change_token_expiry column
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN email_change_token_expiry TIMESTAMP;')
        print("Added email_change_token_expiry column")
    except sqlite3.OperationalError as e:
        print(f"Error adding email_change_token_expiry column: {e}")
    
    # Add new_email column
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN new_email TEXT;')
        print("Added new_email column")
    except sqlite3.OperationalError as e:
        print(f"Error adding new_email column: {e}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database migration completed successfully.")

if __name__ == "__main__":
    add_columns()