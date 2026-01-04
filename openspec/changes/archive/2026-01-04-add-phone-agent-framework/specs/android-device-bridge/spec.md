## ADDED Requirements

### Requirement: ADB Device Connection Management
The Android Device Bridge SHALL manage connections to Android devices via ADB protocol, supporting both USB and network connections.

#### Scenario: Auto-detect single connected device
- **WHEN** exactly one Android device is connected via USB
- **THEN** DeviceBridge automatically connects to that device without requiring serial number
- **AND** retrieves device information (model, Android version, screen size)
- **AND** establishes a persistent connection for subsequent operations

#### Scenario: Multiple devices require explicit selection
- **WHEN** multiple Android devices are connected
- **THEN** DeviceBridge raises an error listing all available devices with serial numbers
- **AND** prompts user to specify device via `--device-serial` or config
- **AND** does not proceed until a single device is selected

#### Scenario: Connect via WiFi ADB
- **WHEN** user specifies device IP address (e.g., `192.168.1.100:5555`)
- **THEN** DeviceBridge attempts to connect via network ADB
- **AND** validates device authorization (may require initial USB pairing)
- **AND** falls back to USB if network connection fails

#### Scenario: Connection health monitoring
- **WHEN** device connection is established
- **THEN** DeviceBridge periodically checks connection health (every 5s or before each action)
- **AND** automatically reconnects if connection drops (up to 3 retry attempts)
- **AND** raises ConnectionError if reconnection fails after retries

### Requirement: Screenshot Capture
The Device Bridge SHALL capture device screenshots in multiple formats suitable for agent processing.

#### Scenario: Capture screenshot as PIL Image
- **WHEN** `capture_screenshot()` is called
- **THEN** executes ADB screencap command
- **AND** returns screenshot as PIL Image object
- **AND** caches image in memory for efficiency
- **AND** completes within 500ms on typical device

#### Scenario: Capture screenshot as bytes
- **WHEN** `capture_screenshot(format='bytes')` is called
- **THEN** returns screenshot as raw PNG bytes
- **AND** maintains original quality without re-encoding
- **AND** suitable for direct agent ingestion

#### Scenario: Screenshot optimization
- **WHEN** device screen resolution exceeds 1080p
- **THEN** optionally downscales to 1080p to reduce latency
- **AND** preserves aspect ratio
- **AND** can be disabled via `preserve_resolution=True` parameter

#### Scenario: Handle screenshot capture failures
- **WHEN** screencap command fails (e.g., permission issue, device locked)
- **THEN** retries up to 2 times with 1s delay
- **AND** raises ScreenshotError with specific failure reason
- **AND** suggests fixes (unlock screen, grant permissions)

### Requirement: Touch and Gesture Actions
The Device Bridge SHALL execute touch-based actions at specified coordinates with pixel-perfect accuracy.

#### Scenario: Execute tap action
- **WHEN** `tap(x=512, y=800)` is called on a 1080x1920 device
- **THEN** sends ADB input tap command at exact coordinates
- **AND** completes within 100ms
- **AND** validates coordinates are within screen bounds
- **AND** raises ValueError if coordinates are out of bounds

#### Scenario: Execute swipe gesture
- **WHEN** `swipe(x1=100, y1=500, x2=100, y2=200, duration=300)` is called
- **THEN** sends ADB swipe command with specified start/end points and duration
- **AND** duration controls swipe speed (in milliseconds)
- **AND** validates all coordinates are within screen bounds
- **AND** completes swipe smoothly without jumps

#### Scenario: Execute long press
- **WHEN** `long_press(x=400, y=600, duration=1000)` is called
- **THEN** simulates tap-and-hold for specified duration (default 1000ms)
- **AND** implemented as `input swipe x y x y duration`
- **AND** useful for context menus and drag operations

#### Scenario: Coordinate validation
- **WHEN** any action receives coordinates
- **THEN** validates x is between 0 and screen_width
- **AND** validates y is between 0 and screen_height
- **AND** raises ValueError with actionable message if invalid

### Requirement: Text Input
The Device Bridge SHALL support text entry via ADB input methods with proper encoding.

#### Scenario: Type English text
- **WHEN** `type_text("Hello World")` is called
- **THEN** sends ADB input text command with properly escaped text
- **AND** handles spaces and special characters correctly
- **AND** text appears in focused input field

#### Scenario: Type Chinese text
- **WHEN** `type_text("你好世界")` is called
- **THEN** encodes text in UTF-8 for ADB transmission
- **AND** uses ADB broadcast input method for unicode support
- **AND** text appears correctly in input field

