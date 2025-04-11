"""
Add missing columns to the database using SQLAlchemy.
"""
from flask import Flask
from sqlalchemy.sql import text
from models import db

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def add_missing_columns():
    """Add missing columns to existing tables."""
    with app.app_context():
        try:
            print("Adding missing columns to the users table...")
            
            # All SQLite column additions have to be done one at a time
            operations = [
                "ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0",
                "ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(100)",
                "ALTER TABLE users ADD COLUMN email_verification_expiry DATETIME",
                "ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE users ADD COLUMN two_factor_code VARCHAR(10)",
                "ALTER TABLE users ADD COLUMN two_factor_expiry DATETIME",
            ]
            
            for operation in operations:
                try:
                    db.session.execute(text(operation))
                    print(f"Successfully executed: {operation}")
                except Exception as e:
                    print(f"Error executing {operation}: {str(e)}")
                    print("The column might already exist or there was an error adding it.")
            
            # Make email nullable
            # This is trickier in SQLite, but we'll try this approach
            try:
                # Check if the email column is nullable
                result = db.session.execute(text("PRAGMA table_info(users)"))
                columns = result.fetchall()
                
                email_column = None
                for column in columns:
                    if column[1] == 'email':  # column[1] is the name
                        email_column = column
                        break
                
                if email_column and email_column[3] == 1:  # column[3] is "notnull" constraint (1 = not null)
                    print("The email column is currently NOT NULL, attempting to modify...")
                    
                    # SQLite doesn't support modifying column constraints directly,
                    # so we need to create a new table and copy the data
                    # This is risky, so we'll just notify the user
                    print("\nWARNING: To make the email column nullable, you need to recreate the users table.")
                    print("This requires a more complex migration that's risky to automate.")
                    print("You have two options:")
                    print("1. Run a migration script to make email nullable (complicated but preserves data)")
                    print("2. Drop and recreate the database (simpler but loses all data)")
                    print("Given the complexity, you might want to consider recreating the database if you don't have important data yet.")
                else:
                    print("Email column either doesn't exist or is already nullable.")
            except Exception as e:
                print(f"Error checking email nullability: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            print("\nAll migrations completed.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            raise

if __name__ == '__main__':
    add_missing_columns()
    print("Database update script completed.")