import pytest
import sys
import time
from models import Job, JobLog, db as _db

def _ensure_job_deleted(app, name):
    """Delete existing job by name to prevent duplicates in production."""
    with app.app_context():
        existing = Job.query.filter_by(name=name).first()
        if existing:
            _db.session.delete(existing)
            _db.session.commit()

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_bash_job(client, app):
    """Test running a real Bash job."""
    _ensure_job_deleted(app, 'Integration Bash')

    # Create job
    resp = client.post('/api/jobs', json={
        'name': 'Integration Bash',
        'job_type': 'bash',
        'script_content': 'echo "integration_success"',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Trigger run
    resp = client.post(f'/api/jobs/{job_id}/run')
    assert resp.status_code == 200
    log_id = resp.get_json()['log_id']

    # Wait for completion (poll DB)
    for _ in range(10):
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            if log and log.status in ['success', 'failed']:
                break
        time.sleep(0.5)
    
    with app.app_context():
        log = _db.session.get(JobLog, log_id)
        assert log.status == 'success'
        assert "integration_success" in log.output

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_ansible_job(client, app):
    """Test running a real Ansible job (ping localhost)."""
    _ensure_job_deleted(app, 'Integration Ansible')

    # Create job
    resp = client.post('/api/jobs', json={
        'name': 'Integration Ansible',
        'job_type': 'ansible',
        'inventory_source_type': 'inline',
        'ansible_inventory': '[local]\nlocalhost ansible_connection=local',
        'ansible_playbook': '''
- name: Test Ping
  hosts: local
  tasks:
    - name: Ping
      ping:
''',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Trigger run
    resp = client.post(f'/api/jobs/{job_id}/run')
    assert resp.status_code == 200
    log_id = resp.get_json()['log_id']

    # Wait for completion
    for _ in range(30):
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            if log and log.status in ['success', 'failed']:
                break
        time.sleep(1)
        
    with app.app_context():
        log = _db.session.get(JobLog, log_id)
        assert log.status == 'success'
        assert '"ping": "pong"' in log.output or 'SUCCESS' in log.output

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_python_inline_job(client, app):
    """Test running an inline Python job."""
    _ensure_job_deleted(app, 'Integration Python Inline')

    # Create job
    resp = client.post('/api/jobs', json={
        'name': 'Integration Python Inline',
        'job_type': 'python',
        'source_type': 'inline',
        'script_content': 'print("Hello from Python Inline")',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Trigger run
    resp = client.post(f'/api/jobs/{job_id}/run')
    assert resp.status_code == 200
    log_id = resp.get_json()['log_id']

    # Wait for completion
    for _ in range(10):
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            if log and log.status in ['success', 'failed']:
                break
        time.sleep(0.5)
        
    with app.app_context():
        log = _db.session.get(JobLog, log_id)
        assert log.status == 'success'
        assert "Hello from Python Inline" in log.output

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_python_file_job(client, app):
    """Test running a file-based Python job."""
    # Note: In a real scenario, we'd need to ensure this file exists in the container.
    # For now, we'll write a temporary file using python itself in a separate 'setup' job 
    # OR simpler: just write the file to the shared scripts volume if it was mounted?
    # BUT, the docker container mounts the current directory to /app. 
    # So we can create a file in the project root/scripts in this test, and the app running in docker sees it.
    
    import os
    
    script_name = "integration_test_script.py"
    # Ensure scripts/tests directory exists
    # This path is on the container (or host if running locally)
    scripts_dir = os.path.join(os.getcwd(), 'scripts', 'tests')
    
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        
    script_path = os.path.join(scripts_dir, script_name)
    with open(script_path, 'w') as f:
        f.write('print("Hello from Python File")')
        
    # Valid script path as seen by the app
    # /app is the working directory, scripts/tests is relative to it
    app_script_path = f"/app/scripts/tests/{script_name}"
    
    _ensure_job_deleted(app, 'Integration Python File')
    
    try:
        # Create job
        resp = client.post('/api/jobs', json={
            'name': 'Integration Python File',
            'job_type': 'python',
            'source_type': 'file',
            'script_path': app_script_path,
            'enabled': True
        })
        job_id = resp.get_json()['id']

        # Trigger run
        resp = client.post(f'/api/jobs/{job_id}/run')
        assert resp.status_code == 200
        log_id = resp.get_json()['log_id']

        # Wait for completion
        for _ in range(10):
            with app.app_context():
                log = _db.session.get(JobLog, log_id)
                if log and log.status in ['success', 'failed']:
                    break
            time.sleep(0.5)
            
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            assert log.status == 'success'
            assert "Hello from Python File" in log.output
            
    finally:
        # Cleanup
        if os.path.exists(script_path):
            pass # os.remove(script_path)

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_bash_file_job(client, app):
    """Test running a file-based Bash job."""
    import os
    
    script_name = "integration_test_bash.sh"
    # Ensure scripts/tests directory exists
    scripts_dir = os.path.join(os.getcwd(), 'scripts', 'tests')
    
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        
    script_path = os.path.join(scripts_dir, script_name)
    with open(script_path, 'w', newline='\n') as f:
        f.write('echo "Hello from Bash File"')
        
    app_script_path = f"/app/scripts/tests/{script_name}"
    
    _ensure_job_deleted(app, 'Integration Bash File')
    
    try:
        # Create job
        resp = client.post('/api/jobs', json={
            'name': 'Integration Bash File',
            'job_type': 'bash',
            'source_type': 'file',
            'script_path': app_script_path,
            'enabled': True
        })
        job_id = resp.get_json()['id']

        # Trigger run
        resp = client.post(f'/api/jobs/{job_id}/run')
        assert resp.status_code == 200
        log_id = resp.get_json()['log_id']

        # Wait for completion
        for _ in range(10):
            with app.app_context():
                log = _db.session.get(JobLog, log_id)
                if log and log.status in ['success', 'failed']:
                    break
            time.sleep(0.5)
            
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            assert log.status == 'success'
            assert "Hello from Bash File" in log.output
            
    finally:
        if os.path.exists(script_path):
            pass # os.remove(script_path)

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_powershell_inline_job(client, app):
    """Test running an inline PowerShell job."""
    _ensure_job_deleted(app, 'Integration PowerShell Inline')

    # Create job
    resp = client.post('/api/jobs', json={
        'name': 'Integration PowerShell Inline',
        'job_type': 'powershell',
        'source_type': 'inline',
        'script_content': 'Write-Output "Hello from PowerShell Inline"',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Trigger run
    resp = client.post(f'/api/jobs/{job_id}/run')
    assert resp.status_code == 200
    log_id = resp.get_json()['log_id']

    # Wait for completion
    for _ in range(20):
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            if log and log.status in ['success', 'failed']:
                break
        time.sleep(0.5)
        
    with app.app_context():
        log = _db.session.get(JobLog, log_id)
        assert log.status == 'success'
        assert "Hello from PowerShell Inline" in log.output

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_powershell_file_job(client, app):
    """Test running a file-based PowerShell job."""
    import os
    
    script_name = "integration_test_pwsh.ps1"
    scripts_dir = os.path.join(os.getcwd(), 'scripts', 'tests')
    
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        
    script_path = os.path.join(scripts_dir, script_name)
    with open(script_path, 'w') as f:
        f.write('Write-Output "Hello from PowerShell File"')
        
    app_script_path = f"/app/scripts/tests/{script_name}"
    
    _ensure_job_deleted(app, 'Integration PowerShell File')
    
    try:
        # Create job
        resp = client.post('/api/jobs', json={
            'name': 'Integration PowerShell File',
            'job_type': 'powershell',
            'source_type': 'file',
            'script_path': app_script_path,
            'enabled': True
        })
        job_id = resp.get_json()['id']

        # Trigger run
        resp = client.post(f'/api/jobs/{job_id}/run')
        assert resp.status_code == 200
        log_id = resp.get_json()['log_id']

        # Wait for completion
        for _ in range(20):
            with app.app_context():
                log = _db.session.get(JobLog, log_id)
                if log and log.status in ['success', 'failed']:
                    break
            time.sleep(0.5)
            
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            assert log.status == 'success'
            assert "Hello from PowerShell File" in log.output
            
    finally:
        if os.path.exists(script_path):
            pass # os.remove(script_path)

@pytest.mark.skipif(sys.platform == "win32", reason="Integration tests run in Docker/Linux")
def test_run_ansible_file_job(client, app):
    """Test running a file-based Ansible Playbook job."""
    import os
    
    script_name = "integration_test_playbook.yml"
    scripts_dir = os.path.join(os.getcwd(), 'scripts', 'tests')
    
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        
    script_path = os.path.join(scripts_dir, script_name)
    with open(script_path, 'w') as f:
        f.write('''
- name: Test Ping File
  hosts: local
  tasks:
    - name: Ping
      ping:
''')
        
    app_script_path = f"/app/scripts/tests/{script_name}"
    
    _ensure_job_deleted(app, 'Integration Ansible File')
    
    try:
        # Create job
        resp = client.post('/api/jobs', json={
            'name': 'Integration Ansible File',
            'job_type': 'ansible',
            'source_type': 'file',
            'script_path': app_script_path,
            'ansible_inventory': '[local]\nlocalhost ansible_connection=local',
            'inventory_source_type': 'inline', # Using inline inventory for simplicity with file playbook
            'enabled': True
        })
        job_id = resp.get_json()['id']

        # Trigger run
        resp = client.post(f'/api/jobs/{job_id}/run')
        assert resp.status_code == 200
        log_id = resp.get_json()['log_id']

        # Wait for completion
        for _ in range(30):
            with app.app_context():
                log = _db.session.get(JobLog, log_id)
                if log and log.status in ['success', 'failed']:
                    break
            time.sleep(1)
            
        with app.app_context():
            log = _db.session.get(JobLog, log_id)
            assert log.status == 'success'
            assert '"ping": "pong"' in log.output or 'SUCCESS' in log.output
            
    finally:
        if os.path.exists(script_path):
            pass # os.remove(script_path)
