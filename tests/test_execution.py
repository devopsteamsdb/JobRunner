from unittest.mock import patch

def test_run_job_endpoint(client):
    """Test manual job trigger endpoint."""
    resp = client.post('/api/jobs', json={
        'name': 'Run Me',
        'job_type': 'bash',
        'script_content': 'echo "run"',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Mock the scheduler service run_job_now method
    with patch('services.scheduler.scheduler_service.run_job_now') as mock_run:
        mock_run.return_value = 'log_123'
        
        response = client.post(f'/api/jobs/{job_id}/run')
        
        assert response.status_code == 200
        assert response.get_json()['log_id'] == 'log_123'
        mock_run.assert_called_once_with(job_id)

def test_toggle_job(client):
    """Test enabling/disabling a job."""
    resp = client.post('/api/jobs', json={
        'name': 'Toggle Me',
        'job_type': 'bash',
        'enabled': True
    })
    job_id = resp.get_json()['id']

    # Disable
    resp = client.post(f'/api/jobs/{job_id}/toggle')
    assert resp.status_code == 200
    assert resp.get_json()['enabled'] is False

    # Enable
    resp = client.post(f'/api/jobs/{job_id}/toggle')
    assert resp.status_code == 200
    assert resp.get_json()['enabled'] is True
