# PyVCAM 2.2.3 Compatibility Fix - Final Solution

## Issue Resolution
Fixed critical PyVCAM compatibility issue that prevented PrimeBSI camera plugin from working.

## Root Cause
PyVCAM 2.2.3 does not have `pyvcam.enums` module. Original code was importing:
```python
from pyvcam.enums import ClearMode, Param, TriggerMode
```

## Solution Applied
Updated to use constants module:
```python
from pyvcam.constants import CLEAR_NEVER, CLEAR_PRE_SEQUENCE, EXT_TRIG_INTERNAL
```

## Additional Fixes
1. **PVCAM State Management**: Added proper `pvc.uninit_pvcam()` before `pvc.init_pvcam()`
2. **Camera Detection**: Fixed inconsistency between `pvc.get_cam_total()` and `Camera.detect_camera()`
3. **Mock Constants**: Added PARAM_* constants to mock tests for advanced parameter handling

## Verification
- Camera detected as `pvcamUSB_0` with 2048x2048 sensor
- Plugin initializes successfully with real hardware
- All PyVCAM functions working correctly

## Files Modified
- `src/pymodaq_plugins_urashg/daq_viewer_plugins/plugins_2D/daq_2Dviewer_PrimeBSI.py`
- `tests/test_primebsi_camera.py`