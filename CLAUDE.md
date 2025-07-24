# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- **PyMoDAQ ≥4.0.0**: Core framework
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
