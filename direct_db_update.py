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
    """Add new columns to the users table."""
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
        "new_email": "TEXT"
    }
    
    # Add missing columns
    for column, type_ in columns_to_add.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {type_};")
                print(f"Added {column} column")
            except sqlite3.OperationalError as e:
                print(f"Error adding {column} column: {e}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database update completed.")

if __name__ == "__main__":
    update_database()