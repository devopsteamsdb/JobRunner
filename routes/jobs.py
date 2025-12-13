from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import os
from werkzeug.utils import secure_filename

from models import db, Job
from services.scheduler import scheduler_service

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')


@jobs_bp.route('', methods=['GET'])
def list_jobs():
    """List all jobs with optional filtering."""
    status = request.args.get('status')
    job_type = request.args.get('type')
    enabled = request.args.get('enabled')
    
    query = Job.query
    
    if status:
        query = query.filter_by(status=status)
    if job_type:
        query = query.filter_by(job_type=job_type)
    if enabled is not None:
        query = query.filter_by(enabled=enabled.lower() == 'true')
    
    jobs = query.order_by(Job.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])


@jobs_bp.route('', methods=['POST'])
def create_job():
    """Create a new job."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Job name is required'}), 400
    if not data.get('job_type'):
        return jsonify({'error': 'Job type is required'}), 400
    
    # Create job
    job = Job(
        name=data['name'],
        description=data.get('description'),
        job_type=data['job_type'],
        source_type=data.get('source_type', 'inline'),
        script_path=data.get('script_path'),
        script_content=data.get('script_content'),
        command=data.get('command'),
        host=data.get('host'),
        port=data.get('port'),
        credential_id=data.get('credential_id'),
        api_url=data.get('api_url'),
        api_method=data.get('api_method', 'GET'),
        api_headers=data.get('api_headers'),
        api_body=data.get('api_body'),
        ansible_playbook=data.get('ansible_playbook'),
        inventory_source_type=data.get('inventory_source_type', 'inline'),
        ansible_inventory=data.get('ansible_inventory'),
        ansible_extra_vars=data.get('ansible_extra_vars'),
        schedule_type=data.get('schedule_type', 'cron'),
        cron_expression=data.get('cron_expression'),
        interval_seconds=data.get('interval_seconds'),
        run_at=datetime.fromisoformat(data['run_at']) if data.get('run_at') else None,
        enabled=data.get('enabled', True)
    )
    
    db.session.add(job)
    db.session.commit()
    
    # Add to scheduler if enabled
    if job.enabled:
        scheduler_service.add_job(job)
    
    # Create job directory in scripts/
    try:
        # Re-import to ensure context if needed, though top-level is fine
        base_dir = os.path.join(current_app.root_path, 'scripts')
        job_dir_name = f"{job.id}_{secure_filename(job.name)}"
        job_dir_path = os.path.join(base_dir, job_dir_name)
        
        if not os.path.exists(job_dir_path):
            os.makedirs(job_dir_path)
            # Create a .gitkeep or empty file to ensure folder isn't empty (optional but good for git)
            with open(os.path.join(job_dir_path, '.gitkeep'), 'w') as f:
                pass
            print(f"Created job directory: {job_dir_path}")
    except Exception as e:
        print(f"Error creating job directory: {e}")
    
    return jsonify(job.to_dict()), 201


@jobs_bp.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get a specific job by ID."""
    job = Job.query.get_or_404(job_id)
    return jsonify(job.to_dict())


