# Correct Move Plugin Implementation Patterns for PyMoDAQ 5.x

## CRITICAL: Parameter Tree Race Condition Resolution

**ROOT CAUSE IDENTIFIED**: PyMoDAQ base classes access `self.settings.child()` during `__init__` before parameter tree is fully initialized.

### ✅ CORRECT Implementation Pattern

**MANDATORY parameter structure** (prevents race condition):
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
                'limits': ['Axis1']  # Single axis by default
            }
        ]
    },
    # Plugin-specific parameters follow...
]
```

**✅ CORRECT Initialization Pattern**:
```python
class DAQ_Move_Plugin(DAQ_Move_base):
    def __init__(self, parent=None, params_state=None):
        # Initialize controller BEFORE calling super()
        self.controller = None
        self._position = 0.0
        
        # Now safe to call super() - parameter tree is properly structured
        super().__init__(parent, params_state)
        
    def commit_settings(self, param):
        """Handle parameter changes AFTER parameter tree is ready"""
        if param.name() == "axis":
            # Safe to access settings here
            axis_value = self.settings.child('multiaxes', 'axis').value()
            # Handle axis changes...
```

### DataActuator Usage Patterns

**Single-Axis Controllers** (MaiTai, Newport):
```python
def move_abs(self, position: Union[float, DataActuator]):
    """Move to absolute position for single-axis controller"""
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # ✅ CORRECT for single axis
    else:
        target_value = float(position)
    
    # Perform move
    self.controller.move_to(target_value)
    self.get_actuator_value()  # Update position
```

**Multi-Axis Controllers** (Elliptec, ESP300):
```python
def move_abs(self, positions: Union[List[float], DataActuator]):
    """Move to absolute positions for multi-axis controller"""
    if isinstance(positions, DataActuator):
        target_array = positions.data[0]  # ✅ CORRECT for multi-axis
    else:
        target_array = positions
    
    # Handle multiple axes
    for axis, target in enumerate(target_array):
        self.controller.move_axis(axis, target)
    
    self.get_actuator_value()  # Update all positions
```

**❌ CRITICAL ERROR to avoid**:
```python
# This causes UI crashes:
target_value = float(position.data[0][0])  # WRONG - double indexing
```

### Hardware Controller Initialization

**✅ CORRECT Pattern** (prevents connection issues):
```python
def ini_actuator(self):
    """Initialize hardware connection"""
    try:
        # Get connection parameters
        port = self.settings.child('connection_settings', 'port').value()
        baudrate = self.settings.child('connection_settings', 'baudrate').value()
        
        # Initialize controller
        self.controller = HardwareController(port=port, baudrate=baudrate)
        self.controller.connect()
        
        # Verify connection
        if not self.controller.is_connected():
            raise ConnectionError(f"Failed to connect to {port}")
        
        # Get initial position
        self.get_actuator_value()
        
        # Set initialized state
        self.initialized = True
        return self.status
        
    except Exception as e:
        self.status.update(msg=f"Initialization failed: {e}", busy=False)
        self.initialized = False
        return self.status
```

### Position Management Patterns

**✅ CORRECT get_actuator_value Implementation**:
```python
def get_actuator_value(self):
    """Get current position from hardware"""
    try:
        if self.controller and self.controller.is_connected():
            # Single axis
            if not self.settings.child('multiaxes', 'ismultiaxes').value():
                position = self.controller.get_position()
                self.current_position = position
                self.emit_status(ThreadCommand('position_is', [position]))
            
            # Multi-axis
            else:
                positions = self.controller.get_all_positions()
                self.current_position = positions
                self.emit_status(ThreadCommand('position_is', positions))
                
    except Exception as e:
        self.emit_status(ThreadCommand('error', [f"Position read failed: {e}"]))
```

### Mandatory Methods for Move Plugins

**All Move plugins MUST implement**:
```python
class DAQ_Move_Plugin(DAQ_Move_base):
    def ini_actuator(self):
        """Initialize hardware connection"""
        # Implementation required
        
    def close(self):
        """Clean shutdown of hardware"""
        try:
            if self.controller:
                self.controller.disconnect()
                self.controller = None
        except Exception as e:
            print(f"Warning: Error during close: {e}")
    
    def get_actuator_value(self):
        """Get current position from hardware"""
        # Implementation required
        
    def move_abs(self, position):
        """Move to absolute position"""
        # Implementation required
        
    def move_rel(self, rel_position):
        """Move relative amount"""
        # Implementation required
        
    def move_home(self):
        """Move to home position"""
        # Implementation required
        
    def stop(self):
        """Stop current motion"""
        # Implementation required
