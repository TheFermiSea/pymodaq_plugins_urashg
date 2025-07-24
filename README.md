# PyMoDAQ Plugins for URASHG Microscopy

[![PyPI version](https://badge.fury.io/py/pymodaq-plugins-urashg.svg)](https://badge.fury.io/py/pymodaq-plugins-urashg)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/pymodaq-plugins-urashg/badge/?version=latest)](https://pymodaq-plugins-urashg.readthedocs.io/en/latest/?badge=latest)

A comprehensive PyMoDAQ plugin package for **URASHG (Ultrafast Reflection-mode Angle-resolved Second Harmonic Generation)** microscopy systems. This package provides complete automation and control for polarimetric SHG measurements with professional-grade reliability and performance.

## 🔬 What is RASHG Microscopy?

Reflection-mode Angle-resolved Second Harmonic Generation (RASHG) is a powerful nonlinear optical technique for studying:
- Surface and interface properties
- Molecular orientation and symmetry
- Anisotropic materials characterization
- Real-time surface dynamics

This plugin package enables fully automated RASHG measurements with precise polarization control, laser stabilization, and synchronized data acquisition.

## 🏗️ System Architecture

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
│   ├── daq_move_redpitaya_fpga.py    # PID laser stabilization
│   ├── daq_move_elliptec.py          # Polarization control
│   └── daq_move_maitai_laser.py      # Laser control
├── daq_viewer_plugins/            # Detection Systems
│   └── plugins_2D/
│       └── daq_2dviewer_pyvcam.py    # Camera interface
└── hardware/                      # Hardware Abstraction
    └── urashg/
        ├── redpitaya_control.py      # FPGA register access
        ├── elliptec_wrapper.py       # Multi-mount controller
        ├── maitai_control.py         # Laser communication
        └── camera_utils.py           # Camera utilities
```

## 🚀 Quick Start

### Prerequisites

**Software Requirements:**
- Python 3.8+
- PyMoDAQ 4.0+
- Windows 10/11 or Linux (for hardware support)

**Hardware Requirements:**
- Red Pitaya (STEMlab 125-14 or similar)
- Thorlabs ELL14 rotation mounts
- Photometrics Prime BSI camera
- USB and Ethernet connectivity

### Installation

#### Option 1: PyPI Installation (Recommended)
```bash
pip install pymodaq-plugins-urashg
```

#### Option 2: Development Installation
```bash
git clone https://github.com/PyMoDAQ/pymodaq_plugins_urashg.git
cd pymodaq_plugins_urashg
pip install -e .
```

#### Option 3: With Optional Dependencies
```bash
# For mock testing
pip install pymodaq-plugins-urashg[mock]

# For galvo integration (future)
pip install pymodaq-plugins-urashg[galvo]

# For development
pip install pymodaq-plugins-urashg[dev]
```

### Hardware Setup

#### Red Pitaya Configuration
1. Flash Red Pitaya with standard OS image
2. Connect to network and note IP address
3. Enable SSH access for remote control
4. Verify FPGA PID controller at base address `0x40300000`

#### Thorlabs ELL14 Setup
1. Connect rotation mounts via USB-to-Serial adapters
2. Note COM port assignments for each mount
3. Home all rotation mounts using Thorlabs software
4. Verify communication using `elliptec` library

#### Camera Setup
1. Install PVCAM drivers from Photometrics
2. Connect camera via USB 3.0 or PCIe
3. Verify detection using Photometrics software
4. Test `pyvcam` library connectivity

### First Measurement

#### 1. Launch PyMoDAQ Dashboard
```python
python -m pymodaq.dashboard
```

#### 2. Load URASHG Plugins
- **Actuators**: Add "RedPitaya FPGA", "Elliptec Polarization"
- **Detectors**: Add "PyVCAM Camera"

#### 3. Configure Hardware
```python
# Example configuration script
from pymodaq_plugins_urashg.examples import basic_setup

# Initialize all hardware
setup = basic_setup.URASHGSetup()
setup.initialize_hardware()

# Run a simple polarization scan
results = setup.run_polarization_scan(
    angles=range(0, 180, 5),  # 0° to 175° in 5° steps
    exposure_time=100,        # 100ms exposure
    averaging=3               # 3 frame average
)
```

## 📊 Key Features

### Automated Measurements
- **Polarization-resolved scans**: Automated rotation of waveplates
- **Angle-resolved measurements**: Coordinated sample/detection positioning
- **Multi-dimensional acquisition**: Combined angle, polarization, and position scans
- **Real-time data visualization**: Live plotting and analysis

### Advanced Control
- **Laser stabilization**: Hardware PID control with <1% stability
- **Precision polarization**: ±0.1° rotation accuracy
- **ROI optimization**: Hardware-accelerated region of interest
- **Background subtraction**: Real-time signal processing

### Professional Features
- **Configuration management**: Save/load complete system states
- **Data export**: HDF5, CSV, and image format support
- **Calibration routines**: Automated polarization and intensity calibration
- **Error handling**: Robust recovery from hardware failures

## 📖 Usage Examples

### Basic Polarization Scan
```python
from pymodaq.dashboard import DashBoard
from pymodaq_plugins_urashg.examples import automated_rashg_scan

# Initialize PyMoDAQ
app = DashBoard()
app.load_preset('RASHG_System.xml')

# Run automated polarization measurement
scanner = automated_rashg_scan.PolarizationScanner(app)
results = scanner.run_scan(
    hwp_angles=range(0, 180, 2),  # 2° steps
    exposure_time=50,             # 50ms exposure
    save_path='./data/pol_scan_001.h5'
)
```

### Advanced Multi-Modal Measurement
```python
from pymodaq_plugins_urashg.examples import advanced_workflows

# Configure complex measurement sequence
workflow = advanced_workflows.RASHGWorkflow()

# Define measurement matrix
workflow.add_scan_axis('polarization', range(0, 180, 5))
workflow.add_scan_axis('sample_angle', range(-30, 31, 1))
workflow.add_scan_axis('laser_power', [50, 75, 100])  # % of max power

# Execute with automated analysis
results = workflow.execute_with_analysis(
    fit_models=['gaussian', 'lorentzian'],
    export_plots=True,
    real_time_feedback=True
)
```

### Custom Analysis Pipeline
```python
from pymodaq_plugins_urashg.analysis import shg_analysis

# Load measurement data
data = shg_analysis.load_rashg_data('measurement_001.h5')

# Apply standard analysis pipeline
analyzer = shg_analysis.RASHGAnalyzer(data)
analyzer.apply_background_correction()
analyzer.extract_polarization_dependence()
analyzer.fit_symmetry_models()

# Generate publication-ready plots
analyzer.create_polar_plots()
analyzer.export_analysis_report('results_001.pdf')
```

## 🔧 Configuration

### Plugin Settings

**Red Pitaya PID Controller:**
```yaml
connection:
  ip_address: "192.168.1.100"
  base_address: 0x40300000

pid_parameters:
  proportional_gain: 0.1
  integral_gain: 0.01
  derivative_gain: 0.001
  setpoint_mw: 100.0

monitoring:
  error_signal: true
  output_signal: true
  sample_rate_hz: 1000
```

**Thorlabs ELL14 Rotation Mounts:**
```yaml
connections:
  qwp_port: "COM3"
  hwp_incident_port: "COM4"
  hwp_analyzer_port: "COM5"

motion_settings:
  home_on_startup: true
  movement_speed: "fast"
  step_size_degrees: 0.1

polarization_presets:
  linear_h: 0.0
  linear_v: 90.0
  circular_r: 45.0
  circular_l: -45.0
```

**Photometrics Prime BSI Camera:**
```yaml
camera_settings:
  exposure_ms: 100.0
  gain: 1
  binning: "1x1"
  readout_mode: "fast"

roi_settings:
  use_hardware_roi: true
  roi_x: 500
  roi_y: 500
  roi_width: 100
  roi_height: 100

processing:
  background_subtraction: true
  signal_threshold: 0.1
  averaging_frames: 1
```

## 🧪 Testing and Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires hardware)
pytest tests/integration/ -m "hardware"

# Mock device tests
pytest tests/mock/
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/PyMoDAQ/pymodaq_plugins_urashg.git
cd pymodaq_plugins_urashg

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src/
isort src/
flake8 src/
```

## 📚 Documentation

### Complete Documentation
- **API Reference**: [pymodaq-plugins-urashg.readthedocs.io](https://pymodaq-plugins-urashg.readthedocs.io/)
- **User Guide**: [docs/user_guide.md](docs/user_guide.md)
- **Hardware Setup**: [docs/hardware_setup.md](docs/hardware_setup.md)
- **Troubleshooting**: [docs/troubleshooting.md](docs/troubleshooting.md)

### Quick References
- **Plugin Configuration**: [docs/plugin_configuration.md](docs/plugin_configuration.md)
- **Measurement Examples**: [examples/](examples/)
- **API Documentation**: [docs/api/](docs/api/)

## 🤝 Contributing

We welcome contributions from the community! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Reporting Issues
- **Bug Reports**: [GitHub Issues](https://github.com/PyMoDAQ/pymodaq_plugins_urashg/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/PyMoDAQ/pymodaq_plugins_urashg/discussions)
- **Questions**: [PyMoDAQ Community Forum](https://github.com/PyMoDAQ/PyMoDAQ/discussions)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyMoDAQ Team**: For the excellent framework and support
- **Thorlabs**: For ELL14 rotation mount support
- **Photometrics**: For camera integration assistance
- **Red Pitaya**: For FPGA development resources
- **Research Community**: For valuable feedback and testing

## 📞 Support

### Getting Help
- **Documentation**: [pymodaq-plugins-urashg.readthedocs.io](https://pymodaq-plugins-urashg.readthedocs.io/)
- **Community Forum**: [PyMoDAQ Discussions](https://github.com/PyMoDAQ/PyMoDAQ/discussions)
- **Email Support**: [contact@pymodaq.org](mailto:contact@pymodaq.org)

### Commercial Support
For commercial support, custom development, or training services, please contact the PyMoDAQ team.

---

**Made with ❤️ by the PyMoDAQ community for the scientific research community.**