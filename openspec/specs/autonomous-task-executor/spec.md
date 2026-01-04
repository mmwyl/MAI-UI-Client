# autonomous-task-executor Specification

## Purpose
TBD - created by archiving change add-phone-agent-framework. Update Purpose after archive.
## Requirements
### Requirement: Autonomous Execution Loop
The Task Executor SHALL orchestrate multi-step task execution by repeatedly invoking the agent and executing predicted actions until completion.

#### Scenario: Execute multi-step task to completion
- **WHEN** executor is initialized with instruction "open app and search for item"
- **THEN** enters loop: capture observation → agent.predict() → execute action
- **AND** continues until agent outputs `{"action": "FINISH"}` or max steps reached
- **AND** tracks all steps in trajectory for replay and debugging
- **AND** returns execution summary with status, steps taken, and duration

#### Scenario: Terminate on FINISH action
- **WHEN** agent outputs `{"action": "FINISH", "reason": "Task completed successfully"}`
- **THEN** executor stops loop immediately
- **AND** marks task as successful in trajectory
- **AND** logs completion reason
- **AND** does not execute any further actions

#### Scenario: Terminate on max steps limit
- **WHEN** executor reaches max_steps (default 50) without FINISH
- **THEN** stops execution loop
- **AND** marks task as incomplete/timeout in trajectory
- **AND** saves partial progress up to step limit
- **AND** logs warning about potential infinite loop

#### Scenario: Progress tracking during execution
- **WHEN** task is executing
- **THEN** updates step counter after each action
- **AND** emits progress events (callbacks or logging) for UI updates
- **AND** includes current step, total steps attempted, last action, agent thinking
- **AND** estimates remaining time based on average step duration

### Requirement: Observation Construction
The Executor SHALL build structured observations from device state to pass to the agent for prediction.

#### Scenario: Construct basic observation
- **WHEN** executor needs observation for next prediction
- **THEN** captures screenshot from device bridge
- **AND** constructs dict with `{"screenshot": <PIL Image or bytes>}`
- **AND** optionally includes `"accessibility_tree"` if enabled
- **AND** passes observation to agent.predict() method

#### Scenario: Include step count in observation
- **WHEN** building observation
- **THEN** optionally includes `"step_count"` and `"max_steps"` in observation
- **AND** allows agent to self-regulate (e.g., decide to FINISH early)
- **AND** configured via `include_step_info=True` parameter

#### Scenario: Observation caching
- **WHEN** action fails and retries are needed
- **THEN** reuses cached screenshot instead of re-capturing
- **AND** only re-captures on successful action execution
- **AND** reduces latency and device load

#### Scenario: Accessibility tree enrichment
- **WHEN** `use_accessibility_tree=True` is configured
- **THEN** captures UI hierarchy in addition to screenshot
- **AND** parses hierarchy into structured format
- **AND** includes in observation dict as `"accessibility_tree"`
- **AND** gracefully handles capture failures (omit tree, continue with screenshot only)

### Requirement: Action Dispatch and Execution
The Executor SHALL parse agent predictions and dispatch appropriate actions to the device bridge.

#### Scenario: Execute tap action
- **WHEN** agent predicts `{"action": "tap", "coordinate": [0.5, 0.3]}`
- **THEN** normalizes coordinate from [0,1] to pixel coordinates
- **AND** calls device_bridge.tap(x, y)
- **AND** waits for action completion and screen settle (default 0.5s)
- **AND** logs action details to trajectory

#### Scenario: Execute swipe action
- **WHEN** agent predicts `{"action": "swipe", "start": [0.5, 0.8], "end": [0.5, 0.2], "duration": 300}`
- **THEN** normalizes start and end coordinates
- **AND** calls device_bridge.swipe(x1, y1, x2, y2, duration)
- **AND** waits for swipe animation to complete
- **AND** captures screenshot after gesture

#### Scenario: Execute type action
- **WHEN** agent predicts `{"action": "type", "text": "search query"}`
- **THEN** calls device_bridge.type_text(text)
- **AND** handles unicode and special characters properly
- **AND** waits for text input to register (0.3s delay)
- **AND** verifies text was entered if possible

#### Scenario: Execute navigation action
- **WHEN** agent predicts `{"action": "back"}`, `{"action": "home"}`, or `{"action": "recent"}`
- **THEN** calls corresponding device_bridge method
- **AND** waits for navigation transition (0.8s for back/home)
- **AND** captures new screen state after navigation

#### Scenario: Invalid action handling
- **WHEN** agent outputs unrecognized action type
- **THEN** logs error with action details
- **AND** raises ActionValidationError with allowed action types
- **AND** optionally retries with same observation (agent may self-correct)
- **AND** counts toward max_steps limit

### Requirement: Tool Call Routing
The Executor SHALL handle special tool call actions (`ask_user`, `mcp_call`) by routing to appropriate handlers.

#### Scenario: Handle ask_user tool call
- **WHEN** agent predicts `{"action": "ask_user", "question": "Which option do you prefer?"}`
- **THEN** pauses execution and invokes user_prompt_handler(question)
- **AND** waits for user input with configurable timeout (default 120s)
- **AND** injects user response into next observation or trajectory
- **AND** resumes execution with updated context

#### Scenario: Handle mcp_call tool call
- **WHEN** agent predicts `{"action": "mcp_call", "tool": "amap_search", "args": {"query": "coffee shop"}}`
- **THEN** validates tool exists in MCP registry
- **AND** invokes mcp_handler.execute(tool, args)
- **AND** captures tool result (success or error)
- **AND** injects result into agent context for next prediction

