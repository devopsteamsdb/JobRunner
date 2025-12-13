from datetime import datetime
from . import db


class Job(db.Model):
    """Job model representing a scheduled task."""
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Job type: python, bash, powershell, ssh, winrm, ansible, api
    job_type = db.Column(db.String(20), nullable=False)
    
    # Source type: inline, file
    source_type = db.Column(db.String(20), default='inline')
    # Path to script file (relative to scripts/ directory)
    script_path = db.Column(db.String(255))
    
    # Script content or command to execute
    script_content = db.Column(db.Text)
    command = db.Column(db.Text)
    
    # For remote execution
    host = db.Column(db.String(255))
    port = db.Column(db.Integer)
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'))
    
    # For API calls
    api_url = db.Column(db.String(500))
    api_method = db.Column(db.String(10), default='GET')
    api_headers = db.Column(db.Text)  # JSON string
    api_body = db.Column(db.Text)
    
    # For Ansible
    ansible_playbook = db.Column(db.Text)
    # Inventory source: inline, file
    inventory_source_type = db.Column(db.String(20), default='inline')
    ansible_inventory = db.Column(db.Text)
    ansible_extra_vars = db.Column(db.Text)  # JSON string
    
    # Schedule (cron expression)
    schedule_type = db.Column(db.String(20), default='cron')  # cron, interval, once
    cron_expression = db.Column(db.String(100))
    interval_seconds = db.Column(db.Integer)
    run_at = db.Column(db.DateTime)  # For 'once' type
    
    # Status
    enabled = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='idle')  # idle, running, success, failed
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credential = db.relationship('Credential', backref='jobs')
    logs = db.relationship('JobLog', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'job_type': self.job_type,
            'source_type': getattr(self, 'source_type', 'inline'),
            'script_path': getattr(self, 'script_path', None),
            'script_content': self.script_content,
            'command': self.command,
            'host': self.host,
            'port': self.port,
            'credential_id': self.credential_id,
            'api_url': self.api_url,
            'api_method': self.api_method,
            'api_headers': self.api_headers,
            'api_body': self.api_body,
            'ansible_playbook': self.ansible_playbook,
            'inventory_source_type': getattr(self, 'inventory_source_type', 'inline'),
            'ansible_inventory': self.ansible_inventory,
            'ansible_extra_vars': self.ansible_extra_vars,
            'schedule_type': self.schedule_type,
            'cron_expression': self.cron_expression,
            'interval_seconds': self.interval_seconds,
            'run_at': self.run_at.isoformat() if self.run_at else None,
            'enabled': self.enabled,
            'status': self.status,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<Job {self.name}>'
