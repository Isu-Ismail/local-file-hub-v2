# ============================================================
# LocalHub v2 - FINAL MAIN.PY (EXE SAFE + SINGLE INSTANCE)
# ============================================================

import multiprocessing
multiprocessing.freeze_support()

import os
import sys
import json
import time
import queue
import shutil
import traceback
import threading
import subprocess
import base64
import signal  # <-- NEW: for POSIX process group kill

# ============================================================
# SINGLE INSTANCE LOCK (NO MORE STALE LOCK FILES)
# ============================================================

def acquire_single_instance_lock():
    if os.name == "nt":
        # Windows global mutex
        import ctypes
        import ctypes.wintypes
        mutex = ctypes.windll.kernel32.CreateMutexW(
            None,
            ctypes.wintypes.BOOL(True),
            "LocalHubV2_SingleInstance"
        )
        if not mutex:
            return False
        if ctypes.windll.kernel32.GetLastError() == 183:
            # ERROR_ALREADY_EXISTS
            return False
        return True
    else:
        # Linux/Mac POSIX flock
        import fcntl
        global _single_instance_file
        lock_path = "/tmp/localhubv2.lock"
        _single_instance_file = open(lock_path, "w")
        try:
            fcntl.flock(_single_instance_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            return False


# ============================================================
# SAFE IMPORT HELPER
# ============================================================

def try_import(path: str, attr: str | None = None):
    try:
        module = __import__(path, fromlist=["*"])
        return getattr(module, attr) if attr else module
    except Exception:
        with open("fatal_import_error.log", "w", encoding="utf-8") as f:
            f.write(f"IMPORT FAILED: {path}\n")
            traceback.print_exc(file=f)
        print("Import error. See fatal_import_error.log")
        sys.exit(1)


# ============================================================
# IMPORT MODULES
# ============================================================

ft = try_import("flet")
LogRedirector = try_import("core.utils", "LogRedirector")
get_exe_folder = try_import("core.utils", "get_exe_folder")
PORT = try_import("config", "PORT")
AppGUI = try_import("core.gui", "AppGUI")
get_local_ip = try_import("core.services", "get_local_ip")
start_ngrok_background = try_import("core.services", "start_ngrok_background")
get_ngrok_url = try_import("core.services", "get_ngrok_url")


# ============================================================
# GLOBAL STATE
# ============================================================

APP_STATE = {
    "server_process": None,
    "ngrok_process": None,
}
log_queue: "queue.Queue[str]" = queue.Queue()


# ============================================================
# EXECUTABLE LAUNCHER
# ============================================================

def get_launcher_executable():
    if getattr(sys, "frozen", False):
        # running as EXE
        return sys.argv[0]
    # running as script
    return [sys.executable, os.path.abspath(__file__)]


# ============================================================
# PROCESS KILL HELPER (KILL TREE)
# ============================================================

def kill_process_tree(proc):
    """
    Silently kill a subprocess and its children, without flashing a console window.
    Works for:
      - server_process (Flask + Werkzeug + Watchdog)
      - ngrok_process
    """
    if not proc:
        return

    try:
        pid = proc.pid
    except Exception:
        return

    # --------------------------
    # WINDOWS (silent kill)
    # --------------------------
    if os.name == "nt":
        try:
            # Use Windows API to kill without spawning console
            import ctypes
            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
                return
        except Exception:
            pass

        # Fallback: silent terminate
        try:
            proc.terminate()
        except Exception:
            pass

        try:
            proc.kill()
        except Exception:
            pass

        return

    # --------------------------
    # POSIX (Linux/Mac)
    # --------------------------
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass



# ============================================================
# FLET APPLICATION
# ============================================================

def main(page: ft.Page):

    page.title = "Local Hub v2"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 950
    page.window_height = 850
    page.padding = 25
    page.window_prevent_close = True

    # Load icon safely in EXE
    try:
        icon_path = os.path.join(get_exe_folder(), "assets", "icon.png")
        page.window_icon = icon_path
    except Exception:
        pass

    # --------------------------------------------------------
    # READ SERVER PROCESS OUTPUT
    # --------------------------------------------------------

    def read_server_output():
        proc = APP_STATE["server_process"]
        if not proc:
            return
        while proc.poll() is None:
            line = proc.stdout.readline()
            if not line:
                break
            log_queue.put(line.rstrip())
        log_queue.put("Server process stopped.")

    # --------------------------------------------------------
    # START SERVER LOGIC
    # --------------------------------------------------------

    def start_server_logic(e=None):
        settings = gui.get_settings()

        if not settings.get("folder_path"):
            gui.add_log_line("Error: Select a folder", color="red")
            return

        try:
            port = int(settings.get("port", PORT))
        except Exception:
            port = PORT

        gui.set_server_state(is_running=True)
        gui.add_log_line("Starting server...", color="cyan")

        local_ip = get_local_ip()
        gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url="Waiting...")
        gui.add_log_line(f"Local: http://{local_ip}:{port}", color="green")

        # Encode settings
        json_str = json.dumps(settings)
        encoded = base64.b64encode(json_str.encode()).decode()

        launcher = get_launcher_executable()
        cmd = (
            launcher + ["--server-mode", encoded]
            if isinstance(launcher, list)
            else [launcher, "--server-mode", encoded]
        )

        # --- IMPORTANT: create process group so we can kill everything later
        creationflags = 0
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "text": True,
            "bufsize": 1,
            "cwd": get_exe_folder(),
        }

        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
            popen_kwargs["creationflags"] = creationflags
        else:
            # new session -> own process group on POSIX
            popen_kwargs["start_new_session"] = True

        try:
            server_proc = subprocess.Popen(cmd, **popen_kwargs)
            APP_STATE["server_process"] = server_proc
        except Exception as e:
            gui.add_log_line("Server spawn failed", color="red")
            with open("server_spawn_error.log", "w", encoding="utf-8") as f:
                f.write("SERVER SPAWN ERROR\n")
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
            gui.set_server_state(is_running=False)
            return

        # capture early crash
        def capture_initial_errors():
            time.sleep(1)
            if server_proc.poll() is not None:
                output = server_proc.stdout.read()
                with open("server_crash.log", "w", encoding="utf-8") as f:
                    f.write(output or "(no output)")
                gui.add_log_line("Server crashed. See server_crash.log", color="red")

        threading.Thread(target=capture_initial_errors, daemon=True).start()
        threading.Thread(target=read_server_output, daemon=True).start()

        # Optional Ngrok
        if settings.get("enable_ngrok"):
            gui.add_log_line("Starting Ngrok...", color="purple")

            def run_ngrok():
                proc = start_ngrok_background(port, settings.get("ngrok_token", ""))
                APP_STATE["ngrok_process"] = proc
                if not proc:
                    gui.add_log_line("Ngrok failed", color="red")
                    return

                # Note: ngrok process itself should be started with CREATE_NEW_PROCESS_GROUP
                # or start_new_session inside start_ngrok_background for best kill behavior.

                for _ in range(20):
                    time.sleep(1)
                    url = get_ngrok_url()
                    if url:
                        gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url=url)
                        gui.add_log_line(f"Ngrok: {url}", color="green")
                        return
                gui.add_log_line("Ngrok timeout", color="red")

            threading.Thread(target=run_ngrok, daemon=True).start()
        else:
            gui.set_urls(local_url=f"http://{local_ip}:{port}", public_url="Disabled")

    # --------------------------------------------------------
    # STOP SERVER
    # --------------------------------------------------------

    def stop_server_logic(e=None):
        gui.add_log_line("Stopping services...", color="red")

        # --- Stop Ngrok completely ---
        if APP_STATE["ngrok_process"]:
            try:
                kill_process_tree(APP_STATE["ngrok_process"])
            except Exception:
                pass
            APP_STATE["ngrok_process"] = None

        # --- Stop server completely (Flask + Watchdog + threads) ---
        proc = APP_STATE["server_process"]
        if proc:
            try:
                kill_process_tree(proc)
            except Exception:
                pass
            APP_STATE["server_process"] = None

        gui.set_server_state(is_running=False)
        gui.set_urls("Offline", "Unavailable")
        gui.add_log_line("Server Offline", color="red")

    # --------------------------------------------------------
    # FILE PICKER
    # --------------------------------------------------------

    def on_browse_result(e: ft.FilePickerResultEvent):
        if e.path:
            gui.path_field.value = e.path
            gui.path_field.update()

    picker = ft.FilePicker(on_result=on_browse_result)
    page.overlay.append(picker)

    def on_browse_click(e):
        picker.get_directory_path()

    def on_minimize(e):
        page.window_minimized = True
        page.update()

    # --------------------------------------------------------
    # GUI SETUP
    # --------------------------------------------------------

    gui = AppGUI(
        on_start=start_server_logic,
        on_stop=stop_server_logic,
        on_browse=on_browse_click,
        on_minimize=on_minimize,
    )
    page.add(ft.Container(content=gui, expand=True))

    # --------------------------------------------------------
    # LOG POLLING THREAD
    # --------------------------------------------------------

    def poll_logs():
        while True:
            try:
                msg = log_queue.get_nowait()
                gui.add_log_line(msg)
            except queue.Empty:
                time.sleep(0.1)

    threading.Thread(target=poll_logs, daemon=True).start()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # ------------------------------
    # SERVER MODE (child process)
    # ------------------------------
    if len(sys.argv) > 1 and sys.argv[1] == "--server-mode":
        try:
            encoded = sys.argv[2]
            if encoded.strip().startswith("{"):
                decoded = encoded
            else:
                decoded = base64.b64decode(encoded).decode()
            sys.argv[2] = decoded
            run_server = try_import("core.server", "run_production_server")
            run_server()
        except Exception as e:
            with open("server_boot_error.log", "w", encoding="utf-8") as f:
                f.write("BOOT ERROR\n")
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
        sys.exit(0)

    # ------------------------------
    # GUI MODE (top-level)
    # ------------------------------

    # single instance check
    if not acquire_single_instance_lock():
        print("Another LocalHubV2 instance is running.")
        sys.exit(0)

    # cleanup temp folder
    try:
        shutil.rmtree(os.path.join(get_exe_folder(), "temp_uploads"), ignore_errors=True)
    except Exception:
        pass

    ft.app(target=main, assets_dir="assets")
