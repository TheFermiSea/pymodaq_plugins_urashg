# PyMoDAQ Plugins for URASHG Microscopy

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![PyMoDAQ Compatibility](https://img.shields.io/badge/PyMoDAQ-5.0%2B-green.svg)](https://pymodaq.cnrs.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/pymodaq-plugins-urashg/badge/?version=latest)](https://pymodaq-plugins-urashg.readthedocs.io/en/latest/?badge=latest)

> **[READY] PyMoDAQ 5.0+ Ready**: This package has been fully migrated and tested with PyMoDAQ 5.0+ including updated data structures, PySide6 compatibility, and modern plugin architecture.

A comprehensive PyMoDAQ plugin package for **URASHG (micro Rotational Anisotropy Second Harmonic Generation)** microscopy systems. This package provides complete automation and control for polarimetric SHG measurements with professional-grade reliability and performance.

## What is μRASHG Microscopy?

Micro Rotational Anisotropy Second Harmonic Generation (μRASHG) is a powerful nonlinear optical technique for studying:
- Surface and interface properties
- Molecular orientation and symmetry
- Anisotropic materials characterization
- Real-time surface dynamics

This plugin package enables fully automated μRASHG measurements with precise polarization control, laser stabilization, and synchronized data acquisition.

## System Architecture

### Supported Hardware Components

**Laser System:**
- MaiTai ultrafast laser with Electro-Optic Modulator (EOM)
- Red Pitaya FPGA-based PID control for power stabilization
- Fast photodiode for power monitoring

**Polarization Control:**
- 3x Thorlabs ELL14 motorized rotation mounts
  - Quarter-wave plate (incident beam)
  - Half-wave plate (incident polarization)
  - Half-wave plate (analyzer)

**Detection System:**
- Photometrics Prime BSI sCMOS camera
- Hardware ROI support for efficient acquisition
- Real-time background subtraction

**Future Extensions:**
- Galvo mirrors for 2D scanning
- Multi-modal measurement capabilities

### Plugin Architecture

```
pymodaq_plugins_urashg/
├── daq_move_plugins/              # Actuator Control
│   ├── DAQ_Move_Elliptec.py          # Polarization control
│   └── DAQ_Move_MaiTai.py            # Laser control
├── daq_viewer_plugins/            # Data Acquisition
│   └── plugins_2D/
│       └── DAQ_Viewer_PrimeBSI.py    # Camera interface
└── hardware/                      # Hardware Abstraction
    └── urashg/                    # Low-level drivers
        ├── camera_utils.py
        ├── elliptec_wrapper.py
        ├── maitai_control.py
        └── system_control.py
```

## Installation

### Requirements

- **Python**: 3.8+
- **PyMoDAQ**: 5.0+ (automatically installed)
- **Qt Framework**: PySide6 (automatically installed)
- **Operating System**: Windows 10+, macOS 10.15+, Linux

### Install via pip

```bash
pip install pymodaq-plugins-urashg
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pymodaq_plugins_urashg.git
cd pymodaq_plugins_urashg

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e .[dev]

# Install with mock devices for testing
pip install -e .[mock]
```

## Configuration

### Hardware Setup

1. **Connect Hardware Components**:
   - Connect MaiTai laser via serial port
   - Install Thorlabs ELL14 rotation mounts
   - Connect Photometrics camera via USB 3.0
   - Set up Red Pitaya FPGA network connection

2. **Configure PyMoDAQ**:
   ```python
   # Launch PyMoDAQ Dashboard
   python -m pymodaq.dashboard
   ```

3. **Add URASHG Plugins**:
   - Move Plugins: `DAQ_Move_Elliptec`, `DAQ_Move_MaiTai`
   - Viewer Plugin: `DAQ_2DViewer_PrimeBSI`

### Software Configuration

The plugins automatically handle hardware initialization with sensible defaults. Advanced users can customize settings in the PyMoDAQ parameter trees.

## Usage Examples

### Basic μRASHG Measurement

```python
import numpy as np
from pymodaq.dashboard import DashBoard

# Initialize PyMoDAQ Dashboard
dashboard = DashBoard()

# Configure measurement parameters
angles = np.arange(0, 180, 5)  # Rotation angles in degrees
integration_time = 100  # ms

# Run automated measurement sequence
for angle in angles:
    # Rotate polarization elements
    dashboard.move_modules['elliptec_hwp'].move_abs(angle)
    
    # Acquire SHG image
    data = dashboard.viewer_modules['prime_camera'].grab_data()
    
    # Process and save data
    # ... your analysis code here
```

### Advanced Multi-Modal Setup

```python
# Configure simultaneous measurements
from pymodaq_plugins_urashg.hardware.urashg import URASHGSystem

# Initialize system controller
system = URASHGSystem()

# Set up synchronized measurement
system.configure_polarimetry_scan(
    hwp_angles=np.arange(0, 180, 10),
    qwp_angles=np.arange(0, 90, 15),
    integration_time=50
)

# Execute measurement
results = system.run_polarimetry_measurement()
```

## Testing

The package includes comprehensive testing with both unit tests and hardware integration tests.

### Run Unit Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests
pytest -m "not hardware"    # Tests without hardware

# Run with coverage
pytest --cov=pymodaq_plugins_urashg --cov-report=term-missing
```

### Development Commands

```bash
# Code formatting
black src/
isort src/

# Linting
flake8 src/

# Install pre-commit hooks
pre-commit install
```

## PyMoDAQ 5.0+ Migration Notes

This package has been fully updated for PyMoDAQ 5.0+ compatibility:

### Key Changes Made:
- **Data Structures**: Updated from `DataFromPlugins` to `DataWithAxes` + `DataToExport`
- **Qt Framework**: Migrated from PyQt5 to PySide6
- **Signal Emission**: Changed from `data_grabed_signal` to `dte_signal`
- **Dependencies**: Updated all PyMoDAQ dependencies to 5.0+
- **Testing**: All tests pass with PyMoDAQ 5.0+ in isolated container environments

### Backward Compatibility:
- **Not compatible** with PyMoDAQ 4.x versions
- For PyMoDAQ 4.x support, use version 0.0.x of this package
- Migration guide available in `docs/migration_guide.md`

## Documentation

- **Full Documentation**: [Read the Docs](https://pymodaq-plugins-urashg.readthedocs.io/)
- **PyMoDAQ Documentation**: [PyMoDAQ Guide](https://pymodaq.cnrs.fr/en/latest/)
- **Hardware Integration**: See `docs/hardware_setup.md`
- **API Reference**: See `docs/api_reference.md`

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

### Code Standards

- **Formatting**: Black (line length 88)
- **Import Sorting**: isort
- **Linting**: flake8
- **Testing**: pytest with coverage
- **Documentation**: Sphinx with numpydoc

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

### Community Support
- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/pymodaq_plugins_urashg/issues)
- **PyMoDAQ Forum**: [Community discussions](https://github.com/PyMoDAQ/PyMoDAQ/discussions)
- **Email Support**: [contact@pymodaq.org](mailto:contact@pymodaq.org)

### Commercial Support
For commercial support, custom development, or training services, please contact the PyMoDAQ team.

---

**Made with love by the PyMoDAQ community for the scientific research community.**