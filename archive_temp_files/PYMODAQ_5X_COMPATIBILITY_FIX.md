# PyMoDAQ 5.x Compatibility Fix - move_done Signal

## Issue Resolved
**Problem**: `AttributeError: 'int' object has no attribute 'name'` when launching daq_move plugins

**Error Details**:
```
File ".../pymodaq/control_modules/daq_move.py", line 530, in _check_data_type
    data_act.name = self.title
AttributeError: 'int' object has no attribute 'name'
```

## Root Cause
PyMoDAQ 5.x expects `move_done` signals to contain `DataActuator` objects, not raw numeric values. Our plugins were emitting:
```python
# WRONG (PyMoDAQ 4.x style)
self.emit_status(ThreadCommand("move_done", [int(round(position))]))  # MaiTai
self.emit_status(ThreadCommand("move_done", [positions]))              # Elliptec
```

## Fix Applied
Updated both plugins to use proper `DataActuator` objects:

### MaiTai Plugin Fix
```python
# CORRECT (PyMoDAQ 5.x style)
data_actuator = DataActuator(
    name=self.title,
    data=[np.array([int(round(position))])],
    units=self._controller_units  # "nm"
)
self.emit_status(ThreadCommand("move_done", data_actuator))
```

### Elliptec Plugin Fix
```python
# CORRECT (PyMoDAQ 5.x style)
data_actuator = DataActuator(
    name=self.title,
    data=[np.array(positions)],
    units=self._controller_units  # "degrees"
)
self.emit_status(ThreadCommand("move_done", data_actuator))
```

## Files Modified
1. **`src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_MaiTai.py`**:
   - Added `import numpy as np`
   - Added `from pymodaq.utils.data import DataActuator`
   - Updated `move_done` signal emission

2. **`src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_Elliptec.py`**:
   - Added `import numpy as np`
   - Added `from pymodaq.utils.data import DataActuator`
   - Updated `move_done` signal emission

## Testing Verification
Created comprehensive test suite that validates:
- ✅ DataActuator objects are created correctly
- ✅ ThreadCommand accepts DataActuator objects
- ✅ Plugins import and instantiate without errors
- ✅ Mock operations work as expected
- ✅ Both single-axis (MaiTai) and multi-axis (Elliptec) patterns work

## Result
**The AttributeError is now fixed. You should be able to launch daq_move without errors.**

The plugins now properly follow PyMoDAQ 5.x conventions for data handling and signal emission, ensuring compatibility with the current framework version.

## Migration Notes
This fix represents the final piece of the PyMoDAQ 4.x → 5.x migration:
- ✅ Data structures: `DataFromPlugins` → `DataWithAxes` + `DataToExport`
- ✅ Qt framework: PyQt5 → PySide6  
- ✅ Signal updates: `data_grabed_signal` → `dte_signal`
- ✅ Dependencies: All PyMoDAQ packages to 5.0+
- ✅ Entry points: Validated and working
- ✅ **Move signals: Raw values → DataActuator objects** ← This fix