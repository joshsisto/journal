#!/usr/bin/env python3
"""
Script to migrate data from SQLite to PostgreSQL database.

Prerequisites:
- Both SQLite and PostgreSQL databases must have the same schema structure
- SQLite database must be specified in SQLITE_DATABASE_URI
- PostgreSQL database must be specified in DATABASE_URL or through individual components

Usage:
    python migrate_sqlite_to_postgres.py
"""

import os
import json
import sqlite3
import psycopg2
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import create_engine

# Load environment variables from .env file
load_dotenv()

# SQLite database path
SQLITE_PATH = 'journal.db'

# PostgreSQL connection settings
if os.environ.get('DATABASE_URL'):
    PG_URL = os.environ.get('DATABASE_URL')
    # If URL starts with postgres://, convert to postgresql:// (required by SQLAlchemy)
    if PG_URL.startswith('postgres://'):
        PG_URL = PG_URL.replace('postgres://', 'postgresql://', 1)
else:
    # Construct from individual components
    PG_USER = os.environ.get('DB_USER', 'postgres')
    PG_PASSWORD = os.environ.get('DB_PASSWORD', '')
    PG_HOST = os.environ.get('DB_HOST', 'localhost')
    PG_NAME = os.environ.get('DB_NAME', 'journal')
    PG_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}/{PG_NAME}"

# Tables to migrate (in order of dependencies)
TABLES = [
    'users',
    'tags',
    'journal_entries',
    'entry_tags',
    'guided_responses',
    'exercise_logs',
    'photos'
]

def get_sqlite_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect(SQLITE_PATH)

def get_pg_connection():
    """Create a connection to the PostgreSQL database."""
    if os.environ.get('DATABASE_URL'):
        parsed_url = os.environ.get('DATABASE_URL')
        # If URL starts with postgres://, keep it as is for psycopg2
        if parsed_url.startswith('postgresql://'):
            parsed_url = parsed_url.replace('postgresql://', 'postgres://', 1)
        return psycopg2.connect(parsed_url)
    else:
        return psycopg2.connect(
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', ''),
            host=os.environ.get('DB_HOST', 'localhost'),
            database=os.environ.get('DB_NAME', 'journal')
        )

def get_table_columns(conn, table_name):
    """Get column names for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
    return [desc[0] for desc in cursor.description]

def export_table_to_json(sqlite_conn, table_name):
    """Export a table from SQLite to a JSON-serializable list of dictionaries."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]
    result = []
    
    for row in cursor.fetchall():
        row_dict = {}
        for i, column in enumerate(columns):
            row_dict[column] = row[i]
        result.append(row_dict)
    
    return result

def import_table_from_json(pg_conn, table_name, data):
    """Import data into a PostgreSQL table."""
    if not data:
        print(f"No data to import for table {table_name}")
        return
    
    cursor = pg_conn.cursor()
    
    # Get column names
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
    columns = [desc[0] for desc in cursor.description]
    
    # Filter data to only include existing columns
    filtered_columns = [col for col in columns if col != 'id']  # Don't include ID as it's auto-generated
    
    for record in data:
        # Filter record to only include existing columns
        filtered_record = {k: v for k, v in record.items() if k in filtered_columns}
        
        if not filtered_record:
            continue
        
        columns_str = ', '.join(filtered_record.keys())
        placeholders = ', '.join(['%s'] * len(filtered_record))
        values = tuple(filtered_record.values())
        
        # Special handling for entry_tags (junction table)
        if table_name == 'entry_tags':
            cursor.execute(
                f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                values
            )
        else:
            # For tables with id column
            cursor.execute(
                f"INSERT INTO {table_name} (id, {columns_str}) VALUES (%s, {placeholders})",
                (record['id'],) + values
            )
    
    pg_conn.commit()
    print(f"Imported {len(data)} records into {table_name}")

def reset_sequences(pg_conn):
    """Reset the sequences for all tables with auto-incrementing IDs."""
    cursor = pg_conn.cursor()
    
    for table in TABLES:
        if table == 'entry_tags':  # Skip junction table with no id
            continue
        
        cursor.execute(f"""
        SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                      (SELECT MAX(id) FROM {table}), 
                      true)
        """)
    
    pg_conn.commit()
    print("Reset all sequences")

def main():
    print("Starting migration from SQLite to PostgreSQL")
    
    # Connect to both databases
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_pg_connection()
    
    try:
        # Process each table
        for table in TABLES:
            print(f"Processing table: {table}")
            data = export_table_to_json(sqlite_conn, table)
            print(f"Exported {len(data)} records from {table}")
            import_table_from_json(pg_conn, table, data)
        
        # Reset sequences
        reset_sequences(pg_conn)
        
        print("Migration completed successfully")
    
    except Exception as e:
        print(f"Error during migration: {str(e)}")
    
    finally:
        # Close connections
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()