@jobs_bp.route('/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    """Update an existing job."""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update fields
    if 'name' in data:
        job.name = data['name']
    if 'description' in data:
        job.description = data['description']
    if 'job_type' in data:
        job.job_type = data['job_type']
    if 'source_type' in data:
        job.source_type = data['source_type']
    if 'script_path' in data:
        job.script_path = data['script_path']
    if 'script_content' in data:
        job.script_content = data['script_content']
    if 'command' in data:
        job.command = data['command']
    if 'host' in data:
        job.host = data['host']
    if 'port' in data:
        job.port = data['port']
    if 'credential_id' in data:
        job.credential_id = data['credential_id']
    if 'api_url' in data:
        job.api_url = data['api_url']
    if 'api_method' in data:
        job.api_method = data['api_method']
    if 'api_headers' in data:
        job.api_headers = data['api_headers']
    if 'api_body' in data:
        job.api_body = data['api_body']
    if 'ansible_playbook' in data:
        job.ansible_playbook = data['ansible_playbook']
    if 'inventory_source_type' in data:
        job.inventory_source_type = data['inventory_source_type']
    if 'ansible_inventory' in data:
        job.ansible_inventory = data['ansible_inventory']
    if 'ansible_extra_vars' in data:
        job.ansible_extra_vars = data['ansible_extra_vars']
    if 'schedule_type' in data:
        job.schedule_type = data['schedule_type']
    if 'cron_expression' in data:
        job.cron_expression = data['cron_expression']
    if 'interval_seconds' in data:
        job.interval_seconds = data['interval_seconds']
    if 'run_at' in data:
        job.run_at = datetime.fromisoformat(data['run_at']) if data['run_at'] else None
    if 'enabled' in data:
        job.enabled = data['enabled']
    
    db.session.commit()
    
    # Update scheduler
    if job.enabled:
        scheduler_service.add_job(job)
    else:
        scheduler_service.remove_job(job.id)
    
    return jsonify(job.to_dict())


@jobs_bp.route('/<int:job_id>/duplicate', methods=['POST'])
def duplicate_job(job_id):
    """Duplicate an existing job."""
    original_job = Job.query.get_or_404(job_id)
    
    # Create new job with copied fields
    new_job = Job(
        name=f"{original_job.name} (Copy)",
        description=original_job.description,
        job_type=original_job.job_type,
        source_type=original_job.source_type,
        script_path=original_job.script_path,
        script_content=original_job.script_content,
        command=original_job.command,
        host=original_job.host,
        port=original_job.port,
        credential_id=original_job.credential_id,
        api_url=original_job.api_url,
        api_method=original_job.api_method,
        api_headers=original_job.api_headers,
        api_body=original_job.api_body,
        ansible_playbook=original_job.ansible_playbook,
        inventory_source_type=getattr(original_job, 'inventory_source_type', 'inline'),
        ansible_inventory=original_job.ansible_inventory,
        ansible_extra_vars=original_job.ansible_extra_vars,
        schedule_type=original_job.schedule_type,
        cron_expression=original_job.cron_expression,
        interval_seconds=original_job.interval_seconds,
        run_at=original_job.run_at,
        enabled=False  # Disabled by default
    )
    
    db.session.add(new_job)
    db.session.commit()
    
    # Create job directory if needed
    try:
        base_dir = os.path.join(current_app.root_path, 'scripts')
        job_dir_name = f"{new_job.id}_{secure_filename(new_job.name)}"
        job_dir_path = os.path.join(base_dir, job_dir_name)
        
        if not os.path.exists(job_dir_path):
            os.makedirs(job_dir_path)
            with open(os.path.join(job_dir_path, '.gitkeep'), 'w') as f:
                pass
            print(f"Created job directory: {job_dir_path}")
    except Exception as e:
        print(f"Error creating duplicate job directory: {e}")
            
    return jsonify(new_job.to_dict()), 201


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job."""
    job = Job.query.get_or_404(job_id)
    
    # Remove from scheduler
    scheduler_service.remove_job(job.id)
    
    # Delete from database
    db.session.delete(job)
    db.session.commit()
    
    return jsonify({'message': 'Job deleted successfully'})


@jobs_bp.route('/<int:job_id>/run', methods=['POST'])
def run_job(job_id):
    """Manually trigger a job execution."""
    job = Job.query.get_or_404(job_id)
    
    log_id = scheduler_service.run_job_now(job.id)
    
    if log_id:
        return jsonify({
            'message': 'Job triggered successfully',
            'log_id': log_id
        })
    else:
        return jsonify({'error': 'Failed to trigger job'}), 500


@jobs_bp.route('/<int:job_id>/toggle', methods=['POST'])
def toggle_job(job_id):
    """Enable or disable a job."""
    job = Job.query.get_or_404(job_id)
    
    job.enabled = not job.enabled
    db.session.commit()
    
    if job.enabled:
        scheduler_service.add_job(job)
    else:
        scheduler_service.remove_job(job.id)
    
    return jsonify({
        'message': f"Job {'enabled' if job.enabled else 'disabled'} successfully",
        'enabled': job.enabled
    })


@jobs_bp.route('/running', methods=['GET'])
def get_running_jobs():
    """Get all currently running jobs."""
    jobs = Job.query.filter_by(status='running').all()
    return jsonify([job.to_dict() for job in jobs])
