#!/usr/bin/env python3
"""
Add location and weather tables to the database.

This script adds:
1. Location table for storing location data
2. Weather table for storing weather information
3. Updates to JournalEntry table to link location and weather
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables before importing app
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from models import db
from sqlalchemy import text

def add_location_weather_tables():
    """Add location and weather tables to the database."""
    app = create_app()
    
    with app.app_context():
        print("Adding location and weather tables...")
        
        # Create Location table
        create_location_table = """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200),
            latitude FLOAT,
            longitude FLOAT,
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),
            postal_code VARCHAR(20),
            location_type VARCHAR(50) DEFAULT 'manual',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create Weather table
        create_weather_table = """
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER,
            journal_entry_id INTEGER,
            temperature FLOAT,
            temperature_unit VARCHAR(10) DEFAULT 'celsius',
            humidity INTEGER,
            pressure FLOAT,
            weather_condition VARCHAR(100),
            weather_description TEXT,
            wind_speed FLOAT,
            wind_direction INTEGER,
            visibility FLOAT,
            uv_index FLOAT,
            precipitation FLOAT,
            precipitation_type VARCHAR(50),
            weather_source VARCHAR(50) DEFAULT 'api',
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (location_id) REFERENCES locations (id),
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id) ON DELETE CASCADE
        );
        """
        
        # Add location_id column to journal_entries
        add_location_to_entries = """
        ALTER TABLE journal_entries 
        ADD COLUMN location_id INTEGER 
        REFERENCES locations(id);
        """
        
        # Add weather_id column to journal_entries  
        add_weather_to_entries = """
        ALTER TABLE journal_entries 
        ADD COLUMN weather_id INTEGER 
        REFERENCES weather_data(id);
        """
        
        try:
            # Execute table creation
            db.session.execute(text(create_location_table))
            print("✓ Created locations table")
            
            db.session.execute(text(create_weather_table))
            print("✓ Created weather_data table")
            
            # Check if columns already exist before adding them
            try:
                db.session.execute(text(add_location_to_entries))
                print("✓ Added location_id column to journal_entries")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ location_id column already exists in journal_entries")
                else:
                    raise e
            
            try:
                db.session.execute(text(add_weather_to_entries))
                print("✓ Added weather_id column to journal_entries")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ weather_id column already exists in journal_entries")
                else:
                    raise e
            
            # Create indexes for better performance
            create_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_locations_lat_lng ON locations(latitude, longitude);",
                "CREATE INDEX IF NOT EXISTS idx_weather_location ON weather_data(location_id);",
                "CREATE INDEX IF NOT EXISTS idx_weather_entry ON weather_data(journal_entry_id);",
                "CREATE INDEX IF NOT EXISTS idx_entries_location ON journal_entries(location_id);",
                "CREATE INDEX IF NOT EXISTS idx_entries_weather ON journal_entries(weather_id);"
            ]
            
            for index_sql in create_indexes:
                db.session.execute(text(index_sql))
            
            print("✓ Created performance indexes")
            
            db.session.commit()
            print("\n✅ Successfully added location and weather tables!")
            
        except Exception as e:
            print(f"❌ Error adding tables: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    add_location_weather_tables()