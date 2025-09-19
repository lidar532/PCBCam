# PCBCam
By: C. W. Wright
<br>Lidar532-AAATTT-gmail.com
<br>Github.com/lidar532
<br>2025-0919

PCBCam uses a camera to help a fiber laser user "see" and perfectly realign a 
circuit board that has been flipped over or taken out and put back in.

The application uses the mouse as the primary tool for navigating the camera feed and managing markers.

## Mouse Interaction with the Image
All of the following actions are performed when your cursor is over the camera feed window:

* **Zoom (Mouse Wheel):** Scrolling the mouse wheel zooms the view in or out.
  The zoom is always centered on the current position of your mouse cursor.

* **Pan (Right-Click + Drag):** When you are zoomed in, you can press and 
  hold the right mouse button and drag the mouse to pan the image.

* **Place Marker (Left-Click):** A single left-click places a new marker at
  the cursor's location. The new marker will have the properties (shape, color, size) currently
  selected in the "Markers" menu.

* **Edit Marker (Right-Click):** A quick right-click (press and release without dragging)
   finds the marker nearest to your cursor and opens the "Edit Marker Properties" dialog for it.

* **Undo (Middle-Click):** Clicking the middle mouse button (the scroll wheel) undoes 
  the last action you performed (whether it was adding, deleting, or editing a marker).

* **Delete Nearest Marker (Shift + Middle-Click):**  Holding the Shift key while clicking 
  the middle mouse button will find the marker nearest to your cursor and open a dialog to confirm its deletion.

## Working with Markers
Markers are unique annotations you can place on the video feed. Each marker is independent
and stores its own set of properties.

### Marker Properties
Every marker has the following attributes, which can be modified in the "Edit Marker Properties" dialog:

* Position: The specific X and Y coordinates on the original, full-resolution image.

* Shape: The marker's shape can be a Cross, Circle, or Square.

* Color: The color can be set to Red, Green, Blue, or Yellow.

* Size: The size can be set to 9px, 15px, or 25px.

* Description: You can add a custom text description to any marker.

### Marker Actions
* **Creating:** Markers are created with a left-click. They take on the properties currently selected
in the GUI's "Markers" menu.

* **Editing:** You can edit any property of a marker—including its coordinates—through the dialog that
appears with a right-click.

* **Undo/Redo:** Any action that affects the marker list (adding, deleting, or editing) can be reversed
with Undo (Middle-Click or Ctrl+Z) and restored with Redo (Ctrl+Y).

* **Saving and Loading:** The entire set of markers for the active camera, along with the camera's name 
and resolution, can be saved to a file. Loading this file will restore all markers and their properties
 and will automatically switch back to the correct camera and resolution.


# Dependencies 
## Python Packages (via pip)
These are the required Python libraries.

* **opencv-python:** The core library for all camera interaction, image processing, and the video display window.

* **numpy:** A required dependency for OpenCV that handles all the underlying numerical and array operations.

* **comtypes:** (Windows Only) Used to get the friendly names of your cameras by querying the operating system directly.

You can install all of them with a single command in your terminal:

> pip install opencv-python numpy comtypes


## External System Tools
These programs need to be installed on your operating system and be accessible
from the command line (in your system's PATH).

* **ffmpeg:** (Required for both Windows and Linux) This is used to perform a detailed
  query of each camera to get a definitive list of its supported resolutions and frame rates.

* **v4l2-utils:** (Linux Only) This provides the v4l2-ctl command, which is the standard 
  way to list camera devices on Linux systems.


| Dependency | Required On | Purpose |
| :--- | :--- | :--- |
| **`opencv-python`** | Windows & Linux | Core camera control and image display |
| **`numpy`** | Windows & Linux | Numerical operations for OpenCV |
| **`comtypes`** | Windows only | Getting camera names |
| **`ffmpeg`** | Windows & Linux | Getting detailed camera resolutions |
| **`v4l2-utils`** | Linux only | Listing camera devices |