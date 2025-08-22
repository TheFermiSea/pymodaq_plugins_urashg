# PyMoDAQ URASHG Plugin Package

A **PyMoDAQ 5.x compliant** plugin package for **μRASHG (micro Rotational Anisotropy Second Harmonic Generation)** microscopy systems. This package provides complete hardware control and experimental automation for polarimetric SHG measurements following PyMoDAQ standards.

## Overview

The URASHG plugin package enables sophisticated polarimetric second harmonic generation measurements through PyMoDAQ's modular framework with full PyMoDAQ 5.x compliance:

- **Standards-compliant architecture**: Follows PyMoDAQ plugin development guidelines
- **Multi-device coordination**: Integrated laser control, polarization optics, cameras, and power meters
- **Real-time data acquisition**: High-speed polarimetric measurements with PyMoDAQ framework integration
- **Unified extension**: Single comprehensive extension for complete system control
- **Hardware abstraction**: Works with real hardware or simulation mode

## PyMoDAQ 5.x Compliance

This plugin package has been designed and tested for full compliance with PyMoDAQ 5.x standards:

### Architecture Standards
- **Hatchling build system**: Uses PyMoDAQ's standard build backend with dynamic entry point generation
- **Single primary extension**: `URASHGMicroscopyExtension` provides comprehensive system control
- **Standard plugin structure**: Proper separation of move plugins, viewer plugins, and hardware abstraction
- **Configuration management**: Implements PyMoDAQ's Config class pattern with template-based configuration

### Plugin Discovery
- **Dynamic entry points**: Automatic plugin discovery via PyMoDAQ's hatchling build hooks
- **Feature declarations**: Proper `[features]` section in `pyproject.toml`
- **Version management**: Uses PyMoDAQ's version management utilities

### Code Quality
- **Import standards**: Consistent use of PyMoDAQ import patterns
- **Error handling**: Proper PyMoDAQ exception handling and status reporting
- **Type safety**: Modern Python typing with PyMoDAQ data structures
- **Documentation**: Comprehensive inline documentation following PyMoDAQ conventions

## Hardware Support

### **Cameras**
- **Photometrics Prime BSI** - sCMOS camera with PyVCAM integration
- Full camera control: exposure, gain, ROI, readout modes
- Real-time SHG image acquisition

### **Motion Control**
- **Thorlabs ELL14 Rotation Mounts** - Polarization control (QWP, HWP)
- **MaiTai Laser** - Wavelength control and EOM power modulation  
- **Newport ESP300** - Precision positioning stages
- **Red Pitaya PID** - Laser stabilization (optional)

### **Detection**
- **Newport 1830-C Power Meter** - Optical power monitoring
- Real-time power measurements during scans

## Installation

### Prerequisites

1. **PVCAM SDK** (for camera support):
   ```bash
   # Download from Photometrics and install to /opt/pvcam
   # Ensure the following files exist:
   ls /opt/pvcam/sdk/include/pvcam.h
   ls /etc/profile.d/pvcam-sdk.sh
   ```

2. **Python Environment**:
   ```bash
   # Requires Python 3.9+
   python --version  # Should be 3.9 or higher
   ```

### Installation Steps

1. **Clone and setup**:
   ```bash
   git clone https://github.com/PyMoDAQ/pymodaq_plugins_urashg.git
   cd pymodaq_plugins_urashg
   ```

2. **Install with UV** (recommended):
   ```bash
   # Install UV package manager if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Create virtual environment and install
   uv venv
   source .venv/bin/activate
   source /etc/profile.d/pvcam-sdk.sh  # Load PVCAM environment
   uv pip install -e .
   ```

3. **Alternative: Install with pip**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   source /etc/profile.d/pvcam-sdk.sh
   pip install -e .
   ```

### Verify Installation

```bash
# Test PyVCAM integration
python -c "
import pyvcam
from pyvcam import pvc
print('✓ PyVCAM available')
pvc.init_pvcam()
print(f'✓ PVCAM initialized, {pvc.get_cam_total()} cameras found')
pvc.uninit_pvcam()
"

