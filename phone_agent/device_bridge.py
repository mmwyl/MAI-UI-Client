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
import time
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image
import adbutils


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
            adb_server_host: ADB server host address.
            adb_server_port: ADB server port.
            
        Raises:
            DeviceNotFoundError: If no device found or multiple devices without serial specified.
        """
        self.adb = adbutils.AdbClient(host=adb_server_host, port=adb_server_port)
        self.device: Optional[adbutils.AdbDevice] = None
        self.screen_width: int = 0
        self.screen_height: int = 0
        self._screenshot_cache: Optional[bytes] = None
        
        self.connect(device_serial)
    
    def list_devices(self) -> List[Dict[str, str]]:
        """
        List all connected Android devices.
        
        Returns:
            List of device info dicts with keys: serial, state, model, android_version.
        """
        devices = []
        for device in self.adb.device_list():
            try:
                info = {
                    "serial": device.serial,
                    "state": device.state,
                }
                # Try to get additional info if device is online
                if device.state == "device":
                    try:
                        info["model"] = device.prop.get("ro.product.model", "Unknown")
                        info["android_version"] = device.prop.get("ro.build.version.release", "Unknown")
                    except:
                        info["model"] = "Unknown"
                        info["android_version"] = "Unknown"
                else:
                    info["model"] = "N/A"
                    info["android_version"] = "N/A"
                devices.append(info)
            except Exception:
                # Skip devices that can't be queried
                continue
        return devices
    
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
            devices = self.adb.device_list()
            
            if not devices:
                raise DeviceNotFoundError(
                    "No Android devices found. Please connect a device via USB and enable USB debugging."
                )
            
            if device_serial:
                # Connect to specific device
                self.device = self.adb.device(serial=device_serial)
            else:
                # Auto-detect single device
                if len(devices) == 1:
                    self.device = devices[0]
                else:
                    device_list_str = "\n".join([f"  - {d.serial}" for d in devices])
                    raise DeviceNotFoundError(
                        f"Multiple devices found. Please specify device serial:\n{device_list_str}\n"
                        f"Use --device-serial <serial> flag."
                    )
            
            # Verify connection and get screen size
            self._verify_connection()
            self.screen_width, self.screen_height = self.get_screen_size()
            
        except adbutils.AdbError as e:
            raise DeviceDisconnectedError(f"Failed to connect to device: {e}")
    
    def _verify_connection(self) -> None:
        """Verify device connection is healthy."""
        if not self.device:
            raise DeviceDisconnectedError("Device not connected")
        
        try:
            # Simple ping to verify connection
            self.device.shell("echo ping")
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
            output = self.device.shell("wm size")
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
                # Capture screenshot using adbutils
                img_bytes = self.device.screenshot()
                self._screenshot_cache = img_bytes
            except Exception as e:
                # Retry once
                try:
                    time.sleep(0.5)
                    img_bytes = self.device.screenshot()
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
            self.device.shell(f"input tap {x} {y}")
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
            self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
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
    
    def type_text(self, text: str) -> None:
        """
        Type text into focused input field.
        
        Args:
            text: Text to type.
            
        Raises:
            ActionExecutionError: If text input fails.
        """
        self._verify_connection()
        
        try:
            # Escape special characters for shell
            escaped_text = text.replace(" ", "%s").replace("&", "\\&")
            self.device.shell(f"input text {escaped_text}")
            self._screenshot_cache = None
        except Exception as e:
            raise ActionExecutionError(f"Failed to type text: {e}")
    
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
            self.device.shell(f"input keyevent {keycode}")
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
            self.device.app_start(package_name)
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
            return {
                "model": self.device.prop.get("ro.product.model", "Unknown"),
                "android_version": self.device.prop.get("ro.build.version.release", "Unknown"),
                "api_level": self.device.prop.get("ro.build.version.sdk", "Unknown"),
                "serial": self.device.serial,
            }
        except Exception:
            return {
                "model": "Unknown",
                "android_version": "Unknown",
                "api_level": "Unknown",
                "serial": self.device.serial if self.device else "Unknown",
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
            output = self.device.shell(f"pm list packages | grep {package_name}")
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
            output = self.device.shell("dumpsys window windows | grep mCurrentFocus")
            # Parse output like: mCurrentFocus=Window{abc123 u0 com.example.app/com.example.MainActivity}
            if "/" in output:
                parts = output.split("/")
                package = parts[0].split()[-1]
                activity = parts[1].split("}")[0]
                return package, activity
            return "Unknown", "Unknown"
        except Exception:
            return "Unknown", "Unknown"
