"""
Script to update User model to make email optional and add email verification fields.
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def update_user_table():
    """Update User table schema for optional email and verification."""
    with app.app_context():
        try:
            print("Updating users table for email verification...")
            
            # Add is_email_verified column
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0"))
            
            # Add email verification token columns
            db.session.execute(text("ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(100)"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN email_verification_expiry DATETIME"))
            
            # Make email nullable by copying to a temporary column and recreating
            # SQLite doesn't support ALTER COLUMN directly
            
            # First, check if email_temp exists to avoid errors on reruns
            result = db.session.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'email_temp' not in columns:
                # Copy email to a temporary column
                db.session.execute(text("ALTER TABLE users ADD COLUMN email_temp VARCHAR(120)"))
                db.session.execute(text("UPDATE users SET email_temp = email"))
                
                # Need to drop and recreate the column to change nullability
                # Create a backup table first
                db.session.execute(text("CREATE TABLE users_backup AS SELECT * FROM users"))
                print("Created backup table users_backup")
                
                # Drop and recreate users table with nullable email
                # This is a complex SQL operation with potential for data loss
                # So we'll provide instructions instead of automatic execution
                
                print("Table updated with new columns, but email column needs manual modification.")
                print("Since SQLite doesn't support altering column constraints directly,")
                print("you'll need to use the backup table to recreate the users table.")
                print("Please run these commands manually in a SQLite console:")
                print("-------------------------------------------------------")
                print("BEGIN TRANSACTION;")
                print("CREATE TABLE users_new (")
                print("    id INTEGER PRIMARY KEY,")
                print("    timezone VARCHAR(50) DEFAULT 'UTC',")
                print("    username VARCHAR(64) NOT NULL UNIQUE,")
                print("    email VARCHAR(120) UNIQUE,")  # Note the UNIQUE constraint but no NOT NULL
                print("    password_hash VARCHAR(128) NOT NULL,")
                print("    created_at DATETIME,")
                print("    reset_token VARCHAR(100),")
                print("    reset_token_expiry DATETIME,")
                print("    email_change_token VARCHAR(100),")
                print("    email_change_token_expiry DATETIME,")
                print("    new_email VARCHAR(120),")
                print("    two_factor_enabled BOOLEAN DEFAULT 0,")
                print("    two_factor_code VARCHAR(10),")
                print("    two_factor_expiry DATETIME,")
                print("    is_email_verified BOOLEAN DEFAULT 0,")
                print("    email_verification_token VARCHAR(100),")
                print("    email_verification_expiry DATETIME,")
                print("    email_temp VARCHAR(120)")
                print(");")
                print("INSERT INTO users_new SELECT * FROM users_backup;")
                print("DROP TABLE users;")
                print("ALTER TABLE users_new RENAME TO users;")
                print("COMMIT;")
                
            db.session.commit()
            print("Added email verification columns successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            print("Some of the columns might already exist or there was an error adding them.")

if __name__ == '__main__':
    update_user_table()
    print("Database update script completed.")