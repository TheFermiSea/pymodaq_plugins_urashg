# PyMoDAQ μRASHG Experiment Architecture Implementation

## Implementation Status (August 2025)

Successfully implemented the complete PyMoDAQ experiment framework for μRASHG measurements with three critical calibration experiments.

## Architecture Overview

### Base Experiment Framework (`URASHGBaseExperiment`)
- **Inheritance**: Extends PyMoDAQ's `ExtensionBase` for native integration
- **Parameter Management**: Hierarchical parameter trees with real-time validation
- **Hardware Integration**: Standardized module access through dashboard interface
- **GUI Framework**: Professional docking interface with control panels
- **Threading**: Non-blocking experiment execution with progress tracking
- **Error Handling**: Comprehensive safety protocols and graceful failure recovery
- **Data Management**: HDF5 storage with metadata preservation

### Key Design Patterns Implemented

#### 1. Hardware Module Access Pattern
```python
# Standardized access through dashboard
self.modules['MaiTai'] = self.dashboard.get_module('MaiTai')
self.modules['Newport1830C'] = self.dashboard.get_module('Newport1830C')

# Consistent DataActuator usage for move operations
target_position = DataActuator(data=[value])
module.move_abs(target_position)
```

#### 2. Parameter Tree Architecture
- **Hierarchical Structure**: Grouped parameters by functionality
- **Real-time Validation**: Parameter change callbacks with error checking
- **Type Safety**: Enforced parameter types and limits
- **GUI Integration**: Automatic parameter tree widget generation

#### 3. Progress Tracking System
- **Multi-level Progress**: Overall experiment and current step progress
- **Time Estimation**: ETA calculation based on elapsed time
- **Status Logging**: Timestamped status messages with GUI display
- **Stop/Pause/Resume**: Full experiment control capabilities

#### 4. Data Structure Design
- **Multi-dimensional Arrays**: Support for complex measurement geometries
- **Metadata Preservation**: Complete experimental conditions stored with data
- **HDF5 Storage**: Efficient storage with compression and organization
- **Coordinate Systems**: Proper axis definitions with units

## Implemented Experiments

### 1. EOM Calibration Experiment
**Purpose**: PID-based laser power control calibration
**Features**:
- **PID Controller**: Optimized parameters (kp=24, ki=3, kd=0.0125)
- **Dual Calibration**: Voltage sweep + closed-loop power control
- **Interpolation Tables**: 2D lookup (wavelength, power) → EOM voltage
- **Validation System**: Independent test points with repeatability analysis
- **Power Stability**: Real-time feedback with convergence criteria

**Critical Implementation Details**:
- **Power Control Loop**: 10 kHz update rate with 0.1% accuracy
- **Wavelength Dependence**: Separate calibration curves per wavelength
- **Safety Limits**: Voltage and power range constraints
- **Error Recovery**: Graceful handling of PID convergence failures

### 2. Elliptec Calibration Experiment  
**Purpose**: Multi-rotator polarization control calibration
**Features**:
- **Homing Sequences**: Reference position establishment for all rotators
- **Malus Law Fitting**: cos²(θ) parameter extraction (A, φ, C)
- **Cross-Calibration**: Multi-rotator interference measurement
- **Wavelength Correction**: Chromatic dispersion compensation
- **Validation Framework**: Independent test points with error analysis

**Critical Implementation Details**:
- **Three Rotators**: H800 (incident HWP), H400 (analyzer HWP), Q800 (QWP)
- **Reference Coordination**: Intelligent positioning of non-active rotators
- **High-Resolution Regions**: Enhanced sampling around critical angles
- **Fit Quality Metrics**: R², RMS residuals, statistical validation

