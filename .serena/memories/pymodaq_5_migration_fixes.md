# PyMoDAQ 5.0+ Migration Fixes Applied

## Critical Data Structure Changes
- **DataFromPlugins Removal**: PyMoDAQ 5.0+ completely removed `DataFromPlugins` class
- **New Pattern**: Replaced with `DataWithAxes` + `DataToExport` combination
- **Signal Change**: `data_grabed_signal` → `dte_signal` for data emission
- **DataSource Specification**: Required `DataSource.raw` vs `DataSource.calculated` specification

## Dependency Updates
- **Qt Framework**: PyQt5 → PySide6 (≥6.0.0) for PyMoDAQ 5.0+ compatibility
- **PyMoDAQ Core**: Updated to ≥5.0.0 with all sub-packages (gui, data, utils)
- **Import Structure**: Fixed import paths to match PyMoDAQ 5.0+ module organization

## Code Quality Fixes
- **Unused Imports**: Removed `get_param_path`, `iter_children` utilities (no longer used)
- **Line Length**: Fixed violations exceeding 88 characters using black formatter
- **Entry Points**: Synchronized between pyproject.toml and plugin_info.toml

## Testing Validation
- **Container Environments**: Used `container-use` for isolated testing
- **All Tests Pass**: 8/8 unit tests pass without hardware dependencies
- **Plugin Discovery**: Confirmed entry points work with PyMoDAQ framework
- **Mock Device Support**: Hardware abstraction allows testing without physical devices

## Files Modified
- `src/pymodaq_plugins_urashg/daq_viewer_plugins/plugins_2D/DAQ_Viewer_PrimeBSI.py`
- `src/pymodaq_plugins_urashg/daq_move_plugins/DAQ_Move_Elliptec.py`  
- `src/pymodaq_plugins_urashg/daq_move_plugins/DAQ_Move_MaiTai.py`
- `pyproject.toml` (dependencies and entry points)
- `plugin_info.toml` (PyMoDAQ metadata)