#### Scenario: Tool call timeout
- **WHEN** ask_user or mcp_call exceeds timeout
- **THEN** executor aborts the tool call
- **AND** logs timeout error with details
- **AND** optionally allows agent to retry or fallback
- **AND** prevents indefinite blocking

#### Scenario: Tool not available
- **WHEN** agent requests MCP tool that is not registered
- **THEN** executor logs error about missing tool
- **AND** returns error message to agent in next observation
- **AND** allows agent to choose alternative action
- **AND** does not crash the entire execution

### Requirement: Error Recovery and Retry Logic
The Executor SHALL implement retry mechanisms for transient failures and graceful degradation strategies.

#### Scenario: Retry failed action
- **WHEN** device action fails (e.g., tap returns error)
- **THEN** retries the same action up to max_retries (default 2)
- **AND** waits exponentially between retries (0.5s, 1s, 2s)
- **AND** re-captures screenshot before retry to check state change
- **AND** logs retry attempt details

#### Scenario: Agent prediction failure
- **WHEN** agent.predict() raises an exception (model timeout, network error)
- **THEN** retries prediction up to 2 times
- **AND** logs exception details
- **AND** if retries exhausted, marks task as failed and terminates
- **AND** saves partial trajectory for debugging

#### Scenario: Device disconnection recovery
- **WHEN** device disconnects during execution
- **THEN** attempts to reconnect (device_bridge handles)
- **AND** pauses execution for up to 30s waiting for reconnection
- **AND** resumes from last successful step if reconnected
- **AND** aborts task if reconnection fails

#### Scenario: Screen state validation
- **WHEN** action is executed
- **THEN** optionally compares before/after screenshots to detect change
- **AND** if no change detected and change was expected, marks as potential failure
- **AND** allows retry or agent re-prediction
- **AND** configured via `validate_screen_change=True`

### Requirement: Trajectory Tracking and Export
The Executor SHALL record all execution steps into a structured trajectory for replay, debugging, and analysis.

#### Scenario: Record trajectory step
- **WHEN** each action is executed
- **THEN** creates TrajStep with: screenshot, agent thinking, action, result, timestamp
- **AND** appends to executor's trajectory list
- **AND** stores screenshots as bytes for portability

#### Scenario: Export trajectory to JSON
- **WHEN** task completes (success or failure)
- **THEN** serializes trajectory to JSON format
- **AND** includes metadata: task_goal, task_id, total_steps, duration, status
- **AND** embeds screenshots as base64 strings (or references to separate files)
- **AND** saves to configured output directory

#### Scenario: Trajectory compression
- **WHEN** trajectory contains many screenshots (memory intensive)
- **THEN** optionally stores screenshots as separate PNG files
- **AND** stores only file references in JSON
- **AND** organized as: `{task_id}/trajectory.json` and `{task_id}/screenshots/*.png`

#### Scenario: Incremental trajectory saving
- **WHEN** executing long tasks (30+ steps)
- **THEN** periodically saves partial trajectory every 10 steps
- **AND** prevents data loss in case of crash or interruption
- **AND** final save overwrites with complete trajectory

### Requirement: Execution Configuration and Tuning
The Executor SHALL support configuration parameters to tune execution behavior for different scenarios.

#### Scenario: Configure step delay
- **WHEN** executor is initialized with `step_delay=1.0`
- **THEN** waits 1.0 seconds after each action before next observation
- **AND** allows animations and UI updates to complete
- **AND** prevents race conditions in fast-paced apps

#### Scenario: Configure max steps limit
- **WHEN** executor is initialized with `max_steps=100`
- **THEN** allows up to 100 action steps before timeout
- **AND** useful for complex tasks (booking, multi-app workflows)
- **AND** prevents infinite loops in poorly conditioned agents

#### Scenario: Enable/disable accessibility tree
- **WHEN** executor is initialized with `use_accessibility_tree=True`
- **THEN** includes UI hierarchy in observations
- **AND** provides richer context to agent
- **AND** trades off additional capture latency (~200ms)

#### Scenario: Configure retry behavior
- **WHEN** executor is initialized with `max_retries=3, retry_delay=1.0`
- **THEN** retries failed actions 3 times with 1s delay between attempts
- **AND** applies to both device actions and agent predictions
- **AND** allows tuning for flaky devices or networks

### Requirement: Termination Conditions and Cleanup
The Executor SHALL properly handle task termination and resource cleanup in all scenarios.

#### Scenario: Graceful shutdown on success
- **WHEN** task completes successfully (FINISH action)
- **THEN** saves final trajectory
- **AND** releases device resources (screenshots cached in memory)
- **AND** logs success summary with metrics
- **AND** returns success status to caller

#### Scenario: Graceful shutdown on failure
- **WHEN** task fails (max steps, error, disconnection)
- **THEN** saves partial trajectory with error details
- **AND** releases all resources
- **AND** logs failure details and potential causes
- **AND** returns failure status with actionable error message

#### Scenario: Interrupt handling (Ctrl+C)
- **WHEN** user presses Ctrl+C during execution
- **THEN** catches interrupt signal gracefully
- **AND** saves trajectory up to current step
- **AND** logs interruption timestamp
- **AND** exits without corrupting logs or leaving zombie processes

#### Scenario: Resource cleanup on exception
- **WHEN** unexpected exception occurs during execution
- **THEN** ensures trajectory is saved (even if incomplete)
- **AND** logs full exception stack trace
- **AND** releases device connection
- **AND** re-raises exception for caller to handle

