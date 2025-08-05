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

This is a PyMoDAQ plugin package for URASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy systems. It provides complete automation and control for polarimetric SHG measurements with three main hardware components:

- **Red Pitaya FPGA**: PID laser stabilization with memory-mapped register access
- **Thorlabs ELL14 rotation mounts**: Serial communication for polarization control (3 mounts: QWP, HWP incident, HWP analyzer)
- **Photometrics Prime BSI camera**: PyVCAM-based 2D detection with ROI support

## [COMPLETE] PyMoDAQ 5.0+ Migration Complete ✅

**Status**: Successfully migrated from PyMoDAQ 4.x to 5.0+ (August 2025) - FULLY WORKING

**Critical DataActuator Fix Applied**:
- **Root Issue**: UI integration failure due to incorrect DataActuator value extraction
- **Solution**: Single-axis controllers MUST use `position.value()`, not `position.data[0][0]`
- **Pattern**: Multi-axis controllers use `position.data[0]` for arrays

**Key Changes Applied**:
- Updated data structures: `DataFromPlugins` → `DataWithAxes` + `DataToExport`
- Qt framework migration: PyQt5 → PySide6
- Signal updates: `data_grabed_signal` → `dte_signal`
- **CRITICAL**: Fixed DataActuator value extraction in move_abs/move_rel methods
- Thread commands: Proper `ThreadStatusMove.MOVE_DONE` signal emission
- Dependency updates: All PyMoDAQ packages to 5.0+
- Entry point validation and consistency fixes

**Testing Status**: ✅ All plugins working with hardware
**UI Integration**: ✅ Restored - wavelength and shutter controls functional
**Plugin Discovery**: ✅ Confirmed working with PyMoDAQ 5.0+ framework

## CRITICAL: DataActuator Usage Patterns

### ✅ Correct Single-Axis Pattern (MaiTai Laser)
```python
def move_abs(self, position: Union[float, DataActuator]):
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # CORRECT!
```

### ✅ Correct Multi-Axis Pattern (Elliptec, ESP300)
```python  
def move_abs(self, positions: Union[List[float], DataActuator]):
    if isinstance(positions, DataActuator):
        target_array = positions.data[0]  # CORRECT for multi-axis!
```

### ❌ NEVER Use This Pattern (Causes UI Failure)
```python
# WRONG - causes UI integration failure:
target_value = float(position.data[0][0])  # DON'T DO THIS!
```

## [COMPLETE] PyVCAM 2.2.3 Camera Integration

**Status**: PrimeBSI camera fully working with real hardware

**Major API Compatibility Fixes Applied**:
- **Import Updates**: `pyvcam.enums` → `pyvcam.constants`
- **Trigger Modes**: Use `exp_modes` dictionary instead of enum objects
- **Clear Modes**: Use `clear_modes` dictionary with integer values
- **Speed Control**: Speed_X naming convention replaces speed_table_index
- **Gain Handling**: Gain names mapped to gain_index values via port_speed_gain_table
- **ROI Structure**: `camera.rois[0]` replaces deprecated `camera.roi` attribute
- **PVCAM State**: Robust initialization/cleanup prevents library conflicts

**Hardware Verification**:
```
Camera: pvcamUSB_0 (Photometrics Prime BSI)
Sensor: 2048x2048 pixels
Temperature: -19.89°C (live monitoring)
Status: Full PyMoDAQ integration functional
```

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
- `daq_2Dviewer_PrimeBSI.py`: Photometrics camera interface using PyVCAM 2.2.3 library with full hardware integration
- Entry points defined under `project.entry-points."pymodaq.viewer_plugins"`

**Hardware Abstraction** (`src/pymodaq_plugins_urashg/hardware/urashg/`):
- Low-level hardware communication and control utilities
- Separate from PyMoDAQ plugin interface for reusability

### Key Dependencies
- **PyMoDAQ ≥5.0.0**: Core framework
- **pyvcam ≥2.2.3**: Camera control with full PyVCAM API compatibility
- **elliptec ≥0.1.0**: Thorlabs rotation mount control
- Hardware-specific libraries are gracefully handled if missing

### Hardware Integration Status
- **PrimeBSI Camera**: FULLY WORKING with PyVCAM 2.2.3 (pvcamUSB_0 detected, -19.89°C live temperature)
- **MaiTai Laser**: FULLY WORKING with serial communication (wavelength control, shutter operations)
- **ESP300 Motion Controller**: Connected via serial hub (ttyUSB3-6), pending configuration
- **Newport 1830-C Power Meter**: Connected via ttyS0, pending testing

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

Coverage reporting excludes test files, examples, and documentation.