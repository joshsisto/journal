"""
Script to make email optional in the User model and add verification fields.
Uses a direct SQLite connection to do the schema migration safely.
"""
import sqlite3
import os
import os.path

# Make sure we use the absolute path to the database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'journal.db')
print(f"Using database at: {DB_PATH}")

def update_schema():
    """Update the database schema to make email optional and add verification."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Migrating database schema to make email optional...")
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Check if columns already exist to avoid errors on reruns
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add verification columns if they don't exist yet
        if 'is_email_verified' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_email_verified INTEGER DEFAULT 0")
            print("Added is_email_verified column")
            
        if 'email_verification_token' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token TEXT")
            print("Added email_verification_token column")
            
        if 'email_verification_expiry' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_expiry TIMESTAMP")
            print("Added email_verification_expiry column")
        
        # SQLite doesn't allow altering column constraints directly
        # We need to create a new table and copy the data
        
        # Create new table with email as nullable
        cursor.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY,
            timezone TEXT DEFAULT 'UTC',
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            is_email_verified INTEGER DEFAULT 0,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP,
            reset_token TEXT,
            reset_token_expiry TIMESTAMP,
            email_change_token TEXT,
            email_change_token_expiry TIMESTAMP,
            new_email TEXT,
            two_factor_enabled INTEGER DEFAULT 0,
            two_factor_code TEXT,
            two_factor_expiry TIMESTAMP,
            email_verification_token TEXT,
            email_verification_expiry TIMESTAMP
        )
        """)
        print("Created new users table with updated schema")
        
        # Copy data from the old table to the new one
        cursor.execute("""
        INSERT INTO users_new
        SELECT
            id,
            timezone,
            username,
            email,
            is_email_verified,
            password_hash,
            created_at,
            reset_token,
            reset_token_expiry,
            email_change_token,
            email_change_token_expiry,
            new_email,
            two_factor_enabled,
            two_factor_code,
            two_factor_expiry,
            email_verification_token,
            email_verification_expiry
        FROM users
        """)
        print(f"Copied {cursor.rowcount} user records to the new table")
        
        # Drop the old table and rename the new one
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        print("Replaced old users table with the new one")
        
        # Commit the transaction
        conn.commit()
        print("Schema migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    update_schema()
    print("Database schema update complete.")