# core/server.py
import base64
import os
import shutil
import secrets
import mimetypes
import math
import sys
import logging
import threading
from functools import wraps

from flask import Flask, render_template, request, abort, session, redirect, url_for, flash, Blueprint, jsonify, send_from_directory
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename, safe_join
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .utils import get_exe_folder
from config import PORT, TEMP_UPLOAD_DIR

# --- FLASK SETUP ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "assets")
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        return os.path.join(root_dir, "assets")

ASSETS_PATH = get_base_path()
TEMPLATE_DIR = os.path.join(ASSETS_PATH, "templates")
STATIC_DIR = os.path.join(ASSETS_PATH, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR, static_url_path='/static')
app.config['SECRET_KEY'] = 'dev_key' 
app.config['ASSETS_DIR'] = ""

# Silence Werkzeug logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 
log.disabled = True

fs = Blueprint('fs', __name__)

# --- SOCKETIO INIT ---
socketio = SocketIO() 

# --- DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'): return abort(401)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin': return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def uploader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin', 'uploader']: return jsonify({"error": "Upload permission required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---
@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') == 'uploader':
        return render_template('upload.html', 
            title=app.config.get('BRAND_TITLE'),
            subtitle=app.config.get('BRAND_SUBTITLE'),
            logo=app.config.get('BRAND_LOGO_B64'),
            max_size=app.config.get('MAX_UPLOAD_BYTES'))
    return render_template('admin.html', role=session.get('role'))

@app.route('/login', methods=['GET'])
def login():
    if session.get('logged_in'): return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/check_login', methods=['POST'])
def check_login():
    password = request.form.get('password')
    if app.config.get('ENABLE_ADMIN') and password == app.config.get('ADMIN_PASS'):
        session['logged_in'] = True; session['role'] = 'admin'
        return redirect(url_for('index'))
    if app.config.get('ENABLE_VIEWER') and password == app.config.get('VIEWER_PASS'):
        session['logged_in'] = True; session['role'] = 'viewer'
        return redirect(url_for('index'))
    if app.config.get('ENABLE_UPLOADER') and password == app.config.get('UPLOADER_PASS'):
        session['logged_in'] = True; session['role'] = 'uploader'
        return redirect(url_for('index'))
    flash('Incorrect password')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- API ROUTES ---
