# Complete μRASHG Extension Architecture & Implementation Plan

## Executive Summary

Based on comprehensive PyMoDAQ Extension research using specialized agents and deep architectural analysis, this document provides the complete production-ready implementation plan for a μRASHG (micro Rotational Anisotropy Second Harmonic Generation) Extension that coordinates all hardware devices through PyMoDAQ 5.x framework.

## Current System Status (August 2025)

**✅ Foundation Complete:**
- All individual plugins PyMoDAQ 5.x compatible and hardware tested
- Entry point paths fixed, plugin discovery working
- Hardware integration verified: Elliptec (3x), PrimeBSI camera, Newport power meter, MaiTai laser
- Repository cleaned and committed to git
- Extensions directory structure exists with placeholders

**🎯 Next Phase:** Transform placeholder extensions into production-ready coordinated μRASHG Extension

## Architecture Decision: Single Primary Extension

**Recommended Approach:** One comprehensive `URASHGMicroscopyExtension` with modular experiment capabilities rather than multiple separate extensions.

**Benefits:**
- Better user experience (single interface)
- Easier maintenance and updates
- Centralized device coordination
- Unified data management

## 1. Core Extension Class Design

### Primary Extension Structure

```python
# File: src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py
from pymodaq.utils.gui_utils import CustomApp

class URASHGMicroscopyExtension(CustomApp):
    """
    Production-ready μRASHG Extension for PyMoDAQ Dashboard
    
    Coordinates:
    - 3x Elliptec rotation mounts (addresses 2,3,8)
    - Photometrics PrimeBSI camera  
    - Newport 1830-C power meter
    - MaiTai laser with EOM control
    - Optional: PyRPL PID stabilization
    """
    
    # Extension metadata
    name = 'μRASHG Microscopy System'
    description = 'Complete polarimetric SHG measurements'
    author = 'μRASHG Development Team'
    version = '1.0.0'
```

### Multi-Device Coordination Architecture

```python
class DeviceManager:
    """Centralized coordination of all μRASHG devices"""
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.modules_manager = dashboard.modules_manager
        self.devices = {
            'camera': None,      # PrimeBSI
            'power_meter': None, # Newport1830C  
            'elliptec': None,    # 3-axis rotation mounts
            'laser': None,       # MaiTai
            'pid': None,         # PyRPL (optional)
        }
        
    def initialize_devices(self):
        """Discover and validate all required devices"""
        
    def synchronize_acquisition(self):
        """Coordinate timing across all devices"""
        
    def emergency_stop(self):
        """Safe shutdown sequence"""
```

## 2. Parameter Tree Architecture

### Hierarchical Configuration System

**Experiment Configuration:**
- Measurement Type: ['Basic RASHG', 'Multi-Wavelength RASHG', 'Full Polarimetric SHG', 'Calibration']
- Polarization Steps: 4-360 (default: 36)
- Integration Time: 1-10000ms (default: 100ms)
- Number of Averages: 1-100 (default: 1)

**Hardware Settings:**
- Device Selection and Address Configuration
- Camera ROI settings (X/Y start, Width/Height)
- Safety Limits (Max power, rotation speed, timeouts)

**Multi-Wavelength Settings:**
- Enable/Disable wavelength scanning
- Start/Stop wavelengths (700-1000nm)
- Number of wavelength steps

**Data Management:**
- Save Directory and File Naming
- Auto-save configuration
- Raw data retention options

## 3. Device Integration Patterns

### Dashboard Module Access

```python
class DeviceIntegrationManager:
    """Production-ready device access through PyMoDAQ dashboard"""
    
    def discover_and_validate_devices(self):
        """Auto-discover and validate required devices"""
        required_devices = {
            'camera': {'type': 'viewer', 'name_pattern': 'PrimeBSI'},
            'power_meter': {'type': 'viewer', 'name_pattern': 'Newport1830C'},
            'elliptec': {'type': 'actuator', 'name_pattern': 'Elliptec'},
            'laser': {'type': 'actuator', 'name_pattern': 'MaiTai'},
        }
        
        # Validation logic here
        
    def setup_synchronized_acquisition(self):
        """Configure coordinated data acquisition"""
        # Camera trigger configuration
        # Power meter averaging setup
        # Timing synchronization
```

### State Machine for Complex Experiments

```python
class ExperimentStateMachine:
    """State management for multi-device experiments"""
    
    states = ['IDLE', 'INITIALIZING', 'MEASURING', 'ANALYZING', 'SAVING', 'ERROR']
    
    def transition_to(self, new_state):
        """Safe state transitions with validation"""
        
    def register_state_callback(self, state, callback):
        """Register callbacks for state entry"""
```

