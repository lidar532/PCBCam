# By: github.com/lidar532
# 2025-0917

import cv2
import numpy as np

# --- Global State Variables ---
zoom_level = 1.0
pan_x, pan_y = 0, 0
is_panning = False      # Restored for panning
last_mouse_pos = (0, 0) # Restored for panning
markers = []

def mouse_events(event, x, y, flags, param):
    """
    Callback function to handle all mouse events.
    - Left-click: Place marker
    - Right-click + Drag: Pan the view
    - Middle-click: Remove last marker
    - Mouse Wheel: Zoom
    """
    global zoom_level, pan_x, pan_y, is_panning, last_mouse_pos, markers

    frame_height, frame_width = param['frame_shape']

    # --- Marker Placement (Left Mouse Click) ---
    if event == cv2.EVENT_LBUTTONDOWN:
        coord_on_rotated_frame_x = pan_x + x / zoom_level
        coord_on_rotated_frame_y = pan_y + y / zoom_level
        original_frame_x = frame_width - 1 - coord_on_rotated_frame_x
        original_frame_y = frame_height - 1 - coord_on_rotated_frame_y
        markers.append((int(original_frame_x), int(original_frame_y)))
        print(f"Marker added at original frame coordinates: ({int(original_frame_x)}, {int(original_frame_y)})")

    # --- Remove Last Marker (Middle Mouse Click) ---
    elif event == cv2.EVENT_MBUTTONDOWN:
        if markers:  # Check if the list is not empty
            markers.pop()  # Remove the last item from the list
            print("Removed the last marker.")
        else:
            print("No markers to remove.")

    # --- Pan Logic (Right Mouse Button) ---
    elif event == cv2.EVENT_RBUTTONDOWN:
        if zoom_level > 1.0:
            is_panning = True
            last_mouse_pos = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE:
        if is_panning:
            dx = x - last_mouse_pos[0]
            dy = y - last_mouse_pos[1]
            pan_x -= int(dx / zoom_level)
            pan_y -= int(dy / zoom_level)
            last_mouse_pos = (x, y)
    elif event == cv2.EVENT_RBUTTONUP:
        is_panning = False

    # --- Zoom Logic (Mouse Wheel) ---
    elif event == cv2.EVENT_MOUSEWHEEL:
        img_x = pan_x + x / zoom_level; img_y = pan_y + y / zoom_level
        if flags > 0: zoom_level = min(zoom_level * 1.2, 10.0)
        else: zoom_level = max(zoom_level / 1.2, 1.0)
        if zoom_level <= 1.0: pan_x, pan_y = 0, 0
        else:
            pan_x = int(img_x - (x / zoom_level)); pan_y = int(img_y - (y / zoom_level))

    # --- Clamp Pan Values (after any change) ---
    view_w = int(frame_width / zoom_level); view_h = int(frame_height / zoom_level)
    max_pan_x = frame_width - view_w; max_pan_y = frame_height - view_h
    pan_x = np.clip(pan_x, 0, max_pan_x); pan_y = np.clip(pan_y, 0, max_pan_y)


# --- Main Application ---
WINDOW_NAME = "Camera Feed"
v = cv2.VideoCapture(0)
if not v.isOpened(): print("Error: Could not open camera."); exit()

# 2592x1944
# 2048x1536 
# 1600x1200
# 1920x1080
width = 1600
height = 1200
v.set(cv2.CAP_PROP_FRAME_WIDTH, width)
v.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
actual_width = int(v.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Requested 1920x1080, but camera set to: {actual_width}x{actual_height}")

r, frame = v.read()
if not r: print("Error: Could not read first frame from camera."); v.release(); exit()

frame_height, frame_width = frame.shape[:2]

cv2.namedWindow(WINDOW_NAME)
callback_param = {'frame_shape': (frame_height, frame_width)}
cv2.setMouseCallback(WINDOW_NAME, mouse_events, callback_param)

while True:
    rv, frame = v.read()
    if not rv: print("Done"); break
    
    frame = cv2.rotate(frame, cv2.ROTATE_180)

    for marker_pos in markers:
        draw_x = frame_width - 1 - marker_pos[0]
        draw_y = frame_height - 1 - marker_pos[1]
        cross_size = 7
        color = (0, 0, 255)
        thickness = 1
        cv2.line(frame, (draw_x - cross_size, draw_y), (draw_x + cross_size, draw_y), color, thickness)
        cv2.line(frame, (draw_x, draw_y - cross_size), (draw_x, draw_y + cross_size), color, thickness)
    
    view_w = int(frame_width / zoom_level); view_h = int(frame_height / zoom_level)
    roi_x, roi_y = pan_x, pan_y
    zoomed_frame = frame[roi_y : roi_y + view_h, roi_x : roi_x + view_w]
    display_frame = cv2.resize(zoomed_frame, (frame_width, frame_height))
    
    cv2.imshow(WINDOW_NAME, display_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
        break

v.release()
cv2.destroyAllWindows()
