"""
Database migration script to add tag-related tables.

Run this script to add the Tag table and entry_tags association table
to an existing database.
"""

import os
import sys
from app import create_app
from models import db
from sqlalchemy import text

def add_tag_tables():
    """Add tag-related tables to the database."""
    app = create_app()
    
    with app.app_context():
        # Execute SQL to create tag table
        with db.engine.connect() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                user_id INTEGER NOT NULL,
                color VARCHAR(7) DEFAULT '#6c757d',
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (name, user_id)
            );
            """))
            
            # Execute SQL to create entry_tags association table
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entry_tags (
                tag_id INTEGER NOT NULL,
                entry_id INTEGER NOT NULL,
                PRIMARY KEY (tag_id, entry_id),
                FOREIGN KEY (tag_id) REFERENCES tags (id),
                FOREIGN KEY (entry_id) REFERENCES journal_entries (id)
            );
            """))
            
            # Commit the transaction
            conn.commit()
        
        print("Tag tables created successfully!")

if __name__ == "__main__":
    add_tag_tables()