## 4. Data Management System

### FAIR-Compliant HDF5 Schema

```python
hdf5_structure = {
    'experiment_metadata': {
        'measurement_type': 'string',
        'timestamp': 'datetime', 
        'operator': 'string',
        'instrument_config': 'group',
    },
    'raw_data': {
        'camera_images': 'array[N, height, width]',
        'power_readings': 'array[N]',
        'timestamps': 'array[N]',
    },
    'processed_data': {
        'rashg_intensity': 'array[N_pol]',
        'polarization_angles': 'array[N_pol]',
        'analysis_parameters': 'group',
    },
    'hardware_positions': {
        'qwp_angles': 'array[N]',
        'hwp_incident_angles': 'array[N]', 
        'hwp_analyzer_angles': 'array[N]',
        'laser_wavelengths': 'array[N_wl]',
    },
    'calibration_data': {
        'polarization_calibration': 'group',
        'power_calibration': 'group',
        'timestamp': 'datetime',
    }
}
```

### Real-Time Visualization

**Visualization Components:**
- Live camera preview with ROI overlay
- Real-time RASHG polar plot
- Power stability monitoring 
- Wavelength dependence display
- Measurement progress indicators

## 5. Experiment Sequences

### Core Measurement Types

**1. Basic RASHG Sequence:**
- Single wavelength polarization sweep
- QWP rotation (0-180° or custom range)
- Synchronized camera + power meter acquisition
- Real-time polar plot updates

**2. Multi-Wavelength RASHG:**
- Coordinate MaiTai wavelength changes
- Full polarization sweep at each wavelength
- 3D data collection (angle, wavelength, intensity)
- Advanced visualization and analysis

**3. Full Polarimetric SHG:**
- Coordinate all 3 rotation mounts (QWP + 2x HWP)
- Complete Stokes parameter determination
- Advanced polarization analysis
- Mueller matrix extraction capability

**4. Calibration Sequences:**
- Automated polarization element calibration
- Power-dependent measurements
- Wavelength-dependent calibration
- System characterization routines

### Measurement Loop Architecture

```python
class BasicRASHGSequence:
    """Production-ready basic RASHG measurement"""
    
    def execute(self):
        """Execute complete measurement sequence"""
        try:
            self._initialize_devices()
            data_collection = self._run_measurement_loop()
            analysis_results = self._analyze_data(data_collection)
            self._save_results(data_collection, analysis_results)
            return analysis_results
        except Exception as e:
            self._handle_error(e)
            raise
    
    def _run_measurement_loop(self):
        """Core measurement loop with device coordination"""
        for angle in self.polarization_angles:
            # Move QWP to position
            self.device_manager.move_qwp(angle)
            self.device_manager.wait_for_movement_complete()
            
            # Acquire synchronized data
            camera_data = self.device_manager.acquire_camera_image()
            power_data = self.device_manager.read_power_meter()
            
            # Store with metadata
            # Update visualization
```

## 6. User Interface Design

### Dock-Based Layout

**Control Panel Dock:**
- Complete parameter tree
- Action buttons (Start, Stop, Pause)
- Progress indicators
- System status display

**Live Preview Dock:**
- Real-time camera image
- ROI overlay and controls
- Image analysis tools

**RASHG Analysis Dock:**
- Real-time polar plots
- Analysis parameters
- Fitting tools and results

**Status and Progress Dock:**
- Device status monitoring
- Measurement progress
- Error reporting and logging

### User Experience Features

- **One-click measurement start**
- **Real-time progress feedback**
- **Intuitive parameter organization**
- **Visual device status indicators**
- **Comprehensive error reporting**
- **Configuration save/load**
- **Measurement presets**

## 7. Entry Point Configuration

### pyproject.toml Update

```toml
[project.entry-points."pymodaq.extensions"]
urashg_microscopy = "pymodaq_plugins_urashg.extensions.urashg_microscopy_extension:URASHGMicroscopyExtension"
```

### plugin_info.toml Update

```toml
[plugin-info.entry-points.extensions]
urashg_microscopy = "pymodaq_plugins_urashg.extensions.urashg_microscopy_extension:URASHGMicroscopyExtension"
```

### Extension Discovery