```

### Error Handling Patterns

**✅ ROBUST Error Handling**:
```python
def move_abs(self, position: Union[float, DataActuator]):
    try:
        # Validate inputs
        if isinstance(position, DataActuator):
            target = float(position.value())
        else:
            target = float(position)
            
        # Check limits
        if not self._check_position_limits(target):
            raise ValueError(f"Position {target} exceeds limits")
        
        # Perform move
        self.controller.move_to(target)
        
        # Wait for completion
        if self.settings.child('motion_settings', 'wait_for_completion').value():
            self._wait_for_move_completion()
            
        # Update position
        self.get_actuator_value()
        
    except Exception as e:
        error_msg = f"Move failed: {e}"
        self.emit_status(ThreadCommand('error', [error_msg]))
        raise
```

### Threading Safety Requirements

**✅ SAFE Threading Patterns**:
```python
def close(self):
    """Thread-safe cleanup"""
    try:
        if hasattr(self, 'controller') and self.controller:
            self.controller.disconnect()
            self.controller = None
    except Exception as e:
        # Log error but don't raise exception during cleanup
        print(f"Warning: Cleanup error: {e}")

# ❌ NEVER use __del__ methods (causes Qt threading issues)
# def __del__(self):
#     self.close()  # This causes dashboard crashes!
```

### Connection Parameter Patterns

**✅ STANDARD Connection Parameters**:
```python
# Add to plugin params list
{
    'title': 'Connection Settings',
    'name': 'connection_settings', 
    'type': 'group',
    'children': [
        {
            'title': 'Port:',
            'name': 'port',
            'type': 'str',
            'value': '/dev/ttyUSB0'
        },
        {
            'title': 'Baudrate:',
            'name': 'baudrate',
            'type': 'list',
            'value': 9600,
            'limits': [9600, 19200, 38400, 57600, 115200]
        },
        {
            'title': 'Timeout (ms):',
            'name': 'timeout',
            'type': 'int',
            'value': 1000,
            'min': 100,
            'max': 10000
        }
    ]
}
```

### Units and Scaling

**✅ PROPER Units Handling**:
```python
# In plugin params
{
    'title': 'Motion Settings',
    'name': 'motion_settings',
    'type': 'group', 
    'children': [
        {
            'title': 'Units:',
            'name': 'units',
            'type': 'list',
            'value': 'degrees',
            'limits': ['degrees', 'radians', 'mm', 'um']
        },
        {
            'title': 'Scaling Factor:',
            'name': 'scaling',
            'type': 'float',
            'value': 1.0,
            'min': 0.001,
            'max': 1000.0
        }
    ]
}

# In move methods
def move_abs(self, position):
    # Apply scaling
    scaling = self.settings.child('motion_settings', 'scaling').value()
    scaled_position = float(position) * scaling
    
    # Send to hardware
    self.controller.move_to(scaled_position)
```

### Multi-Axis Configuration

**✅ CORRECT Multi-Axis Setup**:
```python
# For controllers with multiple axes (ESP300, Elliptec)
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
                'value': True,  # Set True for multi-axis controllers
                'default': True
            },
            {
                'title': 'Number of Axes:',
                'name': 'num_axes',
                'type': 'int',
                'value': 3,  # ESP300 typically has 3 axes
                'min': 1,
                'max': 6
            },
            {
                'title': 'Axis:',
                'name': 'axis',
                'type': 'list',
                'value': 'Axis1',
                'limits': ['Axis1', 'Axis2', 'Axis3']  # Updated dynamically
            }
        ]
    }
]
```

### Common Implementation Pitfalls

**❌ AVOID These Patterns**:

1. **Wrong Parameter Access During Init**:
```python
def __init__(self, parent=None, params_state=None):
    super().__init__(parent, params_state)
    # ❌ WRONG - parameter tree not ready yet
    port = self.settings.child('connection_settings', 'port').value()
```

2. **Incorrect DataActuator Handling**:
```python
def move_abs(self, position):
    # ❌ WRONG - causes type errors
    target = position.value[0].data()
```

3. **Missing Thread Safety**:
```python
def __del__(self):
    # ❌ WRONG - causes Qt threading crashes
    self.controller.disconnect()
```

4. **Improper Error Propagation**:
```python
def move_abs(self, position):
    try:
        self.controller.move_to(position)
    except:
        pass  # ❌ WRONG - swallows all errors silently
```

### Verification Testing

**✅ Test These Patterns Work**:
1. Plugin instantiates without parameter tree errors
2. Hardware initialization succeeds with real devices  
3. Position read/write operations function correctly
4. DataActuator handling works in PyMoDAQ dashboard
5. Multi-axis vs single-axis modes work appropriately
6. Clean shutdown without threading issues

The patterns documented here are based on **successful resolution** of the URASHG plugin parameter tree race conditions and **verified compatibility** with PyMoDAQ 5.x framework requirements.