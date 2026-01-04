# Implementation Tasks

## 1. Project Setup
- [x] 1.1 Create `phone_agent/` package directory structure
- [x] 1.2 Add `__init__.py` with version and exports
- [x] 1.3 Create `setup.py` or update `pyproject.toml` with dependencies
- [x] 1.4 Add CLI entry point: `mai-phone` → `phone_agent.cli:main`
- [x] 1.5 Update `.gitignore` for `~/.mai-phone/` and `*.log` files


## 2. Android Device Bridge (`android-device-bridge` capability)
- [x] 2.1 Implement `DeviceBridge` class with ADB connection management
- [x] 2.2 Add device discovery and selection (`list_devices()`, `connect()`)
- [x] 2.3 Implement screenshot capture → PIL Image + bytes
- [x] 2.4 Add basic actions: `tap(x, y)`, `swipe(x1, y1, x2, y2)`, `type(text)`
- [x] 2.5 Add navigation actions: `back()`, `home()`, `recent_apps()`
- [x] 2.6 Implement `get_screen_size()` for coordinate normalization
- [x] 2.7 Add connection health check and auto-reconnect logic
- [ ] 2.8 Write unit tests with mock ADB responses

## 3. Configuration Management
- [x] 3.1 Create `Config` dataclass for settings
- [x] 3.2 Implement YAML config loading from `~/.mai-phone/config.yaml`
- [x] 3.3 Add config validation and defaults
- [x] 3.4 Support environment variable overrides (e.g., `MAI_PHONE_MODEL_URL`)
- [ ] 3.5 Write config save/load tests

## 4. Autonomous Task Executor (`autonomous-task-executor` capability)
- [x] 4.1 Create `TaskExecutor` class with main execution loop
- [x] 4.2 Implement observation builder (screenshot → obs dict)
- [x] 4.3 Add termination detection (`FINISH` action, max steps)
- [x] 4.4 Implement action dispatch (`tap`, `swipe`, `type`, etc.)
- [x] 4.5 Add `ask_user` tool call handling with user prompt
- [x] 4.6 Add `mcp_call` tool call routing (placeholder for now)
- [x] 4.7 Implement retry logic for failed actions
- [x] 4.8 Add step delay and smart waiting between actions
- [x] 4.9 Create trajectory tracking and export (JSON format)
- [ ] 4.10 Write executor integration tests with mock agent and device

## 5. Agent Integration Layer (`agent-integration` capability)
- [x] 5.1 Create `AgentIntegration` wrapper class
- [x] 5.2 Implement observation formatting for agent (screenshot + optional accessibility tree)
- [x] 5.3 Add action JSON parsing and validation
- [x] 5.4 Implement coordinate transformation (normalized [0,1] → pixels)
- [x] 5.5 Add action type validation (ensure valid action names)
- [x] 5.6 Create error mapping (agent errors → user-friendly messages)
- [ ] 5.7 Write integration layer unit tests

## 6. CLI Interface (`phone-agent-cli` capability)
- [x] 6.1 Create `cli.py` with `click` framework
- [x] 6.2 Implement main command: `mai-phone <instruction>`
- [x] 6.3 Add flags: `--model-url`, `--device-serial`, `--max-steps`, `--debug`
- [x] 6.4 Implement `mai-phone config` subcommand (view/edit config)
- [x] 6.5 Add `mai-phone devices` subcommand (list connected devices)
- [x] 6.6 Implement `mai-phone replay <trajectory_file>` for debugging
- [x] 6.7 Add `mai-phone version` and `mai-phone doctor` (check setup)
- [x] 6.8 Create help text and examples
- [x] 6.9 Add colorized output with `click.echo` and `click.style`
- [ ] 6.10 Write CLI smoke tests

## 7. Logging and Telemetry
- [ ] 7.1 Set up Python `logging` with configurable levels
- [ ] 7.2 Create log directory structure: `~/.mai-phone/logs/{task_id}/`
- [ ] 7.3 Save trajectory JSON after each task completion
- [ ] 7.4 Save error screenshots on action failures
- [ ] 7.5 Add metrics tracking (steps, success rate, execution time)
- [ ] 7.6 Implement log rotation (keep last 100 tasks)

## 8. Error Handling and Recovery
- [ ] 8.1 Add exception handling for ADB disconnections
- [ ] 8.2 Implement retry mechanism with exponential backoff
- [ ] 8.3 Add timeout handling for long-running actions
- [ ] 8.4 Create user-friendly error messages for common issues
- [ ] 8.5 Add graceful shutdown on Ctrl+C (save partial trajectory)
- [ ] 8.6 Write error scenario tests

## 9. Documentation and Examples
- [x] 9.1 Update main `README.md` with Phone Agent quick start section
- [ ] 9.2 Create `docs/phone-agent-guide.md` with detailed usage
- [x] 9.3 Add `examples/basic_tasks.py` with 5 example tasks
- [ ] 9.4 Create `examples/custom_mcp_tools.py` tutorial
- [ ] 9.5 Write troubleshooting guide (ADB issues, model connection)
- [ ] 9.6 Add API reference for `phone_agent` package

## 10. Testing and Validation
- [ ] 10.1 Write unit tests for all modules (>80% coverage)
- [ ] 10.2 Create integration test suite with mock device
- [ ] 10.3 Run manual E2E tests on 3 Android versions (API 21, 28, 34)
- [ ] 10.4 Execute 10 real-world tasks (shopping, navigation, social media)
- [ ] 10.5 Performance testing (measure fps, latency per step)
- [ ] 10.6 Stress testing (50+ step tasks, error injection)

## 11. Packaging and Distribution
- [ ] 11.1 Finalize `setup.py` with proper metadata and dependencies
- [ ] 11.2 Test installation: `pip install -e .` and `pip install .`
- [ ] 11.3 Verify CLI entry point works after install
- [ ] 11.4 Create distribution builds: `python setup.py sdist bdist_wheel`
- [ ] 11.5 Test installation in clean virtualenv
- [ ] 11.6 Prepare for PyPI upload (optional, later phase)

## 12. Polish and Release
- [ ] 12.1 Run `openspec validate add-phone-agent-framework --strict`
- [ ] 12.2 Fix any validation errors
- [ ] 12.3 Code review with maintainers
- [ ] 12.4 Final integration testing
- [ ] 12.5 Update CHANGELOG.md or release notes
- [ ] 12.6 Tag release version
- [ ] 12.7 Announce in README and project website

## Dependencies and Parallelization

**Can be done in parallel:**
- Tasks 2 (Device Bridge) and 3 (Config) are independent
- Tasks 5 (Integration Layer) can start after Task 2.3 (screenshot capture)
- Tasks 7 (Logging) and 8 (Error Handling) can be done alongside Tasks 4-6

**Sequential dependencies:**
- Task 4 (Executor) requires Task 2 (Device Bridge) completion
- Task 6 (CLI) requires Tasks 3 (Config), 4 (Executor), 5 (Integration)
- Task 10 (Testing) requires all implementation tasks
- Task 11 (Packaging) requires all tests passing

**Critical path:**
1. Setup (Task 1) → 2. Device Bridge → 4. Executor → 6. CLI → 10. Testing → 12. Release

**Estimated Timeline:**
- Phase 1 (Core Framework): Tasks 1-5 → 1-2 weeks
- Phase 2 (Integration & Testing): Tasks 6-10 → 1-2 weeks  
- Phase 3 (Polish & Release): Tasks 11-12 → 3-5 days

**Total: 3-4 weeks for complete implementation**
