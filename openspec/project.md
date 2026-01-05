# Project Context

## Purpose
MAI-UI is a family of foundation GUI agents designed to revolutionize human-computer interaction by enabling autonomous mobile device navigation. The project provides vision-language models that can understand screenshots, process natural language instructions, and generate GUI actions for mobile automation.

**Key Goals:**
- Native agent-user interaction with support for `ask_user` tool calls
- Device-cloud collaboration for optimal execution routing
- MCP (Model Context Protocol) tool integration for extended capabilities
- Real-world deployment across GUI grounding and mobile navigation benchmarks

## Tech Stack
- **Language:** Python 3.x
- **ML Framework:** Vision-Language Models (VLMs) via OpenAI-compatible API
- **Model Serving:** vLLM (≥0.11.0) with transformers (≥4.57.0)
- **Core Libraries:**
  - `openai==2.13.0` - LLM API client
  - `Pillow==12.0.0` - Image processing
  - `numpy==2.3.5` - Numerical computations
  - `Jinja2==3.1.6` - Template rendering (prompts)
- **Development Tools:** Jupyter notebooks for demos and testing
- **Model Variants:** 2B, 8B, 32B, and 235B-A22B parameter models

## Project Conventions

### Code Style
- **Naming Conventions:**
  - Classes: `PascalCase` (e.g., `MAIUINaivigationAgent`, `MAIGroundingAgent`)
  - Functions/methods: `snake_case` (e.g., `parse_tagged_text`, `safe_pil_to_bytes`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `SCALE_FACTOR`, `MAI_MOBILE_SYS_PROMPT`)
  - Files: `snake_case.py` (e.g., `mai_naivigation_agent.py`, `unified_memory.py`)

- **Formatting:**
  - Follow PEP 8 guidelines
  - Type hints encouraged for function signatures
  - Comprehensive docstrings with Args/Returns/Raises sections

- **Documentation:**
  - Docstrings in triple-quote format with clear Args/Returns sections
  - Inline comments for complex logic (e.g., coordinate normalization)
  - README-driven development with examples

### Architecture Patterns
- **Agent-Based Architecture:**
  - `BaseAgent` abstract class for common agent functionality
  - Specialized agents: `MAIGroundingAgent` (element localization), `MAIUINaivigationAgent` (navigation)
  - Trajectory-based memory via `TrajStep` for multi-turn interactions

- **Prompt Engineering:**
  - System prompts defined in `prompt.py` module
  - Template-based prompts with Jinja2 support
  - Separate prompts for MCP-enabled vs. standard modes

- **Response Parsing:**
  - XML-style tagged output: `<thinking>...</thinking>` and `<tool_call>...</tool_call>`
  - Structured JSON within `tool_call` tags for action specification
  - Coordinate normalization with `SCALE_FACTOR = 999`

- **Device-Cloud Collaboration:**
  - Dynamic routing based on task complexity and data sensitivity
  - On-device models (2B/8B) for simple tasks
  - Cloud models for complex reasoning

### Testing Strategy
- **Notebook-Based Testing:**
  - `cookbook/grounding.ipynb` - Element grounding demos
  - `cookbook/run_agent.ipynb` - Full navigation agent demos
  - Interactive testing with visual feedback

- **Benchmark Evaluation:**
  - ScreenSpot-Pro (GUI grounding)
  - MMBench GUI L2, OSWorld-G, UI-Vision
  - AndroidWorld, MobileWorld (mobile navigation)

- **Online RL Testing:**
  - Parallel environment scaling (32-512 envs)
  - Step budget validation (15-50 steps)

### Git Workflow
- **Development:** Use feature branches for new capabilities
- **Spec-Driven Development:** Follow OpenSpec workflow (see `openspec/AGENTS.md`)
  - Create proposals before major features
  - Validate with `openspec validate --strict`
  - Archive completed changes to `openspec/changes/archive/`
- **Commits:** Atomic commits with descriptive messages
- **Pull Requests:** Include spec updates for capability changes

## Domain Context

### MAI Phone Agent Framework
- **Core Components:**
  - `main.py`: Primary CLI entry point for autonomous Android control. Supports `--device-id`, `--base-url`, `--apikey`, and model selection.
  - `device_bridge_simple.py`: Robust ADB wrapper using `subprocess`. Handles device connection, screenshots, and input methods (including ADB Keyboard).
  - `mai_naivigation_agent.py`: Core agent logic encapsulating the VLM interaction and coordinate normalization.
  - `app_mapping.yaml`: User-configurable file for mapping natural language app names to Android package names.
