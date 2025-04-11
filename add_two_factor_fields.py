"""
Script to add two-factor authentication fields to the User model.
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Boolean, String, DateTime
from sqlalchemy.sql import text

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def add_2fa_fields():
    """Add 2FA fields to the User model."""
    with app.app_context():
        # Using text queries with SQLAlchemy
        try:
            print("Adding 2FA columns to users table...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN two_factor_code VARCHAR(10)"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN two_factor_expiry DATETIME"))
            db.session.commit()
            print("2FA columns added successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            print("The columns might already exist or there was an error adding them.")

if __name__ == '__main__':
    add_2fa_fields()
    print("Database update script completed.")