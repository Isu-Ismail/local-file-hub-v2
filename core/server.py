import os
import base64
import shutil
import secrets
import mimetypes
import math
import sys
import logging
import threading
import json
import traceback
from functools import wraps

# ============================================================
# GLOBAL CHANGE VERSION (for long-polling clients)
# ============================================================

CURRENT_VERSION = 0
VERSION_LOCK = threading.Lock()


def bump_version(reason=""):
    global CURRENT_VERSION
    with VERSION_LOCK:
        CURRENT_VERSION += 1
    return CURRENT_VERSION


# ============================================================
# EXTERNAL IMPORTS
# ============================================================

try:
    from flask import (
        Flask,
        render_template,
        request,
        abort,
        session,
        redirect,
        url_for,
        flash,
        Blueprint,
        jsonify,
        send_from_directory,
    )
    from werkzeug.utils import secure_filename, safe_join
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:
    traceback.print_exc()
    raise

from .utils import get_exe_folder
from config import PORT, TEMP_UPLOAD_DIR


# ============================================================
# PATH / ASSETS RESOLUTION
# ============================================================

def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "assets")
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        return os.path.join(root_dir, "assets")


ASSETS_PATH = get_base_path()
TEMPLATE_DIR = os.path.join(ASSETS_PATH, "templates")
STATIC_DIR = os.path.join(ASSETS_PATH, "static")


# ============================================================
# FLASK INITIALIZATION
# ============================================================

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
app.config["SECRET_KEY"] = "dev_key"
app.config["ASSETS_DIR"] = ""

# Silence werkzeug logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
log.disabled = True

fs = Blueprint("fs", __name__)


# ============================================================
# DECORATORS
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return abort(401)
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def uploader_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") not in ["admin", "uploader"]:
            return jsonify({"error": "Upload permission required"}), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") == "uploader":
        return render_template(
            "upload.html",
            title=app.config.get("BRAND_TITLE"),
            subtitle=app.config.get("BRAND_SUBTITLE"),
            logo=app.config.get("BRAND_LOGO_B64"),
            max_size=app.config.get("MAX_UPLOAD_BYTES"),
        )

    return render_template("admin.html", role=session.get("role"))


