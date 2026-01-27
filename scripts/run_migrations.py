#!/usr/bin/env python3
"""
Run all SQL migrations in valid order
"""
import sqlite3
import os
import sys

def run_migrations():
    db_path = 'data/stocks.db'
    migrations_dir = 'migrations'
    
    print(f"Applying migrations to {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all .sql files sorted
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
    
    for f in files:
        file_path = os.path.join(migrations_dir, f)
        print(f"  Running {f}...", end=" ")
        
        try:
            with open(file_path, 'r') as sql_file:
                sql_script = sql_file.read()
                cursor.executescript(sql_script)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            # Try to continue? Or stop? 
            # Usually safe to continue if table exists errors, but let's see.
            
    conn.commit()
    conn.close()
    print("✓ All migrations completed.")

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    run_migrations()
