"""
Recreate the database with the updated User model.

WARNING: This script will delete and recreate your database!
Make sure you have a backup before running if your data is important.
"""
import os
import sys
import sqlite3
import getpass
from datetime import datetime
from werkzeug.security import generate_password_hash

def backup_database(db_path):
    """Create a backup of the database."""
    if os.path.exists(db_path):
        backup_path = f"{db_path}.bak-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Created backup at {backup_path}")
            return True
        except Exception as e:
            print(f"Error backing up database: {e}")
            return False
    return True  # No database to backup

def find_database_file():
    """Find the SQLite database file."""
    # Common database locations
    common_locations = [
        "./instance/journal.db",
        "./journal.db",
        "../instance/journal.db"
    ]
    
    for location in common_locations:
        if os.path.exists(location):
            return os.path.abspath(location)
    
    # If database not found in common locations, ask user
    user_input = input("Enter the full path to your journal.db file: ")
    if os.path.exists(user_input):
        return os.path.abspath(user_input)
    
    # If database doesn't exist, ask where to create it
    print("Database file not found. A new database will be created.")
    directory = input("Enter the directory where to create the database (default: ./instance): ") or "./instance"
    
    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)
    
    return os.path.abspath(os.path.join(directory, "journal.db"))

def recreate_database():
    """Delete and recreate the database with the updated schema."""
    # Find database
    db_path = find_database_file()
    print(f"Database path: {db_path}")
    
    # Backup existing database
    if os.path.exists(db_path):
        print(f"WARNING: This will delete and recreate your database at {db_path}")
        confirm = input("Are you sure you want to continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        if not backup_database(db_path):
            print("Database backup failed. Operation cancelled.")
            return
        
        # Delete existing database
        try:
            os.remove(db_path)
            print(f"Deleted existing database at {db_path}")
        except Exception as e:
            print(f"Error deleting database: {e}")
            return
    
    # Create database directory if needed
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table with all fields
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT UNIQUE,                       -- Email is now optional (removed NOT NULL)
        is_email_verified BOOLEAN DEFAULT 0,     -- Track if email is verified
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        timezone TEXT DEFAULT 'UTC',
        reset_token TEXT,
        reset_token_expiry TIMESTAMP,
        email_verification_token TEXT,          -- Token for email verification
        email_verification_expiry TIMESTAMP,    -- Expiry for email verification
        email_change_token TEXT,
        email_change_token_expiry TIMESTAMP,
        new_email TEXT,
        two_factor_enabled BOOLEAN DEFAULT 0,   -- 2FA settings
        two_factor_code TEXT,
        two_factor_expiry TIMESTAMP
    )
    ''')
    
    # Create journal_entries table
    cursor.execute('''
    CREATE TABLE journal_entries (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        content TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        entry_type TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create guided_responses table
    cursor.execute('''
    CREATE TABLE guided_responses (
        id INTEGER PRIMARY KEY,
        journal_entry_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        response TEXT,
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
    )
    ''')
    
    # Create exercise_logs table
    cursor.execute('''
    CREATE TABLE exercise_logs (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        date DATE NOT NULL,
        has_exercised BOOLEAN DEFAULT 0,
        workout_type TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create tags table
    cursor.execute('''
    CREATE TABLE tags (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        color TEXT DEFAULT '#6c757d',
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE (name, user_id)
    )
    ''')
    
    # Create entry_tags table
    cursor.execute('''
    CREATE TABLE entry_tags (
        tag_id INTEGER NOT NULL,
        entry_id INTEGER NOT NULL,
        PRIMARY KEY (tag_id, entry_id),
        FOREIGN KEY (tag_id) REFERENCES tags (id),
        FOREIGN KEY (entry_id) REFERENCES journal_entries (id)
    )
    ''')
    
    # Create a test user
    create_user = input("Do you want to create a test user? (y/n): ")
    if create_user.lower() == 'y':
        username = input("Enter username (default: admin): ") or "admin"
        email = input("Enter email (default: admin@example.com): ") or "admin@example.com"
        password = getpass.getpass("Enter password (default: password): ") or "password"
        
        # Ask if email should be entered
        use_email = input("Do you want to add an email for this user? (y/n): ")
        if use_email.lower() == 'y':
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, timezone) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), 'UTC')
            )
        else:
            cursor.execute(
                "INSERT INTO users (username, password_hash, timezone) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), 'UTC')
            )
    
    # Commit changes and close
    conn.commit()
    conn.close()
    
    print(f"Database successfully recreated at {db_path}")
    print("All tables created with the updated schema.")

if __name__ == "__main__":
    try:
        recreate_database()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)