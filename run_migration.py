#!/usr/bin/env python3
"""
Run database migration for Anchor System
Executes migrations/003_create_anchor_tables.sql
"""

import sqlite3
import os
import sys

def run_migration():
    """Execute the anchor tables migration"""
    
    # Paths
    db_path = 'data/stocks.db'
    migration_file = 'migrations/003_create_anchor_tables.sql'
    
    # Check if files exist
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Read migration SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("📦 Running Anchor System migration...")
    print(f"   Database: {db_path}")
    print(f"   Migration: {migration_file}")
    print()
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute migration
        cursor.executescript(sql)
        conn.commit()
        
        # Verify tables created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('anchors', 'email_codes', 'anchor_tokens')")
        tables = cursor.fetchall()
        
        print("✅ Migration completed successfully!")
        print()
        print("Created tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Check judgments table columns
        cursor.execute("PRAGMA table_info(judgments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'owner_type' in columns and 'owner_id' in columns:
            print()
            print("✅ Judgments table updated with owner columns")
        else:
            print()
            print("⚠️  Warning: owner columns not found in judgments table")
        
        conn.close()
        
        print()
        print("🎉 Anchor System database migration complete!")
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migration()