@fs.route('/browse/', defaults={'subpath': ''})
@fs.route('/browse/<path:subpath>')
@login_required
def browse_files(subpath):
    if session.get('role') == 'uploader': return abort(403)
    try:
        full_path = get_validated_path(subpath)
        items = []
        for item in sorted(os.listdir(full_path)):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            
            if is_dir:
                try: count = len(os.listdir(item_path)); size_str = f"{count} items"
                except: size_str = "--"
            else:
                size_str = format_size(os.path.getsize(item_path))

            items.append({
                "name": item,
                "path": os.path.join(subpath, item).replace('\\', '/'),
                "is_dir": is_dir,
                "file_type": 'folder' if is_dir else get_file_type(item),
                "size": size_str
            })
        breadcrumbs = []
        if subpath:
            parts = subpath.split('/')
            for i, part in enumerate(parts):
                breadcrumbs.append({"name": part, "path": "/".join(parts[:i+1])})
        return jsonify({"path": subpath, "items": items, "breadcrumbs": breadcrumbs})
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- ASYNC MERGE WORKER ---
def background_merge(temp_dir, final_path, total_chunks, current_path, socket_id):
    try:
        temp_final_path = os.path.join(temp_dir, "merged_temp")
        # 64MB Buffer for merge
        with open(temp_final_path, 'wb', buffering=64*1024*1024) as final_file:
            for i in range(total_chunks):
                chunk_p = os.path.join(temp_dir, f"chunk_{i}")
                try:
                    with open(chunk_p, 'rb') as chunk_f: final_file.write(chunk_f.read())
                    os.remove(chunk_p)
                except: pass
        
        if os.path.exists(final_path): os.remove(final_path)
        shutil.move(temp_final_path, final_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

        # SocketIO Context for Threading
        with app.app_context():
            if socket_id:
                socketio.emit('upload_status', {'status': 'completed'}, to=socket_id)
            socketio.emit('reload_data', {'path': current_path})
            
    except Exception as e:
        print(f"Merge Failed: {e}")
        with app.app_context():
            if socket_id:
                socketio.emit('upload_status', {'status': 'error', 'error': str(e)}, to=socket_id)

@fs.route('/upload_chunk', methods=['POST'])
@login_required
@uploader_required
def upload_chunk():
    try:
        file = request.files['file']
        chunk_index = int(request.form['chunkIndex'])
        total_chunks = int(request.form['totalChunks'])
        file_id = request.form['fileId']
        filename = secure_filename(request.form['filename'])
        current_path = request.form.get('path', '')
        socket_id = request.form.get('socketId')

        if session.get('role') == 'uploader':
            limit = app.config.get('MAX_UPLOAD_BYTES', 0)
            total_size = int(request.form.get('totalSize', 0))
            if limit > 0 and total_size > limit:
                return jsonify({"success": False, "error": "File too large."}), 413

        temp_dir = os.path.join(TEMP_UPLOAD_DIR, file_id)
        if not os.path.exists(temp_dir): 
            try: os.makedirs(temp_dir)
            except: pass

        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        with open(chunk_path, "wb") as f: f.write(file.read()) 

        files = [name for name in os.listdir(temp_dir) if name.startswith("chunk_")]
        if len(files) == total_chunks:
            lock_file = os.path.join(temp_dir, ".lock")
            try:
                with open(lock_file, "x"): pass
            except FileExistsError:
                return jsonify({"success": True, "chunk": chunk_index})

            final_dir = get_validated_path(current_path)
            final_path = os.path.join(final_dir, filename)
            
            thread = threading.Thread(target=background_merge, args=(temp_dir, final_path, total_chunks, current_path, socket_id))
            thread.start()
            
            return jsonify({"success": True, "merging": True})

        return jsonify({"success": True, "chunk": chunk_index})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@fs.route('/delete', methods=['POST'])
@login_required
@admin_required
def delete_item():
    try:
        target = get_validated_path(request.json.get('path'))
        if os.path.isdir(target): shutil.rmtree(target)
        else: os.remove(target)
        emit_reload(request.json.get('path'))
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@fs.route('/create_folder', methods=['POST'])
@login_required
@admin_required
def create_folder():
    try:
        path = get_validated_path(request.json.get('path', ''))
        name = secure_filename(request.json.get('folder_name'))
        os.makedirs(os.path.join(path, name))
        emit_reload(request.json.get('path', ''))
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@fs.route('/download/<path:filename>')
@login_required
def download_file(filename):
    if session.get('role') == 'uploader': return abort(403)
    try:
        full_path = get_validated_path(filename)
        if os.path.isdir(full_path):
            folder_name = os.path.basename(full_path)
            temp_zip_base = os.path.join(TEMP_UPLOAD_DIR, folder_name)
            zip_path = shutil.make_archive(temp_zip_base, 'zip', full_path)
            return send_from_directory(os.path.dirname(zip_path), os.path.basename(zip_path), as_attachment=True)
        return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path), as_attachment=True)
    except: return abort(404)

@fs.route('/view/<path:filename>')
@login_required
def view_file(filename):
    if session.get('role') == 'uploader': return abort(403)
    try:
        full_path = get_validated_path(filename)
        if os.path.isdir(full_path): return abort(400)
        return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))
    except: return abort(404)

# --- HELPERS ---
def get_validated_path(subpath):
    base = app.config['ASSETS_DIR']
    if not base: raise ValueError("Server not initialized")
    if subpath == "": return base
    full = os.path.normpath(safe_join(base, subpath))
    if not full.startswith(os.path.normpath(base)): raise PermissionError("Access Denied")
    return full

