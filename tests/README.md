# URASHG Plugin Test Suite

## Overview

Comprehensive test suite for PyMoDAQ URASHG plugins, organized by test type and functionality. This test suite ensures PyMoDAQ 5.x standards compliance and threading safety.

## Test Organization

### Directory Structure
```
tests/
├── README.md                 # This file
├── unit/                     # Fast, isolated component tests
├── integration/              # Plugin and framework integration tests  
├── development/              # GUI and development workflow tests
├── hardware/                 # Hardware-specific tests (future)
└── mock_modules/             # Mock implementations for testing
```

## Test Categories

### Unit Tests (`tests/unit/`)
Fast, isolated tests for individual components without external dependencies.

```bash
pytest tests/unit/
```

**Files:**
- `test_hardware_controllers.py` - Hardware abstraction layer tests
- `test_plugin_discovery.py` - Plugin registration and entry point tests  
- `test_pymodaq_plugins.py` - Plugin class structure tests

### Integration Tests (`tests/integration/`)
Tests that verify plugin integration with PyMoDAQ framework and threading safety.

```bash
pytest tests/integration/
```

**Critical Tests:**
- `test_threading_safety_comprehensive.py` - **CRITICAL** - Prevents QThread crashes
- `test_hardware_controller_threading.py` - Hardware controller threading safety
- `test_esp300_threading_fix.py` - ESP300 specific threading validation

**Plugin Integration:**
- `test_pyrpl_plugin_integration.py` - PyRPL plugin integration validation

### Development Tests (`tests/development/`)
GUI tests and development workflow validation.

```bash
pytest tests/development/
```

**Files:**
- Development GUI launchers and system validation scripts
- Environment setup and configuration tests
- Interactive development tools

### Hardware Tests (`tests/hardware/`)
Tests requiring actual hardware connections.

```bash
pytest tests/hardware/ -m "hardware"
```

**Note**: Directory prepared for future hardware-specific test expansion.

## Mock Testing

### Mock Modules (`tests/mock_modules/`)
Mock implementations allow testing without hardware dependencies.

**Available Mocks:**
- `mock_pymodaq.py` - PyMoDAQ framework mocking
- `mock_pyvcam.py` - Camera hardware mocking
- `mock_serial.py` - Serial communication mocking

### Using Mock Mode
All plugins support mock mode for development:

```python
# Enable mock mode in any plugin
plugin.settings.child("connection_group", "mock_mode").setValue(True)

# Or via parameter path
plugin.settings.child("hardware_settings", "mock_mode").setValue(True)
```

## Running Tests

### Quick Test Commands
```bash
# All tests
python scripts/run_all_tests.py

# Specific categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests
pytest tests/development/             # Development tests

# Critical threading safety tests
pytest tests/integration/test_threading_safety_comprehensive.py
pytest tests/integration/test_hardware_controller_threading.py
```

### Test Markers
```bash
# Hardware tests (requires physical hardware)
pytest -m "hardware"

# Skip slow tests
pytest -m "not slow"

# Integration tests only
pytest -m "integration"
```

### Coverage Reporting
```bash
# Generate coverage report
pytest --cov=pymodaq_plugins_urashg --cov-report=term-missing

# HTML coverage report
pytest --cov=pymodaq_plugins_urashg --cov-report=html
```

## PyMoDAQ Standards Testing

### Threading Safety Tests ⚠️ **CRITICAL**
These tests prevent QThread crashes that cause dashboard failures:

```bash
# Must pass for PyMoDAQ compatibility
pytest tests/integration/test_threading_safety_comprehensive.py -v
```

**What these tests verify:**
- Plugin initialization without QThread conflicts
- Proper cleanup following PyMoDAQ lifecycle
- Garbage collection without crashes
- Multiple plugin creation/destruction cycles

### Plugin Compliance Tests
```bash
# Verify PyMoDAQ 5.x compliance
pytest tests/unit/test_plugin_discovery.py -v
pytest tests/integration/test_pyrpl_plugin_integration.py -v
```

**Standards verified:**
- Entry point registration
- Parameter tree structure
- Data structure usage (`DataWithAxes`, `DataActuator`)
- Signal emission patterns

## Test Results Interpretation

### Expected Results
```
Unit Tests:           ✅ All should pass
Integration Tests:    ✅ All should pass (in mock mode)
Threading Safety:     ✅ CRITICAL - Must pass for PyMoDAQ compatibility
Hardware Tests:       ⚠️ May fail without hardware (expected)
```

### Troubleshooting Test Failures

#### Threading Safety Failures
```
FAILED tests/integration/test_threading_safety_comprehensive.py
```
**Cause**: QThread conflicts in hardware controllers  
**Solution**: Review `THREADING_SAFETY_GUIDELINES.md`  
**Fix**: Remove `__del__` methods from controllers

#### Plugin Discovery Failures
```
FAILED tests/unit/test_plugin_discovery.py
```
**Cause**: Entry point registration issues  
**Solution**: Reinstall package `pip install -e .`  
**Check**: Verify `pyproject.toml` entry points

#### Import Errors
```
ModuleNotFoundError: No module named 'pymodaq_plugins_urashg'
```
**Solution**: Install in development mode:
```bash
pip install -e .
```

## Test Development Guidelines

### Adding New Tests
1. **Choose appropriate category**: unit/integration/development
2. **Use mock mode**: Avoid hardware dependencies unless specifically testing hardware
3. **Follow naming**: `test_<functionality>.py`
4. **Add markers**: Use `@pytest.mark.hardware` for hardware-dependent tests

### Test Templates
```python
# Unit test template
def test_plugin_parameter_structure():
    """Test plugin parameter tree follows PyMoDAQ standards."""
    plugin = DAQ_Move_ESP300()
    assert hasattr(plugin, 'params')
    assert isinstance(plugin.params, list)

# Integration test template  
def test_plugin_pymodaq_integration():
    """Test plugin integrates properly with PyMoDAQ framework."""
    plugin = DAQ_Move_ESP300()
    plugin.settings.child("connection_group", "mock_mode").setValue(True)
    
    result, success = plugin.ini_stage()
    assert success, f"Plugin initialization failed: {result}"
    
    plugin.close()  # Always test cleanup
```

### Mock Development
```python
# Mock hardware for consistent testing
class MockHardware:
    def __init__(self):
        self.connected = False
    
    def connect(self):
        self.connected = True
        return True
    
    def disconnect(self):
        self.connected = False
```

## Continuous Integration

### Required Tests for CI/CD
```bash
# Minimum test suite for CI
pytest tests/unit/                                                    # Fast unit tests
pytest tests/integration/test_threading_safety_comprehensive.py       # Threading safety
pytest tests/integration/test_pyrpl_plugin_integration.py            # Plugin integration
```

### GitHub Actions
Test configuration should include:
- Python 3.8, 3.9, 3.10, 3.11
- PyMoDAQ 5.0+ compatibility
- Threading safety validation
- Plugin discovery verification

## Documentation

- **`THREADING_SAFETY_GUIDELINES.md`**: Critical threading patterns for PyMoDAQ
- **`../CLAUDE.md`**: Comprehensive project documentation
- **`../README.md`**: Main repository documentation

## Contributing

1. **Add tests** for all new functionality
2. **Ensure threading safety** - run threading tests
3. **Use mock mode** for development without hardware
4. **Follow PyMoDAQ standards** - verify with unit tests
5. **Update documentation** when adding test categories

---

**Status**: Comprehensive test coverage ✅ | **Threading Safety**: Verified ✅ | **PyMoDAQ Compliance**: Tested ✅