# main.py
import multiprocessing
import subprocess
import sys
import json
import shutil
import tkinter as tk
from tkinter import messagebox
import webbrowser
import tkinter.font as tkFont
import queue

from gui_module import AppGUI
from camera_process import run_camera_process
from resolution_lister import discover_camera_capabilities

def check_ffmpeg_availability():
    """Checks if ffmpeg is in the system's PATH. Returns True if found, False otherwise."""
    return shutil.which('ffmpeg') is not None

if __name__ == "__main__":
    if not check_ffmpeg_availability():
        class DummyQueue:
            def put(self, *args, **kwargs): pass
            def get_nowait(self, *args, **kwargs): raise queue.Empty
        
        print("MAIN: FFmpeg not found. Displaying error dialog.")
        app = AppGUI(DummyQueue(), DummyQueue(), {})
        app.show_ffmpeg_error_and_exit()
    else:
        multiprocessing.freeze_support()
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

        app = AppGUI(command_queue, update_queue, camera_capabilities)
        app.mainloop()

        camera_proc.join()