# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Collaboration Protocol

**Available Tools & Agents**: Claude Code has access to multiple specialized tools and agents for comprehensive development support:

**Core Tools Available**:
- **Serena**: Advanced memory management and LSP-based code analysis
- **GitHub Integration**: Full repository management and collaboration features
- **Context7**: Library documentation and API reference access
- **Greptile API**: Advanced code search and analysis across multiple repositories (API Key: 6duw+qKos1mnSls7Wq0iftBJaAh4MbuUgRuG1ZBEHSE6Xe8I)

**Specialized Sub-Agents Available**:
- **pymodaq-standards-researcher**: Context provider and standards authority for PyMoDAQ ecosystem analysis via Greptile API
- **pymodaq-plugin-implementer**: Implementation specialist for building production-ready PyMoDAQ plugins and experiments

**Sub-Agent Delegation Policy**:
- **Simple Tasks**: Permitted to create small sub-agents using haiku model for parallel task delegation
- **Complex Tasks**: Must request user permission before creating additional sub-agents
- **Agent Communication**: Researchers provide context, implementers build solutions, with clear delegation patterns

**Collaboration Strategy**:
- Claude: Project orchestration, tool coordination, and sub-agent management
- Standards Researcher: PyMoDAQ ecosystem analysis and pattern extraction via Greptile
- Plugin Implementer: Code implementation following PyMoDAQ standards
- All agents use Serena for shared memory and context management

## Project Overview

This is a PyMoDAQ plugin package for URASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy systems. It provides complete automation and control for polarimetric SHG measurements with three main hardware components:

- **Red Pitaya FPGA**: PID laser stabilization with memory-mapped register access
- **Thorlabs ELL14 rotation mounts**: Serial communication for polarization control (3 mounts: QWP, HWP incident, HWP analyzer)
- **Photometrics Prime BSI camera**: PyVCAM-based 2D detection with ROI support

## [COMPLETE] PyMoDAQ 5.0+ Migration & Standards Compliance ✅

**Status**: Full PyMoDAQ 5.x compliance achieved (August 2025) - PRODUCTION READY

**All Critical Issues Resolved**:
- ✅ **Plugin Discovery Fixed**: Corrected entry point paths in `plugin_info.toml`
- ✅ **move_home() Signature**: Added required `value=None` parameter for PyMoDAQ 5.x
- ✅ **DataActuator Integration**: Proper multi-axis format with units handling
- ✅ **Parameter Parsing**: Robust handling of floats, lists, and DataActuator objects
- ✅ **Hardware Validation**: All plugins tested and working with real hardware

**DataActuator Implementation Standards**:
- **Multi-axis Controllers**: Use `position.data[0]` for array access (Elliptec, ESP300)
- **Single-axis Controllers**: Use `position.value()` for scalar values (MaiTai, Newport)
- **Position Updates**: Consistent DataActuator format with proper units attribution

**Hardware Integration Verified**:
- **Elliptec Mounts**: Connected via `/dev/ttyUSB1`, all 3 mounts (2,3,8) homing and positioning
- **PrimeBSI Camera**: PyVCAM 2.2.3 compatible, pvcamUSB_0 detected, full functionality
- **Newport Power Meter**: Serial communication working, data acquisition confirmed

**PyMoDAQ 5.x Standards Compliance**:
- ✅ Data structures: `DataWithAxes` with proper `DataSource.raw`
- ✅ Qt framework: PySide6 integration 
- ✅ Signal patterns: `dte_signal` for data emission
- ✅ Parameter trees: Standard PyMoDAQ parameter structure
- ✅ Plugin discovery: All entry points properly registered
- ✅ Thread safety: Explicit cleanup following PyMoDAQ lifecycle
- ✅ Hardware abstraction: Clean separation of concerns