# Test plugin discovery
python -c "
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
print('✓ All plugins import successfully')
"
```

## Quick Start

### Option 1: Use Startup Script (Recommended)

```bash
./start_pymodaq_urashg.sh
```

This script automatically:
- Sets up the PVCAM environment
- Tests plugin availability  
- Launches PyMoDAQ dashboard with options

### Option 2: Manual Launch

```bash
# Setup environment
source .venv/bin/activate
source /etc/profile.d/pvcam-sdk.sh

# Launch PyMoDAQ Dashboard
python -m pymodaq.dashboard
```

Then look for URASHG plugins in:
- **Move plugins**: `Add Module → Move → DAQ_Move_Elliptec, DAQ_Move_MaiTai, DAQ_Move_ESP300`
- **Viewer plugins**: `Add Module → Viewer → DAQ_2DViewer_PrimeBSI, DAQ_0DViewer_Newport1830C`
- **Extensions**: `Extensions → URASHGMicroscopyExtension`

## Plugin Overview

### 🎥 **Camera Plugin: DAQ_2DViewer_PrimeBSI**

**Features:**
- Real-time SHG imaging with Photometrics Prime BSI
- Full PyVCAM integration with hardware control
- Simulation mode for development without hardware
- ROI selection and binning support
- Temperature monitoring and control

**Key Parameters:**
- Exposure time: 1-10000 ms
- Gain settings: 1x, 2x, 4x  
- Readout ports: Multiple port selection
- Clear modes: Pre-sequence, Never
- ROI: Configurable region of interest

### 🔄 **Motion Plugins**

#### **DAQ_Move_Elliptec** - Polarization Control
- Controls up to 3 Thorlabs ELL14 rotation mounts
- Axes: HWP Incident, QWP, HWP Analyzer  
- Serial communication with multi-drop addressing
- Precision: 0.1° angular resolution

#### **DAQ_Move_MaiTai** - Laser Control  
- Wavelength control: 700-1000 nm
- EOM power modulation support
- Serial communication with status monitoring
- Real-time wavelength feedback

#### **DAQ_Move_ESP300** - Positioning
- Newport ESP300 motion controller
- Multiple axis coordination
- Precision positioning for sample manipulation

### 📊 **Power Meter Plugin: DAQ_0DViewer_Newport1830C**

- Real-time optical power monitoring
- Multiple wavelength support
- Integration with measurement sequences
- Auto-ranging and averaging

### 🔬 **Extension: URASHGMicroscopyExtension**

**Complete experimental control:**
- Multi-device coordination
- Automated RASHG measurement sequences  
- Real-time data analysis and visualization
- Polarization sweep experiments
- Multi-wavelength scanning
- Data export and analysis tools

## Typical Experiment Workflow

### 1. **Hardware Setup**
```python
# Camera initialization
camera = DAQ_2DViewer_PrimeBSI()
camera.ini_detector()

# Polarization control
elliptec = DAQ_Move_Elliptec()
elliptec.ini_stage()

# Power monitoring  
power_meter = DAQ_0DViewer_Newport1830C()
power_meter.ini_detector()
```

### 2. **RASHG Measurement**
```python
# Set wavelength
laser.move_abs(800)  # 800 nm

# Polarization sweep
for angle in range(0, 180, 5):
    elliptec.move_abs([angle, 0, 0])  # Rotate incident HWP
    time.sleep(0.1)  # Stabilization
    
    # Capture SHG image
    image = camera.grab_data()
    
    # Monitor power
    power = power_meter.grab_data()
    
    # Process and save data
    process_rashg_data(image, angle, power)
```

### 3. **Automated Extension**
```python
# Use the complete extension for automated measurements
extension = URASHGMicroscopyExtension()
extension.run_rashg_scan(
    pol_start=0, pol_end=180, pol_steps=36,
    wavelengths=[780, 800, 820],
    integration_time=100
)
```

## Configuration

### Hardware Configuration

Edit `src/pymodaq_plugins_urashg/hardware/urashg/__init__.py`:

```python
# Serial port assignments
ELLIPTEC_PORT = "/dev/ttyUSB1"  # Rotation mounts
MAITAI_PORT = "/dev/ttyUSB0"    # Laser
NEWPORT_PORT = "/dev/ttyS0"     # Power meter

