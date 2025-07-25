# PyMoDAQ GUI Integration Setup Guide

This guide explains how to set up and test the PyMoDAQ GUI integration for the URASHG plugins.

## Current Status

[READY] **Plugin Development**: All three URASHG plugins are implemented and tested  
[READY] **Mock Testing**: All plugins pass integration tests in mock mode  
[READY] **Package Installation**: Plugin package is installed in development mode  
⚠️ **GUI Integration**: PyMoDAQ version compatibility issues detected  

## Environment Setup

### 1. PyMoDAQ Installation

The current PyMoDAQ installation (v5.0.18) has compatibility issues with the pymodaq_data package. To resolve this:

```bash
# Option 1: Fresh PyMoDAQ installation
pip uninstall pymodaq pymodaq-data pymodaq-gui pymodaq-utils
pip install pymodaq>=5.0.0

# Option 2: Use conda environment (recommended)
conda create -n pymodaq python=3.11
conda activate pymodaq
conda install -c conda-forge pyqt
pip install pymodaq

# Option 3: Use specific compatible versions
pip install pymodaq==4.4.11 pymodaq-data==4.4.11
```

### 2. Plugin Installation

```bash
cd /Users/briansquires/serena_projects/pymodaq_plugins_urashg
pip install -e .
```

## GUI Testing Options

### Option 1: Full PyMoDAQ Dashboard (Recommended)

Once PyMoDAQ is properly installed, launch the dashboard:

```bash
# Method 1: Python module
python -c "from pymodaq.dashboard import DashBoard; DashBoard().show()"

# Method 2: Direct script execution
python -m pymodaq.dashboard

# Method 3: If available, command line tool
pymodaq
```

**Steps to test plugins in Dashboard:**

1. **Launch PyMoDAQ Dashboard**
2. **Add Move Modules**: 
   - Click "Add Module" → "Move"
   - Select "DAQ_Move_Elliptec" from dropdown
   - Configure parameters and test connection
   - Repeat for "DAQ_Move_MaiTai"

3. **Add Viewer Module**:
   - Click "Add Module" → "Viewer" → "2D"
   - Select "DAQ_2DViewer_PrimeBSI" from dropdown
   - Configure camera parameters

4. **Test Mock Mode**:
   - All plugins are designed to work without hardware
   - Serial communication will simulate responses
   - Camera will use dummy data

### Option 2: Individual Plugin Testing

Use the provided test launcher for individual plugin testing:

```bash
python launch_gui_test.py
```

This script provides:
- Plugin import verification
- Individual plugin GUI tests
- Plugin parameter inspection
- Mock operation testing

### Option 3: Jupyter Notebook Testing

Create a Jupyter notebook for interactive testing:

```python
# Cell 1: Import and test plugins
import sys
sys.path.insert(0, 'src')

from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI

print("All plugins imported successfully!")

# Cell 2: Inspect plugin parameters
elliptec = DAQ_Move_Elliptec()
print("Elliptec Parameters:", len(elliptec.params))
print("Axes:", elliptec._axis_names)
print("Commands:", len(elliptec._command_reference))
```

## Troubleshooting

### Issue 1: Import Error `cannot import name 'Q_' from 'pymodaq_data'`

**Solution**: PyMoDAQ version compatibility issue

```bash
# Uninstall all PyMoDAQ packages
pip uninstall pymodaq pymodaq-data pymodaq-gui pymodaq-utils pymodaq-plugin-manager

# Reinstall with specific version
pip install pymodaq==4.4.11

# Or try latest stable
pip install pymodaq --upgrade --force-reinstall
```

### Issue 2: GUI Not Launching

**Solution**: Qt/GUI environment issues

```bash
# Install Qt backend
pip install PySide6>=6.0.0
# or
pip install PyQt6>=6.0.0

# For macOS, you may need:
brew install qt5
export QT_API=pyside6
```

### Issue 3: Plugin Not Found in Dashboard

**Solution**: Entry point registration

```bash
# Reinstall plugin in development mode
pip install -e . --force-reinstall

# Verify entry points
python -c "import pkg_resources; print([ep for ep in pkg_resources.iter_entry_points('pymodaq.move_plugins')])"
```

## Plugin Features in GUI

### Elliptec Plugin GUI Features:
- **Multi-axis control**: HWP_inc, QWP, HWP_ana
- **Serial port configuration**: COM port selection
- **Position control**: Absolute positioning in degrees
- **Motor optimization**: Built-in optimization routine
- **Status monitoring**: Real-time error code display
- **Home positioning**: Automatic homing on connect

### MaiTai Plugin GUI Features:
- **Wavelength control**: Tunable laser wavelength
- **Shutter control**: Open/close laser shutter
- **Status monitoring**: Background thread monitoring
- **Power display**: Real-time output power
- **System status**: Warm-up percentage, pulsing status
- **Safety indicators**: Laser on/off status

### Prime BSI Camera Plugin GUI Features:
- **Dynamic parameters**: Auto-discovered camera settings
- **ROI control**: Region of interest selection
- **Exposure control**: Adjustable exposure time
- **Gain settings**: Camera gain configuration
- **Temperature monitoring**: Sensor temperature display
- **Trigger modes**: Internal/external triggering
- **Data export**: 2D image + 0D integrated signal

## Mock Mode Operation

All plugins are designed to work in mock mode without hardware:

1. **Serial Communication**: Simulated using mock objects
2. **Camera Interface**: PyVCAM fallback provides dummy data
3. **Hardware Responses**: Pre-programmed realistic responses
4. **Parameter Validation**: Full parameter checking without hardware
5. **Status Updates**: Simulated status changes and monitoring

## Next Steps

1. **Resolve PyMoDAQ compatibility** by installing a compatible version
2. **Launch PyMoDAQ Dashboard** using one of the methods above
3. **Add URASHG plugin modules** to the dashboard
4. **Configure mock parameters** for testing
5. **Test plugin functionality** in mock mode
6. **Connect real hardware** when ready for actual measurements

## Hardware Integration

When ready to connect real hardware:

1. **Elliptec Mounts**: Connect via USB-to-serial adapters
2. **MaiTai Laser**: Connect to serial/Ethernet interface
3. **Prime BSI Camera**: Install PyVCAM drivers and connect via USB 3.0
4. **Update Configuration**: Modify COM ports and addresses in plugin settings
5. **Test Hardware**: Verify communication and basic operation

The plugins are fully ready for hardware integration once the GUI environment is properly configured.