# PyMoDAQ μRASHG Experiments

This directory contains the complete suite of PyMoDAQ experiments for micro Rotational Anisotropy Second Harmonic Generation (μRASHG) microscopy.

## Implemented Experiments (Ready for Use)

### 1. Base Experiment Framework (`base_experiment.py`)
**Class**: `URASHGBaseExperiment`

The foundational class providing common functionality for all μRASHG experiments:
- PyMoDAQ extension framework integration
- Hierarchical parameter trees with real-time validation
- Hardware module management through dashboard interface
- Professional GUI with docking interface and progress tracking
- Multi-threaded experiment execution with pause/resume capabilities
- Comprehensive error handling and safety protocols
- HDF5 data storage with metadata preservation

### 2. EOM Calibration Experiment (`eom_calibration.py`)
**Class**: `EOMCalibrationExperiment`

Critical calibration for precise laser power control:
- **PID-based power control** with optimized parameters (kp=24, ki=3, kd=0.0125)
- **Dual calibration approach**: voltage sweep + closed-loop power control
- **2D interpolation tables**: (wavelength, power) → EOM voltage mapping
- **Validation system**: independent test points with repeatability analysis
- **Real-time feedback control** with 0.1% accuracy tolerance

**Required Hardware**: MaiTai laser, Newport power meter, EOM system

### 3. Elliptec Rotator Calibration (`elliptec_calibration.py`)
**Class**: `ElliptecCalibrationExperiment`

Essential calibration for polarization control:
- **Multi-rotator coordination**: H800, H400, Q800 with synchronized control
- **Malus law fitting**: cos²(θ) parameter extraction (A, φ, C)
- **Cross-calibration**: multi-rotator interference measurement
- **Wavelength correction**: chromatic dispersion compensation
- **Homing sequences**: reference position establishment
- **High-resolution sampling**: enhanced accuracy near critical angles

**Required Hardware**: H800, H400, Q800 rotators, MaiTai laser, Newport power meter

### 4. Variable Attenuator Calibration (`variable_attenuator_calibration.py`)
**Class**: `VariableAttenuatorCalibrationExperiment`

Calibration for continuous power control:
- **Wide dynamic range**: 40+ dB attenuation capability
- **Enhanced Malus law**: extinction ratio modeling for realistic performance
- **Attenuation mapping**: target attenuation → angle lookup tables
- **Wavelength compensation**: chromatic dispersion correction factors
- **Hysteresis testing**: bidirectional repeatability validation

**Required Hardware**: Variable attenuator (HWP + polarizer), MaiTai laser, Newport power meter

### 5. Power-Dependent RASHG (PDSHG) (`pdshg_experiment.py`)
**Class**: `PDSHGExperiment`

Core μRASHG measurement without camera:
- **3D datasets**: [wavelength, power, angle] with comprehensive analysis
- **Logarithmic power spacing**: wide dynamic range with thermal management
- **Dual HWP coordination**: synchronized H800/H400 rotation schemes
- **Real-time analysis**: live curve fitting and parameter extraction
- **Background subtraction**: automated signal correction
- **Power law fitting**: SHG exponent analysis with quality metrics

**Required Hardware**: MaiTai laser, H800/H400 rotators, Newport power meter, photodiode

## Future Implementations (Placeholders)

### 6. Basic μRASHG Experiment (`basic_urashg_experiment.py`)
**Class**: `BasicURASHGExperiment` *(Placeholder)*

Complete μRASHG with camera detection:
- **4D data arrays**: [y, x, wavelength, angle]
- **Camera integration**: PrimeBSI with ROI support
- **Spatial mapping**: crystallographic orientation analysis
- **Image processing**: background subtraction and analysis

**Additional Hardware**: PrimeBSI camera, optional galvo scanners

### 7. Wavelength-Dependent RASHG (`wavelength_dependent_rashg.py`)  
**Class**: `WavelengthDependentRASHGExperiment` *(Placeholder)*

