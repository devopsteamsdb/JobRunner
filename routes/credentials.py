from flask import Blueprint, request, jsonify

from models import db, Credential

credentials_bp = Blueprint('credentials', __name__, url_prefix='/api/credentials')


@credentials_bp.route('', methods=['GET'])
def list_credentials():
    """List all credentials (without sensitive data)."""
    credentials = Credential.query.order_by(Credential.name).all()
    return jsonify([cred.to_dict(include_sensitive=False) for cred in credentials])


@credentials_bp.route('', methods=['POST'])
def create_credential():
    """Create a new credential."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if not data.get('name'):
        return jsonify({'error': 'Credential name is required'}), 400
    if not data.get('credential_type'):
        return jsonify({'error': 'Credential type is required'}), 400
    
    # Check for duplicate name
    existing = Credential.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': 'Credential with this name already exists'}), 400
    
    credential = Credential(
        name=data['name'],
        description=data.get('description'),
        credential_type=data['credential_type'],
        username=data.get('username'),
        host_pattern=data.get('host_pattern')
    )
    
    # Set sensitive values
    if data.get('value'):
        credential.set_value(data['value'])
    if data.get('passphrase'):
        credential.set_passphrase(data['passphrase'])
    
    db.session.add(credential)
    db.session.commit()
    
    return jsonify(credential.to_dict(include_sensitive=False)), 201


@credentials_bp.route('/<int:cred_id>', methods=['GET'])
def get_credential(cred_id):
    """Get a specific credential."""
    credential = db.get_or_404(Credential, cred_id)
    return jsonify(credential.to_dict(include_sensitive=False))


@credentials_bp.route('/<int:cred_id>', methods=['PUT'])
def update_credential(cred_id):
    """Update a credential."""
    credential = db.get_or_404(Credential, cred_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' in data:
        # Check for duplicate name
        existing = Credential.query.filter_by(name=data['name']).first()
        if existing and existing.id != cred_id:
            return jsonify({'error': 'Credential with this name already exists'}), 400
        credential.name = data['name']
    
    if 'description' in data:
        credential.description = data['description']
    if 'credential_type' in data:
        credential.credential_type = data['credential_type']
    if 'username' in data:
        credential.username = data['username']
    if 'host_pattern' in data:
        credential.host_pattern = data['host_pattern']
    
    # Update sensitive values only if provided
    if data.get('value'):
        credential.set_value(data['value'])
    if data.get('passphrase'):
        credential.set_passphrase(data['passphrase'])
    
    db.session.commit()
    
    return jsonify(credential.to_dict(include_sensitive=False))


@credentials_bp.route('/<int:cred_id>', methods=['DELETE'])
def delete_credential(cred_id):
    """Delete a credential."""
    credential = db.get_or_404(Credential, cred_id)
    
    # Check if any jobs are using this credential
    if credential.jobs:
        return jsonify({
            'error': 'Cannot delete credential: it is being used by jobs',
            'jobs': [job.name for job in credential.jobs]
        }), 400
    
    db.session.delete(credential)
    db.session.commit()
    
    return jsonify({'message': 'Credential deleted successfully'})


@credentials_bp.route('/types', methods=['GET'])
def get_credential_types():
    """Get available credential types."""
    return jsonify({
        'types': [
            {'value': 'ssh_password', 'label': 'SSH Password'},
            {'value': 'ssh_key', 'label': 'SSH Private Key'},
            {'value': 'winrm', 'label': 'WinRM Password'},
            {'value': 'api_token', 'label': 'API Token'},
            {'value': 'basic_auth', 'label': 'Basic Auth'},
        ]
    })
