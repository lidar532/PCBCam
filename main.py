# main.py
import multiprocessing
import subprocess
import sys
import json
from gui_module import AppGUI
from camera_process import run_camera_process

def discover_available_cameras():
    """Runs the discovery script and returns a list of available cameras."""
    try:
        # Use sys.executable to ensure we use the same Python interpreter
        command = [sys.executable, "camera_lister.py"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        cameras = json.loads(result.stdout)
        return cameras
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"MAIN: Could not discover cameras. Error: {e}")
        return [] # Return an empty list on failure

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # --- ADDED: Discover cameras before starting processes ---
    print("MAIN: Discovering available cameras...")
    available_cameras = discover_available_cameras()
    if not available_cameras:
        print("MAIN: No cameras found. The application may not function correctly.")
    else:
        print(f"MAIN: Found cameras: {available_cameras}")

    command_queue = multiprocessing.Queue()
    update_queue = multiprocessing.Queue()

    camera_proc = multiprocessing.Process(target=run_camera_process, args=(command_queue, update_queue))
    camera_proc.start()

    # Pass the discovered camera list to the GUI
    app = AppGUI(command_queue, update_queue, available_cameras)
    app.mainloop()

    camera_proc.join()