"""
Setup User model fields using SQLAlchemy's create_all.

This script ensures the User model columns are properly set up
by using SQLAlchemy's create_all method, which will add any
missing columns when we run the app.
"""
from app import create_app, db
from models import User

def setup_fields():
    """
    Create database tables with updated User model.
    
    This approach uses SQLAlchemy's create_all() method to ensure
    the table structure matches the model definition, which will add
    the new columns needed for password reset and email change.
    """
    print("Setting up database tables...")
    app = create_app()
    with app.app_context():
        # This will create tables or add missing columns
        db.create_all()
        print("Database tables updated successfully.")
        
        # Print current User model fields
        column_names = [column.name for column in User.__table__.columns]
        print(f"\nUser model columns: {column_names}")
        
        # Verify password reset fields are present
        reset_fields = [
            'reset_token',
            'reset_token_expiry',
            'email_change_token',
            'email_change_token_expiry',
            'new_email'
        ]
        
        missing_fields = [field for field in reset_fields if field not in column_names]
        
        if missing_fields:
            print(f"\nWarning: The following fields are still missing: {missing_fields}")
            print("You may need to manually migrate your database or recreate it.")
        else:
            print("\nAll required fields are present in the User model.")

if __name__ == "__main__":
    setup_fields()