# root/utils.py
# This file holds helper functions used by all other modules.

import sys
import os
import queue

# --- Path Helpers ---

def resource_path(relative_path):
    """ Get absolute path to bundled asset (for PyInstaller) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, "assets", relative_path)

def get_exe_folder():
    """ Get the directory where the main.py or .exe is located """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
    
# ... existing code ...

def read_env_file():
    """ 
    Reads .env file from the EXE folder.
    Returns a dictionary of valid KEY=VALUE pairs.
    Ignores comments (#) and empty values.
    """
    env_path = os.path.join(get_exe_folder(), ".env")
    config = {}
    
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments or lines without equals
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Only save if value is not empty
                    if value:
                        config[key] = value
        except Exception as e:
            print(f"Error reading .env: {e}")
            
    return config

# --- Log Redirector ---
# This class takes all 'print()' statements and puts them in a queue
# The Flet GUI can then read this queue to display logs.
class LogRedirector:
    def __init__(self, log_queue):
        self.log_queue = log_queue
    
    def write(self, message):
        self.log_queue.put(message)
    
    def flush(self):
        pass # Required for stdout interface