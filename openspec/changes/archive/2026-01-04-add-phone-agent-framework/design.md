## Context

This framework fills a critical gap between MAI-UI's excellent model capabilities and real-world usability. Currently, users must write significant boilerplate to bridge the agent with actual Android devices. Inspired by Open-AutoGLM's UX but optimized for MAI-UI's architecture.

**Background:**
- MAI-UI provides `MAIUINaivigationAgent` with `predict()` interface
- Agents output action JSON like `{"action": "tap", "coordinate": [0.5, 0.3]}`
- No execution layer exists to translate predictions into Android actions
- No CLI for end users to provide natural language tasks

**Constraints:**
- Must work with existing agent classes without modification
- Pure Python implementation (cross-platform where possible)
- Android API level 21+ support (covers 95%+ devices)
- Minimal external dependencies beyond Python ecosystem

**Stakeholders:**
- End users: Researchers/developers testing MAI-UI models
- Contributors: Developers building MCP tools or custom actions
- Maintainers: Need clean architecture for long-term support

## Goals / Non-Goals

**Goals:**
1. **Single-Command Experience**: `mai-phone "natural language task"` should work out of the box
2. **Multi-Step Autonomy**: Execute tasks requiring 5-20 steps (booking tickets, shopping)
3. **Error Resilience**: Handle common failures (app crashes, network issues, UI changes)
4. **Tool Integration**: Support `ask_user` and `mcp_call` actions from the agent
5. **Developer Friendly**: Clear logs, trajectory export, debug mode
6. **Extensibility**: Easy to add custom actions or device types (future iOS support)

**Non-Goals:**
1. iOS support in this phase (Android-only)
2. Web automation or desktop GUI (focus on mobile)
3. Advanced RL training infrastructure (inference-only)
4. GUI for configuration (CLI-first, configs in YAML)
5. Enterprise features (multi-device orchestration, distributed execution)
6. Online learning or model fine-tuning

## Decisions

### Decision 1: ADB Wrapper Library
**Choice:** Use `adbutils` (pure Python ADB client)

**Alternatives Considered:**
- Google's official `adb` binary via subprocess → Fragile path dependencies
- `pure-python-adb` → Less maintained, older
- Custom ADB protocol implementation → Too much scope

**Rationale:**
- `adbutils` is actively maintained, pure Python, cross-platform
- Provides high-level APIs (`device.screenshot()`, `device.shell()`)
- Well-tested in production tools (uiautomator2, airtest)

### Decision 2: CLI Framework
**Choice:** Use `click` for command-line interface

**Alternatives Considered:**
- `argparse` (stdlib) → More boilerplate for nice UX
- `typer` (FastAPI-style) → Newer, but `click` is more proven
- Custom parser → Reinventing the wheel

**Rationale:**
- `click` is industry standard (used by Flask, many Google projects)
- Excellent help text generation and argument validation
- Decorators provide clean syntax

### Decision 3: Execution Loop Architecture
**Choice:** Synchronous loop with step-by-step execution

**Flow:**
```
while not done and steps < max_steps:
    screenshot = device.capture()
    obs = {"screenshot": screenshot}
    prediction, action = agent.predict(instruction, obs)
    
    if action["action"] == "FINISH":
        done = True
    elif action["action"] == "ask_user":
        response = prompt_user(action["question"])
        # inject response and continue
    elif action["action"] == "mcp_call":
        result = mcp_handler.execute(action["tool"], action["args"])
        # inject result and continue
    else:
        device.execute_action(action)
    
    steps += 1
```

**Alternatives Considered:**
- Async/await architecture → Overkill for single-device control
- Event-driven with callbacks → Over-engineering for linear flow
- Separate threads for device I/O → Complexity without clear benefit

**Rationale:**
- Synchronous is simpler to debug and reason about
- Device operations (ADB) are already I/O-bound, async won't help much
- Easy to add retry logic and error handling inline

### Decision 4: Configuration Management
**Choice:** YAML config file at `~/.mai-phone/config.yaml` + CLI overrides

**Structure:**
```yaml
model:
  base_url: "http://localhost:8000/v1"
  name: "MAI-UI-8B"
  temperature: 0.0
  history_n: 3

device:
  serial: null  # auto-detect if not specified
  adb_server: "localhost:5037"

execution:
  max_steps: 50
  screenshot_delay: 0.5  # seconds between actions
  retry_attempts: 3

logging:
  level: "INFO"
  save_trajectory: true
  output_dir: "~/.mai-phone/logs"
```

