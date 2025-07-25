# PyMoDAQ 5.0+ Migration Guide

This document outlines the migration from PyMoDAQ 4.x to 5.0+ for the URASHG plugin package.

## Overview

PyMoDAQ 5.0+ introduced significant architectural changes that required comprehensive updates to the plugin structure, data handling, and dependencies.

## Key Changes

### 1. Data Structure Migration

#### Before (PyMoDAQ 4.x)
```python
from pymodaq.utils.data import DataFromPlugins

# Old data emission pattern
data = DataFromPlugins(
    name="PrimeBSI", 
    data=[frame], 
    dim="Data2D", 
    axes=[y_axis, x_axis]
)
self.data_grabed_signal.emit([data])
```

#### After (PyMoDAQ 5.0+)
```python
from pymodaq_data.data import Axis, DataWithAxes, DataToExport, DataSource

# New data emission pattern
dwa_2d = DataWithAxes(
    name="PrimeBSI", 
    source=DataSource.raw, 
    data=[frame], 
    axes=[y_axis, x_axis]
)
dte = DataToExport(name="PrimeBSI_Data", data=[dwa_2d])
self.dte_signal.emit(dte)
```

### 2. Qt Framework Update

#### Before (PyMoDAQ 4.x)
```toml
# pyproject.toml
dependencies = [
    "PyQt5>=5.15.0",
]
```

#### After (PyMoDAQ 5.0+)
```toml
# pyproject.toml
dependencies = [
    "PySide6>=6.0.0",
]
```

### 3. PyMoDAQ Dependencies

#### Before (PyMoDAQ 4.x)
```toml
dependencies = [
    "pymodaq>=4.0.0",
    "pymodaq-gui>=4.0.0",
]
```

#### After (PyMoDAQ 5.0+)
```toml
dependencies = [
    "pymodaq>=5.0.0",
    "pymodaq-gui>=5.0.0",
    "pymodaq-data>=5.0.0",
    "pymodaq-utils>=0.0.14",
]
```

### 4. Signal Changes

#### Before (PyMoDAQ 4.x)
```python
self.data_grabed_signal.emit([data])
```

#### After (PyMoDAQ 5.0+)
```python
self.dte_signal.emit(dte)
```

### 5. Import Structure Updates

#### Before (PyMoDAQ 4.x)
```python
from pymodaq.utils.data import DataFromPlugins
from pymodaq.utils.parameter.utils import get_param_path, iter_children
```

#### After (PyMoDAQ 5.0+)
```python
from pymodaq_data.data import Axis, DataWithAxes, DataToExport, DataSource
# Note: get_param_path and iter_children are no longer needed
```

## Migration Steps

### Step 1: Update Dependencies

1. Update `pyproject.toml`:
   ```bash
   # Update PyMoDAQ dependencies to 5.0+
   # Change PyQt5 to PySide6
   # Add new required packages
   ```

2. Update `plugin_info.toml`:
   ```toml
   [plugin-info.packages]
   pyside6 = ">=6.0.0"
   pymodaq = ">=5.0.0"
   ```

### Step 2: Update Data Structures

1. Replace all `DataFromPlugins` instances:
   ```python
   # Find and replace pattern
   DataFromPlugins(name="...", data=[...], dim="Data2D", axes=[...])
   # with
   dwa = DataWithAxes(name="...", source=DataSource.raw, data=[...], axes=[...])
   dte = DataToExport(name="...", data=[dwa])
   ```

2. Update signal emissions:
   ```python
   # Replace
   self.data_grabed_signal.emit([data])
   # with
   self.dte_signal.emit(dte)
   ```

### Step 3: Remove Unused Imports

Remove deprecated utility imports:
```python
# Remove these lines
from pymodaq.utils.parameter.utils import get_param_path, iter_children
```

### Step 4: Update Entry Points

Ensure consistency between `pyproject.toml` and `plugin_info.toml`:

**pyproject.toml**:
```toml
[project.entry-points."pymodaq.move_plugins"]
DAQ_Move_Elliptec = "pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec"

[project.entry-points."pymodaq.viewer_plugins"]
DAQ_2DViewer_PrimeBSI = "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI"
```

### Step 5: Test Migration

1. Run unit tests:
   ```bash
   pytest tests/ -v
   ```

2. Verify plugin discovery:
   ```python
   import pkg_resources
   plugins = list(pkg_resources.iter_entry_points('pymodaq.move_plugins'))
   print(plugins)
   ```

3. Test in PyMoDAQ Dashboard:
   ```python
   python -m pymodaq.dashboard
   ```

## Common Issues and Solutions

### Issue 1: Import Errors
**Problem**: `ImportError: cannot import name 'DataFromPlugins'`

**Solution**: Update imports to use the new data structure:
```python
from pymodaq_data.data import DataWithAxes, DataToExport, DataSource
```

### Issue 2: Signal Not Working
**Problem**: Data not appearing in PyMoDAQ viewer

**Solution**: Ensure you're using the correct signal:
```python
self.dte_signal.emit(dte)  # Not data_grabed_signal
```

### Issue 3: Qt Import Errors
**Problem**: `ImportError: No module named 'PyQt5'`

**Solution**: Update dependencies to PySide6 and update isort configuration:
```toml
[tool.isort]
known_third_party = ["PySide6", "pymodaq", "numpy"]
```

### Issue 4: Plugin Not Discoverable
**Problem**: Plugin doesn't appear in PyMoDAQ

**Solution**: Check entry point configuration matches between files and reinstall:
```bash
pip install -e .
```

## Testing Migration

### Container-based Testing

For isolated testing, use container environments:

```bash
# Create test environment
container-use create test-env

# Install and test
pip install -e .
pytest tests/ -v
```

### Validation Checklist

- [ ] All imports resolve correctly
- [ ] Unit tests pass (8/8)
- [ ] Entry points are discoverable
- [ ] Plugin loads in PyMoDAQ Dashboard
- [ ] Data emission works correctly
- [ ] No linting errors
- [ ] Dependencies install cleanly

## Backward Compatibility

**Important**: This migration breaks backward compatibility with PyMoDAQ 4.x.

- For PyMoDAQ 4.x, use package version `<1.0.0`
- For PyMoDAQ 5.0+, use package version `>=1.0.0`

## Support

If you encounter issues during migration:

1. Check this guide for common solutions
2. Run the test suite to identify specific problems
3. Open an issue on GitHub with detailed error messages
4. Contact the PyMoDAQ community for support

---

*This migration was completed in January 2025 with comprehensive testing in isolated container environments.*