# PyMoDAQ URASHG Plugin Development Guide

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Quick Setup and Validation
- **Package validation** (FAST - works offline):
  - `cd /path/to/pymodaq_plugins_urashg`
  - `python -c "import sys; sys.path.insert(0, 'src'); import pymodaq_plugins_urashg; print('✅ Package imports OK')"`
  - **Takes**: < 0.1 seconds

### Installation and Dependencies
- **NEVER CANCEL**: Installation can take 60+ seconds even when failing due to network timeouts
- **Primary installation** (requires network, 2-5 minutes when working):
  - `python -m pip install --upgrade pip` -- **NEVER CANCEL: Takes 30-60 seconds**
  - `pip install -e .` -- **NEVER CANCEL: Takes 2-5 minutes, may timeout after 60 seconds**
  - `pip install -e .[dev]` -- **NEVER CANCEL: Takes 3-6 minutes for development dependencies**
- **Fallback installation** (when network fails):
  - `pip install --no-deps -e .` -- **NEVER CANCEL: Takes 30 seconds, will fail on build dependencies**
  - Manual dependency installation requires network access
- **Installation validation**: Network timeouts are common and expected - document as "fails due to network limitations"

### Testing (Multiple Approaches Available)
- **Basic validation** (FAST - works offline):
  - `python scripts/run_all_tests.py` -- **Fails without numpy** but validates environment quickly
  - `python tests/run_compliance_tests.py` -- **Fails without pytest** but shows test structure
  - **Takes**: < 0.1 seconds to fail gracefully with clear error messages
- **Full test suite** (requires dependencies):
  - `pip install pytest pytest-cov pytest-xvfb numpy` -- **NEVER CANCEL: Takes 2-3 minutes**
  - `python -m pytest tests/ -v` -- **NEVER CANCEL: Takes 5-10 minutes for full test suite**
  - `python -m pytest tests/test_pymodaq_compliance.py -v` -- **NEVER CANCEL: Takes 2-3 minutes**
- **Quick offline validation**:
  - `python -c "import ast; [ast.parse(open(f).read()) for f in ['src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_Elliptec.py']]"` -- syntax check
  - **Takes**: < 0.01 seconds per file

### Code Quality (Mixed Availability)
- **Formatting** (requires installation):
  - `pip install black isort flake8` -- **NEVER CANCEL: Takes 1-2 minutes**
  - `black src/` -- **Takes**: 2-5 seconds
  - `isort src/` -- **Takes**: 1-3 seconds
- **Linting** (requires installation):
  - `flake8 src/` -- **Takes**: 3-8 seconds
- **Basic syntax checking** (works offline):
  - `python -c "import ast, os; [ast.parse(open(os.path.join(r,f)).read()) for r,d,fs in os.walk('src') for f in fs if f.endswith('.py')]"` -- **Takes**: < 0.1 seconds

### GUI and Application Testing
- **GUI launcher** (requires full dependencies):
  - `python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py` -- **Fails without numpy/Qt**
  - **Mock mode testing**: Requires PyMoDAQ ecosystem installed
  - **NEVER CANCEL: GUI startup takes 10-30 seconds when working**
- **Plugin discovery validation** (works offline):
  - `python -c "print([line for line in open('pyproject.toml').readlines() if 'DAQ_Move_' in line or 'DAQ_2DViewer_' in line or 'URASHGMicroscopyExtension' in line])"`
  - **Takes**: < 0.01 seconds

## Validation Scenarios

### Always Test After Changes
1. **Plugin discovery validation** (offline, fast):
   ```bash
   python -c "
   with open('pyproject.toml') as f: content = f.read()
   move_plugins = content.count('DAQ_Move_')
   viewer_plugins = content.count('DAQ_2DViewer_') + content.count('DAQ_0DViewer_')
   extensions = content.count('URASHGMicroscopyExtension')
   print(f'Plugins: {move_plugins} move, {viewer_plugins} viewer, {extensions} extension')
   assert move_plugins >= 3 and viewer_plugins >= 2 and extensions >= 1, 'Missing plugins'
   print('✅ Plugin discovery OK')
   "
   ```

2. **Code syntax validation** (offline, fast):
   ```bash
   python -c "
   import ast, os
   files = [os.path.join(r,f) for r,d,fs in os.walk('src') for f in fs if f.endswith('.py')]
   for f in files:
       with open(f) as file: ast.parse(file.read())
   print(f'✅ Syntax valid for {len(files)} files')
   "
   ```