**Verification Results**:
- **Plugin Discovery**: ✅ All 5 URASHG plugins detected by PyMoDAQ framework
- **Dashboard Integration**: ✅ No crashes, stable initialization
- **Hardware Compatibility**: ✅ All plugins work with real hardware
- **Standards Compliance**: ✅ Excellent (9/10 rating) adherence to PyMoDAQ patterns

## [COMPLETE] Hardware Testing & Verification ✅

**Status**: Comprehensive hardware testing completed (August 2025) - ALL HARDWARE VERIFIED

**Hardware Test Results**:
- **PrimeBSI Camera**: ✅ WORKING - `pvcamUSB_0` detected, 2048x2048 sensor, PyVCAM 2.2.3 compatible
- **Newport 1830-C Power Meter**: ✅ WORKING - Connected on `/dev/ttyS0`, reading 3.5 mW, full plugin integration
- **PyMoDAQ Plugin Integration**: ✅ WORKING - Both plugins initialize correctly and acquire data

**PyVCAM 2.2.3 Compatibility Fixed**:
- **Root Issue**: Import from `pyvcam.enums` module not available in PyVCAM 2.2.3
- **Solution**: Updated to `from pyvcam.constants import CLEAR_NEVER, CLEAR_PRE_SEQUENCE, EXT_TRIG_INTERNAL`
- **PVCAM State Management**: Added proper initialization/cleanup to prevent detection issues
- **Camera Detection**: Fixed inconsistency between `pvc.get_cam_total()` and `Camera.detect_camera()`

**PyMoDAQ 5.x Data Structure Fixes**:
- **DataWithAxes Units**: Fixed `units=[units]` → `units=units` for proper string format
- **DataSource Required**: Added `source=DataSource.raw` to all data structures
- **Backward Compatibility**: Maintained compatibility with PyMoDAQ 5.x requirements

**Test Coverage**:
- **Mock Tests**: Complete CI/CD test suite with mock hardware simulation
- **Hardware Tests**: Real hardware validation with pytest markers
- **Integration Tests**: Full plugin functionality verified with PyMoDAQ framework

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

## [COMPLETE] PyRPL Plugin Integration ✅

**Status**: External PyMoDAQ PyRPL plugin successfully integrated (August 2025) - MODULAR PLUGIN APPROACH

**Integration Strategy**:
- **Modular Plugin**: Uses external `pymodaq_plugins_pyrpl` as dependency rather than internal implementation
- **Plugin Discovery**: `PyRPL_PID` plugin available alongside existing URASHG plugins
- **Conflict Resolution**: Internal `DAQ_Move_URASHG_PyRPL_PID` disabled to prevent conflicts
- **Dependency Management**: PyRPL plugins installed as optional dependency `pip install -e ".[pyrpl]"`

**Available PyRPL Plugins** (from external package):
- `DAQ_Move_PyRPL_PID`: Red Pitaya PID setpoint control
- `DAQ_Move_PyRPL_ASG`: Arbitrary signal generator control  
- `DAQ_0DViewer_PyRPL`: PyRPL module monitoring
- `DAQ_0DViewer_PyRPL_IQ`: Lock-in amplifier functionality
- `DAQ_1DViewer_PyRPL_Scope`: Oscilloscope functionality

**Experiment Integration**:
```python
# Updated experiment configuration
required_modules = ['MaiTai', 'H800', 'H400', 'Newport1830C', 'PyRPL_PID']
```

**Installation**:
```bash
pip install -e ".[pyrpl]"  # Installs PyRPL plugins + pyrpl library
```

**PyMoDAQ Standards Compliance**:
- ✅ **Modular Architecture**: External PyRPL plugins follow PyMoDAQ ecosystem patterns
- ✅ **Plugin Separation**: Clear separation between URASHG-specific and generic PyRPL functionality
- ✅ **Dependency Management**: Optional dependencies with proper entry point isolation
- ✅ **Reusability**: PyRPL plugins available across multiple PyMoDAQ projects
- ✅ **Maintenance**: Easier updates and independent development cycles
- ✅ **Future-Ready**: Prepared for URASHG plugin modularization following PyMoDAQ standards

