from typing import Callable, Optional

from .base import BaseExecutor, ExecutionResult

try:
    import winrm
    WINRM_AVAILABLE = True
except ImportError:
    WINRM_AVAILABLE = False


class WinRMExecutor(BaseExecutor):
    """Executor for remote Windows commands via WinRM."""
    
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute command on remote Windows host via WinRM."""
        
        if not WINRM_AVAILABLE:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output="pywinrm is not installed. Run: pip install pywinrm"
            )
        
        host = job.host
        port = job.port or 5985  # Default HTTP port for WinRM
        command = job.command or job.script_content
        
        self._emit_log(log_callback, f"[INFO] Connecting to {host}:{port} via WinRM...")
        
        try:
            # Build endpoint URL
            protocol = 'https' if port == 5986 else 'http'
            endpoint = f"{protocol}://{host}:{port}/wsman"
            
            # Get credentials
            username = credential.username if credential else None
            password = credential.get_value() if credential else None
            
            if not username or not password:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    output="",
                    error_output="Username and password are required for WinRM"
                )
            
            # Create session
            session = winrm.Session(
                endpoint,
                auth=(username, password),
                transport='ntlm',
                server_cert_validation='ignore'
            )
            
            self._emit_log(log_callback, "[INFO] Connected successfully")
            self._emit_log(log_callback, "[INFO] Executing PowerShell command...")
            
            # Execute as PowerShell
            result = session.run_ps(command)
            
            # Process output
            stdout = result.std_out.decode('utf-8', errors='replace') if result.std_out else ""
            stderr = result.std_err.decode('utf-8', errors='replace') if result.std_err else ""
            
            if stdout:
                for line in stdout.splitlines():
                    self._emit_log(log_callback, line)
            if stderr:
                for line in stderr.splitlines():
                    self._emit_log(log_callback, f"[STDERR] {line}")
            
            self._emit_log(log_callback, f"[INFO] Process exited with code {result.status_code}")
            
            return ExecutionResult(
                success=result.status_code == 0,
                exit_code=result.status_code,
                output=stdout,
                error_output=stderr
            )
            
        except Exception as e:
            self._emit_log(log_callback, f"[ERROR] WinRM execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
    
    def validate_job(self, job) -> tuple[bool, str]:
        """Validate job has required fields for WinRM execution."""
        if not job.host:
            return False, "Host is required for WinRM execution"
        if not job.command and not job.script_content:
            return False, "Command or script content is required"
        return True, ""
