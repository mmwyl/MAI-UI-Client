## ADDED Requirements

### Requirement: Agent-Device Adapter
The Integration Layer SHALL provide an adapter that connects MAI-UI agent predictions with device bridge actions seamlessly.

#### Scenario: Initialize integration with agent and device
- **WHEN** `AgentIntegration(agent, device_bridge)` is instantiated
- **THEN** validates agent has `predict()` method
- **AND** validates device_bridge has required action methods
- **AND** retrieves device screen size for coordinate transformation
- **AND** initializes internal state (trajectory, step counter)

#### Scenario: End-to-end prediction to action flow
- **WHEN** `integration.execute_step(instruction, observation)` is called
- **THEN** formats observation for agent compatibility
- **AND** calls agent.predict(instruction, observation)
- **AND** parses prediction response into thinking and action dict
- **AND** validates and executes action via device bridge
- **AND** returns execution result with updated observation

#### Scenario: Support multiple agent types
- **WHEN** integration is initialized with `MAIUINaivigationAgent`
- **THEN** uses navigation agent's specific response format
- **AND** when initialized with `MAIGroundingAgent`
- **THEN** adapts to grounding-specific prediction format
- **AND** provides unified interface regardless of agent type

### Requirement: Coordinate Transformation
The Integration Layer SHALL convert between normalized agent coordinates [0, 1] and device pixel coordinates.

#### Scenario: Transform normalized tap coordinate
- **WHEN** agent outputs `{"action": "tap", "coordinate": [0.5, 0.3]}`
- **THEN** retrieves device screen size (e.g., 1080x1920)
- **AND** calculates pixel coordinates: x = 0.5 * 1080 = 540, y = 0.3 * 1920 = 576
- **AND** passes (540, 576) to device_bridge.tap()

#### Scenario: Transform swipe coordinates
- **WHEN** agent outputs `{"action": "swipe", "start": [0.5, 0.8], "end": [0.5, 0.2]}`
- **THEN** transforms both start and end points to pixels
- **AND** maintains gesture direction and distance correctly
- **AND** passes pixel coordinates to device_bridge.swipe()

#### Scenario: Handle edge coordinates
- **WHEN** agent outputs coordinate [1.0, 1.0] (bottom-right corner)
- **THEN** maps to (screen_width - 1, screen_height - 1)
- **AND** ensures coordinate stays within valid bounds
- **AND** prevents out-of-bounds errors

#### Scenario: Inverse transformation for grounding
- **WHEN** grounding agent needs to output coordinates given pixel location
- **THEN** provides inverse transform: pixel → normalized
- **AND** divides by screen dimensions: norm_x = pixel_x / width
- **AND** ensures output is in [0, 1] range

### Requirement: Action Parsing and Validation
The Integration Layer SHALL parse agent predictions into structured action dictionaries and validate their correctness.

#### Scenario: Parse action from XML-tagged response
- **WHEN** agent returns text with `<thinking>...</thinking><tool_call>{"action": "tap", ...}</tool_call>`
- **THEN** extracts thinking text from thinking tags
- **AND** parses JSON from tool_call tags
- **AND** validates JSON structure (must have "action" key)
- **AND** returns tuple of (thinking, action_dict)

#### Scenario: Validate action type
- **WHEN** parsed action dict is `{"action": "tap", "coordinate": [0.5, 0.3]}`
- **THEN** validates "action" is in allowed list: [tap, swipe, type, back, home, recent, long_press, FINISH, ask_user, mcp_call]
- **AND** raises ValidationError if action type is unknown
- **AND** provides suggestion for similar valid action names

#### Scenario: Validate action parameters
- **WHEN** action is "tap"
- **THEN** validates "coordinate" field exists and is [x, y] list
- **AND** validates both x and y are numeric and in [0, 1] range
- **WHEN** action is "swipe"
- **THEN** validates "start" and "end" coordinates exist
- **AND** optionally validates "duration" is positive integer
- **WHEN** action is "type"
- **THEN** validates "text" field exists and is non-empty string

#### Scenario: Handle malformed JSON
- **WHEN** tool_call tag contains invalid JSON
- **THEN** logs error with raw content for debugging
- **AND** raises JSONParseError with helpful message
- **AND** optionally retries agent prediction to self-correct
- **AND** includes position of JSON syntax error if possible

### Requirement: Observation Formatting
The Integration Layer SHALL format device state into observations compatible with agent input requirements.

#### Scenario: Format screenshot for agent
- **WHEN** device screenshot is captured as PIL Image
- **THEN** checks agent's expected format (PIL Image or bytes)
- **AND** converts if necessary (Image → bytes or bytes → Image)
- **AND** includes in observation dict as `{"screenshot": <formatted>}`

#### Scenario: Include accessibility tree
- **WHEN** UI hierarchy is available and agent supports it
- **THEN** formats accessibility tree into structured dict
- **AND** includes element coordinates, text, class names
- **AND** adds to observation as `{"accessibility_tree": {...}}`
- **AND** omits if tree capture failed (graceful degradation)

#### Scenario: Inject tool call results
- **WHEN** previous step was `ask_user` or `mcp_call`
- **THEN** includes tool result in next observation
- **AND** formats as `{"tool_result": {"tool": "ask_user", "result": "user response"}}`
- **AND** allows agent to use result for next prediction

#### Scenario: Add execution metadata
- **WHEN** configured to include metadata
- **THEN** adds step_count, max_steps, elapsed_time to observation
- **AND** allows agent to self-regulate (e.g., speed up or FINISH early)
- **AND** configured via `include_metadata=True` parameter