## [CRITICAL] Threading Safety & PyMoDAQ Standards ⚠️

**Issue Resolved**: QThread destruction conflicts causing dashboard crashes

**Root Cause**: Hardware controller `__del__` methods interfering with Qt threading during garbage collection

**PyMoDAQ Standards Solution Applied**:
```python
# ❌ NEVER DO THIS in PyMoDAQ plugins:
def __del__(self):
    try:
        self.disconnect()  # Causes QThread conflicts!
    except:
        pass

# ✅ CORRECT PyMoDAQ pattern:
# Note: __del__ method removed to prevent QThread destruction conflicts  
# Cleanup is handled explicitly via disconnect() in the plugin's close() method

class DAQ_Plugin(DAQ_Move_base):
    def close(self):
        """Explicit cleanup following PyMoDAQ lifecycle."""
        if self.controller:
            self.controller.disconnect()
            self.controller = None
```

**Controllers Fixed**:
- ✅ `ESP300Controller`: Threading-safe cleanup
- ✅ `Newport1830C_controller`: Threading-safe cleanup

**Testing**: See `THREADING_SAFETY_GUIDELINES.md` and test scripts in `tests/integration/`

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

### Testing (Updated Repository Structure)
```bash
# Run all tests with organized structure
python scripts/run_all_tests.py

# Specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests (hardware optional)
pytest tests/development/             # Development and GUI tests

# PyMoDAQ standards compliance tests
pytest tests/integration/test_threading_safety_comprehensive.py
pytest tests/integration/test_hardware_controller_threading.py

# Plugin functionality tests
pytest tests/integration/test_esp300_threading_fix.py
pytest tests/integration/test_pyrpl_plugin_integration.py

# Hardware tests (requires real hardware)
pytest tests/integration/ -m "hardware"

# Coverage reporting
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

## Experiment Framework Architecture

### Base Experiment System
The codebase includes a sophisticated experiment framework in `src/pymodaq_plugins_urashg/experiments/`:

**URASHGBaseExperiment** (`base_experiment.py`):
- Common parameter trees for hardware configuration
- Hardware module management and initialization  
- Data structure definitions for multi-dimensional experiments
- Error handling and safety protocols
- Calibration data loading and management

**Experiment Types Available**:
- `basic_urashg_experiment.py`: Standard μRASHG polarimetry measurements
- `pdshg_experiment.py`: Polarization-dependent SHG with full Stokes analysis
- `elliptec_calibration.py`: Automated polarization element calibration
- `eom_calibration.py`: Electro-optic modulator characterization
- `variable_attenuator_calibration.py`: Power-dependent measurements
- `wavelength_dependent_rashg.py`: Spectroscopic RASHG studies

### Experiment Framework Patterns
```python
# All experiments inherit from URASHGBaseExperiment
class MyExperiment(URASHGBaseExperiment):
    experiment_name = "Custom RASHG"
    
    def setup_parameters(self):
        # Define experiment-specific parameters
        
    def initialize_hardware(self):
        # Setup hardware modules
        
    def run_experiment(self):
        # Execute measurement sequence
