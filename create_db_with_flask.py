"""
Create a new database with the Flask application context.
This ensures the schema matches the SQLAlchemy models exactly.
"""
import os
import sys
from datetime import datetime
from flask import Flask
from werkzeug.security import generate_password_hash
from config import Config
from models import db, User, JournalEntry, Tag, GuidedResponse, ExerciseLog, Photo

def backup_database():
    """Create a backup of the database if it exists."""
    db_path = 'journal.db'
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

def create_database():
    """Create a new database with the current SQLAlchemy models."""
    # Create a minimal Flask app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    db.init_app(app)
    
    # Check if database exists
    db_path = 'journal.db'
    if os.path.exists(db_path):
        print(f"WARNING: This will delete and recreate your database at {db_path}")
        confirm = input("Are you sure you want to continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        # Backup the database
        if not backup_database():
            print("Database backup failed. Operation cancelled.")
            return
        
        # Delete the existing database
        try:
            os.remove(db_path)
            print(f"Deleted existing database at {db_path}")
        except Exception as e:
            print(f"Error deleting database: {e}")
            return
    
    # Create the database
    with app.app_context():
        db.create_all()
        print("All database tables created successfully.")
        
        # Ask if a test user should be created
        create_user = input("Do you want to create a test user? (y/n): ")
        if create_user.lower() == 'y':
            username = input("Enter username (default: admin): ") or "admin"
            
            # Ask if email should be provided
            use_email = input("Do you want to add an email for this user? (y/n): ")
            email = None
            if use_email.lower() == 'y':
                email = input("Enter email (default: admin@example.com): ") or "admin@example.com"
                verify_email = input("Mark email as verified? (y/n): ")
                
            password = input("Enter password (default: password): ") or "password"
            
            # Create user
            user = User(
                username=username,
                email=email,
                timezone='UTC'
            )
            user.set_password(password)
            
            # Set email verification
            if use_email.lower() == 'y' and verify_email.lower() == 'y':
                user.is_email_verified = True
            
            db.session.add(user)
            db.session.commit()
            print(f"Created user: {username}")
            if email:
                print(f"Email: {email} (Verified: {user.is_email_verified})")
        
        print("Database setup complete.")

if __name__ == "__main__":
    try:
        create_database()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)