### Requirement: Error Mapping and User Feedback
The Integration Layer SHALL translate technical errors into user-friendly messages with actionable guidance.

#### Scenario: Map device connection error
- **WHEN** device_bridge raises `DeviceDisconnectedError`
- **THEN** wraps in user-friendly message: "Device disconnected. Please check USB connection."
- **AND** suggests specific fixes: "Try: 1) Replug USB cable, 2) Run `mai-phone devices`, 3) Restart ADB server"
- **AND** preserves original exception for debugging

#### Scenario: Map agent timeout error
- **WHEN** agent.predict() times out after 30s
- **THEN** creates message: "Model is not responding. Check if model server is running at <URL>."
- **AND** suggests: "Run `mai-phone doctor` to diagnose model connection"
- **AND** includes timeout value for reference

#### Scenario: Map coordinate out of bounds
- **WHEN** action validation finds coordinate outside [0, 1]
- **THEN** shows error: "Agent predicted invalid coordinate: [1.2, 0.5]. Coordinates must be in [0, 1] range."
- **AND** explains this is likely a model issue
- **AND** suggests checking model version compatibility

#### Scenario: Collect error context
- **WHEN** any error occurs
- **THEN** captures current screenshot (if available)
- **AND** saves to error log directory
- **AND** includes screenshot path in error message
- **AND** adds step number, action attempted, timestamp

### Requirement: Logging and Telemetry
The Integration Layer SHALL provide detailed logging for debugging and performance analysis.

#### Scenario: Log each prediction
- **WHEN** agent makes a prediction
- **THEN** logs thinking text at INFO level
- **AND** logs action JSON at DEBUG level
- **AND** includes agent model name, step number, timestamp
- **AND** formatted for easy reading in logs

#### Scenario: Log action execution
- **WHEN** action is dispatched to device
- **THEN** logs action type and key parameters (e.g., "Tapping at (540, 800)")
- **AND** logs execution time for performance tracking
- **AND** logs success/failure status
- **AND** includes any retry attempts

#### Scenario: Performance metrics collection
- **WHEN** step completes
- **THEN** records latency breakdown: screenshot (ms), agent inference (ms), action execution (ms)
- **AND** aggregates over entire task for summary
- **AND** optionally exports to metrics file (CSV or JSON)
- **AND** useful for optimization and benchmark comparisons

#### Scenario: Debug mode verbose logging
- **WHEN** integration is initialized with `debug=True`
- **THEN** enables TRACE level logging for all operations
- **AND** logs raw agent responses before parsing
- **AND** logs device commands sent via ADB
- **AND** saves intermediary states for deep debugging

### Requirement: Trajectory Integration
The Integration Layer SHALL coordinate with agent's trajectory memory system for multi-turn context.

#### Scenario: Sync trajectory with agent
- **WHEN** action is executed successfully
- **THEN** creates TrajStep with all relevant data
- **AND** adds to agent's trajectory memory via agent.traj_memory.steps.append()
- **AND** ensures agent has access to history for next prediction
- **AND** maintains consistency between agent memory and integration's trajectory

#### Scenario: Load existing trajectory
- **WHEN** resuming a task from saved trajectory
- **THEN** loads trajectory JSON from file
- **AND** reconstructs TrajMemory object
- **AND** calls agent.load_traj(trajectory)
- **AND** resets integration state to match loaded trajectory

#### Scenario: Export merged trajectory
- **WHEN** task completes
- **THEN** merges agent's internal trajectory with integration's execution logs
- **AND** includes all fields: thinking, action, screenshot, device state, timing
- **AND** exports as comprehensive JSON suitable for replay
- **AND** validates trajectory completeness before export

### Requirement: Extensibility and Custom Actions
The Integration Layer SHALL support extending action types and adding custom execution logic.

#### Scenario: Register custom action handler
- **WHEN** user registers custom action via `integration.register_action("custom_tap", handler_fn)`
- **THEN** adds action to allowed list
- **AND** routes "custom_tap" actions to handler_fn
- **AND** handler receives normalized parameters and device bridge
- **AND** allows domain-specific actions (e.g., "select_from_picker")

#### Scenario: Middleware injection
- **WHEN** user configures middleware via `integration.add_middleware(fn)`
- **THEN** calls middleware before/after each action
- **AND** middleware can modify observation, action, or skip execution
- **AND** useful for logging, monitoring, or conditional logic
- **AND** multiple middlewares execute in order of registration

#### Scenario: Custom coordinate transformation
- **WHEN** user provides custom transform via `integration.set_coordinate_transform(fn)`
- **THEN** uses custom function instead of default linear scaling
- **AND** useful for non-uniform scaling or aspect ratio handling
- **AND** function signature: fn(normalized_coords, screen_size) → pixel_coords

### Requirement: Multi-Agent Support
The Integration Layer SHALL support orchestrating multiple agents (e.g., grounding assist + navigation).

#### Scenario: Fallback to grounding agent
- **WHEN** navigation agent prediction fails or confidence is low
- **THEN** optionally invokes grounding agent to locate target element
- **AND** uses grounding result to refine navigation action
- **AND** logs agent switching for analysis

#### Scenario: Agent chain execution
- **WHEN** configured with agent chain: [preprocessing_agent, main_agent, validation_agent]
- **THEN** passes observation through chain sequentially
- **AND** each agent can modify observation or override action
- **AND** final action is result of chain consensus
- **AND** useful for ensemble or specialized agent compositions