### 3. Variable Attenuator Calibration Experiment
**Purpose**: Continuous power control via polarization attenuation
**Features**:
- **Wide Dynamic Range**: 40+ dB attenuation capability
- **Enhanced Malus Law**: Extinction ratio consideration for realistic modeling
- **Attenuation Mapping**: Target attenuation → angle lookup tables
- **Wavelength Compensation**: Chromatic dispersion correction
- **Hysteresis Testing**: Bidirectional repeatability validation

**Critical Implementation Details**:
- **Extinction Ratio Modeling**: Sub-0.01% minimum transmission
- **High-Resolution Sampling**: Enhanced resolution near attenuation minima
- **Power Detection Limits**: Handling of very low power measurements
- **Inverse Lookup Functions**: Real-time angle calculation for target attenuation

## Key Architecture Decisions

### 1. PyMoDAQ Integration Strategy
- **Native Extension**: Full integration with PyMoDAQ framework rather than standalone application
- **Module Reuse**: Leverages existing verified plugins (MaiTai, Elliptec, Newport, PrimeBSI)
- **Parameter Synchronization**: Real-time parameter updates between GUI and hardware
- **Threading Model**: Non-blocking execution with GUI responsiveness

### 2. Calibration Data Management
- **Separated Concerns**: Individual calibration experiments with specific data products
- **Interpolation Ready**: Pre-computed lookup tables for runtime performance
- **Version Control**: Calibration file versioning for reproducibility
- **Validation Integration**: Built-in accuracy verification for all calibrations

### 3. Error Handling Philosophy
- **Graceful Degradation**: Experiments continue with reduced functionality on non-critical failures
- **Safety First**: Hardware protection through parameter validation and limits
- **Recovery Mechanisms**: Automatic retry with parameter adjustment
- **User Intervention Points**: Manual control options for complex failure scenarios

### 4. Performance Optimization
- **Efficient Sampling**: Intelligent angle selection with high-resolution regions
- **Parallel Processing**: Multi-threaded execution where hardware allows
- **Memory Management**: Efficient data structures for large multi-dimensional arrays
- **Real-time Display**: Live visualization without performance impact

## Development Methodology

### 1. Research-Driven Implementation
- **urashg_2 Analysis**: Comprehensive study of existing experimental procedures
- **Parameter Optimization**: Hardware-specific calibration from proven methods
- **Data Structure Compatibility**: ScipyData-compatible arrays with metadata
- **Control Sequence Validation**: Hardware timing and coordination patterns

### 2. Modular Architecture
- **Base Class Pattern**: Common functionality in URASHGBaseExperiment
- **Specific Implementations**: Individual experiments with specialized parameters
- **Hardware Abstraction**: Standardized interface regardless of specific hardware
- **Plugin Architecture**: Easy extension for new experiment types

### 3. Testing Strategy
- **Mock Hardware Support**: Development and testing without physical hardware
- **Parameter Validation**: Comprehensive input checking and range validation
- **Hardware Integration**: Progressive testing with real hardware components
- **Calibration Validation**: Built-in accuracy verification and quality metrics

## Future Extension Points

### 1. Additional Experiments
- **PDSHG Experiment**: Power-dependent RASHG measurements
- **Basic μRASHG Experiment**: Full 4D data collection with camera
- **Wavelength-Dependent RASHG**: Spectroscopic measurements
- **Time-Resolved Studies**: ESP300 integration for kinetic measurements

### 2. Advanced Features
- **Machine Learning Integration**: Intelligent parameter optimization
- **Cloud Storage**: Remote data management and collaboration
- **Real-time Analysis**: Live curve fitting and parameter extraction
- **Automated Scheduling**: Batch experiment execution

### 3. Hardware Extensions
- **Multi-Camera Support**: Parallel detection systems
- **Spectrometer Integration**: Simultaneous spectral measurement
- **Environmental Control**: Temperature and atmosphere management
- **Galvo Scanner**: Spatial mapping capabilities

This architecture provides a solid foundation for advanced μRASHG experiments while maintaining the flexibility for future enhancements and hardware modifications.