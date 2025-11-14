# root/main.py
import flet as ft
import threading
import sys
import queue
import time
import os
import subprocess
import shutil
from PIL import Image
import pystray

# Import our custom modules
from core.utils import LogRedirector, get_exe_folder, resource_path
from config import NGROK_EXE_NAME, PORT 
from core.gui import AppGUI
from core.server import start_server_process
from core.services import get_local_ip, start_ngrok_background, get_ngrok_url

# --- Global App State ---
APP_STATE = {
    "server_thread": None,
    "ngrok_process": None,
    "tray_icon": None,
    "flet_page": None
}

# --- Global Queue for Logging ---
log_queue = queue.Queue()

def main(page: ft.Page):
    APP_STATE["flet_page"] = page
    page.title = "Local File Hub Launcher"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 950
    page.window_height = 850
    page.padding = 25
    page.bgcolor = ft.Colors.BLACK12
    
    # Prevent app from closing when X is clicked, just hide it
    page.window_prevent_close = True

    # --- 1. File Picker Setup ---
    def on_browse_result(e: ft.FilePickerResultEvent):
        if e.path:
            gui.path_field.value = e.path
            gui.path_field.update()
    
    file_picker = ft.FilePicker(on_result=on_browse_result)
    page.overlay.append(file_picker)
    
    # --- 2. MINIMIZE LOGIC (True Hide) ---
    def minimize_to_tray(e=None):
        # This hides the window from the Taskbar completely
        page.window_visible = False
        page.update()
        
        # Notify via GUI log just in case
        # (You can't see it, but it's there when you come back)
        # gui.add_log_line("App minimized to System Tray.", color="orange")

    def restore_from_tray():
        # Called by Pystray thread
        page.window_visible = True
        page.window_to_front()
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

        server_thread = threading.Thread(target=start_server_process, args=(settings,))
        server_thread.daemon = True
        server_thread.start()
        APP_STATE["server_thread"] = server_thread
        
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
        """ Stops processes. If hard_exit=True, kills app completely. """
        if not hard_exit:
            gui.add_log_line("Stopping services...", color="red")
        
        if APP_STATE["ngrok_process"]:
            try:
                APP_STATE["ngrok_process"].terminate()
                APP_STATE["ngrok_process"] = None
            except: pass
        
        # If hard exit, we force kill python tree
        if hard_exit:
            # Stop the tray icon
            if APP_STATE["tray_icon"]:
                APP_STATE["tray_icon"].stop()
            try:
                subprocess.run(["taskkill", "/F", "/PID", str(os.getpid()), "/T"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
            os._exit(0)
        
        # Soft stop reset
        gui.set_server_state(is_running=False)
        gui.set_urls(local_url="", public_url="")
        gui.add_log_line("Server Offline.", color="red")

    # --- 4. WINDOW EVENT HANDLER ---
    def on_window_event(e):
        if e.data == "close":
            # When clicking X, we just Minimize to Tray instead of quitting
            # Unless you want X to Quit. 
            # Let's make X = Quit for safety, and Down Arrow = Minimize
            stop_server_logic(hard_exit=True)

    page.on_window_event = on_window_event

    # --- 5. Initialize GUI ---
    gui = AppGUI(
        on_start=start_server_logic,
        on_stop=lambda e: stop_server_logic(hard_exit=False), 
        on_browse=lambda e: file_picker.get_directory_path(),
        on_minimize=minimize_to_tray # The Arrow button calls this
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

# --- 7. SYSTEM TRAY THREAD ---
def run_tray_icon():
    # Load icon
    icon_path = resource_path("icon.png")
    if not os.path.exists(icon_path):
        # Fallback if icon missing
        print("Icon not found for tray")
        return

    image = Image.open(icon_path)

    def on_open(icon, item):
        # Trigger Flet to show window
        # We need to do this safely since it's a different thread
        # Usually updating a variable referenced by Flet loop works
        if APP_STATE["flet_page"]:
            APP_STATE["flet_page"].window_visible = True
            APP_STATE["flet_page"].window_to_front()
            APP_STATE["flet_page"].update()

    def on_quit(icon, item):
        icon.stop()
        # Kill main app
        subprocess.run(["taskkill", "/F", "/PID", str(os.getpid()), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open Local Hub", on_open, default=True),
        pystray.MenuItem("Quit", on_quit)
    )

    icon = pystray.Icon("LocalHub", image, "Local Hub v2", menu)
    APP_STATE["tray_icon"] = icon
    icon.run()

# --- 8. ENTRY POINT ---
if __name__ == "__main__":
    sys.stdout = LogRedirector(log_queue)
    sys.stderr = sys.stdout
    
    try:
        shutil.rmtree(os.path.join(get_exe_folder(), "temp_uploads"), ignore_errors=True)
    except: pass 
    
    # Start Tray in background thread
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()

    # Start GUI
    ft.app(target=main)