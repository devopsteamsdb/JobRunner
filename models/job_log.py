from datetime import datetime
from . import db


class JobLog(db.Model):
    """Job execution log model."""
    __tablename__ = 'job_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    
    # Execution times
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    
    # Result
    status = db.Column(db.String(20), default='running')  # running, success, failed, cancelled
    exit_code = db.Column(db.Integer)
    
    # Output
    output = db.Column(db.Text)
    error_output = db.Column(db.Text)
    
    # Metadata
    trigger_type = db.Column(db.String(20), default='scheduled')  # scheduled, manual
    
    def to_dict(self):
        """Convert log to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'status': self.status,
            'exit_code': self.exit_code,
            'output': self.output,
            'error_output': self.error_output,
            'trigger_type': self.trigger_type,
            'duration': self._calculate_duration(),
        }
    
    def _calculate_duration(self):
        """Calculate execution duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
    
    def __repr__(self):
        return f'<JobLog {self.id} for Job {self.job_id}>'
