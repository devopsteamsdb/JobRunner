import os
import sys
sys.path.insert(0, os.getcwd())

from app import create_app
from models import db, Job

def create_test_job():
    # Use default config (Development)
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Check if already exists to avoid duplicates
        existing = Job.query.filter_by(name="System Self-Test").first()
        if existing:
            print(f"Job 'System Self-Test' already exists (ID: {existing.id})")
            # Update all fields to match latest config
            existing.description = "Runs the project's integration tests (pytest -v) to verify application health."
            existing.job_type = "bash"
            existing.source_type = "inline"
            existing.command = "export TEST_IN_PRODUCTION=1 && export PYTHONDONTWRITEBYTECODE=1 && cd /app && pytest -p no:cacheprovider -v tests/test_integration.py"
            existing.script_content = """
export PYTHONDONTWRITEBYTECODE=1
cd /app
echo "Starting System Self-Test..."
pytest -p no:cacheprovider -v tests/test_integration.py
"""
            existing.schedule_type = 'cron'
            existing.cron_expression = '0 4 * * *'
            existing.enabled = True
            
            db.session.commit()
            print("Updated existing job with latest configuration.")
            return existing.id

        # Create the job
        # We use 'bash' type to run the pytest command
        job = Job(
            name="System Self-Test",
            description="Runs the project's integration tests (pytest -v) to verify application health.",
            job_type="bash",
            source_type="inline",
            # We explicitly cd to /app to ensure we are in the project root
            # -v for verbose output so user sees passing tests
            # -p no:cacheprovider to prevent writing .pytest_cache
            # PYTHONDONTWRITEBYTECODE=1 to prevent writing __pycache__
            script_content="""
export PYTHONDONTWRITEBYTECODE=1
cd /app
echo "Starting System Self-Test..."
pytest -p no:cacheprovider -v tests/test_integration.py
""",
            enabled=True,
            schedule_type='cron',
            cron_expression='0 4 * * *' # Run at 4 AM daily
        )
        
        db.session.add(job)
        db.session.commit()
        print(f"Created job: {job.name} (ID: {job.id})")
        return job.id

if __name__ == '__main__':
    create_test_job()
