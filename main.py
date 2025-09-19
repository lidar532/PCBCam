# main.py
import multiprocessing
from gui_module import AppGUI
from camera_process import run_camera_process
from resolution_lister import discover_camera_capabilities # CHANGED

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # --- CHANGED: Discover camera capabilities at startup ---
    print("MAIN: Discovering available cameras and resolutions...")
    camera_capabilities = discover_camera_capabilities()
    if not camera_capabilities:
        print("MAIN: No cameras found. The application may not function correctly.")
    else:
        print(f"MAIN: Found capabilities: {camera_capabilities}")

    command_queue = multiprocessing.Queue()
    update_queue = multiprocessing.Queue()

    camera_proc = multiprocessing.Process(target=run_camera_process, args=(command_queue, update_queue))
    camera_proc.start()

    # Pass the full capabilities dictionary to the GUI
    app = AppGUI(command_queue, update_queue, camera_capabilities)
    app.mainloop()

    camera_proc.join()