def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.png', '.gif']: return 'image'
    if ext in ['.mp4', '.mkv', '.avi']: return 'video'
    if ext in ['.pdf']: return 'pdf'
    return 'file'

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_file_size(path):
    try: return format_size(os.path.getsize(path))
    except: return "-"

def emit_reload(path):
    socketio.emit('reload_data', {'path': path})

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if ".tmp" in event.src_path or "temp_uploads" in event.src_path or ".git" in event.src_path: return
        try:
            with app.app_context():
                base = app.config['ASSETS_DIR']
                parent = os.path.dirname(event.src_path)
                rel = os.path.relpath(parent, base)
                if rel == '.': rel = ''
                socketio.emit('reload_data', {'path': rel.replace('\\', '/')})
        except: pass

# --- INITIALIZATION FUNCTIONS ---

def start_server_process(settings):
    """ MODE 1: THREADING (Direct call for debugging only, not used in main) """
    _configure_app(settings)
    
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=3600, ping_interval=25, logger=False, engineio_logger=False)

    obs = Observer()
    obs.schedule(ChangeHandler(), settings['folder_path'], recursive=True)
    obs.start()
    
    try: port = int(settings['port'])
    except: port = 2004
    
    # Add allow_unsafe_werkzeug here as well for safety
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True, use_reloader=False, log_output=False)

def run_production_server():
    """ MODE 2: PRODUCTION (Called by Subprocess) """
    import sys
    import json
    # NOTE: Eventlet has been REMOVED for stability

    try:
        settings = json.loads(sys.argv[2])
        _configure_app(settings)

        # --- CRITICAL: USE THREADING MODE ---
        socketio.init_app(app, 
                          cors_allowed_origins="*", 
                          async_mode='threading', 
                          ping_timeout=3600, 
                          ping_interval=25, 
                          logger=False, 
                          engineio_logger=False)

        obs = Observer()
        obs.schedule(ChangeHandler(), settings['folder_path'], recursive=True)
        obs.start()

        port = int(settings['port'])
        print(f"Standard Server Started on Port {port}")
        
        # --- FIX APPLIED HERE: allow_unsafe_werkzeug=True ---
        socketio.run(app, 
                     host='0.0.0.0', 
                     port=port, 
                     debug=False, 
                     use_reloader=False, 
                     log_output=True,
                     allow_unsafe_werkzeug=True) # <--- THIS FIXES THE ERROR
        
    except Exception as e:
        print(f"Fatal Server Error: {e}")

def _configure_app(settings):
    """ Shared configuration logic """
    app.config['ASSETS_DIR'] = settings['folder_path']
    app.config['ENABLE_ADMIN'] = settings['enable_admin']
    app.config['ADMIN_PASS'] = settings['admin_pass']
    app.config['ENABLE_VIEWER'] = settings['enable_viewer']
    app.config['VIEWER_PASS'] = settings['viewer_pass']
    app.config['ENABLE_UPLOADER'] = settings['enable_uploader']
    app.config['UPLOADER_PASS'] = settings['uploader_pass']
    app.config['BRAND_TITLE'] = settings.get('brand_title', 'File Upload Portal')
    app.config['BRAND_SUBTITLE'] = settings.get('brand_subtitle', 'Please upload your files below.')
    app.config['BRAND_LOGO_B64'] = None

    logo_path = settings.get('brand_logo')
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode('utf-8')
                ext = os.path.splitext(logo_path)[1].lower()
                mime = "image/png" if ext == ".png" else "image/jpeg"
                app.config['BRAND_LOGO_B64'] = f"data:{mime};base64,{b64}"
        except: pass
    
    try:
        mb_limit = int(settings.get('max_upload_size', 0))
        app.config['MAX_UPLOAD_BYTES'] = mb_limit * 1024 * 1024 if mb_limit > 0 else 0
    except:
        app.config['MAX_UPLOAD_BYTES'] = 0

    app.config['SECRET_KEY'] = secrets.token_hex(16)
    
    if 'fs' not in app.blueprints:
        app.register_blueprint(fs, url_prefix='/api')