# root/main.py
import sys
import os
import multiprocessing
import json
import traceback 
import base64 # <--- CRITICAL IMPORT

# 1. CRITICAL: Handle Freeze Support
if __name__ == "__main__":
    multiprocessing.freeze_support()

# 2. SERVER MODE CHECK (The Worker Process)
if len(sys.argv) > 1 and sys.argv[1] == "--server-mode":
    try:
        # --- THE FIX: DECODE ARGUMENTS ---
        # We receive a Base64 string. We must decode it back to JSON
        # so core.server can read it normally.
        encoded_settings = sys.argv[2]
        decoded_json = base64.b64decode(encoded_settings).decode('utf-8')
        
        # Overwrite sys.argv[2] so the server module sees raw JSON as it expects
        sys.argv[2] = decoded_json
        
        from core.server import run_production_server
        run_production_server()
        
    except Exception as e:
        with open("server_boot_error.log", "w") as log_file:
            log_file.write("CRITICAL SERVER ERROR:\n")
            traceback.print_exc(file=log_file)
    
    sys.exit(0)

# --- GUI MODE STARTS HERE ---
import flet as ft
import threading
import queue
import time
import subprocess
import shutil

from core.utils import LogRedirector, get_exe_folder
from config import PORT 
from core.gui import AppGUI
from core.services import get_local_ip, start_ngrok_background, get_ngrok_url

# --- Global App State ---
APP_STATE = {
    "server_process": None, 
    "ngrok_process": None
}

log_queue = queue.Queue()

def main(page: ft.Page):
    page.title = "Local Hub v2"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 950
    page.window_height = 850
    page.padding = 25
    page.bgcolor = ft.Colors.BLACK
    page.window_prevent_close = True
    
    try: page.window_icon = "icon.png" 
    except: pass

    # --- 1. Setup ---
    def on_browse_result(e: ft.FilePickerResultEvent):
        if e.path:
            gui.path_field.value = e.path
            gui.path_field.update()
    
    file_picker = ft.FilePicker(on_result=on_browse_result)
    page.overlay.append(file_picker)
    
    def minimize_app(e):
        page.window_minimized = True
        page.update()

    # --- 2. SERVER LOGIC ---
    def start_server_logic(e=None):
        settings = gui.get_settings()
        
        if not settings['folder_path']:
            gui.add_log_line("Error: Please select a folder first.", color="red")
            return

        try: port = int(settings['port'])
        except: port = PORT; settings['port'] = port

        gui.set_server_state(is_running=True)
        gui.add_log_line("Initializing Standard Engine...", color="cyan")
        
        local_ip = get_local_ip()
        gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url="Waiting...")
        gui.add_log_line(f"Local Network: http://{local_ip}:{port}", color="green")

        # --- LAUNCH SERVER AS SEPARATE PROCESS ---
        
        # Prepare Settings: Convert JSON to Base64 to prevent Argument Splitting
        json_str = json.dumps(settings)
        b64_settings = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        if getattr(sys, 'frozen', False):
            executable = sys.executable 
            cmd = [executable, "--server-mode", b64_settings]
        else:
            executable = sys.executable
            script_path = os.path.abspath(__file__)
            cmd = [executable, script_path, "--server-mode", b64_settings]

        try:
            server_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=get_exe_folder()
            )
            APP_STATE["server_process"] = server_proc
        except Exception as e:
             gui.add_log_line(f"Failed to spawn process: {e}", color="red")
             gui.set_server_state(is_running=False)
             return
        
        def read_server_output():
            while APP_STATE["server_process"] and APP_STATE["server_process"].poll() is None:
                try:
                    line = APP_STATE["server_process"].stdout.readline()
                    if line: log_queue.put(line.strip())
                except: break
            gui.add_log_line("Server process stopped.", color="orange")

        threading.Thread(target=read_server_output, daemon=True).start()

        # --- START NGROK ---
        if settings['enable_ngrok']:
            gui.add_log_line("Starting Ngrok...", color="purple")
            def run_ngrok():
                proc = start_ngrok_background(port, settings['ngrok_token'])
                if not proc:
                    gui.add_log_line("Ngrok failed to start.", color="red"); return
                
                APP_STATE["ngrok_process"] = proc
                for _ in range(10):
                    time.sleep(1)
                    if not APP_STATE["ngrok_process"]: break
                    url = get_ngrok_url()
                    if url:
                        gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url=url)
                        gui.add_log_line(f"Ngrok Online: {url}", color="green")
                        return
                gui.add_log_line("Ngrok timeout.", color="red")
            threading.Thread(target=run_ngrok, daemon=True).start()
        else:
            gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url="Disabled")

    def stop_server_logic(hard_exit=False):
        if not hard_exit: gui.add_log_line("Stopping services...", color="red")
        
        if APP_STATE["ngrok_process"]:
            try: APP_STATE["ngrok_process"].terminate()
            except: pass
            APP_STATE["ngrok_process"] = None

        if APP_STATE["server_process"]:
            try:
                subprocess.run(["taskkill", "/F", "/PID", str(APP_STATE["server_process"].pid), "/T"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
            APP_STATE["server_process"] = None

        if hard_exit:
            try: subprocess.run(["taskkill", "/F", "/PID", str(os.getpid()), "/T"], stdout=subprocess.DEVNULL)
            except: pass
            sys.exit(0)
        
        gui.set_server_state(is_running=False)
        gui.set_urls(local_url="", public_url="")
        gui.add_log_line("Server Offline.", color="red")

    def on_window_event(e):
        if e.data == "close": stop_server_logic(hard_exit=True)

    page.on_window_event = on_window_event
    gui = AppGUI(on_start=start_server_logic, on_stop=lambda e: stop_server_logic(False), on_browse=lambda e: file_picker.get_directory_path(), on_minimize=minimize_app)
    page.add(ft.Container(content=gui, expand=True))

    def poll_logs():
        while True:
            try:
                msg = log_queue.get_nowait()
                if msg: gui.add_log_line(msg, color="white")
            except queue.Empty: time.sleep(0.1)
    threading.Thread(target=poll_logs, daemon=True).start()

if __name__ == "__main__":
    try: shutil.rmtree(os.path.join(get_exe_folder(), "temp_uploads"), ignore_errors=True)
    except: pass
    ft.app(target=main, assets_dir="assets")