- **Capabilities:**
  - **Full Action Space:** `click`, `long_press`, `swipe` (direction/coordinate), `drag`, `type` (UTF-8 support), `system_button` (home/back/menu/enter), `open`, `answer`, `terminate`, `wait`
  - **Robustness:** 
    - Automatic ADB Keyboard switching for reliable Chinese input.
    - Infinite loop detection and prevention mechanics.
    - Intelligent `open` action with mapping lookup, fuzzy search, and `am start` fallback for system apps like Settings.
  - **Compatibility:** Local vLLM (`EMPTY` api_key) and OpenAI-compatible services (e.g., Qwen, GPT-4).

### GUI Agent Fundamentals
- **GUI Grounding:** Locating UI elements from natural language descriptions
- **Action Space:**
  - **Touch:** `click` (tap), `long_press`, `drag`
  - **Gesture:** `swipe` (supports `direction="up/down..."` or `start/end` coordinates)
  - **Input:** `type` (text input with Unicode support via ADB Keyboard broadcast)
  - **System:** `system_button` (back, home, menu, enter), `open` (launch app), `terminate`, `wait`
  - **Interaction:** `answer` (chat response), `ask_user`
- **Observation:** Screenshots (PIL Images or bytes), optional XML accessibility trees
- **Multi-Step Navigation:** Chained actions to complete complex user goals

### MCP (Model Context Protocol)
- Tool integration framework for extending agent capabilities
- Example tools: AMap navigation, file operations, calendar queries
- JSON-based tool call specification

### Trajectory Memory
- History-aware predictions using previous steps
- `history_n` configuration controls how many past steps to include
- Screenshot history for visual context

### Coordinate Systems
- Model outputs normalized coordinates [0, 999] in internal logic
- **Agent Normalization:** `mai_naivigation_agent` normalizes 0-999 -> [0, 1] before passing to executor
- **Executor Execution:** `main.py` maps [0, 1] -> [0, screen_pixel] for device actions
- Supports both percentage and pixel-based positioning

## Important Constraints

### Technical Constraints
- **Model Serving:** Requires vLLM-compatible OpenAI API endpoint or standard OpenAI API
- **Memory:** Large context lengths for multi-turn scenarios (RL optimization)
- **GPU Requirements:** Tensor parallelism for larger models (8B+)
- **Image Processing:** Screenshots must be PIL Images or bytes
- **Response Format:** Strict XML tag parsing (`<thinking>`, `<tool_call>`)
- **Android Input:** Native `input text` limited to ASCII; `ADBKeyBoard` required for robust Chinese/Unicode input

### Business Constraints
- **Real-World Deployment:** Focus on practical, deployable agents
- **Data Privacy:** Device-cloud routing considers data sensitivity
- **Latency:** On-device execution for 40%+ reduction in cloud API calls

### Regulatory/Licensing
- **License:** Apache License 2.0
- **Attribution:** Developed by Alibaba Cloud (Tongyi-MAI team)
- **Third-Party Components:** See NOTICE file for dependencies

## External Dependencies

### Model Hosting
- **HuggingFace Models:**
  - [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B)
  - [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B)
- **vLLM Server:** OpenAI-compatible API at `http://localhost:8000/v1` (default)

### Key APIs & Services
- **OpenAI API Client:** Compatible endpoint for model inference
- **Pillow:** Image manipulation and format conversion
- **NumPy:** Array operations for coordinate transformations

### Development Resources
- **Project Website:** [https://tongyi-mai.github.io/MAI-UI/](https://tongyi-mai.github.io/MAI-UI/)
- **arXiv Paper:** [https://arxiv.org/abs/2512.22047](https://arxiv.org/abs/2512.22047)
- **GitHub Repository:** [https://github.com/Tongyi-MAI/MAI-UI](https://github.com/Tongyi-MAI/MAI-UI)

### Benchmark Datasets
- ScreenSpot-Pro, MMBench GUI L2, OSWorld-G, UI-Vision (grounding)
- AndroidWorld, MobileWorld (navigation)
