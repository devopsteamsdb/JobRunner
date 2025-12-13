from datetime import datetime
from . import db
import base64
import os


class Credential(db.Model):
    """Credential model for storing authentication information."""
    __tablename__ = 'credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # Credential type: ssh_password, ssh_key, winrm, api_token, basic_auth
    credential_type = db.Column(db.String(20), nullable=False)
    
    # Authentication details
    username = db.Column(db.String(100))
    # Encrypted password/key/token (base64 encoded for simplicity - use proper encryption in production)
    encrypted_value = db.Column(db.Text)
    
    # For SSH keys
    ssh_key_passphrase = db.Column(db.Text)  # Encrypted
    
    # Host pattern for matching (optional)
    host_pattern = db.Column(db.String(255))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_value(self, value):
        """Encode and store the credential value."""
        # Simple base64 encoding - in production use proper encryption!
        if value:
            self.encrypted_value = base64.b64encode(value.encode()).decode()
    
    def get_value(self):
        """Decode and return the credential value."""
        if self.encrypted_value:
            return base64.b64decode(self.encrypted_value.encode()).decode()
        return None
    
    def set_passphrase(self, passphrase):
        """Encode and store SSH key passphrase."""
        if passphrase:
            self.ssh_key_passphrase = base64.b64encode(passphrase.encode()).decode()
    
    def get_passphrase(self):
        """Decode and return SSH key passphrase."""
        if self.ssh_key_passphrase:
            return base64.b64decode(self.ssh_key_passphrase.encode()).decode()
        return None
    
    def to_dict(self, include_sensitive=False):
        """Convert credential to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'credential_type': self.credential_type,
            'username': self.username,
            'host_pattern': self.host_pattern,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            data['value'] = self.get_value()
        return data
    
    def __repr__(self):
        return f'<Credential {self.name}>'