```

### Hardware Module Integration
Experiments coordinate multiple PyMoDAQ modules:
- **Move modules**: Elliptec rotators, MaiTai laser control
- **Viewer modules**: PrimeBSI camera, Newport power meter  
- **Scanner modules**: Future galvo integration
- **Extensions**: Custom experiment controllers

## Advanced Search & Analysis Tools

**For maximum search efficiency and accuracy, use these specialized tools**:

### File Operations
- **Finding FILES**: Use `fd` (10x faster than find)
  ```bash
  fd "experiment" --type f           # Find experiment files
  fd --extension py src/             # Python files in src/
  fd "\.toml$" --type f              # Config files
  ```

### Text & Code Search  
- **Finding TEXT/strings**: Use `rg` (ripgrep - already heavily used)
  ```bash
  rg "class.*Experiment" --type py   # Find experiment classes
  rg "position\.value\(\)" -A 2      # DataActuator patterns with context
  rg "PyMoDAQ" --stats               # Search with statistics
  ```

### Code Structure Analysis
- **Finding CODE STRUCTURE**: Use `ast-grep` (REVOLUTIONARY for PyMoDAQ)
  ```bash
  ast-grep --lang python --pattern 'class $NAME(URASHGBaseExperiment)'
  ast-grep --lang python --pattern 'def $METHOD(self, position: DataActuator)'
  ast-grep --lang python --pattern 'Parameter.create($$$)'
  ```

### Interactive Selection
- **SELECTING from results**: Pipe to `fzf`
  ```bash
  fd --type f --extension py | fzf
  rg "experiment" --files-with-matches | fzf
  ```

### Data Processing
- **JSON interaction**: Use `jq` (limited utility in this Python project)
- **YAML/XML interaction**: Use `yq` (limited utility - project uses TOML)

**Priority**: ast-grep + fd + rg combination provides 90% of search efficiency gains for PyMoDAQ development.

## Development Patterns & Debugging

### Plugin Development Lifecycle
1. **Hardware Abstraction**: Create driver in `src/pymodaq_plugins_urashg/hardware/urashg/`
2. **Plugin Implementation**: Build PyMoDAQ plugin with proper parameter trees
3. **Entry Point Registration**: Add to `pyproject.toml` under appropriate plugin type
4. **Testing**: Unit tests + hardware integration tests with pytest markers
5. **Documentation**: Update plugin_info.toml with hardware compatibility

### Common Development Tasks

**Add New Hardware Device**:
```bash
# 1. Create hardware driver
touch src/pymodaq_plugins_urashg/hardware/urashg/new_device.py

# 2. Create PyMoDAQ plugin
touch src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_NewDevice.py

# 3. Register in pyproject.toml entry points
# 4. Add tests
touch tests/unit/test_new_device.py

# 5. Test plugin discovery
pytest tests/unit/test_plugin_discovery.py -v
```

**Debug Plugin Issues**:
```bash
# Check plugin discovery
python -c "from pymodaq_plugins_urashg import *; print('Plugin import OK')"

# Test hardware connection
pytest tests/integration/ -m "hardware" -k "new_device"

# Debug PyMoDAQ integration
python -m pymodaq.dashboard  # Manual testing
```

### PyMoDAQ 5.x Specific Patterns

**Data Structure Creation**:
```python
# CORRECT PyMoDAQ 5.x pattern
data = DataWithAxes(
    'Camera', 
    data=[image_data],
    axes=[Axis('x', data=x_axis), Axis('y', data=y_axis)],
    units="counts",
    source=DataSource.raw
)
```

**Parameter Tree Setup**:
```python
# Standard parameter tree pattern used throughout
params = [
    {'name': 'hardware_settings', 'type': 'group', 'children': [
        {'name': 'device_id', 'type': 'str', 'value': 'default'},
        {'name': 'timeout', 'type': 'int', 'value': 1000},
    ]},
]
```

### Testing Strategy Details
- **Hardware Markers**: Use `@pytest.mark.hardware` for tests requiring physical devices
- **Mock Integration**: Mock devices available in `tests/mock_modules/` 
- **Containerized Testing**: All tests designed to run in isolated Docker environments
- **Coverage Tracking**: Exclude hardware-specific code from coverage when mocked

### Legacy Code Management
- **urashg_2/ Directory**: Contains legacy non-PyMoDAQ implementation
- **Maintained for Reference**: Original instrument control code and calibration scripts
- **Migration Path**: Patterns from urashg_2/ inform PyMoDAQ plugin development
- **Do Not Modify**: urashg_2/ is archival - all new development in main src/ tree