# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0

"""Simple Android Device Bridge using subprocess ADB calls."""

import io
import subprocess
import time
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image


class DeviceBridge:
    """Simple ADB wrapper using subprocess calls."""
    
    def __init__(self, device_serial: Optional[str] = None):
        """Initialize with optional device serial."""
        self.device_serial = device_serial
        self.screen_width = 0
        self.screen_height = 0
        
        # Get screen size
        self.screen_width, self.screen_height = self.get_screen_size()
    
    def _adb_command(self, *args) -> str:
        """Execute ADB command and return output."""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ADB command failed: {result.stderr}")
        return result.stdout.strip()
    
    def _adb_command_bytes(self, *args) -> bytes:
        """Execute ADB command and return bytes output."""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise Exception(f"ADB command failed: {result.stderr.decode()}")
        return result.stdout
    
    def list_devices(self) -> List[Dict[str, str]]:
        """List connected devices."""
        output = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = output.stdout.strip().split('\n')[1:]  # Skip header
        
        devices = []
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) == 2:
                    devices.append({
                        "serial": parts[0],
                        "state": parts[1],
                        "model": "Unknown",
                        "android_version": "Unknown"
                    })
        return devices
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        output = self._adb_command("shell", "wm", "size")
        # Output: "Physical size: 1080x1920"
        size_str = output.split(":")[-1].strip()
        width, height = map(int, size_str.split("x"))
        return width, height
    
    def capture_screenshot(self, format: str = "pil") -> Any:
        """Capture screenshot."""
        img_bytes = self._adb_command_bytes("exec-out", "screencap", "-p")
        
        if format == "bytes":
            return img_bytes
        elif format == "pil":
            return Image.open(io.BytesIO(img_bytes))
        else:
            raise ValueError(f"Invalid format: {format}")
    
    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self._adb_command("shell", "input", "tap", str(x), str(y))
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """Swipe gesture."""
        self._adb_command("shell", "input", "swipe", 
                         str(x1), str(y1), str(x2), str(y2), str(duration))
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> None:
        """Long press."""
        self.swipe(x, y, x, y, duration)
    
    def type_text(self, text: str) -> None:
        """Type text."""
        escaped = text.replace(" ", "%s").replace("&", "\\&")
        self._adb_command("shell", "input", "text", escaped)
    
    def press_back(self) -> None:
        """Press back button."""
        self._adb_command("shell", "input", "keyevent", "4")
    
    def press_home(self) -> None:
        """Press home button."""
        self._adb_command("shell", "input", "keyevent", "3")
    
    def press_recent(self) -> None:
        """Press recent apps."""
        self._adb_command("shell", "input", "keyevent", "187")
    
    def get_device_info(self) -> Dict[str, str]:
        """Get device info."""
        try:
            model = self._adb_command("shell", "getprop", "ro.product.model")
            version = self._adb_command("shell", "getprop", "ro.build.version.release")
            return {
                "model": model,
                "android_version": version,
                "api_level": "Unknown",
                "serial": self.device_serial or "Unknown"
            }
        except:
            return {
                "model": "Unknown",
                "android_version": "Unknown", 
                "api_level": "Unknown",
                "serial": self.device_serial or "Unknown"
            }
