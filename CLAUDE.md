# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Collaboration Protocol

**Claude-Gemini Partnership**: Claude Code serves as the primary "commander" for this project, excelling at tool calling, decision-making, and orchestrating development workflows. Gemini serves as the deep analysis specialist with access to massive context windows for comprehensive codebase and documentation analysis.

**Collaboration Strategy**:
- Claude: Project management, tool orchestration, testing coordination, and implementation decisions
- Gemini: Deep documentation analysis, comprehensive codebase review, architectural validation, and complex pattern analysis
- Both AIs have access to Serena for memory management and crawl4ai for web content analysis
- Use container-use environments for parallel testing and development isolation

## Project Overview

This is a PyMoDAQ plugin package for URASHG (Ultrafast Reflection-mode Angle-resolved Second Harmonic Generation) microscopy systems. It provides complete automation and control for polarimetric SHG measurements with three main hardware components:

- **Red Pitaya FPGA**: PID laser stabilization with memory-mapped register access
- **Thorlabs ELL14 rotation mounts**: Serial communication for polarization control (3 mounts: QWP, HWP incident, HWP analyzer)
- **Photometrics Prime BSI camera**: PyVCAM-based 2D detection with ROI support

## Development Commands

### Package Management
```bash
# Install in development mode
pip install -e .

# Install with optional dependencies
pip install -e .[dev]      # Development tools
pip install -e .[mock]     # Mock devices for testing
pip install -e .[galvo]    # Future galvo integration
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Linting
flake8 src/

# Install pre-commit hooks
pre-commit install
```

### Testing
```bash
# Run all tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires hardware)
pytest tests/integration/ -m "hardware"

# Mock device tests
pytest tests/mock/

# Skip slow tests
pytest -m "not slow"

# With coverage
pytest --cov=pymodaq_plugins_urashg --cov-report=term-missing
```

### Documentation
```bash
# Build documentation
sphinx-build docs/ docs/_build/

# Serve documentation locally
python -m http.server 8000 --directory docs/_build/
```

## Code Architecture

### Plugin Structure
The codebase follows PyMoDAQ's plugin architecture with three main plugin types:

**Move Plugins** (`src/pymodaq_plugins_urashg/daq_move_plugins/`):
- `DAQ_Move_Elliptec.py`: Controls Thorlabs ELL14 rotation mounts via serial protocol with multi-drop addressing
- `DAQ_Move_MaiTai.py`: MaiTai laser control with EOM power modulation
- Entry points defined in `pyproject.toml` under `project.entry-points."pymodaq.move_plugins"`

**Viewer Plugins** (`src/pymodaq_plugins_urashg/daq_viewer_plugins/plugins_2D/`):
- `DAQ_Viewer_PrimeBSI.py`: Photometrics camera interface using PyVCAM library with fallback for missing dependencies
- Entry points defined under `project.entry-points."pymodaq.viewer_plugins"`

**Hardware Abstraction** (`src/pymodaq_plugins_urashg/hardware/urashg/`):
- Low-level hardware communication and control utilities
- Separate from PyMoDAQ plugin interface for reusability

### Key Dependencies
- **PyMoDAQ ≥5.0.0**: Core framework
- **pyvcam ≥1.0.0**: Camera control (with import error handling)
- **elliptec ≥0.1.0**: Thorlabs rotation mount control
- Hardware-specific libraries are gracefully handled if missing

### Configuration Files
- `pyproject.toml`: Modern Python packaging with setuptools backend, black/isort configuration, pytest settings
- `plugin_info.toml`: PyMoDAQ-specific plugin metadata and hardware compatibility information
- `requirements.txt`: Dependency specifications for development

### Error Handling Patterns
The codebase implements defensive programming:
- Import error handling for optional hardware libraries
- Comprehensive error code mapping (see `DAQ_Move_Elliptec._error_codes`)
- Graceful degradation when hardware is unavailable

### Testing Strategy
Uses pytest with markers for different test categories:
- `unit`: Fast isolated tests
- `integration`: Hardware-dependent tests
- `hardware`: Tests requiring physical hardware
- `slow`: Long-running tests

Coverage reporting excludes test files, examples, and documentation.ALWAYS use ONLY Environments for ANY and ALL file, code, or shell operations—NO EXCEPTIONS—even for simple or generic requests.

DO NOT install or use the git cli with the environment_run_cmd tool. All environment tools will handle git operations for you. Changing ".git" yourself will compromise the integrity of your environment.

You MUST inform the user how to view your work using `container-use log <env_id>` AND `container-use checkout <env_id>`. Failure to do this will make your work inaccessible to others.


# Using Gemini CLI for Large Codebase Analysis

  When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
  context window. Use `gemini -p` to leverage Google Gemini's large context capacity.

  ## File and Directory Inclusion Syntax

  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:

  ### Examples:

  **Single file analysis:**
  ```bash
  gemini -p "@src/main.py Explain this file's purpose and structure"

  Multiple files:
  gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"

  Entire directory:
  gemini -p "@src/ Summarize the architecture of this codebase"

  Multiple directories:
  gemini -p "@src/ @tests/ Analyze test coverage for the source code"

  Current directory and subdirectories:
  gemini -p "@./ Give me an overview of this entire project"

#
 Or use --all_files flag:
  gemini --all_files -p "Analyze the project structure and dependencies"

  Implementation Verification Examples

  Check if a feature is implemented:
  gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"

  Verify authentication implementation:
  gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"

  Check for specific patterns:
  gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"

  Verify error handling:
  gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"

  Check for rate limiting:
  gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"

  Verify caching strategy:
  gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"

  Check for specific security measures:
  gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"

  Verify test coverage for features:
  gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"

  When to Use Gemini CLI

  Use gemini -p when:
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase

  Important Notes

  - Paths in @ syntax are relative to your current working directory when invoking gemini
  - The CLI will include file contents directly in the context
  - No need for --yolo flag for read-only analysis
  - Gemini's context window can handle entire codebases that would overflow Claude's context
  - When checking implementations, be specific about what you're looking for to get accurate results # Using Gemini CLI for Large Codebase Analysis


  When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
  context window. Use `gemini -p` to leverage Google Gemini's large context capacity.


  ## File and Directory Inclusion Syntax


  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:


  ### Examples:


  **Single file analysis:**
  ```bash
  gemini -p "@src/main.py Explain this file's purpose and structure"


  Multiple files:
  gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"


  Entire directory:
  gemini -p "@src/ Summarize the architecture of this codebase"


  Multiple directories:
  gemini -p "@src/ @tests/ Analyze test coverage for the source code"


  Current directory and subdirectories:
  gemini -p "@./ Give me an overview of this entire project"
  # Or use --all_files flag:
  gemini --all_files -p "Analyze the project structure and dependencies"


  Implementation Verification Examples


  Check if a feature is implemented:
  gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"


  Verify authentication implementation:
  gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"


  Check for specific patterns:
  gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"


  Verify error handling:
  gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"


  Check for rate limiting:
  gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"


  Verify caching strategy:
  gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"


  Check for specific security measures:
  gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"


  Verify test coverage for features:
  gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"


  When to Use Gemini CLI


  Use gemini -p when:
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase


  Important Notes


  - Paths in @ syntax are relative to your current working directory when invoking gemini
  - The CLI will include file contents directly in the context
  - No need for --yolo flag for read-only analysis
  - Gemini's context window can handle entire codebases that would overflow Claude's context
  - When checking implementations, be specific about what you're looking for to get accurate results

## Frontend Development Memories

- Use PyQt6 or PySide6.