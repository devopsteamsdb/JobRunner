from abc import ABC, abstractmethod
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of a job execution."""
    success: bool
    exit_code: int
    output: str
    error_output: str = ""
    
    def __str__(self):
        return f"ExecutionResult(success={self.success}, exit_code={self.exit_code})"


class BaseExecutor(ABC):
    """Base class for all job executors."""
    
    @abstractmethod
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """
        Execute the job.
        
        Args:
            job: The Job model instance
            credential: Optional Credential model instance
            log_callback: Optional callback function for real-time logging
            
        Returns:
            ExecutionResult with success status, exit code, and output
        """
        pass
    
    def _emit_log(self, callback: Optional[Callable[[str], None]], message: str):
        """Helper to emit log messages if callback is provided."""
        if callback:
            callback(message)
    
    @abstractmethod
    def validate_job(self, job) -> tuple[bool, str]:
        """
        Validate that the job has all required fields for this executor.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
