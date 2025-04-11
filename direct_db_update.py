"""
Direct database update to add the required columns.

This script uses SQLite's ALTER TABLE command to add the needed columns
without relying on Flask or SQLAlchemy.
"""
import sqlite3
import os
import sys

def find_database_file():
    """Find the SQLite database file location."""
    # Common locations to check
    possible_locations = [
        "./instance/journal.db",  # Default Flask instance location
        "./journal.db",           # App root
        "../journal.db",          # One level up
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            return os.path.abspath(location)
    
    # Let the user specify the location
    print("Database file not found in common locations.")
    user_path = input("Please enter the full path to your journal.db file: ")
    
    if os.path.exists(user_path):
        return os.path.abspath(user_path)
    else:
        print(f"Error: File not found at {user_path}")
        sys.exit(1)

def update_database():
    """Add new columns to the users table and fix email constraints."""
    # Find database
    db_path = find_database_file()
    print(f"Using database at: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not cursor.fetchone():
        print("Error: 'users' table not found in the database.")
        conn.close()
        return
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(users);")
    existing_columns = [row[1] for row in cursor.fetchall()]
    print(f"Existing columns: {existing_columns}")
    
    # Define columns to add and their types
    columns_to_add = {
        "reset_token": "TEXT",
        "reset_token_expiry": "TIMESTAMP",
        "email_change_token": "TEXT",
        "email_change_token_expiry": "TIMESTAMP",
        "new_email": "TEXT",
        "is_email_verified": "BOOLEAN DEFAULT 0",
        "email_verification_token": "TEXT",
        "email_verification_expiry": "TIMESTAMP",
        "two_factor_enabled": "BOOLEAN DEFAULT 0",
        "two_factor_code": "TEXT",
        "two_factor_expiry": "TIMESTAMP"
    }
    
    # Add missing columns
    for column, type_ in columns_to_add.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {type_};")
                print(f"Added {column} column")
            except sqlite3.OperationalError as e:
                print(f"Error adding {column} column: {e}")
    
    # Create a new table with correct constraints for email
    print("Rebuilding users table to ensure email is optional...")
    try:
        # Create a new table with the proper structure
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,        -- Email is now optional (no NOT NULL)
            is_email_verified BOOLEAN DEFAULT 0,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timezone TEXT DEFAULT 'UTC',
            reset_token TEXT,
            reset_token_expiry TIMESTAMP,
            email_verification_token TEXT,
            email_verification_expiry TIMESTAMP,
            email_change_token TEXT,
            email_change_token_expiry TIMESTAMP,
            new_email TEXT,
            two_factor_enabled BOOLEAN DEFAULT 0,
            two_factor_code TEXT,
            two_factor_expiry TIMESTAMP
        )
        ''')
        
        # Copy all data
        cursor.execute('''
        INSERT INTO users_new 
        SELECT id, username, email, 
               COALESCE(is_email_verified, 0) as is_email_verified,
               password_hash, created_at, 
               COALESCE(timezone, 'UTC') as timezone,
               reset_token, reset_token_expiry,
               email_verification_token, email_verification_expiry,
               email_change_token, email_change_token_expiry,
               new_email,
               COALESCE(two_factor_enabled, 0) as two_factor_enabled,
               two_factor_code, two_factor_expiry
        FROM users
        ''')
        
        # Delete old table and rename new one
        cursor.execute('DROP TABLE users')
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        print("Users table rebuilt with correct structure for optional email")
    except sqlite3.Error as e:
        print(f"Error rebuilding users table: {e}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database update completed.")

if __name__ == "__main__":
    update_database()