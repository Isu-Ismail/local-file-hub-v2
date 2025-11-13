# core/services.py
import socket
import subprocess
import os
import time
import json
import urllib.request
import sys
from config import NGROK_EXE_NAME, ROOT_DIR

def get_local_ip():
    """ Finds the local Wi-Fi/Ethernet IP address """
    try:
        # We connect to a public DNS (Cloudflare) just to determine which network interface is active.
        # No data is actually sent.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_ngrok_background(port, token=None):
    """ Starts Ngrok silently and returns the process object """
    
    # 1. Find Ngrok
    # Check if running from Source or Exe
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = ROOT_DIR
        
    ngrok_path = os.path.join(base_path, NGROK_EXE_NAME)
    
    if not os.path.exists(ngrok_path):
        print(f"[Error] Ngrok not found at: {ngrok_path}")
        return None

    # 2. Apply Token (if provided)
    if token and "Paste" not in token:
        subprocess.run(
            [ngrok_path, "config", "add-authtoken", token],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL
        )

    # 3. Start Process
    cmd = [ngrok_path, 'http', str(port)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL, # We use API to get URL, not stdout
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=base_path
    )
    return process

def get_ngrok_url():
    """ Polls the local Ngrok API to get the Public URL """
    try:
        # Ngrok exposes a local API on port 4040
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
            data = json.loads(response.read().decode('utf-8'))
            if len(data['tunnels']) > 0:
                return data['tunnels'][0]['public_url']
    except:
        pass
    return None