**Rationale:**
- YAML is human-readable and easy to edit
- CLI flags can override config for quick experiments
- Sensible defaults prevent required configuration

### Decision 5: Action Coordinate System
**Choice:** Agent outputs [0, 1] normalized coordinates, framework converts to pixels

**Implementation:**
```python
def execute_tap(device, normalized_coords):
    width, height = device.screen_size()
    x = int(normalized_coords[0] * width)
    y = int(normalized_coords[1] * height)
    device.shell(f"input tap {x} {y}")
```

**Rationale:**
- Consistent with MAI-UI agent output (divided by SCALE_FACTOR=999)
- Device-independent (works across screen resolutions)
- Clear boundary: agent handles prediction, framework handles execution

## Risks / Trade-offs

### Risk 1: ADB Connection Stability
**Mitigation:**
- Implement connection health checks before each action
- Auto-reconnect on disconnection (up to 3 retries)
- Clear error messages for common issues (USB debugging, authorization)

### Risk 2: Action Execution Timing
Many Android apps have animations/loading states.
**Mitigation:**
- Configurable `screenshot_delay` between actions (default 0.5s)
- Optional accessibility tree parsing to detect UI state changes
- Smart wait: check if screen changed before proceeding

### Risk 3: Task Completion Detection
Agent may not know when task is truly complete.
**Mitigation:**
- Require agent to output `{"action": "FINISH", "reason": "..."}` explicitly
- Max steps limit to prevent infinite loops (default 50)
- Expose step count to agent in observation for self-awareness

### Risk 4: User Interaction Blocking
`ask_user` calls block execution waiting for input.
**Mitigation:**
- Timeout on user prompts (default 120s)
- Allow "skip" or "cancel" to abort task gracefully
- Log all interactions for replay/debugging

### Trade-off: USB vs WiFi ADB
**Decision:** Support both, default to USB
- USB: More stable, faster, but requires cable
- WiFi: Convenient, but flaky on some networks
- Allow configuration via `--device-mode {usb|wifi|auto}`

### Trade-off: Accessibility Tree Parsing
**Decision:** Optional, disabled by default
- Pro: Richer UI context for agent (element IDs, text)
- Con: Slower capture (~200ms extra), not all apps expose it
- Enable via `--use-accessibility-tree` flag

## Migration Plan

**Phase 1: Core Framework (Week 1-2)**
1. Implement `android_device_bridge.py` with basic actions (tap, swipe, type)
2. Build `executor.py` with synchronous execution loop
3. Create `cli.py` with basic command structure

**Phase 2: Integration & Testing (Week 2-3)**
4. Implement `integration.py` to connect agent with device
5. Add tool call handling (`ask_user`, `mcp_call` placeholders)
6. Write example tasks and validate end-to-end

**Phase 3: Polish & Docs (Week 3-4)**
7. Add configuration management and logging
8. Create comprehensive README section with tutorials
9. Add error handling and recovery mechanisms
10. Package for PyPI distribution

**Rollback Plan:**
- All code is additive (new `phone_agent/` package)
- No changes to existing agent classes
- Can be removed entirely without affecting core models

**Testing Strategy:**
- Unit tests for each component (device bridge, executor, integration)
- Integration tests with mock ADB device
- Manual E2E tests on real Android device (API 21, 28, 34)
- Smoke test suite: 5 basic tasks (open app, search, navigate back)

## Open Questions

1. **MCP Tool Integration**: Should we bundle common MCP tools (calendar, contacts) or require users to install separately?
   - **Proposal**: Start with `ask_user` only, document MCP integration pattern, add tools incrementally

2. **Device-Cloud Routing**: How to implement task complexity detection for routing?
   - **Proposal**: Defer to later iteration, use single model for now, expose hooks for routing logic

3. **Trajectory Export Format**: JSON, pickle, or custom binary?
   - **Proposal**: JSON for human readability, add binary support if performance needed

4. **Multi-Device Support**: Should CLI support multiple devices in one command?
   - **Proposal**: No, keep 1 task = 1 device, users can script multi-device if needed

5. **Error Screenshots**: Should we save screenshots on action failures?
   - **Proposal**: Yes, save to `logs/{task_id}/error_{step}.png` for debugging

6. **Internationalization**: Support non-English UI languages?
   - **Proposal**: Yes via agent (model handles Chinese/English), framework is language-agnostic

**Decisions Needed:**
- Package name: `mai-phone` or `maiui-phone` or `phone-agent`? → **Recommend: `mai-phone`** (short, memorable)
- Entry point: `mai-phone` or `maiphone` or `mai`? → **Recommend: `mai-phone`** (clear namespace)
