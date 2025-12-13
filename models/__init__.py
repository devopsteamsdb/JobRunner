from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .job import Job
from .job_log import JobLog
from .credential import Credential

__all__ = ['db', 'Job', 'JobLog', 'Credential']
