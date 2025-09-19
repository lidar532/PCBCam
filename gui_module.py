# gui_module.py
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, Toplevel, Scale, Spinbox, Entry, Text
import json
import queue
import os

class AppGUI(tk.Tk):
    def __init__(self, command_queue, update_queue, camera_capabilities):
        super().__init__()
        self.command_queue = command_queue
        self.update_queue = update_queue
        self.camera_capabilities = camera_capabilities # CHANGED
        
        self.camera_states = {}
        self.current_resolution = (1920, 1080)
        self.current_filepath = None
        self.current_camera_name = "Default"
        self.camera_index_var = tk.IntVar(value=0)
        self.marker_shape = tk.StringVar(value='Cross')
        self.marker_color_name = tk.StringVar(value='Red')
        self.marker_size = tk.IntVar(value=15)

        self.title("Camera Control Panel")
        self.geometry("800x450")
        
        self._create_menus()
        self._create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self._on_exit)
        self.after(100, self._check_for_updates)

    def _create_widgets(self):
        # (no changes in this method)
        tree_frame = ttk.Frame(self); tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        columns = ('index', 'x', 'y', 'shape', 'color', 'size', 'desc')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.heading('index', text='#'); self.tree.heading('x', text='X-Coord'); self.tree.heading('y', text='Y-Coord'); self.tree.heading('shape', text='Shape'); self.tree.heading('color', text='Color'); self.tree.heading('size', text='Size'); self.tree.heading('desc', text='Description')
        self.tree.column('index', width=40, anchor=tk.CENTER); self.tree.column('x', width=80, anchor=tk.CENTER); self.tree.column('y', width=80, anchor=tk.CENTER); self.tree.column('shape', width=80, anchor=tk.W); self.tree.column('color', width=80, anchor=tk.W); self.tree.column('size', width=60, anchor=tk.CENTER); self.tree.column('desc', width=200, anchor=tk.W)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        button_frame = ttk.Frame(self); button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        desc_button = ttk.Button(button_frame, text="Add/Edit Last Marker...", command=self._open_description_dialog_event)
        desc_button.pack(side=tk.LEFT)
        restart_button = ttk.Button(button_frame, text="Restart Camera", command=self._restart_camera)
        restart_button.pack(side=tk.LEFT, padx=10)

    def _create_menus(self):
        self.menubar = tk.Menu(self); self.config(menu=self.menubar)
        file_menu = tk.Menu(self.menubar, tearoff=0); self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_file); file_menu.add_command(label="Load Markers...", command=self._load_file); file_menu.add_command(label="Save", command=self._save_current_file); file_menu.add_command(label="Save Markers As...", command=self._save_as_file); file_menu.add_separator(); file_menu.add_command(label="Exit", command=self._on_exit)
        camera_menu = tk.Menu(self.menubar, tearoff=0); self.menubar.add_cascade(label="Camera", menu=camera_menu)
        
        select_camera_menu = tk.Menu(camera_menu, tearoff=0); camera_menu.add_cascade(label="Select Camera", menu=select_camera_menu)
        if self.camera_capabilities:
            for index, caps in self.camera_capabilities.items():
                select_camera_menu.add_radiobutton(label=f"[{index}] {caps['name']}", value=index, variable=self.camera_index_var, command=self._switch_camera)
        else: select_camera_menu.add_command(label="No cameras found", state="disabled")

        # CHANGED: Create the resolution menu, but populate it dynamically
        self.resolution_menu = tk.Menu(camera_menu, tearoff=0)
        camera_menu.add_cascade(label="Set Resolution", menu=self.resolution_menu)
        self._update_resolution_menu() # Populate for the default camera

        camera_menu.add_separator(); camera_menu.add_command(label="Camera Settings...", command=self._open_cam_settings)
        marker_menu = tk.Menu(self.menubar, tearoff=0); self.menubar.add_cascade(label="Markers", menu=marker_menu)
        shape_menu = tk.Menu(marker_menu, tearoff=0); marker_menu.add_cascade(label="Shape", menu=shape_menu)
        for shape in ['Cross', 'Circle', 'Square']: shape_menu.add_radiobutton(label=shape, variable=self.marker_shape, command=self._set_marker_shape)
        color_menu = tk.Menu(marker_menu, tearoff=0); marker_menu.add_cascade(label="Color", menu=color_menu)
        self.colors = {'Red': (0, 0, 255), 'Green': (0, 255, 0), 'Blue': (255, 0, 0), 'Yellow': (0, 255, 255)}
        for color_name in self.colors: color_menu.add_radiobutton(label=color_name, variable=self.marker_color_name, command=self._set_marker_color)
        size_menu = tk.Menu(marker_menu, tearoff=0); marker_menu.add_cascade(label="Size (pixels)", menu=size_menu)
        for size in [9, 15, 25]: size_menu.add_radiobutton(label=f"{size}px", value=size, variable=self.marker_size, command=self._set_marker_size)
        help_menu = tk.Menu(self.menubar, tearoff=0); self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Commands", command=self._show_help); help_menu.add_command(label="About", command=self._show_about)

    # ADDED: New method to dynamically build the resolution menu
    def _update_resolution_menu(self):
        self.resolution_menu.delete(0, tk.END) # Clear existing entries
        
        cam_index = self.camera_index_var.get()
        caps = self.camera_capabilities.get(cam_index)

        if caps and caps['resolutions']:
            for w, h in caps['resolutions']:
                self.resolution_menu.add_command(label=f"{w}x{h}", command=lambda w=w, h=h: self._set_resolution(w, h))
        else:
            self.resolution_menu.add_command(label="No resolutions found", state="disabled")

    def _refresh_marker_table(self):
        # (no changes in this method)
        for item in self.tree.get_children(): self.tree.delete(item)
        bgr_to_color_name = {v: k for k, v in self.colors.items()}
        current_markers = self._get_current_cam_state().get('markers', [])
        for i, marker in enumerate(current_markers):
            pos, shape = marker['pos'], marker['shape']; color_name = bgr_to_color_name.get(tuple(marker['color']), "Custom")
            size, desc = marker['size'], marker.get('desc', ''); self.tree.insert('', tk.END, values=(i+1, pos[0], pos[1], shape, color_name, f"{size}px", desc))

    def _check_for_updates(self):
        # (no changes in this method)
        needs_refresh = False
        try:
            while True:
                command, value = self.update_queue.get_nowait()
                if command == 'sync_markers': self._get_current_cam_state()['markers'] = value; needs_refresh = True
                elif command == 'status_update':
                    status = value; self.current_camera_name = status['name']; self.camera_index_var.set(status['index']); self.current_resolution = status['resolution']; needs_refresh = True
                elif command == 'confirm_delete_marker': index, marker_data = value; self._confirm_delete(index, marker_data)
                elif command == 'show_description_dialog_for_marker': marker_index = value; self._open_description_dialog_event(marker_index=marker_index)
                elif command == 'exit_gui': self.destroy()
        except queue.Empty: pass
        if needs_refresh: self._refresh_marker_table()
        self.after(100, self._check_for_updates)

    def _show_about(self): messagebox.showinfo("About PCB Cam","PCB Cam Utility\nVersion 1.3\n\nDeveloped by C. W. Wright Lidar532{ATT}Gmail.com assisted by Gemini 1.0 AI.")
    def _show_help(self):
        help_win = Toplevel(self); help_win.title("Commands")
        frame = ttk.Frame(help_win); frame.pack(expand=True, fill=tk.BOTH)
        scrollbar = ttk.Scrollbar(frame)
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Courier New", 10), padx=10, pady=10, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH); scrollbar.config(command=text_widget.yview)
        help_text = """
Keyboard and Mouse Commands
--------------------------------------------------
Actions below apply to the Camera Feed window.
... (text omitted for brevity) ...
"""
        text_widget.insert(tk.END, help_text); text_widget.config(state="disabled")
        help_win.update_idletasks()
        required_height, required_width = help_win.winfo_reqheight(), help_win.winfo_reqwidth()
        screen_height = help_win.winfo_screenheight()
        if required_height > screen_height / 2: help_win.geometry(f"{required_width}x{int(screen_height / 2)}"); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x = self.winfo_x()+(self.winfo_width()/2)-(help_win.winfo_width()/2); y = self.winfo_y()+(self.winfo_height()/2)-(help_win.winfo_height()/2)
        help_win.geometry(f"+{int(x)}+{int(y)}"); help_win.transient(self); help_win.grab_set()

    def _get_current_cam_state(self):
        cam_index = self.camera_index_var.get()
        if cam_index not in self.camera_states: self.camera_states[cam_index] = {"markers": [], "undo_stack": [], "redo_stack": []}
        return self.camera_states[cam_index]

    def _restart_camera(self): self.command_queue.put(('restart_camera', None))
    def _confirm_delete(self, index, marker_data):
        marker_num = index + 1; desc = marker_data.get('desc', ''); details = f"Marker #{marker_num} at {marker_data['pos']}"
        if desc: details += f"\nDescription: {desc}"
        self.attributes('-topmost', True); user_response = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this marker?\n\n{details}")
        self.attributes('-topmost', False)
        if user_response: self.command_queue.put(('delete_marker_confirmed', index))
    def _open_description_dialog_event(self, event=None, marker_index=None):
        current_markers = self._get_current_cam_state().get('markers', [])
        if not current_markers: messagebox.showinfo("Info", "Please add a marker first."); return
        if marker_index is None: marker_index = len(current_markers) - 1
        DescriptionDialog(self, current_markers, self.colors, self._update_marker_from_dialog, starting_index=marker_index)
    def _update_marker_from_dialog(self, index, updated_marker_data):
        current_markers = self._get_current_cam_state().get('markers', [])
        if 0 <= index < len(current_markers):
            current_markers[index] = updated_marker_data; self._refresh_marker_table()
            self.command_queue.put(('update_marker', (index, current_markers[index])))
        else: messagebox.showerror("Error", f"Invalid marker number: {index + 1}")
    
    # --- CHANGED: _switch_camera now updates the resolution menu ---
    def _switch_camera(self):
        self.command_queue.put(('switch_camera', self.camera_index_var.get()))
        self._update_resolution_menu() # Re-populate the menu for the new camera
        self._refresh_marker_table()
        
    def _set_resolution(self, w, h): self.command_queue.put(('set_resolution', (w, h)))
    def _set_marker_shape(self): self.command_queue.put(('set_marker_shape', self.marker_shape.get()))
    def _set_marker_color(self): self.command_queue.put(('set_marker_color', self.colors[self.marker_color_name.get()]))
    def _set_marker_size(self): self.command_queue.put(('set_marker_size', self.marker_size.get()))
    def _new_file(self):
        if messagebox.askyesno("Confirm New", "Clear all current markers?"): self.current_filepath = None; self.command_queue.put(('clear_markers', None))
    def _load_file(self):
        filepath = filedialog.askopenfilename(title="Load PCB Cam File", filetypes=[("PCB Cam Files", "*-pcbcam.txt"), ("All Files", "*.*")])
        if not filepath: return
        try:
            with open(filepath, 'r') as f: data = json.load(f)
            self.current_filepath = filepath; self.command_queue.put(('load_file', data))
        except Exception as e: messagebox.showerror("Error", f"Failed to load file.\n{e}")
    def _save_current_file(self):
        if self.current_filepath:
            data_to_save = {"camera_name": self.current_camera_name, "camera_index": self.camera_index_var.get(), "resolution": self.current_resolution, "markers": self._get_current_cam_state().get('markers', [])}
            try:
                with open(self.current_filepath, 'w') as f: json.dump(data_to_save, f, indent=4)
                print(f"GUI: Saved file to {self.current_filepath}")
            except Exception as e: messagebox.showerror("Error", f"Failed to save file.\n{e}")
        else: self._save_as_file()
    def _save_as_file(self):
        filepath = filedialog.asksaveasfilename(title="Save PCB Cam File", defaultextension=".txt", filetypes=[("PCB Cam Files", "*-pcbcam.txt"), ("All Files", "*.*")])
        if not filepath: return
        root, ext = os.path.splitext(filepath)
        if not root.lower().endswith("-pcbcam"): root += "-pcbcam"
        final_filepath = root + ".txt"
        data_to_save = {"camera_name": self.current_camera_name, "camera_index": self.camera_index_var.get(), "resolution": self.current_resolution, "markers": self._get_current_cam_state().get('markers', [])}
        try:
            with open(final_filepath, 'w') as f: json.dump(data_to_save, f, indent=4)
            self.current_filepath = final_filepath; print(f"GUI: Saved new file to {final_filepath}")
        except Exception as e: messagebox.showerror("Error", f"Failed to save file.\n{e}")
    def _open_cam_settings(self): CameraSettingsWindow(self, self.command_queue)
    def _on_exit(self): self.command_queue.put(('exit', None)); self.destroy()

