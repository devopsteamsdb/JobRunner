import io
from typing import Callable, Optional

from .base import BaseExecutor, ExecutionResult

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SSHExecutor(BaseExecutor):
    """Executor for remote SSH commands."""
    
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute command on remote host via SSH."""
        
        if not PARAMIKO_AVAILABLE:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output="paramiko is not installed. Run: pip install paramiko"
            )
        
        host = job.host
        port = job.port or 22
        command = job.command or job.script_content
        
        self._emit_log(log_callback, f"[INFO] Connecting to {host}:{port}...")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'timeout': 30,
            }
            
            if credential:
                connect_kwargs['username'] = credential.username
                
                if credential.credential_type == 'ssh_key':
                    # Use SSH key
                    key_data = credential.get_value()
                    passphrase = credential.get_passphrase()
                    
                    # Try to load as RSA, then DSA, then ECDSA, then Ed25519
                    key = self._load_private_key(key_data, passphrase)
                    if key:
                        connect_kwargs['pkey'] = key
                    else:
                        return ExecutionResult(
                            success=False,
                            exit_code=-1,
                            output="",
                            error_output="Failed to load SSH private key"
                        )
                else:
                    # Use password
                    connect_kwargs['password'] = credential.get_value()
            
            client.connect(**connect_kwargs)
            self._emit_log(log_callback, "[INFO] Connected successfully")
            
            # Execute command
            self._emit_log(log_callback, f"[INFO] Executing command...")
            stdin, stdout, stderr = client.exec_command(command, timeout=3600)
            
            # Stream output
            output_lines = []
            error_lines = []
            
            for line in iter(stdout.readline, ''):
                line = line.rstrip()
                output_lines.append(line)
                self._emit_log(log_callback, line)
            
            for line in iter(stderr.readline, ''):
                line = line.rstrip()
                error_lines.append(line)
                self._emit_log(log_callback, f"[STDERR] {line}")
            
            exit_code = stdout.channel.recv_exit_status()
            client.close()
            
            self._emit_log(log_callback, f"[INFO] Process exited with code {exit_code}")
            
            return ExecutionResult(
                success=exit_code == 0,
                exit_code=exit_code,
                output='\n'.join(output_lines),
                error_output='\n'.join(error_lines)
            )
            
        except paramiko.AuthenticationException as e:
            self._emit_log(log_callback, f"[ERROR] Authentication failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=f"Authentication failed: {str(e)}"
            )
        except paramiko.SSHException as e:
            self._emit_log(log_callback, f"[ERROR] SSH error: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=f"SSH error: {str(e)}"
            )
        except Exception as e:
            self._emit_log(log_callback, f"[ERROR] Connection failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
    
    def _load_private_key(self, key_data: str, passphrase: Optional[str] = None):
        """Load SSH private key from string."""
        key_file = io.StringIO(key_data)
        passphrase_bytes = passphrase.encode() if passphrase else None
        
        key_types = [
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key,
        ]
        
        for key_type in key_types:
            try:
                key_file.seek(0)
                return key_type.from_private_key(key_file, password=passphrase_bytes)
            except (paramiko.SSHException, ValueError):
                continue
        
        return None
    
    def validate_job(self, job) -> tuple[bool, str]:
        """Validate job has required fields for SSH execution."""
        if not job.host:
            return False, "Host is required for SSH execution"
        if not job.command and not job.script_content:
            return False, "Command or script content is required"
        return True, ""
