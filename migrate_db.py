from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating database...")
    try:
        # Check if columns exist
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(jobs)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'source_type' not in columns:
                print("Adding source_type column...")
                conn.execute(text("ALTER TABLE jobs ADD COLUMN source_type VARCHAR(20) DEFAULT 'inline'"))
            else:
                print("source_type column already exists.")

            if 'inventory_source_type' not in columns:
                print("Adding inventory_source_type column...")
                conn.execute(text("ALTER TABLE jobs ADD COLUMN inventory_source_type VARCHAR(20) DEFAULT 'inline'"))
            else:
                print("inventory_source_type column already exists.")

            if 'script_path' not in columns:
                print("Adding script_path column...")
                conn.execute(text("ALTER TABLE jobs ADD COLUMN script_path VARCHAR(255)"))
            else:
                print("script_path column already exists.")
                
            conn.commit()
            print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
