import os
import sys
sys.path.insert(0, os.getcwd())

from app import create_app
from models import db, Job

def fix_demo_job():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Find 'Demo Python File' job (ID 12 likely, or by name)
        job = Job.query.filter_by(name="Demo Python File").first()
        
        if not job:
            print("Job 'Demo Python File' not found.")
            return
            
        print(f"Current script_path: {job.script_path}")
        
        # We want just the filename, relative to scripts/
        # Or explicit container path /app/scripts/demo_script.py
        # Based on error "/app/scripts/D:..." implies the code prepends /app/scripts/
        # So we should set it to just the filename.
        
        new_path = "demo_script.py"
        job.script_path = new_path
        
        db.session.commit()
        print(f"Updated job {job.id} script_path to: {job.script_path}")

if __name__ == '__main__':
    fix_demo_job()
