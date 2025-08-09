# Comprehensive Development Plan for PyMoDAQ μRASHG Implementation

## Executive Summary
Based on comprehensive analysis of the urashg_2 repository, this plan outlines the development strategy for implementing advanced μRASHG experiments in PyMoDAQ. The existing codebase provides a complete foundation for multi-dimensional polarimetric SHG measurements with sophisticated calibration and control systems.

## Phase 1: Core Infrastructure Development (Weeks 1-4)

### 1.1 Advanced Calibration System
**Priority: CRITICAL**
```python
# Implement calibration data management
class URASHGCalibrationManager:
    - EOM power calibration (wavelength + power → voltage lookup)
    - Rotator Malus law fitting (cos²(θ) parameter extraction)
    - Multi-rotator polarization state calibration
    - Wavelength-dependent correction factors
    - Real-time calibration validation
```

### 1.2 Enhanced Hardware Control
**Extend existing plugins with advanced features:**

#### EOM Power Control Enhancement
```python
# Upgrade DAQ_Move_MaiTai with EOM integration
class DAQ_Move_MaiTai_EOM(DAQ_Move_MaiTai):
    - PID-based power control (kp=24, ki=3, kd=0.0125)
    - Wavelength-dependent calibration lookup
    - Real-time photodiode feedback
    - Power stability validation (±0.1% tolerance)
    - Emergency power limiting
```

#### Multi-Rotator Coordination
```python
# Create coordinated rotator control
class URASHGRotatorController:
    - Synchronized multi-rotator movements
    - Polarization state calculation (Stokes parameters)
    - Hardware offset management (Q800, H800, H400)
    - Homing sequence optimization
    - Position verification protocols
```

### 1.3 Data Structure Framework
**Implement ScipyData-compatible arrays:**
```python
# Multi-dimensional data containers
URASHGDataContainer:
    - 4D Camera: [y, x, wavelength, angle]
    - 3D Voltage: [wavelength, power, angle] 
    - 4D Spectral: [wavelength, energy, angle, power]
    - Metadata preservation (exposure, power, date, calibration)
    - Variance tracking for error analysis
    - HDF5 storage with compression
```

## Phase 2: Experiment Implementation (Weeks 5-8)

### 2.1 Core μRASHG Experiment
**Primary measurement mode:**
```python
class URASHGExperiment(PyMoDAQExtension):
    Parameters:
    - Wavelength range: start, stop, step (nm)
    - HWP angle range: 0-360°, configurable step
    - Power range: logarithmic spacing, multiple points
    - Camera ROI: configurable region of interest
    
    Workflow:
    FOR power IN power_range:
        FOR wavelength IN wavelength_range:
            FOR angle IN angle_range:
                - Set laser wavelength (60s stabilization)
                - Adjust power via EOM PID control
                - Rotate HWPs (H800: α/2, H400: 360-25-α/2)
                - Acquire camera sequence (5 frames)
                - Record photodiode voltage
                - Record spectrometer data
                - Background subtraction
                - Real-time display update
```

### 2.2 Power-Dependent SHG (PDSHG)
**Optimized for power studies:**
```python
class PDSHGExperiment(URASHGExperiment):
    Features:
    - Power-first loop optimization
    - Descending power order (thermal management)
    - Variable attenuator integration
    - Enhanced statistics (100 PD samples)
    - Wavelength-dependent Malus calibration
    
    Data: [wavelength, power, angle] → voltage + spectrum
```

### 2.3 Temperature-Dependent Studies
**Extend for cryogenic measurements:**
```python
class TDPLExperiment(PyMoDAQExtension):
    - LakeShore temperature controller integration
    - Temperature stabilization protocols
    - Arrhenius analysis capabilities
    - Multi-temperature data containers
    - Automated temperature ramping
```

## Phase 3: Advanced Features (Weeks 9-12)

### 3.1 Real-time Analysis Pipeline
```python
class URASHGAnalyzer:
    - Live curve fitting (cos² functions)
    - Stokes parameter calculation
    - Polarization state visualization
    - Power-dependent analysis
    - Wavelength-dependent trends
    - Statistical significance testing
```

### 3.2 Multi-Experiment Coordination
```python
class URASHGCampaign:
    - Sequential experiment execution
    - Parameter space optimization
    - Automated calibration verification
    - Data quality assessment
    - Experimental condition logging
    - Result comparison across experiments
```