3. **PyMoDAQ 5.x compliance check** (when pytest available):
   ```bash
   python -m pytest tests/test_pymodaq_compliance.py -v
   ```
   -- **NEVER CANCEL: Takes 2-3 minutes**

4. **Mock device testing** (when full environment available):
   ```bash
   PYMODAQ_TEST_MODE=mock python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py
   ```
   -- **NEVER CANCEL: Takes 10-30 seconds to start, test for 30-60 seconds**

## Build Process

### Package Building
- **Build requirements**:
  - `pip install build twine` -- **NEVER CANCEL: Takes 1-2 minutes**
- **Build commands**:
  - `python -m build` -- **NEVER CANCEL: Takes 30-90 seconds**
  - `twine check dist/*` -- **Takes**: 5-10 seconds

### Documentation
- **Documentation serving** (works offline):
  - `python -m http.server 8000 --directory docs/` -- serves existing docs
  - **Takes**: instant startup, runs continuously
- **Documentation validation** (offline):
  - Check key files exist: `README.md`, `CLAUDE.md`, `pyproject.toml`, `plugin_info.toml`

## Common Problems and Solutions

### Network Timeouts
- **Problem**: `pip install` commands fail with "Read timed out"
- **Solution**: Document as expected behavior, provide offline validation alternatives
- **Expected timing**: 60+ seconds before timeout

### Missing Dependencies
- **Problem**: Tests fail with "No module named 'pytest'" or "No module named 'numpy'"
- **Solution**: Use offline validation methods or document dependency requirements
- **Working offline**: Package structure validation, syntax checking, plugin discovery work without dependencies

### GUI Testing Without Hardware
- **Problem**: Need to test GUI functionality without physical hardware
- **Solution**: Set `PYMODAQ_TEST_MODE=mock` environment variable for mock device simulation
- **Alternative**: Use plugin discovery and syntax validation as substitutes

### Plugin Development Workflow
1. **Create new plugin file**: `touch src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_NewDevice.py`
2. **Add entry point**: Edit `pyproject.toml` under appropriate plugin section
3. **Validate syntax**: Use offline syntax checking command above
4. **Test discovery**: Use plugin discovery validation command above
5. **Full testing**: When dependencies available, run compliance tests

## Important File Locations

### Source Code
- **Main plugins**: `src/pymodaq_plugins_urashg/daq_move_plugins/`, `src/pymodaq_plugins_urashg/daq_viewer_plugins/`
- **Extensions**: `src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py`
- **Hardware abstraction**: `src/pymodaq_plugins_urashg/hardware/urashg/`

### Configuration
- **Package config**: `pyproject.toml` (entry points, dependencies, build settings)
- **Plugin metadata**: `plugin_info.toml`
- **Documentation**: `README.md`, `CLAUDE.md` (comprehensive development guide)

### Testing
- **Test suites**: `tests/unit/` (18 files), `tests/hardware/` (2 files)
- **Test runners**: `scripts/run_all_tests.py`, `tests/run_compliance_tests.py`
- **CI configuration**: `.github/workflows/ci.yml`

### Quick Reference Commands Summary
```bash
# Offline validation (always works, < 0.1s each)
python -c "import sys; sys.path.insert(0, 'src'); import pymodaq_plugins_urashg"
python -c "import ast; ast.parse(open('src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_Elliptec.py').read())"

# Online installation (2-5 minutes, NEVER CANCEL)
pip install -e .[dev]

# Testing (5-10 minutes when working, NEVER CANCEL)
python -m pytest tests/ -v

# Code quality (1-3 minutes setup, 5-10 seconds execution)
pip install black isort flake8  # Setup once
black src/ && isort src/ && flake8 src/

# GUI testing (10-30 seconds startup when working, NEVER CANCEL)
PYMODAQ_TEST_MODE=mock python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py
```

## Expected Timing Reference
- **Package validation**: < 0.1 seconds (offline)
- **Syntax checking**: < 0.1 seconds (offline)  
- **Plugin discovery**: < 0.01 seconds (offline)
- **pip install basic**: 60+ seconds (may timeout)
- **pip install full**: 2-5 minutes (NEVER CANCEL)
- **Test suite full**: 5-10 minutes (NEVER CANCEL)
- **GUI startup**: 10-30 seconds (NEVER CANCEL)
- **Code formatting**: 2-5 seconds (after install)
- **Package build**: 30-90 seconds (NEVER CANCEL)

This is a PyMoDAQ 5.x compliant plugin package for μRASHG microscopy systems with comprehensive testing infrastructure, mock device support, and professional CI/CD pipeline.