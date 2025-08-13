# PyMoDAQ Official Architecture Patterns Research

## Overview
Based on comprehensive research of PyMoDAQ 5.x documentation, templates, and Context7 analysis, this document provides definitive patterns for implementing PyMoDAQ plugins correctly.

## Plugin Types and When to Use Each

### 1. Instrument Plugins (Individual Device Control)
**Use for:** Single device control (cameras, motion controllers, power meters)
**Structure:** 
- `DAQ_Move_XXX` - Controls actuators/motion devices
- `DAQ_Viewer_XXX` - Controls detectors/sensors

**Entry Points Required:**
```toml
[project.entry-points."pymodaq.move_plugins"]
daq_move_Template = "pymodaq_plugins_mypackage.daq_move_plugins.daq_move_Template:DAQ_Move_Template"

[project.entry-points."pymodaq.viewer_plugins"]  
daq_2Dviewer_Template = "pymodaq_plugins_mypackage.daq_viewer_plugins.plugins_2D.daq_2Dviewer_Template:DAQ_2DViewer_Template"
```

### 2. Extensions (Multi-Device Coordination) ⭐ **RECOMMENDED FOR URASHG**
**Use for:** Complex experiments requiring coordinated control of multiple devices
**Structure:** Inherit from `gutils.CustomApp`
**Benefits:** 
- Access to all dashboard actuators/detectors via `self.dashboard` 
- Can coordinate complex measurement sequences
- Integrated with PyMoDAQ dashboard environment
- Perfect for microscopy/spectroscopy experiments

**Entry Points Required:**
```toml
[project.entry-points."pymodaq.extensions"]
extension_name = "pymodaq_plugins_mypackage.extensions.extension_name"
```

### 3. Custom Applications (Standalone Systems)
**Use for:** Complete standalone applications outside PyMoDAQ framework
**Structure:** Independent Qt applications
**When to Use:** When you need complete control over the UI and don't need PyMoDAQ integration

## Multi-Axis Plugin Patterns (CRITICAL FOR ELLIPTEC)

### Correct Multi-Axis Implementation
```python
class DAQ_Move_Elliptec(DAQ_Move_base):
    """Multi-axis rotation mount controller"""
    
    # REQUIRED: Define axes as list or dict
    _axis_names = ['QWP', 'HWP_incident', 'HWP_analyzer']
    # OR as dict:
    _axis_names = {'QWP': 0, 'HWP_incident': 1, 'HWP_analyzer': 2}
    
    # REQUIRED: Corresponding units for each axis
    _controller_units = ['degrees', 'degrees', 'degrees']
    
    # REQUIRED: Precision for each axis
    _epsilons = [0.1, 0.1, 0.1]
    
    # Accessing current axis info:
    def move_abs(self, position):
        current_axis = self.axis_name      # e.g., 'QWP'  
        axis_index = self.axis_value       # e.g., 0 or 'QWP'
        axis_unit = self.axis_unit         # e.g., 'degrees'
        axis_epsilon = self.epsilon        # e.g., 0.1
```

## DataActuator Usage Patterns (FIXES YOUR CURRENT ERRORS)

### PyMoDAQ 5.x Correct Patterns

#### Single-Axis Controllers (MaiTai Laser)
```python
def move_abs(self, position: Union[float, DataActuator]):
    """CORRECT pattern for single-axis"""
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # ✅ CORRECT!
        # Do NOT use: position.data[0][0] - causes "float not iterable"
```

#### Multi-Axis Controllers (Elliptec, ESP300) 
```python
def move_abs(self, positions: Union[List[float], DataActuator]):
    """CORRECT pattern for multi-axis"""
    if isinstance(positions, DataActuator):
        target_array = positions.data[0]  # ✅ CORRECT for multi-axis!
        # This returns array-like object for multiple axes
```

### Data Structure Creation (PyMoDAQ 5.x)
```python
from pymodaq_data.data import DataWithAxes, Axis
from pymodaq.utils.data import DataSource

# CORRECT PyMoDAQ 5.x data emission
data = DataWithAxes(
    'Camera', 
    data=[image_data],
    axes=[Axis('x', data=x_axis), Axis('y', data=y_axis)],
    units="counts",  # String, NOT list!
    source=DataSource.raw
)
```

