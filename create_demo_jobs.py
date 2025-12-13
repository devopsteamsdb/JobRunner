import os
import sys
from datetime import datetime

# Add project root to python path
sys.path.insert(0, os.getcwd())

from app import create_app
from models import db, Job

def create_demo_jobs():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # 1. Inline Python Job
        job_inline = Job(
            name="Demo Python Inline",
            description="A demo job running inline Python code.",
            job_type="python",
            source_type="inline",
            script_content="""
import sys
import time
print("Hello from Demo Python Inline!")
print(f"Python version: {sys.version}")
print("Sleeping for 2 seconds...")
time.sleep(2)
print("Done!")
""",
            enabled=True,
            schedule_type='cron',
            cron_expression='0 0 * * *' # Run daily at midnight (placeholder)
        )
        
        # 2. File-based Python Job
        # First create the file
        scripts_dir = os.path.join(app.root_path, 'scripts')
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)
            
        script_filename = "demo_script.py"
        script_path = os.path.join(scripts_dir, script_filename)
        
        with open(script_path, 'w') as f:
            f.write("""
import platform
import os

print("Hello from Demo Python File!")
print(f"Running on: {platform.system()} {platform.release()}")
print(f"Current Directory: {os.getcwd()}")
""")
        print(f"Created script file at: {script_path}")
        
        job_file = Job(
            name="Demo Python File",
            description="A demo job running a Python script file.",
            job_type="python",
            source_type="file",
            script_path=script_path,
            enabled=True,
            schedule_type='cron',
            cron_expression='0 0 * * *'
        )
        
        # Add to DB
        db.session.add(job_inline)
        db.session.add(job_file)
        
        try:
            db.session.commit()
            print("Successfully created demo jobs:")
            print(f"  - {job_inline.name} (ID: {job_inline.id})")
            print(f"  - {job_file.name} (ID: {job_file.id})")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating jobs: {e}")

if __name__ == '__main__':
    create_demo_jobs()
