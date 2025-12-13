import subprocess
import tempfile
import os
import json
from typing import Callable, Optional

from .base import BaseExecutor, ExecutionResult


class AnsibleExecutor(BaseExecutor):
    """Executor for Ansible playbooks."""
    
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute Ansible playbook."""
        
        # Check if ansible-playbook is available
        if not self._command_exists('ansible-playbook'):
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output="ansible-playbook is not installed. Install Ansible first."
            )
        
        playbook_content = job.ansible_playbook
        inventory_content = job.ansible_inventory
        extra_vars = job.ansible_extra_vars
        host = job.host
        
        # New: Check for file source
        source_type = getattr(job, 'source_type', 'inline')
        script_path = getattr(job, 'script_path', None)
        
        self._emit_log(log_callback, f"[INFO] Preparing Ansible playbook execution ({source_type})...")
        
        # Create temporary files
        temp_files = []
        
        try:
            # Handle Playbook
            if source_type == 'file' and script_path:
                # Resolve path
                base_dir = os.path.abspath('scripts')
                playbook_path = os.path.join(base_dir, script_path)
                if not os.path.exists(playbook_path):
                     raise FileNotFoundError(f"Playbook file not found: {playbook_path}")
                self._emit_log(log_callback, f"[INFO] Using playbook file: {playbook_path}")
            else:
                # Write playbook to temp file
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.yml',
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(playbook_content)
                    playbook_path = f.name
                    temp_files.append(playbook_path)
            
            # Build command
            cmd = ['ansible-playbook', playbook_path]
            
            # Handle inventory
            inventory_source_type = getattr(job, 'inventory_source_type', 'inline')
            
            if inventory_source_type == 'file' and inventory_content:
                base_dir = os.path.abspath('scripts')
                inventory_path = os.path.join(base_dir, inventory_content)
                if not os.path.exists(inventory_path):
                     raise FileNotFoundError(f"Inventory file not found: {inventory_path}")
                self._emit_log(log_callback, f"[INFO] Using inventory file: {inventory_path}")
                cmd.extend(['-i', inventory_path])
            elif inventory_content:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.ini',
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(inventory_content)
                    inventory_path = f.name
                    temp_files.append(inventory_path)
                cmd.extend(['-i', inventory_path])
            elif host:
                # Use host directly as inventory
                cmd.extend(['-i', f'{host},'])
            
            # Handle extra vars
            if extra_vars:
                try:
                    vars_dict = json.loads(extra_vars) if isinstance(extra_vars, str) else extra_vars
                    with tempfile.NamedTemporaryFile(
                        mode='w',
                        suffix='.json',
                        delete=False,
                        encoding='utf-8'
                    ) as f:
                        json.dump(vars_dict, f)
                        vars_path = f.name
                        temp_files.append(vars_path)
                    cmd.extend(['-e', f'@{vars_path}'])
                except json.JSONDecodeError:
                    # If not JSON, treat as key=value format
                    cmd.extend(['-e', extra_vars])
            
            # Handle credentials
            if credential:
                if credential.username:
                    cmd.extend(['-u', credential.username])
                
                if credential.credential_type == 'ssh_key':
                    # Write SSH key to temp file
                    with tempfile.NamedTemporaryFile(
                        mode='w',
                        delete=False,
                        encoding='utf-8'
                    ) as f:
                        f.write(credential.get_value())
                        key_path = f.name
                        temp_files.append(key_path)
                    os.chmod(key_path, 0o600)
                    cmd.extend(['--private-key', key_path])
                elif credential.credential_type == 'ssh_password':
                    # For password auth, we need sshpass or ask-pass
                    cmd.append('--ask-pass')
            
            # Add verbosity
            cmd.append('-v')
            
            self._emit_log(log_callback, f"[INFO] Running: {' '.join(cmd)}")
            
            # Execute
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                output_lines.append(line)
                self._emit_log(log_callback, line)
            
            process.wait()
            exit_code = process.returncode
            
            self._emit_log(log_callback, f"[INFO] Ansible playbook finished with exit code {exit_code}")
            
            return ExecutionResult(
                success=exit_code == 0,
                exit_code=exit_code,
                output='\n'.join(output_lines),
                error_output=""
            )
            
        except Exception as e:
            self._emit_log(log_callback, f"[ERROR] Ansible execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
    
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
        """Validate job has required fields for Ansible execution."""
        source_type = getattr(job, 'source_type', 'inline')
        script_path = getattr(job, 'script_path', None)
        
        if source_type == 'file':
            if not script_path:
                return False, "Playbook path is required for file-based execution"
        elif not job.ansible_playbook:
            return False, "Ansible playbook content is required"
            
        if not job.host and not job.ansible_inventory:
            return False, "Host or inventory is required for Ansible execution"
        return True, ""
