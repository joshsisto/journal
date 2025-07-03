#!/usr/bin/env python3
"""
Fix missing template_id column in journal_entries table.

This script adds the missing template_id column that was referenced in the
model but not created during the initial migration.
"""

from app import create_app
from models import db
import sqlite3

def fix_template_id_column():
    """Add the missing template_id column to journal_entries table."""
    app = create_app()
    
    with app.app_context():
        print("🔧 Fixing missing template_id column in journal_entries table...")
        
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(db.text("PRAGMA table_info(journal_entries)"))
                columns = [row[1] for row in result]
                
                if 'template_id' in columns:
                    print("✅ template_id column already exists!")
                    return
                
                print("📝 Adding template_id column to journal_entries table...")
                
                # Add the missing column
                conn.execute(db.text("""
                    ALTER TABLE journal_entries 
                    ADD COLUMN template_id INTEGER 
                    REFERENCES journal_templates(id)
                """))
                conn.commit()
                
                print("✅ template_id column added successfully!")
                
                # Verify the column was added
                result = conn.execute(db.text("PRAGMA table_info(journal_entries)"))
                columns = [row[1] for row in result]
            
            if 'template_id' in columns:
                print("✅ Column verified in database schema!")
            else:
                print("❌ Column verification failed!")
                return False
            
            print("🎉 Database fix completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing database: {str(e)}")
            return False

if __name__ == "__main__":
    fix_template_id_column()