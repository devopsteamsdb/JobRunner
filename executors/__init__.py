from .base import BaseExecutor
from .local import LocalExecutor
from .ssh import SSHExecutor
from .winrm import WinRMExecutor
from .ansible import AnsibleExecutor
from .api import APIExecutor

__all__ = [
    'BaseExecutor',
    'LocalExecutor', 
    'SSHExecutor',
    'WinRMExecutor',
    'AnsibleExecutor',
    'APIExecutor',
]


def get_executor(job_type):
    """Get the appropriate executor for a job type."""
    executors = {
        'python': LocalExecutor,
        'bash': LocalExecutor,
        'powershell': LocalExecutor,
        'ssh': SSHExecutor,
        'winrm': WinRMExecutor,
        'ansible': AnsibleExecutor,
        'api': APIExecutor,
    }
    executor_class = executors.get(job_type)
    if executor_class:
        return executor_class()
    raise ValueError(f"Unknown job type: {job_type}")
