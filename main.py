# root/main.py
import flet as ft
import threading
import sys
import queue
import time
import os
import subprocess
import shutil
import multiprocessing # <--- 1. ADD THIS IMPORT

# Import our custom modules
from core.utils import LogRedirector, get_exe_folder
from config import NGROK_EXE_NAME, PORT 
from core.gui import AppGUI
from core.server import start_server_process
from core.services import get_local_ip, start_ngrok_background, get_ngrok_url

# --- Global App State ---
APP_STATE = {
    "server_thread": None,
    "ngrok_process": None
}

# --- Global Queue for Logging ---
log_queue = queue.Queue()

def main(page: ft.Page):
    page.title = "Local Hub v2"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 950
    page.window_height = 850
    page.padding = 25
    page.bgcolor = ft.Colors.BLACK
    page.window_prevent_close = True
    page.window_icon = "icon.png"

    # --- 1. File Picker Setup ---
    def on_browse_result(e: ft.FilePickerResultEvent):
        if e.path:
            gui.path_field.value = e.path
            gui.path_field.update()
    
    file_picker = ft.FilePicker(on_result=on_browse_result)
    page.overlay.append(file_picker)
    
    # --- 2. MINIMIZE LOGIC ---
    def minimize_app(e):
        page.window_minimized = True
        page.update()

    # --- 3. SERVER LOGIC ---
    def start_server_logic(e=None):
        settings = gui.get_settings()
        
        if not settings['folder_path']:
            gui.add_log_line("Error: Please select a folder first.", color="red")
            return

        try:
            port = int(settings['port'])
            if not 1024 <= port <= 65535: raise ValueError
        except:
            port = PORT
            gui.add_log_line(f"Invalid port. Defaulting to {port}.", color="orange")
            settings['port'] = port

        gui.set_server_state(is_running=True)
        gui.add_log_line("Initializing services...", color="cyan")
        
        local_ip = get_local_ip()
        local_url = f"http://{local_ip}:{port}"
        gui.set_urls(local_url=local_url, public_url="Waiting...")
        gui.add_log_line(f"Local Network: {local_url}", color="green")

        # Start Flask Server
        server_thread = threading.Thread(target=start_server_process, args=(settings,))
        server_thread.daemon = True
        server_thread.start()
        APP_STATE["server_thread"] = server_thread
        
        # Start Ngrok
        if settings['enable_ngrok']:
            gui.add_log_line("Starting Ngrok Tunnel...", color="purple")
            
            def run_ngrok_flow():
                proc = start_ngrok_background(port, settings['ngrok_token'])
                if not proc:
                    gui.add_log_line("Error: Could not start ngrok.exe", color="red")
                    return
                
                APP_STATE["ngrok_process"] = proc
                public_url = None
                for _ in range(10): 
                    time.sleep(1)
                    if not APP_STATE["ngrok_process"]: break 
                    public_url = get_ngrok_url()
                    if public_url: break
                
                if public_url:
                    gui.set_urls(local_url=local_url, public_url=public_url)
                    gui.add_log_line(f"Ngrok Online: {public_url}", color="green")
                else:
                    gui.add_log_line("Ngrok connection timeout.", color="red")
                    gui.set_urls(local_url=local_url, public_url="Failed")

            threading.Thread(target=run_ngrok_flow, daemon=True).start()
        else:
            gui.set_urls(local_url=local_url, public_url="Disabled")

    def stop_server_logic(hard_exit=False):
        gui.add_log_line("Stopping services...", color="red")
        
        if APP_STATE["ngrok_process"]:
            try:
                APP_STATE["ngrok_process"].terminate()
                APP_STATE["ngrok_process"] = None
                gui.add_log_line("Ngrok process stopped.", color="orange")
            except Exception as e:
                print(f"Ngrok stop error: {e}")
        
        if hard_exit:
            try:
                subprocess.run(["taskkill", "/F", "/PID", str(os.getpid()), "/T"], check=True, stdout=subprocess.DEVNULL)
            except: pass
        
        if not hard_exit:
            gui.set_server_state(is_running=False)
            gui.set_urls(local_url="", public_url="")
            gui.add_log_line("Server Offline.", color="red")

    # --- 4. WINDOW EVENT HANDLER ---
    def on_window_event(e):
        if e.data == "close":
            stop_server_logic(hard_exit=True)
            page.window_destroy()

    page.window_prevent_close = True
    page.on_window_event = on_window_event

    # --- 5. Initialize GUI ---
    gui = AppGUI(
        on_start=start_server_logic,
        on_stop=lambda e: stop_server_logic(hard_exit=False), 
        on_browse=lambda e: file_picker.get_directory_path(),
        on_minimize=minimize_app 
    )
    
    page.add(ft.Container(content=gui, expand=True))
    
    # --- 6. Log Polling ---
    def poll_logs():
        while True:
            try:
                message = log_queue.get_nowait()
                if message:
                    gui.add_log_line(message.strip(), color="white")
            except queue.Empty:
                time.sleep(0.1)

    threading.Thread(target=poll_logs, daemon=True).start()

# --- 7. Start Application ---
if __name__ == "__main__":
    # --- 2. ADD THIS LINE (CRITICAL) ---
    multiprocessing.freeze_support() 
    
    sys.stdout = LogRedirector(log_queue)
    sys.stderr = sys.stdout
    
    try:
        shutil.rmtree(os.path.join(get_exe_folder(), "temp_uploads"), ignore_errors=True)
    except: pass 
        
    ft.app(target=main, assets_dir="assets")