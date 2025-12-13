from gevent import monkey
monkey.patch_all()

import os
from flask import Flask, request
from flask_socketio import SocketIO

from config import config
from models import db
from services.scheduler import scheduler_service
from routes import jobs_bp, logs_bp, credentials_bp, views_bp, files_bp

# Initialize SocketIO
socketio = SocketIO()


def create_app(config_name=None, cleanup_scheduler=True):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='gevent')
    
    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(credentials_bp)
    app.register_blueprint(files_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()

        # Ensure default file structure exists
        base_scripts_dir = os.path.join(app.root_path, 'scripts')
        default_dirs = ['ansible', 'powershell']
        
        if not os.path.exists(base_scripts_dir):
            os.makedirs(base_scripts_dir)
            
        for d in default_dirs:
            p = os.path.join(base_scripts_dir, d)
            if not os.path.exists(p):
                os.makedirs(p)
                # Create .gitkeep to ensure persistence visibility
                with open(os.path.join(p, '.gitkeep'), 'w') as f:
                    pass
    
    # Initialize scheduler
    scheduler_service.init_app(app, socketio, cleanup=cleanup_scheduler)
    
    # Register SocketIO namespace
    register_socketio_events(socketio)
    
    return app


def register_socketio_events(socketio):
    """Register SocketIO event handlers."""
    
    @socketio.on('connect', namespace='/jobs')
    def handle_connect():
        print(f'[DEBUG] Client connected to /jobs namespace. SID: {request.sid}')
    
    @socketio.on('disconnect', namespace='/jobs')
    def handle_disconnect():
        print(f'[DEBUG] Client disconnected from /jobs namespace. SID: {request.sid}')
    
    @socketio.on('subscribe', namespace='/jobs')
    def handle_subscribe(data):
        """Subscribe to job log updates."""
        job_id = data.get('job_id')
        if job_id:
            from flask_socketio import join_room
            join_room(f'job_{job_id}')
            print(f'[DEBUG] Client {request.sid} subscribed to job_{job_id}')
    
    @socketio.on('unsubscribe', namespace='/jobs')
    def handle_unsubscribe(data):
        """Unsubscribe from job log updates."""
        job_id = data.get('job_id')
        if job_id:
            from flask_socketio import leave_room
            leave_room(f'job_{job_id}')
            print(f'Client unsubscribed from job {job_id}')


# Create default app instance ONLY if run directly or by WSGI (not when imported for tests)
# But Flask/Gunicorn expects 'app' to be importable if using module:app pattern.
# However, Dockerfile uses 'python app.py' so it uses __main__.
# If we need it for 'flask run', we can leave it but we MUST disable cleanup.

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
