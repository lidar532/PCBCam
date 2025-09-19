# camera_lister.py
import sys
import subprocess
import json

def get_cameras_windows_comtypes():
    """Uses comtypes to get a list of camera names and indices on Windows."""
    try:
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        
        DEVICES_CATEGORY_GUID = "{860BB310-5D01-11d0-BD3B-00A0C911CE86}"
        devices_list = []
        
        pSysDevEnum = comtypes.client.CreateObject("{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}")
        pEnumCat = pSysDevEnum.CreateClassEnumerator(comtypes.GUID(DEVICES_CATEGORY_GUID), 0)
        
        if pEnumCat is not None:
            for index, pMoniker in enumerate(pEnumCat):
                prop_bag = pMoniker.BindToStorage(0, 0, comtypes.GUID("{55272A00-42CB-11CE-8135-00AA004BB851}"))
                friendly_name = prop_bag.Read("FriendlyName", 0)
                devices_list.append({"index": index, "name": friendly_name})
        
        comtypes.CoUninitialize()
        return devices_list
    except (ImportError, Exception) as e:
        print(f"Lister: comtypes method failed. Error: {e}", file=sys.stderr)
        return []

def get_cameras_windows_powershell():
    """Fallback method using PowerShell to get camera names."""
    print("Lister: comtypes failed, trying PowerShell fallback...", file=sys.stderr)
    try:
        command = "Get-PnpDevice -Class 'Camera','Image' -Status 'OK' | Select-Object FriendlyName | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, check=True)
        
        output = result.stdout.strip()
        if not output:
            return []
            
        data = json.loads(output)
        if not isinstance(data, list):
            data = [data]

        devices_list = [{"index": i, "name": item['FriendlyName']} for i, item in enumerate(data)]
        return devices_list
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
        print(f"Lister: PowerShell method failed. Error: {e}", file=sys.stderr)
        return []

def get_cameras_linux():
    try:
        cmd = "v4l2-ctl --list-devices"
        result = subprocess.run(cmd.split(), capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        devices, current_device_name, device_paths = [], None, []
        for line in output.split('\n'):
            if not line.startswith('\t'):
                current_device_name = line.strip().split(' (')[0]
                device_paths = []
            elif line.strip().startswith('/dev/video'):
                device_paths.append(line.strip())
            
            if current_device_name and device_paths:
                for path in device_paths:
                    try:
                        index = int(path.replace('/dev/video', ''))
                        if not any(d['name'] == current_device_name for d in devices):
                             devices.append({"index": index, "name": current_device_name})
                    except ValueError: continue
                device_paths = []
        return sorted(devices, key=lambda d: d['index'])
    except (FileNotFoundError, subprocess.CalledProcessError, Exception) as e:
        print(f"Lister: Could not list cameras using v4l2-ctl. Error: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    cameras = []
    if sys.platform == "win32":
        cameras = get_cameras_windows_comtypes()
        if not cameras:
            cameras = get_cameras_windows_powershell()
    elif sys.platform.startswith("linux"):
        cameras = get_cameras_linux()
    
    print(json.dumps(cameras))