#### Scenario: Type special characters
- **WHEN** `type_text("test@example.com")` with special chars is called
- **THEN** escapes shell special characters (@, $, &, etc.)
- **AND** transmits text without corruption
- **AND** handles common symbols (., _, -, @)

#### Scenario: Clear text field
- **WHEN** `clear_text(char_count=20)` is called
- **THEN** sends backspace keyevents to delete specified number of characters
- **AND** default clears 100 characters if count not specified
- **AND** performed rapidly (multiple backspaces per second)

### Requirement: Navigation Actions
The Device Bridge SHALL provide system-level navigation actions (back, home, recent apps).

#### Scenario: Press back button
- **WHEN** `press_back()` is called
- **THEN** sends ADB keyevent KEYCODE_BACK (4)
- **AND** navigates to previous screen/activity
- **AND** completes within 50ms

#### Scenario: Press home button
- **WHEN** `press_home()` is called
- **THEN** sends ADB keyevent KEYCODE_HOME (3)
- **AND** returns to device home screen
- **AND** minimizes current app

#### Scenario: Open recent apps
- **WHEN** `press_recent()` is called
- **THEN** sends ADB keyevent KEYCODE_APP_SWITCH (187)
- **AND** opens recent apps overview screen
- **AND** allows task switching

#### Scenario: Open app by package name
- **WHEN** `launch_app("com.xiaohongshu.app")` is called
- **THEN** uses ADB monkey command to launch app by package
- **AND** waits for app to fully load (3s default timeout)
- **AND** raises AppLaunchError if app not installed

### Requirement: Device Information Retrieval
The Device Bridge SHALL retrieve device properties and state information for decision-making.

#### Scenario: Get screen dimensions
- **WHEN** `get_screen_size()` is called
- **THEN** executes ADB wm size command
- **AND** returns tuple of (width, height) as integers
- **AND** caches result for subsequent calls (screen size rarely changes)

#### Scenario: Get device model and version
- **WHEN** `get_device_info()` is called
- **THEN** retrieves device model via `getprop ro.product.model`
- **AND** retrieves Android version via `getprop ro.build.version.release`
- **AND** returns structured dict with model, version, API level

#### Scenario: Check app installation
- **WHEN** `is_app_installed("com.xiaohongshu.app")` is called
- **THEN** queries package manager via ADB pm list packages
- **AND** returns True if package is found, False otherwise
- **AND** caches result for performance

#### Scenario: Get current activity
- **WHEN** `get_current_activity()` is called
- **THEN** executes ADB dumpsys window command
- **AND** parses output to extract current foreground activity
- **AND** returns package name and activity name as tuple

### Requirement: Accessibility Tree Capture (Optional)
The Device Bridge SHALL optionally capture UI hierarchy via accessibility services for richer context.

#### Scenario: Capture UI hierarchy XML
- **WHEN** `capture_ui_hierarchy()` is called with accessibility enabled
- **THEN** executes ADB uiautomator dump command
- **AND** retrieves XML file from device
- **AND** parses XML into structured dict format
- **AND** completes within 200-500ms (slower than screenshot)

#### Scenario: Accessibility service disabled
- **WHEN** `capture_ui_hierarchy()` is called but accessibility services are off
- **THEN** returns None or empty dict (graceful degradation)
- **AND** logs warning about missing accessibility data
- **AND** does not block execution

#### Scenario: Parse UI elements
- **WHEN** UI hierarchy XML is retrieved
- **THEN** extracts element attributes (text, class, bounds, clickable)
- **AND** flattens hierarchy into list of elements with coordinates
- **AND** provides element filtering by attributes

### Requirement: Error Handling and Resilience
The Device Bridge SHALL handle ADB errors gracefully and provide actionable error messages.

#### Scenario: Device unauthorized
- **WHEN** USB debugging authorization is not granted
- **THEN** raises DeviceUnauthorizedError with clear message
- **AND** instructs user to check phone screen for authorization popup
- **AND** waits up to 30s for user to grant permission

#### Scenario: ADB server not running
- **WHEN** ADB daemon is not running on host machine
- **THEN** attempts to start ADB server automatically
- **AND** retries connection after server starts
- **AND** raises ADBNotFoundError if ADB binary is not in PATH

#### Scenario: Command timeout
- **WHEN** ADB command takes longer than timeout (default 10s)
- **THEN** kills the hung process
- **AND** raises CommandTimeoutError with command details
- **AND** suggests checking device responsiveness

#### Scenario: Device disconnection during operation
- **WHEN** device disconnects mid-operation (cable unplugged, etc.)
- **THEN** immediately raises DeviceDisconnectedError
- **AND** saves state before disconnection if possible
- **AND** allows graceful recovery on reconnection
