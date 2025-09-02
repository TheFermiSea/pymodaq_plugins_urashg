# PyMoDAQ URASHG Plugin Package

A **PyMoDAQ 5.x compliant** plugin package for **μRASHG (micro Rotational Anisotropy Second Harmonic Generation)** microscopy systems. This package provides complete hardware control and experimental automation for polarimetric SHG measurements with a **fully functional unified GUI interface**.

## 🎉 Status: Production Ready

✅ **GUI Interface**: Fully working unified 5-panel interface for complete system control
✅ **Mock Device Support**: Comprehensive simulation for GUI testing without hardware
✅ **PyMoDAQ 5.x Compliance**: 16/16 tests passing - complete standards compliance
✅ **Plugin Discovery**: All 5 plugins discoverable by PyMoDAQ framework
✅ **Measurement System**: Functional calibration and measurement workflows

## Important Notice

**This is an UNOFFICIAL plugin package** developed independently by TheFermiSea. While it follows PyMoDAQ 5.x standards and is fully functional, it is not officially endorsed or maintained by the PyMoDAQ team.

- **Repository**: https://github.com/TheFermiSea/pymodaq_plugins_urashg
- **Author**: TheFermiSea (squires.b@gmail.com)
- **PyMoDAQ Compatibility**: 5.x
- **Support**: Community-driven (not official PyMoDAQ support)

## Overview

The URASHG plugin package enables sophisticated polarimetric second harmonic generation measurements through PyMoDAQ's modular framework:

- **Standards-compliant architecture**: Follows PyMoDAQ 5.x plugin development guidelines
- **Multi-device coordination**: Integrated laser control, polarization optics, cameras, and power meters
- **Real-time data acquisition**: High-speed polarimetric measurements with PyMoDAQ framework integration
- **Unified extension**: Single comprehensive extension for complete system control
- **Hardware abstraction**: Works with real hardware or simulation mode

## Plugin Components

### Move Plugins (Motion Control)
- **DAQ_Move_Elliptec** - Thorlabs ELL14 rotation mount control for polarization optics
- **DAQ_Move_MaiTai** - MaiTai Ti:Sapphire laser wavelength and power control
- **DAQ_Move_ESP300** - Newport ESP300 multi-axis motion controller for positioning

### Viewer Plugins (Detection)
- **DAQ_2DViewer_PrimeBSI** - Photometrics Prime BSI sCMOS camera control
- **DAQ_0DViewer_Newport1830C** - Newport 1830-C optical power meter

### Extensions
- **URASHGMicroscopyExtension** - Comprehensive microscopy control interface

## Hardware Support

### Cameras
- **Photometrics Prime BSI** - sCMOS camera with PyVCAM integration
- Full camera control: exposure, gain, ROI, readout modes
- Real-time SHG image acquisition

### Motion Control
- **Thorlabs ELL14 Rotation Mounts** - Polarization control (QWP, HWP)
- **MaiTai Laser** - Wavelength control and EOM power modulation
- **Newport ESP300** - Precision positioning stages

### Detection
- **Newport 1830-C Power Meter** - Optical power monitoring
- Real-time power measurements during scans

## Installation

### Prerequisites

**UV Package Manager** (Recommended):
```bash
# Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Installation Steps

**Using UV (Recommended)**:
```bash
# Clone repository
git clone https://github.com/TheFermiSea/pymodaq_plugins_urashg.git
cd pymodaq_plugins_urashg

# Setup with UV
python manage_uv.py setup                    # Complete project setup
python manage_uv.py install --hardware       # Install with hardware dependencies
python manage_uv.py launch                   # Launch extension
```

**Using pip** (Alternative):
```bash
# Basic installation
pip install -e .

# With hardware dependencies
pip install -e .[hardware]

# Development installation
pip install -e .[dev]

# PyRPL (Red Pitaya) - Optional and problematic
# PyRPL has compatibility issues with modern Python
# Only install if you specifically need Red Pitaya FPGA control:
pip install -e .[pyrpl]  # May fail - see PyRPL section below
```

### PyRPL Installation Issues

**PyRPL is optional** - the URASHG plugins work perfectly without it. PyRPL is only needed for Red Pitaya FPGA control and has known compatibility issues:

**Known Issues:**
- PyRPL depends on `futures==3.4.0` which is Python 2 only
- Conflicts with modern Python 3 environments
- Installation often fails with UV and modern pip

**Solutions:**

1. **Recommended: Use without PyRPL** (Default)
   - All plugins work with comprehensive mock system
   - Red Pitaya functionality gracefully disabled
   - No installation issues

2. **If you need PyRPL:**
   ```bash
   # Try installing PyRPL manually first
   pip install pyrpl>=0.9.3

   # Then install URASHG plugins
   uv add . --optional pyrpl
   ```

3. **Alternative PyRPL approaches:**
   - Use PyRPL in a separate Python 2.7 environment
   - Use Docker container with PyRPL pre-installed
   - Contact PyRPL maintainers for Python 3 compatibility

### PyMoDAQ Integration

After installation, the plugins will be automatically discovered by PyMoDAQ:

```bash
# Launch PyMoDAQ Dashboard
python -m pymodaq.dashboard
```

The URASHG extension will be available in the Extensions menu.

## Usage

### Unified GUI Interface (Recommended)

**Launch the standalone URASHG interface directly**:
```bash
# Using UV (recommended)
uv run python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py

