# URASHG PyMoDAQ UI and Stability Fixes

## Issues Resolved

### ✅ MaiTai Laser UI Enhanced
**Problem**: No shutter control, poor wavelength interface, shutter buttons buried in submenus  
**Solution**: Added comprehensive control interface:
- **Target Wavelength**: Integer input field (700-900nm) with validation
- **Set Wavelength Button**: Applies target wavelength to hardware
- **Open/Close Shutter Buttons**: Direct shutter control (moved to main control group)
- **Real-time Status**: Current wavelength, power, shutter state
- **Hardware Controller**: Added missing `open_shutter()` and `close_shutter()` convenience methods

### ✅ Elliptec Multi-Axis Support  
**Problem**: 3 rotators not clearly visible in UI  
**Solution**: Enhanced axis naming and configuration:
- **HWP_Incident**: Half-wave plate incident polarizer (address 2)
- **QWP**: Quarter-wave plate (address 3) 
- **HWP_Analyzer**: Half-wave plate analyzer (address 8)
- **Multi-axis**: All 3 axes exposed in PyMoDAQ interface

### ✅ X11 Stability Solutions
**Problem**: X11 connection breaking on menu hover  
**Solutions**: Multiple launcher options:

1. **`launch_daq_move_ultimate.sh`** - Direct X11 with maximum stability
2. **`launch_daq_move_vnc.sh`** - VNC-based (most stable)
3. **`launch_daq_move_robust.sh`** - Original robust approach

## Usage

### Recommended (Ultimate Stability):
```bash
./launch_daq_move_ultimate.sh
```

### For Persistent Sessions:
```bash
./launch_daq_move_vnc.sh
# Then connect VNC viewer to hostname:5901
```

### Features Now Available:

#### MaiTai Plugin:
- ✅ **Wavelength Control**: Set target wavelength with validation
- ✅ **Shutter Control**: Open/close buttons directly visible in main control group
- ✅ **Real-time Monitoring**: Live wavelength, power, shutter state
- ✅ **Hardware Integration**: Direct MaiTai laser communication
- ✅ **UI Accessibility**: No nested submenus - all controls at top level

#### Elliptec Plugin:
- ✅ **Multi-Axis Control**: 3 independent rotation mounts
- ✅ **Clear Naming**: HWP_Incident, QWP, HWP_Analyzer
- ✅ **Individual Control**: Each mount controllable separately
- ✅ **Position Monitoring**: Real-time position feedback

#### All Plugins:
- ✅ **Hardware Discovery**: All 5 plugins visible in PyMoDAQ
- ✅ **Stable Connections**: No repeated connect/disconnect cycles
- ✅ **Error Handling**: Comprehensive error reporting and recovery

## Expected Behavior

1. **Launch Success**: PyMoDAQ starts without X11 crashes
2. **Plugin Visibility**: All URASHG plugins appear in dropdown menus
3. **MaiTai Interface**: Shows wavelength input, set button, and shutter controls directly in main control group
4. **Elliptec Interface**: Shows 3 separate axis controls for the rotators  
5. **Stable Operation**: No crashes on menu hover or hardware interaction
6. **Shutter Accessibility**: Open/Close shutter buttons visible without clicking submenus

## Troubleshooting

If X11 still crashes:
1. Try VNC approach: `./launch_daq_move_vnc.sh`
2. Check SSH X11 forwarding: `ssh -Y -C user@host`
3. Verify X11 working: `xeyes` should display without crashes

If plugins missing:
1. Verify installation: `pip list | grep urashg`
2. Check plugin discovery: `python -c "from pymodaq.utils.daq_utils import get_plugins; print(len(get_plugins()))"`