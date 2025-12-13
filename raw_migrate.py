import sqlite3
import os

db_path = os.path.join('instance', 'scheduler.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check current columns
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if 'source_type' not in columns:
        print("Adding source_type column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN source_type TEXT DEFAULT 'inline'")
    
    if 'script_path' not in columns:
        print("Adding script_path column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN script_path TEXT")
        
    conn.commit()
    print("Migration successful.")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
