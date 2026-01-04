# Change: Add Phone Agent Framework for Autonomous Android Control

## Why

The MAI-UI repository currently provides excellent vision-language model agents (`MAIUINaivigationAgent`, `MAIGroundingAgent`) but lacks a complete execution framework for users to actually control Android devices. Users cannot easily run commands like "打开小红书搜索附近美食" or "订高铁票" and have the agent autonomously execute multi-step tasks on a real phone.

This gap prevents the project from being production-ready and limits its real-world application. Open-source alternatives like Open-AutoGLM provide this complete experience, but MAI-UI needs its own framework optimized for its architecture.

**Problem:**
- No command-line interface for end users
- No Android device bridge (ADB wrapper) for screen capture and action execution
- No autonomous execution loop to handle multi-step task completions
- No error recovery or user interaction handling (`ask_user`, `mcp_call`)
- Users must write significant boilerplate code just to test the models

**Opportunity:**
- Deliver a complete, production-ready phone agent system
- Enable users to get started with a simple CLI command
- Demonstrate MAI-UI's real-world capabilities end-to-end
- Build a framework that showcases device-cloud collaboration and MCP integration

## What Changes

We will build a **Phone Agent Framework** from 0 to 1, consisting of four major capabilities:

1. **CLI Interface** (`phone-agent-cli`)
   - Simple command: `mai-phone "open Xiaohongshu and search nearby food"`
   - Configuration management (model URL, device selection, logging)
   - Interactive and batch execution modes
   - Task history and replay functionality

2. **Android Device Bridge** (`android-device-bridge`)
   - ADB wrapper for device discovery and connection
   - Screenshot capture (PIL Image + bytes) with caching
   - Action execution: tap, swipe, type, back, home, long press
   - Coordinate transformation (normalized to pixel coordinates)
   - USB and WiFi ADB support

3. **Autonomous Task Executor** (`autonomous-task-executor`)
   - Main execution loop: observe → predict → execute → validate
   - Multi-step task completion with trajectory tracking
   - Termination detection (task completion or max steps)
   - Error handling and recovery (retries, fallback strategies)
   - Tool call routing (`ask_user` → user prompt, `mcp_call` → MCP handler)

4. **Integration Layer** (`agent-integration`)
   - Glue between agent predictions and device actions
   - Observation builder (screenshot + optional accessibility tree)
   - Action parser and validator
   - Logging and telemetry (trajectory export, metrics)

**Key Features:**
- One-command setup: `pip install -e . && mai-phone "your task"`
- Compatible with existing `MAIUINaivigationAgent` without modification
- Extensible architecture for custom actions and MCP tools
- Device-cloud collaboration ready (routing logic for simple/complex tasks)

## Impact

**Affected Specs (4 new capabilities):**
- `specs/phone-agent-cli/spec.md` - NEW
- `specs/android-device-bridge/spec.md` - NEW
- `specs/autonomous-task-executor/spec.md` - NEW
- `specs/agent-integration/spec.md` - NEW

**Affected Code:**
- Create `phone_agent/` top-level package
  - `phone_agent/cli.py` - CLI entry point
  - `phone_agent/device_bridge.py` - ADB wrapper
  - `phone_agent/executor.py` - Task execution loop
  - `phone_agent/integration.py` - Agent-device integration
  - `phone_agent/config.py` - Configuration management
  - `phone_agent/utils.py` - Shared utilities
- Update `setup.py` or `pyproject.toml` for CLI entry point
- Add `examples/` with sample tasks and scripts
- Update `README.md` with Phone Agent quick start section

**Infrastructure:**
- Add dependencies: `adbutils` or `pure-python-adb` for ADB, `click` or `typer` for CLI
- Add configuration file: `~/.mai-phone/config.yaml` (optional)
- Add logging directory: `~/.mai-phone/logs/` for trajectories

**Breaking Changes:**
- None (purely additive)

**Migration Notes:**
- N/A (new feature)

**User Benefits:**
- From notebooks to production: single command execution
- Complete learning path: grounding → navigation → autonomous control
- Real-world demos that "just work"
- Foundation for advanced features (MCP tools, device-cloud routing)
