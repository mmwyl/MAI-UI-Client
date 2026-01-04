# phone-agent-cli Specification

## Purpose
TBD - created by archiving change add-phone-agent-framework. Update Purpose after archive.
## Requirements
### Requirement: Command-Line Task Execution
The Phone Agent CLI SHALL provide a simple command-line interface for users to execute natural language tasks on Android devices.

#### Scenario: Basic task execution
- **WHEN** user runs `mai-phone "open Xiaohongshu and search nearby food"`
- **THEN** the CLI connects to the default Android device, loads the MAI-UI agent, and executes the multi-step task autonomously
- **AND** displays progress indicators showing current step and action being performed
- **AND** saves the execution trajectory to `~/.mai-phone/logs/{task_id}/trajectory.json`

#### Scenario: Explicit device selection
- **WHEN** user runs `mai-phone --device-serial ABC123 "book train ticket"`
- **THEN** the CLI connects to the device with serial number "ABC123"
- **AND** executes the task on that specific device
- **AND** fails gracefully with clear error message if device is not found

#### Scenario: Custom model configuration
- **WHEN** user runs `mai-phone --model-url http://192.168.1.100:8000/v1 "search product"`
- **THEN** the CLI uses the specified model endpoint instead of default
- **AND** validates the connection before starting execution
- **AND** shows warning if model version differs from expected

### Requirement: Device Management Commands
The CLI SHALL provide subcommands to list, configure, and diagnose Android device connections.

#### Scenario: List connected devices
- **WHEN** user runs `mai-phone devices`
- **THEN** displays a formatted table of all ADB-connected devices
- **AND** shows device serial, model name, Android version, and connection status
- **AND** indicates which device is the default (if configured)

#### Scenario: Check system health
- **WHEN** user runs `mai-phone doctor`
- **THEN** verifies ADB installation and accessibility
- **AND** checks model endpoint connectivity and response
- **AND** validates configuration file syntax
- **AND** reports all issues with actionable fix suggestions

#### Scenario: Show version information
- **WHEN** user runs `mai-phone version`
- **THEN** displays the Phone Agent framework version
- **AND** shows MAI-UI model version (if connected)
- **AND** lists key dependency versions (adbutils, openai, etc.)

### Requirement: Configuration Management
The CLI SHALL support viewing and editing configuration through subcommands and file-based settings.

#### Scenario: View current configuration
- **WHEN** user runs `mai-phone config show`
- **THEN** displays the merged configuration (file + defaults + overrides)
- **AND** indicates source of each setting (file, env var, or default)
- **AND** masks sensitive values (API keys, credentials)

#### Scenario: Initialize configuration file
- **WHEN** user runs `mai-phone config init`
- **THEN** creates `~/.mai-phone/config.yaml` with default values
- **AND** prompts for model URL and device preferences
- **AND** does not overwrite existing config unless `--force` flag is used

#### Scenario: CLI flag overrides config file
- **WHEN** user runs `mai-phone --max-steps 100 "complex task"` and config file has `max_steps: 50`
- **THEN** the CLI uses 100 steps (command-line flag takes precedence)
- **AND** logs the override for transparency

### Requirement: Trajectory Replay and Debugging
The CLI SHALL support replaying saved trajectories for debugging and analysis.

#### Scenario: Replay saved trajectory
- **WHEN** user runs `mai-phone replay ~/.mai-phone/logs/task-123/trajectory.json`
- **THEN** displays each step's observation, thinking, and action in sequence
- **AND** shows screenshots at each step (if available)
- **AND** allows stepping through with Enter key or playing continuously

#### Scenario: Export trajectory to video
- **WHEN** user runs `mai-phone replay --export-video output.mp4 trajectory.json`
- **THEN** creates a video showing screenshots with overlay text of actions
- **AND** includes timing information and step numbers
- **AND** generates at configurable FPS (default 2 fps)

### Requirement: User Interaction Handling
The CLI SHALL provide an interactive prompt when the agent requests user input via `ask_user` tool calls.

#### Scenario: Agent asks for clarification
- **WHEN** agent outputs `{"action": "ask_user", "question": "Which train class? (1st/2nd)"}`
- **THEN** CLI pauses execution and displays the question prominently
- **AND** prompts user for text input with timeout (default 120s)
- **AND** passes user response back to agent and continues execution

#### Scenario: User cancels during prompt
- **WHEN** agent asks a question and user types "cancel" or presses Ctrl+C
- **THEN** CLI aborts the task gracefully
- **AND** saves partial trajectory up to that point
- **AND** displays summary of completed steps before cancellation

#### Scenario: User interaction timeout
- **WHEN** agent asks a question and user does not respond within timeout
- **THEN** CLI aborts the task with timeout error
- **AND** saves partial trajectory and error details
- **AND** suggests increasing timeout via `--ask-timeout` flag

### Requirement: Progress and Status Reporting
The CLI SHALL display real-time progress information during task execution.

#### Scenario: Live progress display
- **WHEN** task is executing
- **THEN** CLI shows current step number and total steps attempted
- **AND** displays last action taken (e.g., "Step 5/50: Tapped at (512, 800)")
- **AND** shows agent's thinking/reasoning for current step
- **AND** updates display without scrolling (uses carriage return or terminal manipulation)

#### Scenario: Task completion summary
- **WHEN** task completes (success or failure)
- **THEN** displays summary: total steps, duration, final status
- **AND** shows path to saved trajectory file
- **AND** provides next steps or suggestions (e.g., "Run `mai-phone replay <path>` to review")

#### Scenario: Error reporting
- **WHEN** an error occurs (device disconnected, model timeout, action failed)
- **THEN** displays error message in red with clear description
- **AND** shows error screenshot path if available
- **AND** suggests recovery actions (e.g., "Check USB connection and retry")
- **AND** includes error code for documentation lookup

### Requirement: Command-Line Help and Examples
The CLI SHALL provide comprehensive help text and usage examples accessible via `--help` flags.

#### Scenario: Main help text
- **WHEN** user runs `mai-phone --help`
- **THEN** displays overview of all commands and global options
- **AND** shows 3-5 quick examples for common use cases
- **AND** includes links to full documentation

#### Scenario: Subcommand help
- **WHEN** user runs `mai-phone config --help`
- **THEN** displays detailed help for the `config` subcommand
- **AND** lists all available sub-subcommands (show, init, etc.)
- **AND** explains each option and argument

#### Scenario: Interactive examples
- **WHEN** user runs `mai-phone examples`
- **THEN** displays a list of 10+ example tasks with descriptions
- **AND** allows user to select and run an example task immediately
- **AND** shows the command that would be executed for learning

