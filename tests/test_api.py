import json
from models import Job

def test_create_get_job(client):
    """Test creating and retrieving a job."""
    response = client.post('/api/jobs', json={
        'name': 'Test Job',
        'job_type': 'bash',
        'script_content': 'echo "hello"',
        'schedule_type': 'cron',
        'cron_expression': '* * * * *',
        'enabled': True
    })
    assert response.status_code == 201
    data = response.get_json()
    job_id = data['id']
    assert data['name'] == 'Test Job'

    # Get the job
    response = client.get(f'/api/jobs/{job_id}')
    assert response.status_code == 200
    assert response.get_json()['name'] == 'Test Job'

def test_update_job(client):
    """Test updating a job."""
    # Create
    resp = client.post('/api/jobs', json={
        'name': 'Update Me',
        'job_type': 'bash',
        'script_content': 'original'
    })
    job_id = resp.get_json()['id']

    # Update
    resp = client.put(f'/api/jobs/{job_id}', json={
        'name': 'Updated',
        'script_content': 'new'
    })
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Updated'

def test_delete_job(client):
    """Test deleting a job."""
    resp = client.post('/api/jobs', json={'name': 'Delete Me', 'job_type': 'bash'})
    job_id = resp.get_json()['id']

    resp = client.delete(f'/api/jobs/{job_id}')
    assert resp.status_code == 200

    resp = client.get(f'/api/jobs/{job_id}')
    assert resp.status_code == 404

def test_duplicate_job(client):
    """Test duplicating a job."""
    resp = client.post('/api/jobs', json={
        'name': 'Original',
        'job_type': 'python',
        'script_content': 'print("hi")',
        'schedule_type': 'interval',
        'interval_seconds': 60
    })
    job_id = resp.get_json()['id']

    # Duplicate
    resp = client.post(f'/api/jobs/{job_id}/duplicate')
    assert resp.status_code == 201
    new_job = resp.get_json()
    
    assert new_job['name'] == 'Original (Copy)'
    assert new_job['job_type'] == 'python'
    assert new_job['script_content'] == 'print("hi")'
    assert new_job['enabled'] is False  # Should be disabled by default
