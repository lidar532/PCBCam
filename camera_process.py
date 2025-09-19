# camera_process.py
import cv2
import numpy as np
import queue
import time
import math
import sys
import subprocess
import json # ADDED: To fix NameError

if sys.platform == "win32":
    try:
        import comtypes
        import comtypes.client
    except ImportError:
        print("CAM: WARNING - 'comtypes' library not found.")

class CameraHandler:
    def __init__(self, command_queue, update_queue):
        self.command_queue, self.update_queue = command_queue, update_queue
        self.camera_states = {}
        self.zoom_level, self.pan_x, self.pan_y = 1.0, 0, 0
        self.is_panning, self.last_mouse_pos = False, (0, 0)
        self.right_button_down, self.pan_start_pos = False, (0,0)
        self.DRAG_THRESHOLD_SQ = 5**2
        self.frame_height, self.frame_width = 1080, 1920
        self.WINDOW_NAME, self.device_index, self.camera_name = "Initializing...", 0, "Unknown Camera"
        self.marker_shape, self.marker_color, self.marker_size = 'Cross', (0,0,255), 15
        self.restart_attempts, self.MAX_RESTART_ATTEMPTS = 0, 5

    def _get_current_cam_state(self):
        if self.device_index not in self.camera_states:
            self.camera_states[self.device_index] = {"markers": [], "undo_stack": [], "redo_stack": []}
        return self.camera_states[self.device_index]

    def _sync_gui_markers(self):
        self.update_queue.put(('sync_markers', self._get_current_cam_state()['markers']))

    def _undo_action(self):
        state = self._get_current_cam_state()
        if not state['undo_stack']: return
        last_action = state['undo_stack'].pop(); state['redo_stack'].append(last_action)
        action_type = last_action.get('action_type')
        if action_type == 'add': state['markers'].pop()
        elif action_type == 'delete': state['markers'].insert(last_action['index'], last_action['data'])
        elif action_type == 'modify': state['markers'][last_action['index']] = last_action['old_data']
        self._sync_gui_markers()
        
    def _redo_action(self):
        state = self._get_current_cam_state()
        if not state['redo_stack']: return
        last_action = state['redo_stack'].pop(); state['undo_stack'].append(last_action)
        action_type = last_action.get('action_type')
        if action_type == 'add': state['markers'].append(last_action['data'])
        elif action_type == 'delete': del state['markers'][last_action['index']]
        elif action_type == 'modify': state['markers'][last_action['index']] = last_action['new_data']
        self._sync_gui_markers()

    def _get_camera_name(self):
        if sys.platform == "win32":
            name = self._get_camera_name_windows_comtypes()
            if name == f"Camera {self.device_index}":
                name = self._get_camera_name_windows_powershell()
            return name
        elif sys.platform.startswith("linux"):
            return self._get_camera_name_linux()
        else:
            return f"Camera {self.device_index}"

    def _get_camera_name_windows_comtypes(self):
        try:
            comtypes.CoInitialize()
            DEVICES_CATEGORY_GUID="{860BB310-5D01-11d0-BD3B-00A0C911CE86}"; devices = []
            pSysDevEnum = comtypes.client.CreateObject("{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}")
            pEnumCat = pSysDevEnum.CreateClassEnumerator(comtypes.GUID(DEVICES_CATEGORY_GUID), 0)
            if pEnumCat is not None:
                for pMoniker in pEnumCat:
                    prop_bag = pMoniker.BindToStorage(0, 0, comtypes.GUID("{55272A00-42CB-11CE-8135-00AA004BB851}"))
                    devices.append(prop_bag.Read("FriendlyName", 0))
            comtypes.CoUninitialize()
            if self.device_index < len(devices):
                return devices[self.device_index]
        except Exception as e:
            print(f"CAM: comtypes method failed. Error: {e}")
        return f"Camera {self.device_index}"

    def _get_camera_name_windows_powershell(self):
        print("CAM: comtypes failed, trying PowerShell fallback...")
        try:
            command = "Get-PnpDevice -Class 'Camera','Image' -Status 'OK' | Select-Object FriendlyName | ConvertTo-Json"
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            if not output: return f"Camera {self.device_index}"
            data = json.loads(output)
            if not isinstance(data, list): data = [data]
            devices = [item['FriendlyName'] for item in data]
            if self.device_index < len(devices): return devices[self.device_index]
        except Exception as e:
            print(f"CAM: PowerShell method failed. Error: {e}")
        return f"Camera {self.device_index}"
        
    def _get_camera_name_linux(self):
        try:
            cmd = "v4l2-ctl --list-devices"; result = subprocess.run(cmd.split(), capture_output=True, text=True)
            output = result.stdout.strip(); devices = []; current_device_name = None; device_paths = []
            for line in output.split('\n'):
                if not line.startswith('\t'): current_device_name = line.strip().split(' (')[0]; device_paths = []
                elif line.strip().startswith('/dev/video'): device_paths.append(line.strip())
                if current_device_name and device_paths:
                    for path in device_paths:
                        try:
                            index = int(path.replace('/dev/video', ''))
                            if not any(d['name'] == current_device_name for d in devices): devices.append({"index": index, "name": current_device_name})
                        except ValueError: continue
                    device_paths = []
            if self.device_index < len(devices): return devices[self.device_index]['name']
        except Exception as e: print(f"CAM: Could not get camera name using v4l2-ctl. Error: {e}")
        return f"Camera {self.device_index}"

    def _initialize_camera(self, w=1920, h=1080):
        if hasattr(self, 'v'):
            try: cv2.destroyWindow(self.WINDOW_NAME)
            except cv2.error: pass
            self.v.release()
        self.camera_name = self._get_camera_name()
        self.v = cv2.VideoCapture(self.device_index)
        if not self.v.isOpened(): print("CAM: Error: Could not open camera."); return False
        self.v.set(cv2.CAP_PROP_FRAME_WIDTH, w); self.v.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.v.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.frame_width = int(self.v.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.v.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.frame_width == 0 or self.frame_height == 0: print("CAM: Error: Failed to set resolution."); return False
        self.WINDOW_NAME = f"{self.camera_name} - {self.frame_width}x{self.frame_height}"
        cv2.namedWindow(self.WINDOW_NAME); cv2.setMouseCallback(self.WINDOW_NAME, self.mouse_events)
        status = {"name": self.camera_name, "index": self.device_index, "resolution": (self.frame_width, self.frame_height)}
        self.update_queue.put(('status_update', status))
        return True

    def handle_commands(self):
        try:
            command, value = self.command_queue.get_nowait()
            state = self._get_current_cam_state()
            if command == 'exit': return False
            elif command == 'switch_camera':
                self.device_index = value
                self._initialize_camera(self.frame_width, self.frame_height)
                self._sync_gui_markers()
            elif command == 'restart_camera': self._initialize_camera(self.frame_width, self.frame_height)
            elif command == 'delete_marker_confirmed':
                index_to_delete = value
                if 0 <= index_to_delete < len(state['markers']):
                    deleted_marker = state['markers'].pop(index_to_delete)
                    action = {'action_type': 'delete', 'index': index_to_delete, 'data': deleted_marker}
                    state['undo_stack'].append(action); state['redo_stack'].clear(); self._sync_gui_markers()
            elif command == 'update_marker':
                index, new_marker_data = value
                if 0 <= index < len(state['markers']):
                    old_marker_data = state['markers'][index]
                    action = {'action_type': 'modify', 'index': index, 'old_data': old_marker_data, 'new_data': new_marker_data}
                    state['undo_stack'].append(action); state['redo_stack'].clear()
                    state['markers'][index] = new_marker_data; self._sync_gui_markers()
            elif command == 'set_resolution': self._initialize_camera(value[0], value[1])
            elif command == 'set_property':
                prop_name, val = value
                prop_map = {'brightness': cv2.CAP_PROP_BRIGHTNESS, 'contrast': cv2.CAP_PROP_CONTRAST}
                if prop_name in prop_map: self.v.set(prop_map[prop_name], val)
            elif command == 'clear_markers':
                state['markers'].clear(); state['undo_stack'].clear(); state['redo_stack'].clear(); self._sync_gui_markers()
            elif command == 'load_file':
                self.device_index = value.get('camera_index', self.device_index)
                state = self._get_current_cam_state()
                state['markers'] = value.get('markers', []); state['undo_stack'].clear(); state['redo_stack'].clear()
                res = value.get('resolution', (1920, 1080))
                self._initialize_camera(res[0], res[1]); self._sync_gui_markers()
            elif command == 'set_marker_shape': self.marker_shape = value
            elif command == 'set_marker_color': self.marker_color = value
            elif command == 'set_marker_size': self.marker_size = value
            elif command == 'get_current_markers': self._sync_gui_markers()
        except queue.Empty: pass
        return True

    def draw_markers(self, frame):
        current_markers = self._get_current_cam_state()['markers']
        for marker in current_markers:
            pos, shape, color, size = marker['pos'], marker['shape'], marker['color'], marker['size']
            draw_x, draw_y = self.frame_width - 1 - pos[0], self.frame_height - 1 - pos[1]
            half_size = size // 2
            if shape == 'Cross':
                cv2.line(frame, (draw_x - half_size, draw_y), (draw_x + half_size, draw_y), color, 1)
                cv2.line(frame, (draw_x, draw_y - half_size), (draw_x, draw_y + half_size), color, 1)
            elif shape == 'Circle': cv2.circle(frame, (draw_x, draw_y), half_size, color, 1)
            elif shape == 'Square': cv2.rectangle(frame, (draw_x-half_size, draw_y-half_size), (draw_x+half_size, draw_y+half_size), color, 1)

    def mouse_events(self, event, x, y, flags, param):
        state = self._get_current_cam_state()
        if event == cv2.EVENT_LBUTTONDOWN:
            state['redo_stack'].clear()
            coord_on_rotated_frame_x, coord_on_rotated_frame_y = self.pan_x + x/self.zoom_level, self.pan_y + y/self.zoom_level
            original_frame_x, original_frame_y = self.frame_width-1-coord_on_rotated_frame_x, self.frame_height-1-coord_on_rotated_frame_y
            new_marker = {"pos": (int(round(original_frame_x)), int(round(original_frame_y))), "shape": self.marker_shape, "color": self.marker_color, "size": self.marker_size, "desc": ""}
            state['markers'].append(new_marker); state['undo_stack'].append({'action_type': 'add', 'data': new_marker}); self._sync_gui_markers()
        elif event == cv2.EVENT_MBUTTONDOWN:
            if (flags & cv2.EVENT_FLAG_SHIFTKEY): self.find_and_request_delete(x, y)
            else: self._undo_action()
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.zoom_level > 1.0: self.right_button_down, self.pan_start_pos, self.is_panning = True, (x, y), False
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.right_button_down:
                if not self.is_panning:
                    dist_sq = (x - self.pan_start_pos[0])**2 + (y - self.pan_start_pos[1])**2
                    if dist_sq > self.DRAG_THRESHOLD_SQ: self.is_panning, self.last_mouse_pos = True, self.pan_start_pos
                if self.is_panning:
                    dx, dy = x-self.last_mouse_pos[0], y-self.last_mouse_pos[1]
                    self.pan_x -= int(round(dx / self.zoom_level)); self.pan_y -= int(round(dy / self.zoom_level))
                    self.last_mouse_pos = (x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            if self.right_button_down and not self.is_panning: self.find_and_request_description_dialog(x, y)
            self.right_button_down, self.is_panning = False, False
        elif event == cv2.EVENT_MOUSEWHEEL:
            img_x, img_y = self.pan_x + x / self.zoom_level, self.pan_y + y / self.zoom_level
            if flags > 0: self.zoom_level = min(self.zoom_level * 1.2, 10.0)
            else: self.zoom_level = max(self.zoom_level / 1.2, 1.0)
            if self.zoom_level <= 1.0: self.pan_x, self.pan_y = 0, 0
            else: self.pan_x, self.pan_y = int(round(img_x-(x/self.zoom_level))), int(round(img_y-(y/self.zoom_level)))
        view_w, view_h = int(self.frame_width / self.zoom_level), int(self.frame_height / self.zoom_level)
        max_pan_x, max_pan_y = self.frame_width-view_w, self.frame_height-view_h
        self.pan_x, self.pan_y = np.clip(self.pan_x, 0, max_pan_x), np.clip(self.pan_y, 0, max_pan_y)

    def find_and_request_description_dialog(self, window_x, window_y):
        current_markers = self._get_current_cam_state()['markers']
        if not current_markers: return
        coord_on_rot_x, coord_on_rot_y = self.pan_x + window_x/self.zoom_level, self.pan_y + window_y/self.zoom_level
        target_x, target_y = self.frame_width-1-coord_on_rot_x, self.frame_height-1-coord_on_rot_y
        min_dist_sq, nearest_index = float('inf'), -1
        for i, marker in enumerate(current_markers):
            dist_sq = (marker['pos'][0] - target_x)**2 + (marker['pos'][1] - target_y)**2
            if dist_sq < min_dist_sq: min_dist_sq, nearest_index = dist_sq, i
        if nearest_index != -1: self.update_queue.put(('show_description_dialog_for_marker', nearest_index))
    def find_and_request_delete(self, window_x, window_y):
        current_markers = self._get_current_cam_state()['markers']
        if not current_markers: return
        coord_on_rot_x, coord_on_rot_y = self.pan_x + window_x/self.zoom_level, self.pan_y + window_y/self.zoom_level
        target_x, target_y = self.frame_width-1-coord_on_rot_x, self.frame_height-1-coord_on_rot_y
        min_dist_sq, nearest_index = float('inf'), -1
        for i, marker in enumerate(current_markers):
            dist_sq = (marker['pos'][0] - target_x)**2 + (marker['pos'][1] - target_y)**2
            if dist_sq < min_dist_sq: min_dist_sq, nearest_index = dist_sq, i
        if nearest_index != -1: self.update_queue.put(('confirm_delete_marker', (nearest_index, current_markers[nearest_index])))

    def run(self):
        if not self._initialize_camera(): self.update_queue.put(('exit_gui', None)); return
        while True:
            if not self.handle_commands(): break
            rv, frame = self.v.read()
            if not rv:
                print(f"CAM: Frame grab failed... restart {self.restart_attempts+1}/{self.MAX_RESTART_ATTEMPTS}...")
                self.v.release(); time.sleep(2.0)
                if self._initialize_camera(self.frame_width, self.frame_height):
                    print("CAM: Camera restart successful."); self.restart_attempts = 0; continue
                else:
                    self.restart_attempts += 1
                    if self.restart_attempts >= self.MAX_RESTART_ATTEMPTS:
                        print(f"CAM: Max restart attempts reached."); self.update_queue.put(('exit_gui', None)); break
                    else: continue
            self.restart_attempts = 0
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            self.draw_markers(frame)
            view_w, view_h = int(self.frame_width / self.zoom_level), int(self.frame_height / self.zoom_level)
            zoomed_frame = frame[self.pan_y : self.pan_y + view_h, self.pan_x : self.pan_x + view_w]
            display_frame = cv2.resize(zoomed_frame, (self.frame_width, self.frame_height))
            cv2.imshow(self.WINDOW_NAME, display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 26: self._undo_action() # CTRL+Z
            elif key == 25: self._redo_action() # CTRL+Y
            elif key == ord('q') or cv2.getWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                self.update_queue.put(('exit_gui', None)); break

def run_camera_process(command_queue, update_queue):
    handler = CameraHandler(command_queue, update_queue)
    handler.run()