### 3.3 Advanced GUI Development
**Enhanced PyMoDAQ extension:**
```python
class URASHGApp(CustomApp):
    Features:
    - Multi-panel experimental control
    - Real-time 2D/1D/0D visualization
    - Parameter optimization suggestions
    - Calibration status monitoring
    - Experiment progress tracking
    - Data export utilities
```

## Phase 4: Validation and Optimization (Weeks 13-16)

### 4.1 Hardware Integration Testing
- **EOM-Red Pitaya synchronization**
- **Multi-camera coordination (if needed)**
- **Elliptec rotator reliability testing**
- **Long-duration experiment stability**
- **Power control accuracy validation**

### 4.2 Data Analysis Validation
- **Compare with existing urashg_2 results**
- **Statistical analysis of measurement precision**
- **Calibration curve stability over time**
- **Background subtraction accuracy**
- **Metadata integrity verification**

### 4.3 Performance Optimization
- **Loop timing optimization**
- **Memory usage optimization for large datasets**
- **HDF5 storage compression and speed**
- **GUI responsiveness during long experiments**
- **Hardware communication efficiency**

## Phase 5: Advanced Experiments (Weeks 17-20)

### 5.1 Multi-Dimensional Parameter Spaces
```python
# 6D experiment capability
class AdvancedURASHG:
    Dimensions: [y, x, wavelength, theta, phi, power]
    - Theta: Incident polarization angle
    - Phi: QWP ellipticity control
    - Full polarimetric characterization
    - Nonlinear susceptibility tensor elements
```

### 5.2 Automated Optimization
```python
class URASHGOptimizer:
    - Intelligent parameter space exploration
    - Signal-to-noise optimization
    - Adaptive measurement strategies
    - Machine learning integration
    - Experimental condition prediction
```

### 5.3 High-Throughput Capabilities
- **Parallel processing for analysis**
- **Automated sample positioning (future)**
- **Batch experiment scheduling**
- **Remote experiment monitoring**
- **Cloud data storage integration**

## Critical Implementation Considerations

### 1. Hardware Dependencies
- **EOM calibration files are ESSENTIAL** - experiments cannot run without proper calibration
- **Rotator homing sequences are CRITICAL** - reference positioning affects all measurements
- **PID control parameters may need tuning** - hardware-specific optimization required

### 2. Data Management Strategy
- **HDF5 with compression** for large multi-dimensional datasets
- **Metadata standardization** for reproducibility
- **Backup strategies** for long experiments
- **Version control** for calibration data

### 3. Error Handling Philosophy
- **Graceful degradation** when hardware fails
- **Automatic retry** with parameter adjustment
- **Manual intervention points** for complex issues
- **Comprehensive logging** for debugging

### 4. Testing Strategy
- **Mock hardware simulation** for development
- **Hardware-in-the-loop testing** for validation
- **Long-duration stability testing** for reliability
- **Cross-platform compatibility** testing

## Resource Requirements

### Development Team
- **Primary Developer**: PyMoDAQ plugin development
- **Hardware Specialist**: EOM and rotator integration
- **Data Analysis Expert**: Algorithm implementation
- **Testing Coordinator**: Validation and optimization

### Hardware Access
- **Complete μRASHG setup** for integration testing
- **Calibration standards** for validation
- **Multiple laser wavelengths** for testing
- **Reference samples** for comparison

### Software Infrastructure
- **Development PyMoDAQ environment**
- **Version control system** (Git)
- **Continuous integration** for testing
- **Documentation system** (Sphinx)

## Success Metrics

### Technical Milestones
1. **Calibration system accuracy**: ±0.1% power control
2. **Measurement reproducibility**: <1% variation between runs
3. **Data integrity**: 100% metadata preservation
4. **Experiment duration**: Support for 24+ hour measurements
5. **GUI responsiveness**: <100ms update latency

### Scientific Validation
1. **Reproduce existing urashg_2 results** within measurement uncertainty
2. **Demonstrate enhanced capabilities** not available in original system
3. **Validate multi-dimensional experiments** with known samples
4. **Confirm calibration stability** over extended periods
5. **Document performance improvements** over legacy system

This comprehensive plan provides a roadmap for developing a world-class μRASHG experimental system within the PyMoDAQ framework, leveraging all the insights gained from the urashg_2 repository analysis.