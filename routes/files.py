from flask import Blueprint, jsonify, request, current_app
import os
import shutil
from werkzeug.utils import secure_filename

files_bp = Blueprint('files', __name__)

def get_base_dir():
    # Base directory for scripts/files
    # Scripts are mounted at /app/scripts
    return os.path.join(current_app.root_path, 'scripts')

def is_safe_path(path):
    # Prevent directory traversal
    base_dir = os.path.abspath(get_base_dir())
    target_path = os.path.abspath(os.path.join(base_dir, path))
    return target_path.startswith(base_dir)

@files_bp.route('/api/files/tree', methods=['GET'])
def get_file_tree():
    """Get recursive file tree."""
    base_dir = get_base_dir()
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    def scan_dir(path):
        items = []
        try:
            with os.scandir(path) as it:
                for entry in it:
                    # Hide .gitkeep files specifically, allow other dotfiles
                    if entry.name == '.gitkeep':
                        continue
                    item = {
                        'name': entry.name,
                        'path': os.path.relpath(entry.path, base_dir).replace('\\', '/'),
                        'type': 'directory' if entry.is_dir() else 'file'
                    }
                    if entry.is_dir():
                        item['children'] = scan_dir(entry.path)
                    items.append(item)
        except OSError:
            pass
        return sorted(items, key=lambda x: (x['type'] != 'directory', x['name']))

    return jsonify(scan_dir(base_dir))

@files_bp.route('/api/files/content', methods=['GET'])
def get_file_content():
    """Get content of a file."""
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Path required'}), 400
    
    if not is_safe_path(path):
        return jsonify({'error': 'Invalid path'}), 403
        
    full_path = os.path.join(get_base_dir(), path)
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except UnicodeDecodeError:
        return jsonify({'content': '<Binary file content cannot be displayed>'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/files/content', methods=['POST'])
def save_file_content():
    """Save content to a file."""
    data = request.json
    path = data.get('path')
    content = data.get('content')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    if not is_safe_path(path):
        return jsonify({'error': 'Invalid path'}), 403
        
    full_path = os.path.join(get_base_dir(), path)
    
    try:
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/files/create', methods=['POST'])
def create_item():
    """Create a new file or directory."""
    data = request.json
    path = data.get('path')
    is_dir = data.get('is_directory', False)
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    if not is_safe_path(path):
        return jsonify({'error': 'Invalid path'}), 403
        
    full_path = os.path.join(get_base_dir(), path)
    
    if os.path.exists(full_path):
        return jsonify({'error': 'Item already exists'}), 409
        
    try:
        if is_dir:
            os.makedirs(full_path)
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write('')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/files/delete', methods=['POST'])
def delete_item():
    """Delete a file or directory."""
    data = request.json
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    if not is_safe_path(path):
        return jsonify({'error': 'Invalid path'}), 403
        
    full_path = os.path.join(get_base_dir(), path)
    
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.unlink(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/files/upload', methods=['POST'])
def upload_files():
    """Upload multiple files or directories."""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    target_path_arg = request.form.get('target_path', '')
    
    # Validate target path base
    if target_path_arg and not is_safe_path(target_path_arg):
        return jsonify({'error': 'Invalid target path'}), 403

    success_count = 0
    errors = []

    for file in files:
        if file.filename == '':
            continue
            
        # For folder uploads, filename might contain paths like "folder/file.txt"
        # We need to respect that structure relative to target_path
        filename = file.filename
        
        # Security check: ensure the resulting path is safe
        # Combine target_path_arg with the file's relative path
        if target_path_arg:
            final_rel_path = os.path.join(target_path_arg, filename)
        else:
            final_rel_path = filename
            
        if not is_safe_path(final_rel_path):
            errors.append(f"Skipped unsafe path: {filename}")
            continue
            
        full_path = os.path.join(get_base_dir(), final_rel_path)
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file.save(full_path)
            success_count += 1
        except Exception as e:
            errors.append(f"Failed to save {filename}: {str(e)}")

    return jsonify({
        'success': True,
        'count': success_count,
        'errors': errors
    })
