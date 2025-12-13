from flask import Blueprint, request, jsonify

from models import db, JobLog, Job

logs_bp = Blueprint('logs', __name__, url_prefix='/api')


@logs_bp.route('/jobs/<int:job_id>/logs', methods=['GET'])
def get_job_logs(job_id):
    """Get execution history for a specific job."""
    job = Job.query.get_or_404(job_id)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs = JobLog.query.filter_by(job_id=job_id)\
        .order_by(JobLog.started_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [log.to_dict() for log in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })


@logs_bp.route('/logs/<int:log_id>', methods=['GET'])
def get_log(log_id):
    """Get a specific log entry."""
    log = JobLog.query.get_or_404(log_id)
    return jsonify(log.to_dict())


@logs_bp.route('/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """Delete a specific log entry."""
    log = JobLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return jsonify({'message': 'Log deleted successfully'})


@logs_bp.route('/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """Delete old log entries."""
    data = request.get_json() or {}
    days = data.get('days', 30)
    
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    deleted = JobLog.query.filter(JobLog.started_at < cutoff).delete()
    db.session.commit()
    
    return jsonify({
        'message': f'Deleted {deleted} log entries older than {days} days'
    })


@logs_bp.route('/logs/recent', methods=['GET'])
def get_recent_logs():
    """Get recent log entries across all jobs."""
    limit = request.args.get('limit', 50, type=int)
    
    logs = JobLog.query\
        .order_by(JobLog.started_at.desc())\
        .limit(limit)\
        .all()
    
    return jsonify([log.to_dict() for log in logs])
