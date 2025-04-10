# add_timezone_column.py

from app import create_app
from models import db
from sqlalchemy import text

def add_timezone_column():
    """Add timezone column to users table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Use text() for raw SQL in newer SQLAlchemy versions
            db.session.execute(text('ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT "UTC"'))
            db.session.commit()
            print("Successfully added timezone column to users table")
        except Exception as e:
            print(f"Error adding timezone column: {e}")
            print("Attempting alternative method...")
            try:
                # Alternative method using SQLAlchemy Core
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT "UTC"'))
                print("Successfully added timezone column using alternative method")
            except Exception as e2:
                print(f"Alternative method also failed: {e2}")
                print("Please see option 2 or 3 in the instructions")

if __name__ == "__main__":
    add_timezone_column()