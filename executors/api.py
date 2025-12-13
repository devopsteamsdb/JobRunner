import json
from typing import Callable, Optional

import requests

from .base import BaseExecutor, ExecutionResult


class APIExecutor(BaseExecutor):
    """Executor for REST API calls."""
    
    def execute(
        self,
        job,
        credential=None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """Execute REST API call."""
        
        url = job.api_url
        method = (job.api_method or 'GET').upper()
        headers_json = job.api_headers
        body = job.api_body
        
        self._emit_log(log_callback, f"[INFO] Making {method} request to {url}...")
        
        try:
            # Parse headers
            headers = {}
            if headers_json:
                try:
                    headers = json.loads(headers_json)
                except json.JSONDecodeError as e:
                    return ExecutionResult(
                        success=False,
                        exit_code=-1,
                        output="",
                        error_output=f"Invalid headers JSON: {str(e)}"
                    )
            
            # Add auth headers if credential provided
            if credential:
                if credential.credential_type == 'api_token':
                    headers['Authorization'] = f'Bearer {credential.get_value()}'
                elif credential.credential_type == 'basic_auth':
                    import base64
                    auth_string = f"{credential.username}:{credential.get_value()}"
                    auth_bytes = base64.b64encode(auth_string.encode()).decode()
                    headers['Authorization'] = f'Basic {auth_bytes}'
            
            # Parse body
            json_body = None
            data_body = None
            
            if body:
                try:
                    json_body = json.loads(body)
                except json.JSONDecodeError:
                    # Not JSON, send as raw data
                    data_body = body
            
            # Make request
            self._emit_log(log_callback, f"[INFO] Headers: {json.dumps({k: '***' if 'auth' in k.lower() else v for k, v in headers.items()})}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                data=data_body,
                timeout=300,  # 5 minute timeout
                verify=True
            )
            
            # Log response
            self._emit_log(log_callback, f"[INFO] Response Status: {response.status_code}")
            self._emit_log(log_callback, f"[INFO] Response Headers: {dict(response.headers)}")
            
            # Try to format response body
            try:
                response_json = response.json()
                response_text = json.dumps(response_json, indent=2)
            except (json.JSONDecodeError, ValueError):
                response_text = response.text
            
            self._emit_log(log_callback, f"[INFO] Response Body:")
            for line in response_text.splitlines():
                self._emit_log(log_callback, line)
            
            # Determine success (2xx status codes)
            success = 200 <= response.status_code < 300
            
            return ExecutionResult(
                success=success,
                exit_code=0 if success else response.status_code,
                output=response_text,
                error_output="" if success else f"HTTP {response.status_code}"
            )
            
        except requests.exceptions.Timeout:
            self._emit_log(log_callback, "[ERROR] Request timed out")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output="Request timed out after 300 seconds"
            )
        except requests.exceptions.ConnectionError as e:
            self._emit_log(log_callback, f"[ERROR] Connection error: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=f"Connection error: {str(e)}"
            )
        except Exception as e:
            self._emit_log(log_callback, f"[ERROR] API call failed: {str(e)}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output="",
                error_output=str(e)
            )
    
    def validate_job(self, job) -> tuple[bool, str]:
        """Validate job has required fields for API execution."""
        if not job.api_url:
            return False, "API URL is required"
        if not job.api_url.startswith(('http://', 'https://')):
            return False, "API URL must start with http:// or https://"
        return True, ""