```python
# src/pymodaq_plugins_urashg/extensions/__init__.py
EXTENSION_NAME = 'μRASHG Microscopy System'
CLASS_NAME = 'URASHGMicroscopyExtension'

try:
    from .urashg_microscopy_extension import URASHGMicroscopyExtension
    __all__ = ['URASHGMicroscopyExtension']
except ImportError as e:
    logger.warning(f"Could not import μRASHG extension: {e}")
    __all__ = []
```

## 8. 10-Week Implementation Roadmap

### Phase 1: Core Extension Framework (Weeks 1-2)
- Create URASHGMicroscopyExtension class
- Implement comprehensive parameter tree
- Setup dock-based UI layout
- Configure entry points and test discovery
- Implement DeviceManager for module access

**Deliverables:**
- Extension appears in PyMoDAQ dashboard menu
- Parameter tree functional and responsive
- Basic UI layout with docks
- Device discovery working

### Phase 2: Device Integration (Weeks 3-4)
- Implement device coordination through dashboard modules
- Create synchronization mechanisms
- Add safety interlocks and error handling
- Implement basic measurement sequence
- Add real-time status monitoring

**Deliverables:**
- All devices accessible through extension
- Basic measurement sequence working
- Error handling mechanisms
- Device status monitoring

### Phase 3: Advanced Measurements (Weeks 5-6)
- Implement full RASHG measurement loops
- Add multi-wavelength capability
- Create data collection and synchronization
- Implement real-time visualization
- Add configuration management

**Deliverables:**
- Complete basic RASHG measurements
- Multi-wavelength capability
- Real-time visualization
- Configuration save/load

### Phase 4: Data Management & Analysis (Weeks 7-8)
- Implement comprehensive HDF5 export
- Add real-time analysis and visualization
- Create measurement reporting
- Implement data validation
- Add advanced analysis tools

**Deliverables:**
- FAIR-compliant data export
- Real-time analysis
- Comprehensive reporting
- Data quality validation

### Phase 5: Production Hardening (Weeks 9-10)
- Comprehensive error handling
- Performance optimization
- UI polish and usability testing
- Documentation and user guides
- Full hardware integration testing

**Deliverables:**
- Production-ready extension
- Complete documentation
- Hardware integration testing
- User acceptance testing

## 9. Success Metrics

### Technical Success Criteria
- ✅ Extension discoverable in PyMoDAQ dashboard
- ✅ All devices accessible through single interface
- ✅ Complete RASHG measurements automated
- ✅ FAIR-compliant data export
- ✅ Real-time visualization and analysis
- ✅ Robust error handling

### User Experience Success Criteria  
- ✅ Intuitive parameter configuration
- ✅ Clear measurement progress feedback
- ✅ Comprehensive status monitoring
- ✅ Easy data access and visualization
- ✅ Reliable operation

### Performance Success Criteria
- ✅ Uninterrupted measurement sequences
- ✅ Responsive real-time visualization
- ✅ Efficient data export
- ✅ Stable memory usage during long measurements

## 10. Key Advantages of Extension Approach

### vs Individual Plugins
- **Coordinated Control:** Seamless multi-device synchronization
- **Unified Interface:** Single control point for complex experiments
- **Data Integration:** Correlated multi-device datasets
- **Experiment Logic:** Complex measurement sequences

### vs Custom Applications
- **PyMoDAQ Integration:** Leverage existing ecosystem
- **Device Discovery:** Automatic plugin detection
- **Data Management:** Built-in HDF5 export and visualization
- **Maintenance:** Framework updates automatic

## Implementation Status & Next Steps

**Current Status (August 2025):**
- ✅ Research and architecture planning complete
- ✅ Individual plugins PyMoDAQ 5.x compatible  
- ✅ Hardware integration verified
- ✅ Repository cleaned and documented
- 🎯 Ready for Extension implementation

**Immediate Next Steps:**
1. Begin Phase 1 implementation
2. Create URASHGMicroscopyExtension class structure
3. Implement basic parameter tree
4. Setup entry points and test discovery
5. Validate extension appears in PyMoDAQ dashboard

## Conclusion

This architecture provides a comprehensive, production-ready roadmap for transforming the existing hardware-verified plugins into a sophisticated, coordinated μRASHG Extension. The design leverages PyMoDAQ's Extension framework to provide seamless multi-device coordination while maintaining all the benefits of the ecosystem integration.

The modular architecture ensures maintainability and extensibility while the comprehensive implementation plan provides clear deliverables and success metrics for each phase. This approach transforms individual device plugins into a cohesive, professional measurement system suitable for advanced polarimetric SHG research.