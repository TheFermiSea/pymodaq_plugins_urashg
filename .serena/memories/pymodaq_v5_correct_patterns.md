# PyMoDAQ v5.x Correct Plugin Patterns

## CRITICAL: Parameter Tree Initialization Race Condition

**ROOT CAUSE**: PyMoDAQ base classes access `self.settings.child()` during `__init__` before parameter tree is ready.

**ERROR PATTERN**:
```python
# ❌ WRONG - causes "Parameter Settings has no child named multiaxes" error
class DAQ_Move_Plugin(DAQ_Move_base):
    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)  # Base class tries to access self.settings immediately
```

**CORRECT PATTERN** (from PyMoDAQ mock examples):
```python
# ✅ CORRECT - deferred parameter access
class DAQ_Move_Plugin(DAQ_Move_base):
    def __init__(self, parent=None, params_state=None):
        self.controller = None  # Initialize before super()
        super().__init__(parent, params_state)  # Base class can now safely access parameters

    def commit_settings(self, param):
        """Called AFTER parameter tree is ready"""
        # Safe to access self.settings here
        if param.name() == "axis":
            self.get_actuator_value()
```

## Parameter Structure Requirements

**MANDATORY parameter structure for Move plugins**:
```python
params = [
    {
        'title': 'MultiAxes:',
        'name': 'multiaxes',
        'type': 'group',
        'children': [
            {
                'title': 'is Multiaxis:',
                'name': 'ismultiaxes',
                'type': 'bool',
                'value': False,
                'default': False
            },
            {
                'title': 'Status:',
                'name': 'multi_status',
                'type': 'list',
                'value': 'Master',
                'default': 'Master',
                'limits': ['Master', 'Slave']
            },
            {
                'title': 'Axis:',
                'name': 'axis',
                'type': 'list',
                'value': 'Axis1',
                'default': 'Axis1',
                'limits': ['Axis1']
            }
        ]
    },
    # Plugin-specific parameters go here
]
```

**MANDATORY parameter structure for Viewer plugins**:
```python
params = [
    {
        'title': 'Cam settings:',
        'name': 'camera_settings',
        'type': 'group',
        'children': [
            {
                'title': 'Camera Model:',
                'name': 'camera_type',
                'type': 'str',
                'value': 'Camera1',
                'readonly': True
            }
        ]
    }
]
```

## Mandatory Methods for Viewer Plugins

**ALL Viewer plugins MUST implement these methods**:
```python
class DAQ_2DViewer_Plugin(DAQ_Viewer_base):
    def ini_detector(self, controller=None):
        """Initialize the detector/camera"""
        pass
    
    def ini_stage(self):
        """CRITICAL: This method is mandatory but often forgotten"""
        pass
    
    def commit_settings(self, param):
        """Handle parameter changes"""
        pass
    
    def close(self):
        """Cleanup when closing"""
        pass
    
    def grab_data(self, Naverage=1, **kwargs):
        """Acquire data from detector"""
        pass
```

## DataActuator Usage Patterns

**Single-axis controllers** (MaiTai, Newport):
```python
def move_abs(self, position: Union[float, DataActuator]):
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # ✅ CORRECT
    else:
        target_value = float(position)
```

**Multi-axis controllers** (Elliptec, ESP300):
```python
def move_abs(self, positions: Union[List[float], DataActuator]):
    if isinstance(positions, DataActuator):
        target_array = positions.data[0]  # ✅ CORRECT for multi-axis
    else:
        target_array = positions
```

**❌ NEVER do this** (causes UI failure):
```python
target_value = float(position.data[0][0])  # WRONG!
```

## PyVCAM 2.2.3 Correct API Usage

**❌ WRONG** (non-existent in PyVCAM 2.2.3):
```python
import pyvcam.pvc  # Module doesn't exist!
```

**✅ CORRECT** PyVCAM 2.2.3 patterns:
```python
import pyvcam
from pyvcam import Camera
from pyvcam.constants import CLEAR_NEVER, CLEAR_PRE_SEQUENCE, EXT_TRIG_INTERNAL

# Initialization
pyvcam.pvc.init_pvcam()
camera = next(Camera.detect_camera())

# Cleanup
camera.close()
pyvcam.pvc.uninit_pvcam()
```

## Plugin Entry Points Structure

**Correct pyproject.toml entry points**:
```toml
[project.entry-points."pymodaq.move_plugins"]
urashg_elliptec = "pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec"
urashg_maitai = "pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai"

[project.entry-points."pymodaq.viewer_plugins"] 
urashg_primebsi = "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI"
```

## Threading Safety Requirements

**❌ NEVER use __del__ methods** (causes QThread conflicts):
```python
def __del__(self):
    self.disconnect()  # Causes dashboard crashes!
```

**✅ CORRECT cleanup pattern**:
```python
def close(self):
    """Explicit cleanup following PyMoDAQ lifecycle"""
    if self.controller:
        self.controller.disconnect()
        self.controller = None
```

## Data Structure Requirements (PyMoDAQ 5.x)

**✅ CORRECT DataWithAxes usage**:
```python
from pymodaq.utils.data import DataWithAxes, Axis, DataSource

data = DataWithAxes(
    'Camera',
    data=[image_data],
    axes=[Axis('x', data=x_axis), Axis('y', data=y_axis)],
    units="counts",  # String, not list!
    source=DataSource.raw  # Required in v5.x
)
```

## Common PyMoDAQ v5.x Import Patterns

```python
# Standard PyMoDAQ imports
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters_fun, main
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main
from pymodaq.utils.data import DataWithAxes, Axis, DataSource
from pymodaq.utils.parameter import Parameter

# Hardware abstraction
from pymodaq.utils.logger import set_logger, get_logger
```

## Real vs Mock Plugin Testing

**Mock plugins work** because they follow these patterns exactly.
**Our plugins fail** because they violate these fundamental requirements.

**Key insight**: PyMoDAQ mock examples are the GOLD STANDARD - they demonstrate working patterns that we must follow exactly.

## Implementation Priority Order

1. **Fix parameter tree race condition** - affects ALL Move plugins
2. **Add missing mandatory methods** - especially `ini_stage()` for Camera
3. **Fix PyVCAM API usage** - update to 2.2.3 compatible calls  
4. **Verify DataActuator patterns** - ensure single vs multi-axis correctness
5. **Test with real hardware** - only after structural fixes are complete

## Validation Strategy

- Use `test_real_hardware.py` to verify each fix
- Compare against working PyMoDAQ mock plugins
- Test plugin discovery: `python -c "from pymodaq_plugins_urashg import *"`
- Test PyMoDAQ integration: Load plugins in dashboard without crashes