## move_home() Method Signature (FIXES YOUR HOMING ERROR)

### PyMoDAQ 5.x Correct Implementation
```python
def move_home(self, value=None):
    """
    Move to home position
    
    Parameters
    ---------- 
    value : any, optional
        Home position value (can be None for default home)
    """
    try:
        # Implementation depends on hardware:
        # Option 1: Hardware has built-in home
        self.controller.move_home()
        
        # Option 2: Move to predefined position
        home_position = 0.0  # or from settings
        self.move_abs(home_position)
        
        # REQUIRED: Update current position and emit signals
        current_pos = self.get_actuator_value()
        self.emit_value(DataActuator(data=current_pos, units=self.axis_unit))
        self.emit_status(ThreadCommand('move_done', current_pos))
        
    except Exception as e:
        self.emit_status(ThreadCommand('Update_Status', f'Homing failed: {e}'))
        raise
```

## Thread Communication Patterns

### Status Updates
```python
from pymodaq.control_modules.utils import ThreadCommand

# Update status bar
self.emit_status(ThreadCommand('Update_Status', 'Initializing...'))

# Update current position 
self.emit_status(ThreadCommand('get_actuator_value', 
                              DataActuator(data=position, units='degrees')))

# Signal move completed
self.emit_status(ThreadCommand('move_done', final_position))

# Update settings dynamically
self.emit_status(ThreadCommand('update_settings', 
                              [['param_name'], new_value, 'value']))
```

## Hardware Integration Best Practices

### Safe Hardware Wrapper Import
```python
try:
    from .hardware.elliptec_wrapper import ElliptecWrapper
    HAS_ELLIPTEC = True
except ImportError:
    HAS_ELLIPTEC = False
    # Provide mock or raise informative error
```

### Parameter Tree Structure
```python
params = [
    {'title': 'Hardware Settings', 'name': 'hardware_settings', 'type': 'group', 'children': [
        {'title': 'Device Port:', 'name': 'port', 'type': 'str', 'value': 'COM1'},
        {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 1000},
        {'title': 'Address:', 'name': 'address', 'type': 'int', 'value': 0, 'limits': [0, 15]},
    ]},
    {'title': 'Multiaxes:', 'name': 'multiaxes', 'type': 'group', 'children': [
        {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': self._axis_names},
        {'title': 'Status:', 'name': 'multi_status', 'type': 'table'},
    ]},
]
```

## Key Findings for URASHG System

### Architecture Recommendation: **PyMoDAQ Extensions**
Your μRASHG system should use **PyMoDAQ Extensions** rather than standalone plugins because:

1. **Multi-Device Coordination:** Extensions can access all dashboard devices simultaneously
2. **Experiment Control:** Built for complex measurement sequences  
3. **Data Integration:** Seamless data flow between devices
4. **GUI Integration:** Proper integration with PyMoDAQ dashboard

### Current Issues Root Causes
1. **DataActuator Errors:** Using wrong patterns for single vs multi-axis
2. **move_home() Errors:** Missing required `value` parameter
3. **UI Integration:** Individual plugins don't coordinate well for complex experiments

### Recommended Architecture
```
μRASHG Extension (coordinates all devices)
├── MaiTai Plugin (laser control)  
├── Elliptec Plugin (3-axis rotation)
├── PrimeBSI Plugin (camera)
├── Newport Plugin (power meter)
└── ESP300 Plugin (translation stages)
```

## Template Repository Analysis

The official `pymodaq_plugins_template` provides:
- Standard project structure with `pyproject.toml`
- Entry point configurations
- Testing frameworks
- GitHub Actions for CI/CD
- Clear documentation templates

**Key Template Features:**
- Supports all plugin types (Move, Viewer0D/1D/2D, PID)
- Includes hardware abstraction layer patterns
- Provides configuration management examples
- Shows proper import handling for optional dependencies

## Next Steps for URASHG Implementation

1. **Immediate Fix:** Update DataActuator usage patterns in existing plugins
2. **Architecture Migration:** Implement URASHG Extension for coordinated control  
3. **Plugin Refinement:** Fix move_home() signatures in all move plugins
4. **Testing Integration:** Ensure all plugins work correctly with extension coordinator

This research provides the definitive patterns needed to resolve your current PyMoDAQ integration issues and implement a proper μRASHG measurement system.