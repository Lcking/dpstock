import sqlite3
import os
import json

def debug_admin_data():
    db_path = 'data/stocks.db'
    if not os.path.exists(db_path):
        print("DB not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== Table: anchors ===")
    try:
        cursor.execute("SELECT * FROM anchors LIMIT 5")
        rows = cursor.fetchall()
        print(f"Total count: {len(rows)} (showing max 5)")
        for row in rows:
            print(dict(row))
            
        cursor.execute("SELECT count(*) FROM anchors")
        print(f"Real Count: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Table: judgments ===")
    try:
        cursor.execute("SELECT id, status, validation_date, created_at FROM judgments LIMIT 5")
        rows = cursor.fetchall()
        print(f"Total count: {len(rows)} (showing max 5)")
        for row in rows:
            print(dict(row))

        cursor.execute("SELECT count(*) FROM judgments")
        print(f"Real Count: {cursor.fetchone()[0]}")
        
        # Check verification_status column existence
        cursor.execute("PRAGMA table_info(judgments)")
        columns = [r['name'] for r in cursor.fetchall()]
        print(f"Columns: {columns}")
        
        if 'verification_status' in columns:
            cursor.execute("SELECT count(*) FROM judgments WHERE verification_status = 'CONFIRMED'")
            print(f"Confirmed Count: {cursor.fetchone()[0]}")
        else:
            print("Column 'verification_status' NOT FOUND!")
            
    except Exception as e:
        print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    debug_admin_data()
