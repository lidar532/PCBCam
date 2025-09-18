# main.py
import multiprocessing
from gui_module import AppGUI
from camera_process import run_camera_process

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Queue for GUI -> Camera commands
    command_queue = multiprocessing.Queue()
    # ADDED: Queue for Camera -> GUI updates
    update_queue = multiprocessing.Queue()

    # Create and start the camera process, passing both queues
    camera_proc = multiprocessing.Process(target=run_camera_process, args=(command_queue, update_queue))
    camera_proc.start()

    # Create the GUI application, passing both queues
    app = AppGUI(command_queue, update_queue)
    app.mainloop()

    # When the GUI is closed, wait for the camera process to finish
    camera_proc.join()