class DescriptionDialog(Toplevel):
    # (no changes)
    def __init__(self, parent, markers, colors, callback, starting_index=0):
        super().__init__(parent); self.markers=markers; self.colors=colors; self.bgr_to_color_name={v:k for k,v in self.colors.items()}; self.callback=callback; self.title("Edit Marker Properties"); self.geometry("400x300")
        self.marker_num_var=tk.IntVar(); self.x_var=tk.IntVar(); self.y_var=tk.IntVar(); self.shape_var=tk.StringVar(); self.color_var=tk.StringVar(); self.size_var=tk.IntVar(); self.desc_var=tk.StringVar()
        main_frame = ttk.Frame(self, padding="10"); main_frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(main_frame, text="Marker #:").grid(row=0, column=0, sticky="w", pady=2)
        self.marker_spinbox = Spinbox(main_frame, from_=1, to=len(markers) if markers else 1, textvariable=self.marker_num_var, width=7, command=self._on_marker_selection_change); self.marker_spinbox.grid(row=0, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="X Coordinate:").grid(row=1, column=0, sticky="w", pady=2)
        self.x_spinbox = Spinbox(main_frame, from_=0, to=9999, textvariable=self.x_var, width=7, command=self._on_coordinate_change); self.x_spinbox.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="Y Coordinate:").grid(row=2, column=0, sticky="w", pady=2)
        self.y_spinbox = Spinbox(main_frame, from_=0, to=9999, textvariable=self.y_var, width=7, command=self._on_coordinate_change); self.y_spinbox.grid(row=2, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="Shape:").grid(row=3, column=0, sticky="w", pady=2)
        self.shape_combo = ttk.Combobox(main_frame, textvariable=self.shape_var, values=['Cross', 'Circle', 'Square'], state='readonly', width=10); self.shape_combo.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="Color:").grid(row=4, column=0, sticky="w", pady=2)
        self.color_combo = ttk.Combobox(main_frame, textvariable=self.color_var, values=list(self.colors.keys()), state='readonly', width=10); self.color_combo.grid(row=4, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="Size:").grid(row=5, column=0, sticky="w", pady=2)
        self.size_combo = ttk.Combobox(main_frame, textvariable=self.size_var, values=[9, 15, 25], state='readonly', width=10); self.size_combo.grid(row=5, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="Description:").grid(row=6, column=0, sticky="w", pady=2)
        self.desc_entry = ttk.Entry(main_frame, textvariable=self.desc_var, width=30); self.desc_entry.grid(row=6, column=1, sticky="ew", pady=2)
        btn_frame = ttk.Frame(main_frame); ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5); ttk.Button(btn_frame, text="Update", command=self._on_update).pack(side=tk.LEFT, padx=5); ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5); btn_frame.grid(row=7, column=0, columnspan=2, pady=15)
        self.x_spinbox.bind("<MouseWheel>", self._on_x_scroll); self.y_spinbox.bind("<MouseWheel>", self._on_y_scroll)
        if markers: self.marker_num_var.set(starting_index + 1); self._on_marker_selection_change()
        self.transient(parent); self.grab_set(); self.desc_entry.focus_set()
    def _on_x_scroll(self, event):
        if event.delta > 0: self.x_spinbox.invoke('buttonup')
        else: self.x_spinbox.invoke('buttondown')
        self._on_coordinate_change()
    def _on_y_scroll(self, event):
        if event.delta > 0: self.y_spinbox.invoke('buttonup')
        else: self.y_spinbox.invoke('buttondown')
        self._on_coordinate_change()
    def _on_coordinate_change(self):
        if hasattr(self, '_after_id'): self.after_cancel(self._after_id)
        self._after_id = self.after(200, self._apply_changes)
    def _on_marker_selection_change(self):
        try:
            index = self.marker_num_var.get() - 1
            if 0 <= index < len(self.markers):
                marker_data = self.markers[index]
                self.x_var.set(marker_data['pos'][0]); self.y_var.set(marker_data['pos'][1])
                self.shape_var.set(marker_data['shape']); color_name = self.bgr_to_color_name.get(tuple(marker_data['color']), "")
                self.color_var.set(color_name); self.size_var.set(marker_data['size']); self.desc_var.set(marker_data.get('desc', ''))
        except (tk.TclError, IndexError): pass
    def _apply_changes(self):
        try:
            marker_index = self.marker_num_var.get() - 1
            updated_marker_data = {"pos": (self.x_var.get(), self.y_var.get()), "shape": self.shape_var.get(), "color": self.colors[self.color_var.get()], "size": self.size_var.get(), "desc": self.desc_var.get()}
            self.callback(marker_index, updated_marker_data); return True
        except (tk.TclError, KeyError): messagebox.showerror("Invalid Input", "Please ensure all fields are set correctly."); return False
    def _on_update(self): self._apply_changes()
    def _on_ok(self):
        if self._apply_changes(): self.destroy()
class CameraSettingsWindow(Toplevel):
    def __init__(self, parent, command_queue):
        super().__init__(parent); self.command_queue=command_queue; self.title("Camera Settings"); self.geometry("300x200")
        tk.Label(self, text="Brightness").pack(); Scale(self, from_=0, to=255, orient=tk.HORIZONTAL, command=self._set_brightness, variable=tk.DoubleVar(value=128)).pack(fill=tk.X, padx=10)
        tk.Label(self, text="Contrast").pack(); Scale(self, from_=0, to=255, orient=tk.HORIZONTAL, command=self._set_contrast, variable=tk.DoubleVar(value=128)).pack(fill=tk.X, padx=10)
    def _set_brightness(self, value): self.command_queue.put(('set_property', ('brightness', int(float(value)))))
    def _set_contrast(self, value): self.command_queue.put(('set_property', ('contrast', int(float(value)))))