# Camera settings
CAMERA_COOLING_TEMP = -20  # °C
DEFAULT_EXPOSURE = 100     # ms
```

### Plugin Parameters

Each plugin supports extensive parameter customization through PyMoDAQ's parameter system. Key settings:

- **Exposure times**: Optimized for SHG signal levels
- **Polarization ranges**: Configurable angular sweeps  
- **Integration times**: Balanced speed vs. signal quality
- **ROI settings**: Focus on sample regions of interest

## Development

### Adding New Hardware

1. **Create hardware controller**:
   ```bash
   touch src/pymodaq_plugins_urashg/hardware/urashg/new_device.py
   ```

2. **Create PyMoDAQ plugin**:
   ```bash
   touch src/pymodaq_plugins_urashg/daq_move_plugins/daq_move_NewDevice.py
   ```

3. **Register in entry points** (`pyproject.toml`):
   ```toml
   [project.entry-points."pymodaq.move_plugins"]
   "DAQ_Move_NewDevice" = "pymodaq_plugins_urashg.daq_move_plugins.daq_move_NewDevice:DAQ_Move_NewDevice"
   ```

### Testing

```bash
# Run plugin tests
pytest tests/ -v

# Test specific plugin
python -c "
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
plugin = DAQ_Move_Elliptec()
print('Plugin test successful')
"
```

## Troubleshooting

### Common Issues

#### **PyVCAM Installation**
```bash
# Error: KeyError: 'PVCAM_SDK_PATH'
export PVCAM_SDK_PATH="/opt/pvcam/sdk"
source /etc/profile.d/pvcam-sdk.sh
```

#### **Plugin Discovery**
```bash
# If plugins don't appear in PyMoDAQ:
rm -rf ~/.pymodaq/cache/  # Clear cache
uv pip uninstall pymodaq-plugins-urashg
uv pip install -e .       # Reinstall
```

#### **Serial Communication**
```bash
# Check device permissions
sudo usermod -a -G dialout $USER  # Add user to dialout group
sudo chmod 666 /dev/ttyUSB*        # Grant permissions
```

#### **Camera Issues**
```bash
# Test PVCAM directly
/opt/pvcam/bin/PVCamTest/x86_64/PVCamTest

# Check camera temperature
python -c "
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
camera = DAQ_2DViewer_PrimeBSI()
camera.ini_detector()
print(f'Camera ready, simulation mode: {camera.simulation_mode}')
"
```

### Performance Tips

1. **Optimize exposure times** based on SHG signal strength
2. **Use ROI** to reduce data transfer and increase frame rates  
3. **Enable hardware binning** for improved signal-to-noise
4. **Monitor temperature** for stable long-term measurements
5. **Use appropriate averaging** for noise reduction

## Documentation

- **API Documentation**: See `docs/` directory
- **Example Scripts**: See `examples/` directory  
- **Hardware Manuals**: Check manufacturer documentation
- **PyMoDAQ Documentation**: [pymodaq.org](http://pymodaq.org)

## Support

### Getting Help

1. **Check logs**: PyMoDAQ logs provide detailed error information
2. **Test individual plugins**: Isolate issues to specific components
3. **Hardware verification**: Test devices with manufacturer software
4. **GitHub Issues**: Report bugs and feature requests

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-device`
3. **Follow coding standards**: Use Black formatter and type hints
4. **Add tests**: Ensure new code is tested
5. **Submit pull request**: Include clear description of changes

## License

MIT License - see `LICENSE` file for details.

## Citation

If you use this plugin package in your research, please cite:

```bibtex
@software{pymodaq_urashg_plugin,
  title={PyMoDAQ URASHG Plugin Package},
  author={PyMoDAQ Plugin Development Team},
  year={2025},
  url={https://github.com/PyMoDAQ/pymodaq_plugins_urashg},
  version={0.1.0}
}
```

## Acknowledgments

- **PyMoDAQ Team** - Framework and architecture
- **Photometrics** - PyVCAM library and camera support  
- **Thorlabs** - Elliptec rotation mount hardware
- **Newport** - Power meter and motion control hardware
- **μRASHG Research Community** - Scientific guidance and testing

---

**Ready for your μRASHG measurements!** 🔬✨

For the latest updates and documentation, visit: [GitHub Repository](https://github.com/PyMoDAQ/pymodaq_plugins_urashg)