# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Android Device Bridge for Phone Agent Framework.

This module provides ADB wrapper functionality for device connection,
screenshot capture, and action execution on Android devices.
"""

import io
import subprocess
import time
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image


class DeviceBridgeError(Exception):
    """Base exception for device bridge errors."""
    pass


class DeviceNotFoundError(DeviceBridgeError):
    """Raised when no device is found or multiple devices require selection."""
    pass


class DeviceDisconnectedError(DeviceBridgeError):
    """Raised when device connection is lost."""
    pass


class ScreenshotError(DeviceBridgeError):
    """Raised when screenshot capture fails."""
    pass


class ActionExecutionError(DeviceBridgeError):
    """Raised when action execution fails."""
    pass


class DeviceBridge:
    """
    Android Device Bridge for controlling Android devices via ADB.
    
    Provides methods for device connection, screenshot capture, and
    executing touch/gesture actions.
    
    Attributes:
        device: adbutils.AdbDevice instance
        screen_width: Device screen width in pixels
        screen_height: Device screen height in pixels
    """
    
    def __init__(self, device_serial: Optional[str] = None, adb_server_host: str = "127.0.0.1", adb_server_port: int = 5037):
        """
        Initialize Device Bridge.
        
        Args:
            device_serial: Optional device serial number. If None, auto-detects single device.
            adb_server_host: ADB server host address (unused, kept for compatibility).
            adb_server_port: ADB server port (unused, kept for compatibility).
            
        Raises:
            DeviceNotFoundError: If no device found or multiple devices without serial specified.
        """
        self.device_serial = device_serial
        self.screen_width: int = 0
        self.screen_height: int = 0
        self._screenshot_cache: Optional[bytes] = None
        
        self.connect(device_serial)
    
    def _adb_command(self, *args) -> str:
        """Execute ADB command and return text output."""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise Exception(f"ADB command failed: {result.stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise DeviceDisconnectedError("ADB command timed out")
        except Exception as e:
            raise DeviceDisconnectedError(f"ADB command failed: {e}")
    
    def _adb_command_bytes(self, *args) -> bytes:
        """Execute ADB command and return bytes output."""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                raise Exception(f"ADB command failed: {result.stderr.decode()}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise DeviceDisconnectedError("ADB command timed out")
        except Exception as e:
            raise DeviceDisconnectedError(f"ADB command failed: {e}")
    
    def list_devices(self) -> List[Dict[str, str]]:
        """
        List all connected Android devices.
        
        Returns:
            List of device info dicts with keys: serial, state, model, android_version.
        """
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split('\n')[1:]  # Skip "List of devices attached"
            
            devices = []
            for line in lines:
                line = line.strip()
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        serial = parts[0]
                        state = parts[1]
                        
                        # Try to get device info
                        model = "Unknown"
                        version = "Unknown"
                        if state == "device":
                            try:
                                model_cmd = ["adb", "-s", serial, "shell", "getprop", "ro.product.model"]
                                model_result = subprocess.run(model_cmd, capture_output=True, text=True, timeout=5)
                                if model_result.returncode == 0:
                                    model = model_result.stdout.strip()
                                
                                version_cmd = ["adb", "-s", serial, "shell", "getprop", "ro.build.version.release"]
                                version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=5)
                                if version_result.returncode == 0:
                                    version = version_result.stdout.strip()
                            except:
                                pass
                        
                        devices.append({
                            "serial": serial,
                            "state": state,
                            "model": model,
                            "android_version": version
                        })
            
            return devices
        except Exception as e:
            raise DeviceBridgeError(f"Failed to list devices: {e}")
    
    def connect(self, device_serial: Optional[str] = None) -> None:
        """
        Connect to an Android device.
        
        Args:
            device_serial: Optional device serial. If None, auto-detects single device.
            
        Raises:
            DeviceNotFoundError: If no device or multiple devices without serial.
            DeviceDisconnectedError: If connection fails.
        """
        try:
            devices = self.list_devices()
            
            if not devices:
                raise DeviceNotFoundError(
                    "No Android devices found. Please connect a device and enable USB debugging.\n"
                    "For WiFi ADB: adb connect <IP>:<PORT>"
                )
            
            if device_serial:
                # Check if specified device exists
                device_found = any(d['serial'] == device_serial for d in devices)
                if not device_found:
                    available = "\n".join([f"  - {d['serial']}" for d in devices])
                    raise DeviceNotFoundError(
                        f"Device {device_serial} not found.\nAvailable devices:\n{available}"
                    )
                self.device_serial = device_serial
            else:
                # Auto-detect single device
                if len(devices) == 1:
                    self.device_serial = devices[0]['serial']
                else:
                    device_list_str = "\n".join([f"  - {d['serial']}" for d in devices])
                    raise DeviceNotFoundError(
                        f"Multiple devices found. Please specify device serial:\n{device_list_str}\n"
                        f"Use --device-serial <serial> flag."
                    )
            
            # Verify connection and get screen size
            self._verify_connection()
            self.screen_width, self.screen_height = self.get_screen_size()
            
        except DeviceNotFoundError:
            raise
        except Exception as e:
            raise DeviceDisconnectedError(f"Failed to connect to device: {e}")
    
    def _verify_connection(self) -> None:
        """Verify device connection is healthy."""
        if not self.device_serial:
            raise DeviceDisconnectedError("Device not connected")
        
        try:
            # Simple ping to verify connection
            self._adb_command("shell", "echo", "ping")
        except Exception as e:
            raise DeviceDisconnectedError(f"Device connection lost: {e}")
    
    def reconnect(self, max_retries: int = 3) -> bool:
        """
        Attempt to reconnect to device.
        
        Args:
            max_retries: Maximum number of reconnection attempts.
            
        Returns:
            True if reconnection successful, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                time.sleep(1)  # Wait before retry
                self._verify_connection()
                return True
            except DeviceDisconnectedError:
                if attempt < max_retries - 1:
                    continue
                return False
        return False
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get device screen dimensions.
        
        Returns:
            Tuple of (width, height) in pixels.
            
        Raises:
            DeviceDisconnectedError: If device is not connected.
        """
        self._verify_connection()
        
        try:
            # Use wm size command
            output = self._adb_command("shell", "wm", "size")
            # Output format: "Physical size: 1080x1920"
            size_str = output.strip().split(":")[-1].strip()
            width, height = map(int, size_str.split("x"))
            return width, height
        except Exception as e:
            raise DeviceDisconnectedError(f"Failed to get screen size: {e}")
    
    def capture_screenshot(self, format: str = "pil", use_cache: bool = False) -> Any:
        """
        Capture device screenshot.
        
        Args:
            format: Output format - "pil" for PIL Image, "bytes" for raw PNG bytes.
            use_cache: If True, return cached screenshot if available.
            
        Returns:
            PIL Image or bytes depending on format parameter.
            
        Raises:
            ScreenshotError: If screenshot capture fails.
        """
        if use_cache and self._screenshot_cache:
            img_bytes = self._screenshot_cache
        else:
            self._verify_connection()
            
            try:
                # Capture screenshot using adb exec-out screencap
                img_bytes = self._adb_command_bytes("exec-out", "screencap", "-p")
                self._screenshot_cache = img_bytes
            except Exception as e:
                # Retry once
                try:
                    time.sleep(0.5)
                    img_bytes = self._adb_command_bytes("exec-out", "screencap", "-p")
                    self._screenshot_cache = img_bytes
                except Exception as retry_error:
                    raise ScreenshotError(f"Failed to capture screenshot: {retry_error}")
        
        if format == "bytes":
            return img_bytes
        elif format == "pil":
            try:
                return Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                raise ScreenshotError(f"Failed to convert screenshot to PIL Image: {e}")
        else:
            raise ValueError(f"Invalid format: {format}. Use 'pil' or 'bytes'.")
    
    def tap(self, x: int, y: int) -> None:
        """
        Execute tap action at specified coordinates.
        
        Args:
            x: X coordinate in pixels.
            y: Y coordinate in pixels.
            
        Raises:
            ValueError: If coordinates are out of bounds.
            ActionExecutionError: If tap execution fails.
        """
        if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
            raise ValueError(
                f"Coordinates ({x}, {y}) out of bounds. "
                f"Screen size: {self.screen_width}x{self.screen_height}"
            )
        
        self._verify_connection()
        
        try:
            self._adb_command("shell", "input", "tap", str(x), str(y))
            # Clear screenshot cache after action
            self._screenshot_cache = None
        except Exception as e:
            raise ActionExecutionError(f"Failed to execute tap at ({x}, {y}): {e}")
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """
        Execute swipe gesture.
        
        Args:
            x1: Start X coordinate in pixels.
            y1: Start Y coordinate in pixels.
            x2: End X coordinate in pixels.
            y2: End Y coordinate in pixels.
            duration: Swipe duration in milliseconds.
            
        Raises:
            ValueError: If coordinates are out of bounds.
            ActionExecutionError: If swipe execution fails.
        """
        for x, y in [(x1, y1), (x2, y2)]:
            if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
                raise ValueError(
                    f"Coordinates ({x}, {y}) out of bounds. "
                    f"Screen size: {self.screen_width}x{self.screen_height}"
                )
        
        self._verify_connection()
        
        try:
            self._adb_command("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration))
            self._screenshot_cache = None
        except Exception as e:
            raise ActionExecutionError(f"Failed to execute swipe: {e}")
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> None:
        """
        Execute long press at specified coordinates.
        
        Args:
            x: X coordinate in pixels.
            y: Y coordinate in pixels.
            duration: Press duration in milliseconds.
            
        Raises:
            ValueError: If coordinates are out of bounds.
            ActionExecutionError: If long press execution fails.
        """
        # Long press is implemented as swipe with same start/end coordinates
        self.swipe(x, y, x, y, duration)
    
    def type_text(self, text: str) -> tuple:
        """
        Type text into focused input field.
        
        For non-ASCII text (like Chinese), uses ADB Keyboard if installed.
        
        Args:
            text: Text to type.
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not text:
            return True, ""
        
        self._verify_connection()
        
        import base64
        
        # Check for non-ASCII characters
        is_ascii = all(ord(c) < 128 for c in text)
        
        if not is_ascii:
            # Check if ADB Keyboard is installed
            if not self.is_app_installed("com.android.adbkeyboard"):
                error_msg = (
                    f"Cannot type non-ASCII text '{text}': "
                    f"ADBKeyBoard is not installed. "
                    f"Please install from https://github.com/senzhk/ADBKeyBoard"
                )
                return False, error_msg
            
            # For non-ASCII (e.g. Chinese), use ADB Keyboard broadcast
            try:
                # Ensure ADB Keyboard is enabled and set as default
                self._adb_command("shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME")
                self._adb_command("shell", "ime", "set", "com.android.adbkeyboard/.AdbIME")
                
                b64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                self._adb_command(
                    "shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_text
                )
                self._screenshot_cache = None
                return True, ""
            except Exception as e:
                error_msg = f"Failed to send non-ASCII text via broadcast: {e}"
                return False, error_msg
        
        # For ASCII text
        try:
            # Escape special characters for shell
            escaped = text.replace(" ", "%s").replace("\'", r"\'").replace('\"', r'\"').replace("(", r"\(").replace(")", r"\)").replace("&", r"\&")
            self._adb_command("shell", "input", "text", escaped)
            self._screenshot_cache = None
            return True, ""
        except Exception as e:
            error_msg = f"Error typing text: {e}"
            return False, error_msg
    
    def press_back(self) -> None:
        """Press back button (KEYCODE_BACK = 4)."""
        self._execute_keyevent(4, "back")
    
    def press_home(self) -> None:
        """Press home button (KEYCODE_HOME = 3)."""
        self._execute_keyevent(3, "home")
    
    def press_recent(self) -> None:
        """Press recent apps button (KEYCODE_APP_SWITCH = 187)."""
        self._execute_keyevent(187, "recent apps")
    
    def _execute_keyevent(self, keycode: int, name: str) -> None:
        """
        Execute keyevent command.
        
        Args:
            keycode: Android keycode number.
            name: Human-readable name for error messages.
        """
        self._verify_connection()
        
        try:
            self._adb_command("shell", "input", "keyevent", str(keycode))
            self._screenshot_cache = None
        except Exception as e:
            raise ActionExecutionError(f"Failed to press {name}: {e}")
    
    def launch_app(self, package_name: str) -> None:
        """
        Launch app by package name.
        
        Args:
            package_name: Android package name (e.g., "com.android.chrome").
            
        Raises:
            ActionExecutionError: If app launch fails.
        """
        self._verify_connection()
        
        try:
            # Launch app using monkey command
            self._adb_command("shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            time.sleep(2)  # Wait for app to load
            self._screenshot_cache = None
        except Exception as e:
            raise ActionExecutionError(f"Failed to launch app {package_name}: {e}")
    
    def get_device_info(self) -> Dict[str, str]:
        """
        Get device information.
        
        Returns:
            Dict with keys: model, android_version, api_level, serial.
        """
        self._verify_connection()
        
        try:
            model = self._adb_command("shell", "getprop", "ro.product.model")
            version = self._adb_command("shell", "getprop", "ro.build.version.release")
            api_level = self._adb_command("shell", "getprop", "ro.build.version.sdk")
            
            return {
                "model": model,
                "android_version": version,
                "api_level": api_level,
                "serial": self.device_serial,
            }
        except Exception:
            return {
                "model": "Unknown",
                "android_version": "Unknown",
                "api_level": "Unknown",
                "serial": self.device_serial or "Unknown",
            }
    
    def is_app_installed(self, package_name: str) -> bool:
        """
        Check if app is installed.
        
        Args:
            package_name: Android package name.
            
        Returns:
            True if app is installed, False otherwise.
        """
        self._verify_connection()
        
        try:
            output = self._adb_command("shell", "pm", "list", "packages")
            return package_name in output
        except Exception:
            return False
    
    def get_current_activity(self) -> Tuple[str, str]:
        """
        Get current foreground activity.
        
        Returns:
            Tuple of (package_name, activity_name).
        """
        self._verify_connection()
        
        try:
            output = self._adb_command("shell", "dumpsys", "window", "windows")
            # Parse output like: mCurrentFocus=Window{abc123 u0 com.example.app/com.example.MainActivity}
            for line in output.split('\n'):
                if 'mCurrentFocus' in line and "/" in line:
                    parts = line.split("/")
                    package = parts[0].split()[-1]
                    activity = parts[1].split("}")[0]
                    return package, activity
            return "Unknown", "Unknown"
        except Exception:
            return "Unknown", "Unknown"