# Or using the UV management script
python manage_uv.py launch
```

**GUI Features**:
- **5-Panel Layout**: Control, Camera Data, Analysis Plots, Device Status, Elliptec Control
- **Mock Device Support**: Click "Initialize Devices" to test with simulated hardware
- **Real-time Feedback**: Live status updates and measurement progress
- **Integrated Workflow**: Complete measurement and calibration sequences

### PyMoDAQ Dashboard Integration

**Alternative: Use with PyMoDAQ Dashboard**:

1. **Launch PyMoDAQ Dashboard**:
   ```bash
   python -m pymodaq.dashboard
   ```

2. **Load URASHG Extension**:
   - Navigate to Extensions menu
   - Select "URASHGMicroscopyExtension"

3. **Configure Hardware**:
   - Set appropriate serial ports and device parameters
   - Test hardware connections

### Plugin Configuration

Each plugin supports extensive configuration:

- **Camera settings**: Exposure, gain, ROI, cooling
- **Motion control**: Speed, acceleration, limits
- **Power monitoring**: Wavelength, units, averaging

### Mock Mode Testing

**Comprehensive mock device simulation for GUI testing**:

1. **Launch the GUI**:
   ```bash
   uv run python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py
   ```

2. **Initialize Mock Devices**:
   - Click "Initialize Devices" button in toolbar
   - Mock devices will be created automatically

3. **Test Features**:
   - **Device Status**: Shows all devices as "Connected"
   - **SHG Camera**: Displays simulated camera data with realistic patterns
   - **Measurements**: Run calibrations and measurements with mock data
   - **Controls**: Test all parameter adjustments and device operations

**Mock devices include**:
- Elliptec rotation mounts (3-axis polarization control)
- MaiTai laser (wavelength control)
- PrimeBSI camera (with realistic SHG patterns)
- Newport power meter (with noise simulation)

## Development

### Environment Setup

**Using UV**:
```bash
python manage_uv.py setup                    # Complete setup
python manage_uv.py install --all            # All dependencies
```

### Testing

```bash
# Run all tests
python manage_uv.py test

# Run compliance tests
uv run pytest tests/test_pymodaq_compliance.py -v

# Run specific test categories
uv run pytest tests/unit/ -v                 # Unit tests
uv run pytest tests/hardware/ -v -m hardware # Hardware tests
```

### Code Quality

```bash
# Format code
uv run black src/
uv run isort src/

# Linting
uv run flake8 src/
```

## PyMoDAQ 5.x Compliance

This package is **fully compliant** with PyMoDAQ 5.x standards:

✅ **Plugin Structure**: Proper inheritance from DAQ_Move_base/DAQ_Viewer_base
✅ **Initialization**: Required `ini_attributes()` methods implemented
✅ **Import Patterns**: Uses `pymodaq_gui.parameter`, `pymodaq_utils.utils`
✅ **Entry Points**: Correctly registered in pyproject.toml
✅ **Data Handling**: Uses DataWithAxes and DataToExport patterns
✅ **Extension Architecture**: Follows CustomApp patterns

**Compliance Test Results**: 16/16 tests passing

## Project Structure

```
pymodaq_plugins_urashg/
├── src/pymodaq_plugins_urashg/
│   ├── daq_move_plugins/          # Motion control plugins
│   ├── daq_viewer_plugins/        # Detection plugins
│   ├── extensions/                # PyMoDAQ extensions
│   ├── hardware/urashg/           # Hardware abstraction layer
│   ├── utils/                     # Utilities and configuration
│   └── resources/                 # Configuration templates
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   ├── hardware/                  # Hardware integration tests
│   └── mock_modules/              # Mock hardware for testing
├── docs/                          # Documentation
├── pyproject.toml                 # Modern Python packaging
└── README.md                      # This file
```

## Contributing

Contributions are welcome! Please ensure:

1. **PyMoDAQ Standards**: Follow PyMoDAQ 5.x development patterns
2. **Testing**: Add tests for new functionality
3. **Documentation**: Update documentation for changes
4. **Code Quality**: Use black, isort, and flake8 for formatting

### Development Workflow

```bash
# Setup development environment
python manage_uv.py setup
python manage_uv.py install --dev

# Make changes, then test
python manage_uv.py test
uv run pytest tests/test_pymodaq_compliance.py -v

# Format code
uv run black src/
uv run isort src/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **PyMoDAQ Team** for the excellent framework and development patterns
- **URASHG Research Community** for experimental techniques and requirements
- **Hardware Vendors** (Photometrics, Thorlabs, Newport) for driver support

---

*This package demonstrates best practices for PyMoDAQ 5.x plugin development and serves as a reference implementation for complex multi-device microscopy systems.*