@app.route("/login", methods=["GET"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/check_login", methods=["POST"])
def check_login():
    password = request.form.get("password", "")

    if app.config.get("ENABLE_ADMIN") and password == app.config.get("ADMIN_PASS"):
        session["logged_in"] = True
        session["role"] = "admin"
        return redirect(url_for("index"))

    if app.config.get("ENABLE_VIEWER") and password == app.config.get("VIEWER_PASS"):
        session["logged_in"] = True
        session["role"] = "viewer"
        return redirect(url_for("index"))

    if app.config.get("ENABLE_UPLOADER") and password == app.config.get("UPLOADER_PASS"):
        session["logged_in"] = True
        session["role"] = "uploader"
        return redirect(url_for("index"))

    flash("Incorrect password")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/api/check_updates")
def check_updates():
    try:
        client_version = int(request.args.get("version", 0))
    except:
        client_version = 0
    return jsonify({
        "update": CURRENT_VERSION > client_version,
        "version": CURRENT_VERSION
    })


@fs.route("/browse/", defaults={"subpath": ""})
@fs.route("/browse/<path:subpath>")
@login_required
def browse_files(subpath):

    if session.get("role") == "uploader":
        return abort(403)

    try:
        full_path = get_validated_path(subpath)
        items = []

        for item in sorted(os.listdir(full_path)):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)

            size_str = (
                f"{len(os.listdir(item_path))} items"
                if is_dir else
                format_size(os.path.getsize(item_path))
            )

            items.append({
                "name": item,
                "path": os.path.join(subpath, item).replace("\\", "/"),
                "is_dir": is_dir,
                "file_type": "folder" if is_dir else get_file_type(item),
                "size": size_str,
            })

        breadcrumbs = []
        if subpath:
            parts = subpath.split("/")
            for i, part in enumerate(parts):
                breadcrumbs.append({"name": part, "path": "/".join(parts[:i+1])})

        return jsonify({"path": subpath, "items": items, "breadcrumbs": breadcrumbs})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# UPLOAD & MERGE
# ============================================================

def background_merge(temp_dir, final_path, total_chunks, current_path):
    try:
        temp_final = os.path.join(temp_dir, "merged_temp")

        with open(temp_final, "wb", buffering=64 * 1024 * 1024) as final_file:
            for i in range(total_chunks):
                chunk = os.path.join(temp_dir, f"chunk_{i}")
                try:
                    with open(chunk, "rb") as c:
                        final_file.write(c.read())
                    os.remove(chunk)
                except:
                    pass

        if os.path.exists(final_path):
            os.remove(final_path)

        shutil.move(temp_final, final_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

        bump_version("upload_merge_complete")

    except Exception:
        traceback.print_exc()


@fs.route("/upload_chunk", methods=["POST"])
@login_required
@uploader_required
def upload_chunk():
    try:
        file = request.files["file"]
        chunk_index = int(request.form["chunkIndex"])
        total_chunks = int(request.form["totalChunks"])
        file_id = request.form["fileId"]
        filename = secure_filename(request.form["filename"])
        current_path = request.form.get("path", "")
        total_size = int(request.form.get("totalSize", 0))

        # enforce size limit
        if session.get("role") == "uploader":
            limit = app.config.get("MAX_UPLOAD_BYTES", 0)
            if limit > 0 and total_size > limit:
                return jsonify({"success": False, "error": "File too large"}), 413

        temp_dir = os.path.join(TEMP_UPLOAD_DIR, file_id)
        os.makedirs(temp_dir, exist_ok=True)

        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        with open(chunk_path, "wb") as f:
            f.write(file.read())

        files = [n for n in os.listdir(temp_dir) if n.startswith("chunk_")]

        if len(files) == total_chunks:
            lock_file = os.path.join(temp_dir, ".lock")

            try:
                with open(lock_file, "x"):
                    pass
            except FileExistsError:
                return jsonify({"success": True, "chunk": chunk_index})

            final_dir = get_validated_path(current_path)
            final_path = os.path.join(final_dir, filename)

            threading.Thread(
                target=background_merge,
                args=(temp_dir, final_path, total_chunks, current_path),
                daemon=True,
            ).start()

            return jsonify({"success": True, "merging": True})

        return jsonify({"success": True, "chunk": chunk_index})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# DELETE / CREATE
# ============================================================

@fs.route("/delete", methods=["POST"])
@login_required
@admin_required
def delete_item():
    try:
        target = get_validated_path(request.json.get("path"))
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

        bump_version("delete")
        return jsonify({"success": True})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@fs.route("/create_folder", methods=["POST"])
@login_required
@admin_required
def create_folder():
    try:
        path = get_validated_path(request.json.get("path", ""))
        name = secure_filename(request.json.get("folder_name"))
        os.makedirs(os.path.join(path, name), exist_ok=True)

        bump_version("create_folder")
        return jsonify({"success": True})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# DOWNLOAD / VIEW
# ============================================================

@fs.route("/download/<path:filename>")
@login_required
def download_file(filename):
    if session.get("role") == "uploader":
        return abort(403)

    try:
        full_path = get_validated_path(filename)

        if os.path.isdir(full_path):
            folder_name = os.path.basename(full_path)
            temp_zip_base = os.path.join(TEMP_UPLOAD_DIR, folder_name)
            zip_path = shutil.make_archive(temp_zip_base, "zip", full_path)
            return send_from_directory(
                os.path.dirname(zip_path),
                os.path.basename(zip_path),
                as_attachment=True,
            )

        return send_from_directory(
            os.path.dirname(full_path),
            os.path.basename(full_path),
            as_attachment=True,
        )

    except:
        traceback.print_exc()
        return abort(404)


@fs.route("/view/<path:filename>")
@login_required
def view_file(filename):
    if session.get("role") == "uploader":
        return abort(403)

    try:
        full_path = get_validated_path(filename)

        if os.path.isdir(full_path):
            return abort(400)

        return send_from_directory(
            os.path.dirname(full_path),
            os.path.basename(full_path),
        )

    except:
        traceback.print_exc()
        return abort(404)


# ============================================================
# HELPERS
# ============================================================

def get_validated_path(subpath):
    base = app.config["ASSETS_DIR"]
    if not base:
        raise ValueError("Server not initialized")

    if subpath == "":
        return base

    full = os.path.normpath(safe_join(base, subpath))
    if not full.startswith(os.path.normpath(base)):
        raise PermissionError("Access Denied")

    return full


def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()

    image_ext = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"]
    video_ext = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"]
    audio_ext = [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"]
    pdf_ext = [".pdf"]
    word_ext = [".doc", ".docx"]
    excel_ext = [".xls", ".xlsx", ".csv"]
    ppt_ext = [".ppt", ".pptx"]
    text_ext = [".txt", ".md", ".rtf"]
    archive_ext = [".zip", ".rar", ".7z", ".tar", ".gz"]
    code_ext = [
        ".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".cs",
        ".php", ".json", ".xml", ".ts", ".rs", ".go", ".kt"
    ]

    if ext in image_ext: return "image"
    if ext in video_ext: return "video"
    if ext in audio_ext: return "audio"
    if ext in pdf_ext: return "pdf"
    if ext in word_ext: return "word"
    if ext in excel_ext: return "excel"
    if ext in ppt_ext: return "powerpoint"
    if ext in text_ext: return "text"
    if ext in archive_ext: return "zip"
    if ext in code_ext: return "code"

    return "file"


def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


# ============================================================
# WATCHDOG
# ============================================================

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if (
            ".tmp" in event.src_path
            or "temp_uploads" in event.src_path
            or ".git" in event.src_path
        ):
            return

        try:
            base = app.config["ASSETS_DIR"]
            parent = os.path.dirname(event.src_path)
            if not base:
                return
            if not os.path.commonpath([base, parent]).startswith(os.path.normpath(base)):
                return

            bump_version("watchdog_event")

        except:
            pass


# ============================================================
# CONFIG
# ============================================================

def _configure_app(settings):
    folder_path = os.path.normpath(settings["folder_path"])
    if not os.path.exists(folder_path):
        raise RuntimeError("Folder does not exist: " + folder_path)

    settings["folder_path"] = folder_path

    app.config["ASSETS_DIR"] = folder_path
    app.config["ENABLE_ADMIN"] = settings["enable_admin"]
    app.config["ADMIN_PASS"] = settings["admin_pass"]
    app.config["ENABLE_VIEWER"] = settings["enable_viewer"]
    app.config["VIEWER_PASS"] = settings["viewer_pass"]
    app.config["ENABLE_UPLOADER"] = settings["enable_uploader"]
    app.config["UPLOADER_PASS"] = settings["uploader_pass"]
    app.config["BRAND_TITLE"] = settings.get("brand_title", "File Upload Portal")
    app.config["BRAND_SUBTITLE"] = settings.get("brand_subtitle", "")
    app.config["BRAND_LOGO_B64"] = None

    logo_path = settings.get("brand_logo")
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
                ext = os.path.splitext(logo_path)[1].lower()
                mime = "image/png" if ext == ".png" else "image/jpeg"
                app.config["BRAND_LOGO_B64"] = f"data:{mime};base64,{b64}"
        except:
            pass

    try:
        mb_limit = int(settings.get("max_upload_size", 0))
        app.config["MAX_UPLOAD_BYTES"] = mb_limit * 1024 * 1024 if mb_limit > 0 else 0
    except:
        app.config["MAX_UPLOAD_BYTES"] = 0

    app.config["SECRET_KEY"] = secrets.token_hex(16)

    if "fs" not in app.blueprints:
        app.register_blueprint(fs, url_prefix="/api")


# ============================================================
# PRODUCTION ENTRY (EXE MODE)
# ============================================================

def run_production_server():

    try:
        if len(sys.argv) < 3:
            raise RuntimeError("Expected settings JSON in sys.argv[2]")

        settings = json.loads(sys.argv[2])

        _configure_app(settings)

        folder = settings["folder_path"]

        obs = Observer()
        obs.schedule(ChangeHandler(), folder, recursive=True)
        obs.start()

        # log essential
        port = int(settings.get("port", PORT))
        print(f"Server started on port {port}")

        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    except Exception as e:
        traceback.print_exc()
        try:
            with open("server_boot_error.log", "w", encoding="utf-8") as f:
                f.write("CRITICAL SERVER FAILURE\n")
                f.write(str(e) + "\n\n")
                traceback.print_exc(file=f)
        except:
            pass

        sys.exit(1)
