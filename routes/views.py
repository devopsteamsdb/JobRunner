from flask import Blueprint, render_template
from models import Job, Credential, JobLog

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def dashboard():
    # Statistics
    total_jobs = Job.query.count()
    enabled_jobs = Job.query.filter_by(enabled=True).count()
    
    # Running jobs
    running_jobs = Job.query.filter_by(status='running').all()
    
    # Recent activity (last 10 logs)
    recent_logs = JobLog.query.order_by(JobLog.started_at.desc()).limit(10).all()
    
    # Run stats (simple count of all time logs)
    success_count = JobLog.query.filter_by(status='success').count()
    failed_count = JobLog.query.filter_by(status='failed').count()
    
    return render_template(
        'dashboard.html',
        total_jobs=total_jobs,
        enabled_jobs=enabled_jobs,
        running_jobs=running_jobs,
        recent_logs=recent_logs,
        success_count=success_count,
        failed_count=failed_count
    )

@views_bp.route('/jobs')
def jobs_list():
    jobs = Job.query.order_by(Job.name).all()
    return render_template('jobs.html', jobs=jobs)

@views_bp.route('/jobs/new')
def job_form_new():
    credentials = Credential.query.order_by(Credential.name).all()
    return render_template('job_form.html', job=None, credentials=credentials)

@views_bp.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    # Fetch recent logs (last 10)
    # Note: job.logs is a dynamic relationship (query object)
    logs = job.logs.order_by(JobLog.started_at.desc()).limit(10).all()
    
    return render_template('job_detail.html', job=job, logs=logs)

@views_bp.route('/jobs/<int:job_id>/edit')
def job_form_edit(job_id):
    job = Job.query.get_or_404(job_id)
    credentials = Credential.query.order_by(Credential.name).all()
    return render_template('job_form.html', job=job, credentials=credentials)

@views_bp.route('/credentials')
def credentials_list():
    credentials = Credential.query.order_by(Credential.name).all()
    return render_template('credentials.html', credentials=credentials)

@views_bp.route('/files')
def file_manager():
    return render_template('file_manager.html')
