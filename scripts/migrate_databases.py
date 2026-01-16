#!/usr/bin/env python3
"""
One-time migration: Consolidate databases
Move anchor data from stock_scanner.db to stocks.db
"""
import sqlite3
from pathlib import Path
import sys

def migrate():
    """Migrate anchor data to stocks.db"""
    
    source_db = 'data/stock_scanner.db'
    target_db = 'data/stocks.db'
    
    print("=== Database Consolidation Migration ===\n")
    
    # Check if source exists
    if not Path(source_db).exists():
        print(f"✓ No {source_db} found, skipping migration")
        return
    
    # Check if target exists
    if not Path(target_db).exists():
        print(f"✗ Target database {target_db} not found!")
        sys.exit(1)
    
    conn_source = sqlite3.connect(source_db)
    conn_target = sqlite3.connect(target_db)
    
    cursor_source = conn_source.cursor()
    cursor_target = conn_target.cursor()
    
    # Tables to migrate
    tables = ['anchors', 'email_codes', 'anchor_tokens']
    
    total_migrated = 0
    
    for table in tables:
        try:
            # Check if table exists in source
            cursor_source.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor_source.fetchone():
                print(f"  {table}: not found in source, skipping")
                continue
            
            # Get data from source
            cursor_source.execute(f'SELECT * FROM {table}')
            rows = cursor_source.fetchall()
            
            if not rows:
                print(f"  {table}: 0 rows (empty)")
                continue
            
            # Get column names
            cursor_source.execute(f'PRAGMA table_info({table})')
            columns = [col[1] for col in cursor_source.fetchall()]
            
            # Ensure table exists in target
            cursor_target.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor_target.fetchone():
                print(f"  {table}: table doesn't exist in target, skipping")
                continue
            
            # Insert into target
            placeholders = ','.join(['?' for _ in columns])
            
            migrated = 0
            for row in rows:
                try:
                    cursor_target.execute(
                        f'INSERT OR REPLACE INTO {table} VALUES ({placeholders})',
                        row
                    )
                    migrated += 1
                except sqlite3.Error as e:
                    print(f"    Warning: Failed to migrate row: {e}")
            
            total_migrated += migrated
            print(f"  {table}: {migrated} rows migrated")
            
        except sqlite3.Error as e:
            print(f"  {table}: Error - {e}")
    
    conn_target.commit()
    
    # Verify migration
    print("\n=== Verification ===")
    for table in tables:
        try:
            cursor_target.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor_target.fetchone()[0]
            print(f"  {table}: {count} rows in stocks.db")
        except:
            print(f"  {table}: not found")
    
    conn_source.close()
    conn_target.close()
    
    print(f"\n✓ Migration complete! {total_migrated} total rows migrated")
    print(f"\nNext steps:")
    print(f"1. Backup stock_scanner.db: cp {source_db} {source_db}.backup")
    print(f"2. Restart application")
    print(f"3. Test anchor functionality")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
