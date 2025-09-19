# resolution_lister.py
import sys
import subprocess
import json
import re

def get_camera_devices_windows():
    devices = []
    try:
        command = "Get-PnpDevice -Class 'Camera','Image' -Status 'OK' | Select-Object FriendlyName | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, check=True, encoding='utf-8')
        output = result.stdout.strip()
        if not output: return []
        data = json.loads(output)
        if not isinstance(data, list): data = [data]
        devices = [item['FriendlyName'] for item in data]
    except Exception as e:
        print(f"Lister: PowerShell method failed. Error: {e}", file=sys.stderr)
    return devices

def get_camera_devices_linux():
    devices = []
    try:
        cmd = "v4l2-ctl --list-devices"
        result = subprocess.run(cmd.split(), capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        devices = re.findall(r'(/dev/video\d+)', output)
    except Exception as e:
        print(f"Lister: v4l2-ctl failed. Error: {e}", file=sys.stderr)
    return devices

def parse_ffmpeg_resolutions_windows(output, min_fps):
    regex = re.compile(r"s=(\d+x\d+)\s+fps=([\d\.]+)")
    found_resolutions = set()
    for line in output.split('\n'):
        if "vcodec=mjpeg" in line:
            matches = regex.findall(line)
            for res_str, fps_str in matches:
                fps = float(fps_str)
                if fps >= min_fps:
                    w, h = map(int, res_str.split('x'))
                    found_resolutions.add((w, h))
    return sorted(list(found_resolutions), key=lambda res: res[0]*res[1])

def parse_ffmpeg_resolutions_linux(output, min_fps):
    found_resolutions = set()
    lines = output.split('\n')
    in_mjpeg_block = False
    for line in lines:
        line = line.strip()
        if line.startswith('[') and ']' in line:
            in_mjpeg_block = "'MJPG'" in line or "(Motion-JPEG)" in line
        if in_mjpeg_block:
            if line.startswith('Size:'):
                res_matches = re.findall(r'(\d+x\d+)', line)
                fps_matches = re.findall(r'(\d+\.\d+)\s*fps', line)
                if res_matches and fps_matches:
                    fps = float(fps_matches[0])
                    if fps >= min_fps:
                        w, h = map(int, res_matches[0].split('x'))
                        found_resolutions.add((w, h))
    return sorted(list(found_resolutions), key=lambda res: res[0]*res[1])

def discover_camera_capabilities(min_fps=30, format_vcodec='mjpeg'):
    all_camera_caps = {}
    
    if sys.platform == "win32":
        devices = get_camera_devices_windows()
        for index, device_name in enumerate(devices):
            try:
                command = f'ffmpeg -list_options true -f dshow -i video="{device_name}"'
                result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8')
                output = result.stdout + result.stderr
                
                # --- ADDED: Debug printing ---
                print("-" * 20, file=sys.stderr)
                print(f"DEBUG: Raw FFmpeg output for '{device_name}':", file=sys.stderr)
                print(output, file=sys.stderr)
                print("-" * 20, file=sys.stderr)
                
                resolutions = parse_ffmpeg_resolutions_windows(output, min_fps)
                all_camera_caps[index] = {"name": device_name, "resolutions": resolutions}
            except Exception as e:
                print(f"Error processing '{device_name}': {e}", file=sys.stderr)
                all_camera_caps[index] = {"name": device_name, "resolutions": []}

    elif sys.platform.startswith("linux"):
        # (Linux logic is unchanged)
        devices = get_camera_devices_linux()
        for index, device_path in enumerate(devices):
            try:
                command = f"ffmpeg -list_formats all -f v4l2 -i {device_path}"
                result = subprocess.run(command.split(), capture_output=True, text=True)
                output = result.stdout + result.stderr
                resolutions = parse_ffmpeg_resolutions_linux(output, min_fps)
                all_camera_caps[index] = {"name": device_path, "resolutions": resolutions}
            except Exception as e:
                print(f"Error processing '{device_path}': {e}", file=sys.stderr)
                all_camera_caps[index] = {"name": device_path, "resolutions": []}

    return all_camera_caps

if __name__ == '__main__':
    print("Detecting camera resolutions with default settings (min 30fps, mjpeg format)...")
    detected_caps = discover_camera_capabilities()
    
    if not detected_caps:
        print("\nNo cameras or supported resolutions found.")
    else:
        print("\n--- Detection Results ---")
        for index, caps in detected_caps.items():
            print(f"\nCamera Index: {index} | Name: {caps['name']}")
            if caps['resolutions']:
                res_str = ", ".join([f"{w}x{h}" for w, h in caps['resolutions']])
                print(f"  Supported Resolutions: {res_str}")
            else:
                print("  No resolutions found matching the criteria.")
        print("\n-------------------------")