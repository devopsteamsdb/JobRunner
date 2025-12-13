import subprocess
import tempfile
import os
import sys
import re
from typing import Callable, Optional

from .base import BaseExecutor, ExecutionResult


class LocalExecutor(BaseExecutor):
    """Executor for local Python, Bash, and PowerShell scripts."""
    
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute a local script or command."""
        
        job_type = job.job_type
        script_content = job.script_content
        command = job.command
        
        # New: Check for file source
        source_type = getattr(job, 'source_type', 'inline')
        script_path = getattr(job, 'script_path', None)
        
        self._emit_log(log_callback, f"[INFO] Starting {job_type} execution ({source_type})...")
        
        try:
            if job_type == 'python':
                return self._execute_python(script_content, log_callback, 
                                          source_type=source_type, script_path=script_path)
            elif job_type == 'bash':
                return self._execute_bash(script_content or command, log_callback,
                                        source_type=source_type, script_path=script_path)
            elif job_type == 'powershell':
                return self._execute_powershell(script_content or command, log_callback,
                                              source_type=source_type, script_path=script_path)
            else:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    output="",
                    error_output=f"Unsupported job type for LocalExecutor: {job_type}"
                )
        except Exception as e:
            self._emit_log(log_callback, f"[ERROR] Execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
    
    def _resolve_script_path(self, relative_path: str) -> str:
        """Resolve script path relative to scripts directory."""
        # Assuming scripts/ is in project root
        base_dir = os.path.abspath('scripts')
        return os.path.join(base_dir, relative_path)

    def _execute_python(
        self,
        script_content: str,
        log_callback: Optional[Callable[[str], None]] = None,
        source_type: str = 'inline',
        script_path: str = None
    ) -> ExecutionResult:
        """Execute Python script."""
        actual_script_path = None
        is_temp = False

        try:
            if source_type == 'file' and script_path:
                actual_script_path = self._resolve_script_path(script_path)
                if not os.path.exists(actual_script_path):
                    raise FileNotFoundError(f"Script file not found: {actual_script_path}")
            else:
                is_temp = True
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(script_content)
                    actual_script_path = f.name
            
            self._emit_log(log_callback, f"[INFO] Running Python script: {actual_script_path}")
            return self._execute_with_streaming(
                [sys.executable, '-u', actual_script_path],
                log_callback
            )
        finally:
            if is_temp and actual_script_path and os.path.exists(actual_script_path):
                os.unlink(actual_script_path)
    
    def _execute_bash(
        self,
        script_content: str,
        log_callback: Optional[Callable[[str], None]] = None,
        source_type: str = 'inline',
        script_path: str = None
    ) -> ExecutionResult:
        """Execute Bash script."""
        shell_cmd = self._get_bash_command()
        actual_script_path = None
        is_temp = False
        
        try:
            if source_type == 'file' and script_path:
                actual_script_path = self._resolve_script_path(script_path)
                if not os.path.exists(actual_script_path):
                    raise FileNotFoundError(f"Script file not found: {actual_script_path}")
                
                # Check for line endings and sanitize in-place if needed
                # Use newline='' to prevent Python from auto-translating \r\n to \n during read
                with open(actual_script_path, 'r', encoding='utf-8', newline='') as f:
                    content = f.read()
                
                if '\r' in content:
                    self._emit_log(log_callback, f"[INFO] Normalizing line endings in {actual_script_path}")
                    with open(actual_script_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.write(content.replace('\r\n', '\n').replace('\r', '\n'))

            else:
                is_temp = True
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.sh',
                    delete=False,
                    encoding='utf-8',
                    newline='\n'
                ) as f:
                    # Normalize line endings to Unix-style
                    content = script_content if script_content else ""
                    f.write(content.replace('\r\n', '\n').replace('\r', '\n'))
                    actual_script_path = f.name
            
            self._emit_log(log_callback, f"[INFO] Running Bash script: {actual_script_path}")
            
            cmd = []
            if shell_cmd:
                cmd = [shell_cmd, actual_script_path]
            else:
                cmd = ['bash', actual_script_path]
                
            return self._execute_with_streaming(cmd, log_callback)
        finally:
            if is_temp and actual_script_path and os.path.exists(actual_script_path):
                os.unlink(actual_script_path)
    
    def _execute_powershell(
        self,
        script_content: str,
        log_callback: Optional[Callable[[str], None]] = None,
        source_type: str = 'inline',
        script_path: str = None
    ) -> ExecutionResult:
        """Execute PowerShell script."""
        actual_script_path = None
        is_temp = False

        try:
            if source_type == 'file' and script_path:
                actual_script_path = self._resolve_script_path(script_path)
                if not os.path.exists(actual_script_path):
                    raise FileNotFoundError(f"Script file not found: {actual_script_path}")
                
                # Check for line endings and sanitize in-place if needed
                # Use newline='' to prevent Python from auto-translating \r\n to \n during read
                with open(actual_script_path, 'r', encoding='utf-8', newline='') as f:
                    content = f.read()
                
                if '\r' in content:
                    self._emit_log(log_callback, f"[INFO] Normalizing line endings in {actual_script_path}")
                    with open(actual_script_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.write(content.replace('\r\n', '\n').replace('\r', '\n'))
            else:
                is_temp = True
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.ps1',
                    delete=False,
                    encoding='utf-8',
                    newline='\n'
                ) as f:
                    # Normalize line endings to Unix-style
                    content = script_content if script_content else ""
                    # Do NOT prepend $ErrorActionPreference here to avoid ParserError with param() blocks
                    f.write(content.replace('\r\n', '\n').replace('\r', '\n'))
                    actual_script_path = f.name
            
            self._emit_log(log_callback, f"[INFO] Running PowerShell script: {actual_script_path}")
            
            ps_cmd = 'pwsh' if self._command_exists('pwsh') else 'powershell'
            
            cmd = [ps_cmd, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', actual_script_path]
            
            return self._execute_with_streaming(cmd, log_callback)
        finally:
            if is_temp and actual_script_path and os.path.exists(actual_script_path):
                os.unlink(actual_script_path)

    # ... _execute_with_streaming ...
    
    # ... _get_bash_command ...

    # ... _command_exists ...

    def validate_job(self, job) -> tuple[bool, str]:
        """Validate job has required fields."""
        source_type = getattr(job, 'source_type', 'inline')
        script_path = getattr(job, 'script_path', None)
        
        if source_type == 'file':
             if not script_path:
                 return False, "Script path is required for file-based jobs"
        elif not job.script_content and not job.command:
            return False, "Script content or command is required"
        return True, ""

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI escape sequences from text."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _execute_with_streaming(
        self,
        cmd: list[str],
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute a command and stream its output."""
        try:
            # Use Popen to stream output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # bufsiz=1 means line buffered
                bufsize=1,
                # On Windows, we might need to handle encoding carefully, but text=True usually handles it.
                encoding='utf-8', 
                errors='replace'
            )
            
            stdout_output = []
            stderr_output = []
            
            # With gevent monkey patching, standard reads should be cooperative
            with process.stdout:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                        
                    line = line.strip()
                    if line:
                        clean_line = self._strip_ansi(line)
                        stdout_output.append(clean_line)
                        self._emit_log(log_callback, clean_line)
            
            # After stdout is closed, read remaining stderr
            stderr_content = process.stderr.read()
            if stderr_content:
                for line in stderr_content.splitlines():
                    clean_line = self._strip_ansi(line)
                    stderr_output.append(clean_line)
                    self._emit_log(log_callback, f"[STDERR] {clean_line}")
            
            return_code = process.wait()
            
            return ExecutionResult(
                success=return_code == 0,
                exit_code=return_code,
                output='\n'.join(stdout_output),
                error_output='\n'.join(stderr_output)
            )
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            self._emit_log(log_callback, f"[ERROR] {error_msg}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
    
    def _get_bash_command(self) -> Optional[str]:
        """Get the path to bash executable."""
        if sys.platform != 'win32':
            return 'bash'
        
        # Check for Git Bash
        git_bash_paths = [
            r'C:\Program Files\Git\bin\bash.exe',
            r'C:\Program Files (x86)\Git\bin\bash.exe',
        ]
        for path in git_bash_paths:
            if os.path.exists(path):
                return path
        
        # Check for WSL
        if self._command_exists('wsl'):
            return 'wsl'
        
        return None
    
    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    def validate_job(self, job) -> tuple[bool, str]:
        """Validate job has required fields."""
        source_type = getattr(job, 'source_type', 'inline')
        script_path = getattr(job, 'script_path', None)
        
        if source_type == 'file':
             if not script_path:
                 return False, "Script path is required for file-based jobs"
        elif not job.script_content and not job.command:
            return False, "Script content or command is required"
        return True, ""
