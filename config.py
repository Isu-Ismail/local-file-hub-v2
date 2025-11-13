# root/config.py
# This file holds all shared, non-changing configuration.
# We will import these values into gui.py and server.py.

import os
from utils import get_exe_folder # Import our helper

# --- Core Config ---
PORT = 2004
DEFAULT_PASSWORD = "local"
NGROK_EXE_NAME = "ngrok.exe"

# --- Path Config ---
# Get the folder where the .exe is.
ROOT_DIR = get_exe_folder() 

# Path for our temp_uploads (for chunking)
TEMP_UPLOAD_DIR = os.path.join(ROOT_DIR, "temp_uploads")

# Path for our bundled assets (HTML/CSS/JS)
# This will be overridden by utils.resource_path() in the final .exe
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")