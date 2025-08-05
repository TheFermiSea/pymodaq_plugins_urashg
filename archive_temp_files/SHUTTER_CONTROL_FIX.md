# MaiTai Shutter Control Fix

## Issue Resolved
**Problem**: User reported "I am still unable to close the shutter on the maitai. There is no button in the daq_move window, and when I click 'close shutter' in the control menu (have to click a button to open it) nothing happens"

## Root Causes Identified
1. **UI Accessibility**: Shutter controls were buried in nested subgroups (`control_group` → `shutter_control` → buttons)
2. **Missing Hardware Methods**: Plugin was calling `open_shutter()` and `close_shutter()` methods that didn't exist in the hardware controller

## Fixes Applied

### 1. Hardware Controller Enhancement
**File**: `src/pymodaq_plugins_urashg/hardware/urashg/maitai_control.py`

Added convenience methods:
```python
def open_shutter(self) -> bool:
    """Open shutter (convenience method)."""
    return self.set_shutter(True)

def close_shutter(self) -> bool:
    """Close shutter (convenience method).""" 
    return self.set_shutter(False)
```

### 2. UI Structure Improvement
**File**: `src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_MaiTai.py`

**Before** (nested structure):
```
Laser Control
└── Shutter Control (subgroup)
    ├── Open Shutter
    └── Close Shutter
```

**After** (flat structure):
```
Laser Control
├── Target Wavelength
├── Set Wavelength
├── Open Shutter
└── Close Shutter
```

## Testing Verification
Created comprehensive test suite (`test_maitai_shutter.py`) that validates:
- ✅ Hardware controller methods work properly
- ✅ UI parameter structure is correct  
- ✅ Shutter buttons are at top level of control group
- ✅ All buttons are properly configured as actions

## Result
**Shutter controls are now directly visible in the main Laser Control group:**
- No more nested submenus to navigate
- Open Shutter and Close Shutter buttons work immediately when clicked
- Real-time shutter state monitoring in Status group
- Full hardware integration with proper error handling

The user should now be able to see and use the shutter controls without any navigation issues.