Spectroscopic μRASHG measurements:
- **Fine wavelength resolution**: adaptive sampling
- **Spectral analysis**: line shape fitting and resonance detection
- **Dispersion correction**: chromatic effects compensation
- **Multi-order analysis**: susceptibility tensor extraction

**Additional Hardware**: Wide-range tunable laser, optional spectrometer

## Usage Examples

### Running a Calibration Experiment

```python
from pymodaq_plugins_urashg.experiments import EOMCalibrationExperiment

# Initialize experiment with PyMoDAQ dashboard
experiment = EOMCalibrationExperiment(dashboard=dashboard)

# Configure parameters through GUI or programmatically
experiment.settings.child('eom_calibration', 'wavelength_range', 'start_nm').setValue(750.0)
experiment.settings.child('eom_calibration', 'wavelength_range', 'stop_nm').setValue(850.0)

# Initialize hardware
experiment.initialize_hardware()

# Start experiment
experiment.start_experiment()
```

### Running a PDSHG Measurement

```python
from pymodaq_plugins_urashg.experiments import PDSHGExperiment

# Initialize and configure
experiment = PDSHGExperiment(dashboard=dashboard)

# Set measurement ranges
experiment.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'min_power').setValue(0.001)
experiment.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'max_power').setValue(0.020)

# Load EOM calibration
experiment.settings.child('pdshg_experiment', 'power_control', 'eom_calibration_file').setValue('/path/to/eom_calibration.h5')

# Run experiment
experiment.initialize_hardware()
experiment.start_experiment()
```

## Experiment Workflow

### Typical μRASHG Measurement Sequence

1. **Hardware Setup**: Initialize all required PyMoDAQ modules
2. **Calibration Phase**:
   - Run `EOMCalibrationExperiment` for power control
   - Run `ElliptecCalibrationExperiment` for rotator calibration
   - Run `VariableAttenuatorCalibrationExperiment` if needed
3. **Measurement Phase**:
   - Load calibration files
   - Run `PDSHGExperiment` for core measurements
   - Optionally run `BasicURASHGExperiment` for spatial mapping
4. **Analysis**: Use built-in fitting and analysis tools

### Data Products

Each experiment generates:
- **HDF5 data files** with complete measurement arrays
- **Calibration tables** for runtime use by other experiments
- **Metadata files** with experimental conditions and parameters
- **Analysis reports** with fitting results and quality metrics

## Hardware Requirements

### Core Hardware (All Experiments)
- **MaiTai laser**: Wavelength control and power modulation
- **Newport 1830-C power meter**: Accurate power measurement
- **PyMoDAQ dashboard**: Hardware coordination and control

### Polarization Control
- **H800**: Half-wave plate for incident polarization (800nm)
- **H400**: Half-wave plate for analyzer (400nm/SHG)
- **Q800**: Quarter-wave plate for ellipticity control (optional)

### Detection Systems
- **Photodiode**: Real-time signal monitoring (PDSHG)
- **PrimeBSI camera**: 2D imaging (Basic μRASHG)
- **Spectrometer**: Spectral analysis (optional)

### Power Control
- **EOM system**: Voltage-controlled power modulation
- **Variable attenuator**: Alternative continuous power control

## Development Status

- ✅ **Base Framework**: Complete and tested
- ✅ **EOM Calibration**: Complete implementation
- ✅ **Elliptec Calibration**: Complete implementation  
- ✅ **Variable Attenuator Calibration**: Complete implementation
- ✅ **PDSHG Experiment**: Complete implementation
- 🚧 **Basic μRASHG**: Framework ready, implementation pending
- 🚧 **Wavelength-Dependent RASHG**: Framework ready, implementation pending

## Architecture Features

- **PyMoDAQ 5.x Native**: Full integration with modern PyMoDAQ framework
- **Professional GUI**: Docking interface with real-time monitoring
- **Multi-threaded**: Non-blocking experiment execution
- **Safety First**: Comprehensive error handling and hardware protection
- **Extensible**: Easy addition of new experiment types
- **Research-Grade**: Production-quality implementation based on proven methods

For detailed implementation information, see the individual experiment modules and the comprehensive development documentation in the Serena memories.