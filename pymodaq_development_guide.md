# PyMoDAQ Plugin Development Guide for Polarimetric SHG Microscope Systems

## Executive Summary

PyMoDAQ provides a mature, modular framework for scientific instrument control with **sophisticated plugin architecture**, **hierarchical settings management**, and **robust hardware abstraction**. This guide delivers production-ready implementation patterns for your specific hardware stack: Red Pitaya PID control, Thorlabs ELL14 rotation mounts, and Photometrics Prime BSI camera integration.

The framework supports **over 50 official plugins** across major manufacturers, uses **entry point-based plugin discovery**, and provides **comprehensive development tools** including templates, mock devices, and automated testing infrastructure. Key architectural strengths include **memory-mapped FPGA register access**, **hardware ROI support**, and **thread-safe multi-instrument coordination**.

## Core PyMoDAQ Architecture and Plugin System

### Plugin Discovery and Registration

PyMoDAQ implements an **entry point-based plugin discovery system** that automatically detects installed packages at startup. The framework searches for packages following the `pymodaq_plugins_xxxx` naming convention and loads them dynamically through Python's entry points mechanism.

**Plugin organization structure:**
```
pymodaq_plugins_manufacturer/
├── src/pymodaq_plugins_manufacturer/
│   ├── daq_move_plugins/           # Actuator plugins
│   ├── daq_viewer_plugins/         # Detector plugins
│   │   ├── plugins_0D/
│   │   ├── plugins_1D/
│   │   └── plugins_2D/
│   └── hardware/                   # Hardware wrapper classes
│       └── manufacturer/
└── plugin_info.toml               # Entry point definitions
```

**Critical naming conventions:**
- Package: `pymodaq_plugins_xxxx`
- Actuator script: `daq_move_DeviceName.py`
- Actuator class: `DAQ_Move_DeviceName`
- Detector script: `daq_2Dviewer_DeviceName.py`
- Detector class: `DAQ_2DViewer_DeviceName`

### Settings Tree Architecture and Parameter Handling

PyMoDAQ extends **PyQtGraph's Parameter system** for hierarchical settings management. The parameter tree uses a **parent-child relationship** structure with XML serialization for persistence and inter-thread communication.

**Parameter types available:**
- `group`: Container for nested parameters
- `int`/`float`: Numeric controls with validation
- `str`: Text input fields
- `list`: Dropdown selections
- `bool`: Checkbox controls
- `browsepath`: File/directory selection
- Custom types for specialized needs

**Implementation pattern:**
```python
params = [
    {'title': 'Connection Settings:', 'name': 'connection', 'type': 'group', 'children': [
        {'title': 'IP Address:', 'name': 'ip_address', 'type': 'str', 'value': '192.168.1.100'},
        {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': 5000, 'min': 1, 'max': 65535},
    ]},
    {'title': 'Hardware Config:', 'name': 'hardware', 'type': 'group', 'children': [
        {'title': 'Enable Feature:', 'name': 'enable_feature', 'type': 'bool', 'value': True},
        {'title': 'Gain:', 'name': 'gain', 'type': 'float', 'value': 1.0, 'min': 0.1, 'max': 10.0}
    ]}
]
```

**Parameter communication workflow:**
1. **UI changes trigger** `commit_settings(param)` method automatically
2. **Plugin updates hardware** based on parameter modifications
3. **ThreadCommand objects** provide thread-safe inter-module communication
4. **XML serialization** enables configuration persistence and sharing

## DAQ_Move Plugin Implementation for Multi-Axis Actuators

### Base Class Structure and Required Methods

All actuator plugins inherit from `DAQ_Move_base` and must implement **mandatory methods** for PyMoDAQ integration:

```python
class DAQ_Move_ELL14(DAQ_Move_base):
    # Multi-axis configuration
    _axis_names = ['Rotator_1', 'Rotator_2', 'Rotator_3']
    _controller_units = ['degrees', 'degrees', 'degrees']
    _epsilons = [0.1, 0.1, 0.1]  # Position tolerance values
    
    def ini_attributes(self):
        """Initialize plugin-specific attributes"""
        self.controller = None
        
    def get_actuator_value(self):
        """Retrieve current position from hardware"""
        position = self.controller.get_current_position()
        return DataActuator(data=position)
        
    def move_abs(self, position):
        """Execute absolute position move"""
        self.controller.move_absolute(position.value())
        self.poll_moving()  # Wait for completion
        
    def move_rel(self, position):
        """Execute relative position move"""
        self.controller.move_relative(position.value())
        self.poll_moving()
        
    def move_home(self):
        """Return to home position"""
        self.controller.move_home()
        
    def close(self):
        """Clean up hardware connections"""
        if self.controller:
            self.controller.close()
```

### Multi-Axis Implementation Patterns

PyMoDAQ supports **Master/Slave architecture** for multi-axis controllers where multiple plugin instances share a single hardware controller:

**Master/Slave configuration:**
- **Master instance**: Initializes the physical hardware controller
- **Slave instances**: Reference the Master's controller through shared `controller_ID`
- **Automatic axis selection**: GUI displays axis combo box for multi-axis controllers
- **Shared parameter space**: All instances use the same settings tree structure

**Multi-axis access patterns:**
```python
# Access current axis information
current_axis = self.axis_index_key    # int or str identifier
axis_name = self.axis_name           # human-readable axis name
axis_unit = self.axis_unit           # measurement units
axis_value = self.axis_value         # current position value

# Configure axis properties
self.axis_units = ['mm', 'mm', 'degrees']  # Set units for all axes
```

### Thorlabs ELL14 Integration Implementation

For ELL14 rotator integration, **three primary library options** are available:

**Option 1: PyLabLib Integration (Recommended)**
```python
from pylablib.devices import Thorlabs

class DAQ_Move_ELL14_PyLabLib(DAQ_Move_base):
    _axis_names = ['ELL14_Rotator']
    _controller_units = ['degrees']
    
    params = [
        {'title': 'Connection:', 'name': 'connection', 'type': 'group', 'children': [
            {'title': 'COM Port:', 'name': 'com_port', 'type': 'str', 'value': 'COM3'},
            {'title': 'Device Address:', 'name': 'device_addr', 'type': 'int', 'value': 0},
        ]},
        {'title': 'Motion Settings:', 'name': 'motion', 'type': 'group', 'children': [
            {'title': 'Home on Startup:', 'name': 'home_on_init', 'type': 'bool', 'value': True},
            {'title': 'Step Size (deg):', 'name': 'step_size', 'type': 'float', 'value': 0.1}
        ]}
    ]
    
    def ini_stage(self, controller=None):
        if controller is None:
            self.controller = Thorlabs.ElliptecMotor(
                conn=self.settings['connection', 'com_port'],
                addr=self.settings['connection', 'device_addr']
            )
            if self.settings['motion', 'home_on_init']:
                self.controller.home()
        else:
            self.controller = controller
        return True
```

**Communication protocol characteristics:**
- **Serial interface**: 9600 baud, 8-N-1 format
- **Command structure**: 2-character commands plus parameters
- **Multi-device support**: Up to 16 devices on single bus
- **Synchronous operation**: All commands block until completion

## DAQ_Viewer Plugin Implementation for Camera Systems

### Base Class Architecture and Camera Integration

Camera plugins inherit from `DAQ_Viewer_base` with dimensional classification (`DAQ_2DViewer` for imaging systems). PyMoDAQ provides **GenericPylablibCamera** as a sophisticated base class for camera integration.

**Key camera plugin attributes:**
```python
class DAQ_2DViewer_PrimeBSI(GenericPylablibCamera):
    hardware_averaging = True      # Enable hardware-based averaging
    live_mode_available = True     # Support real-time acquisition
    
    def list_cameras(self):
        """Return list of available cameras"""
        return Photometrics.list_cameras()
    
    def init_controller(self):
        """Initialize camera controller"""
        self.controller = Photometrics.PvcamCamera(self.camera_name)
```

### ROI Functionality Implementation

Hardware ROI provides **superior performance** compared to software ROI by reducing data transfer and processing overhead:

**ROI parameter structure:**
```python
roi_params = [
    {'title': 'ROI Settings:', 'name': 'roi_settings', 'type': 'group', 'children': [
        {'title': 'Use Hardware ROI:', 'name': 'use_roi', 'type': 'bool', 'value': False},
        {'title': 'X Start:', 'name': 'roi_x', 'type': 'int', 'value': 0, 'min': 0},
        {'title': 'Y Start:', 'name': 'roi_y', 'type': 'int', 'value': 0, 'min': 0},
        {'title': 'Width:', 'name': 'roi_width', 'type': 'int', 'value': 1024, 'min': 1},
        {'title': 'Height:', 'name': 'roi_height', 'type': 'int', 'value': 1024, 'min': 1}
    ]}
]
```

**ROI data processing and emission:**
```python
def grab_data(self, Naverage=1, **kwargs):
    # Configure hardware ROI if enabled
    if self.settings['roi_settings', 'use_roi']:
        roi = (self.settings['roi_settings', 'roi_x'],
               self.settings['roi_settings', 'roi_y'], 
               self.settings['roi_settings', 'roi_width'],
               self.settings['roi_settings', 'roi_height'])
        self.controller.set_roi(*roi)
    
    # Acquire frame data
    frame = self.controller.get_frame(
        exp_time=self.settings['exposure_ms']
    )
    
    # Create data axes for proper display
    x_axis = Axis(label='X', units='pixels', data=np.arange(frame.shape[1]))
    y_axis = Axis(label='Y', units='pixels', data=np.arange(frame.shape[0]))
    
    # Emit structured data
    self.dte_signal.emit(DataToExport('PrimeBSI', data=[
        DataFromPlugins(name='Camera_Image', data=[frame], 
                       dim='Data2D', x_axis=x_axis, y_axis=y_axis)
    ]))
```

### Photometrics Prime BSI Integration with PyVCAM

**PyVCAM library integration pattern:**
```python
from pyvcam import pvc
from pyvcam.camera import Camera

class DAQ_2DViewer_PrimeBSI(DAQ_Viewer_base):
    def ini_detector(self, controller=None):
        if controller is None:
            pvc.init_pvcam()
            cameras = Camera.detect_camera()
            if not cameras:
                raise RuntimeError("No Photometrics cameras detected")
            self.controller = next(cameras)
            self.controller.open()
        else:
            self.controller = controller
            
        # Configure camera capabilities
        self.setup_camera_parameters()
        return True
    
    def setup_camera_parameters(self):
        """Configure camera-specific parameters"""
        # Query camera capabilities
        exp_range = self.controller.exp_time_range
        gain_range = self.controller.gain_range
        
        # Update parameter limits based on hardware
        self.settings.child('exposure_ms').setLimits(exp_range)
        self.settings.child('gain').setLimits(gain_range)
```

**Advanced camera features:**
- **Hardware averaging**: Utilize camera's built-in frame averaging
- **Binning support**: 1x1, 2x2, 4x4 hardware binning options
- **Speed tables**: Different readout modes for speed vs. noise optimization
- **Callback acquisition**: Asynchronous frame acquisition with callbacks

## Memory-Mapped FPGA Register Access for Red Pitaya

### FPGA Memory Architecture and Register Mapping

Red Pitaya uses **Zynq-7010 FPGA** with ARM processor and **memory-mapped I/O** for hardware control:

**Memory layout:**
- `0x00000000 - 0x0FFFFFFF`: System DRAM
- `0x40000000 - 0x400FFFFF`: Housekeeping (GPIO, PID control)
- `0x40100000 - 0x401FFFFF`: Oscilloscope registers
- `0x40200000 - 0x402FFFFF`: Signal generator registers

**Register access implementation:**
```python
import mmap
import os
import struct

class RedPitayaFPGAControl:
    def __init__(self, base_addr=0x40000000):
        self.base_addr = base_addr
        self.page_size = os.sysconf(os.sysconf_names['SC_PAGESIZE'])
        
        # Open memory device
        self.mem_fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        
        # Map FPGA register space
        self.fpga_regs = mmap.mmap(
            self.mem_fd,
            0x1000,  # 4KB mapping
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
            offset=self.base_addr & ~(self.page_size - 1)
        )
    
    def write_register(self, offset, value):
        """Write 32-bit value to FPGA register"""
        struct.pack_into('<I', self.fpga_regs, offset, value & 0xFFFFFFFF)
    
    def read_register(self, offset):
        """Read 32-bit value from FPGA register"""
        return struct.unpack_from('<I', self.fpga_regs, offset)[0]
    
    def close(self):
        """Clean up memory mapping"""
        if hasattr(self, 'fpga_regs'):
            self.fpga_regs.close()
        if hasattr(self, 'mem_fd'):
            os.close(self.mem_fd)
```

### PID Controller Integration Patterns

**Red Pitaya PID register structure:**
```python
class RedPitayaPIDControl(DAQ_Move_base):
    def __init__(self):
        self.pid_registers = {
            'setpoint': 0x40000010,      # PID setpoint register
            'output': 0x40000014,        # PID output readback  
            'kp': 0x40000018,            # Proportional gain
            'ki': 0x4000001C,            # Integral gain
            'kd': 0x40000020,            # Derivative gain
            'reset': 0x40000024,         # Integrator reset
            'enable': 0x40000028         # PID enable/disable
        }
    
    def set_pid_parameters(self, kp, ki, kd):
        """Configure PID controller gains"""
        # Convert to fixed-point representation
        kp_fixed = int(kp * (1 << 16))  # 16.16 fixed point
        ki_fixed = int(ki * (1 << 16))
        kd_fixed = int(kd * (1 << 16))
        
        self.fpga_control.write_register(self.pid_registers['kp'], kp_fixed)
        self.fpga_control.write_register(self.pid_registers['ki'], ki_fixed)
        self.fpga_control.write_register(self.pid_registers['kd'], kd_fixed)
    
    def move_abs(self, position):
        """Set PID setpoint for absolute positioning"""
        setpoint = int(position.value() * self.settings['scale_factor'])
        self.fpga_control.write_register(self.pid_registers['setpoint'], setpoint)
        
        # Enable PID controller
        self.fpga_control.write_register(self.pid_registers['enable'], 1)
        
        # Start position monitoring
        self.poll_moving()
```

## Hardware Library Integration Best Practices

### Library Integration Architecture Patterns

**Hardware wrapper implementation:**
```python
# hardware/manufacturer/device_wrapper.py
class DeviceWrapper:
    def __init__(self, connection_params):
        self.connection_params = connection_params
        self.device = None
        self.is_connected = False
    
    def connect(self):
        try:
            self.device = ManufacturerSDK.Device(**self.connection_params)
            self.device.initialize()
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        if self.device and self.is_connected:
            self.device.close()
            self.is_connected = False
```

**Error handling and resource management:**
```python
def ini_stage(self, controller=None):
    try:
        if controller is None:
            self.wrapper = DeviceWrapper(self.get_connection_params())
            if not self.wrapper.connect():
                raise RuntimeError("Failed to connect to hardware")
            self.controller = self.wrapper.device
        else:
            self.controller = controller
            
        self.emit_status(ThreadCommand('Update_Status', 
                                     ['Hardware initialized successfully', 'log']))
        return True
        
    except Exception as e:
        self.emit_status(ThreadCommand('Update_Status', 
                                     [f'Initialization failed: {str(e)}', 'log']))
        return False

def close(self):
    """Implement comprehensive cleanup"""
    try:
        if hasattr(self, 'wrapper') and self.wrapper:
            self.wrapper.disconnect()
        if hasattr(self, 'controller'):
            self.controller = None
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
```

### Thread Safety and Communication Patterns

**ThreadCommand usage for inter-thread communication:**
```python
# Status updates to UI thread
self.emit_status(ThreadCommand('Update_Status', ['Moving to position...', 'log']))

# Movement completion signaling  
self.emit_status(ThreadCommand('move_done'))

# Custom data communication
self.custom_sig.emit(ThreadCommand('CustomCommand', [data_payload]))
```

## Production-Ready Plugin Development Guidelines

### Plugin Template and Structure Standards

**Use the official template repository**: `pymodaq_plugins_template` provides the **complete scaffolding** for plugin development with:
- Proper directory structure
- GitHub Actions configuration
- Testing infrastructure setup
- Documentation templates
- Entry point configuration

**Mandatory implementation checklist:**
1. **Inherit from correct base class** (`DAQ_Move_base` or `DAQ_Viewer_base`)
2. **Implement all mandatory methods** completely
3. **Follow strict naming conventions** for automatic discovery
4. **Handle settings changes** in `commit_settings()` method
5. **Use proper data emission** with `DataToExport` objects
6. **Implement comprehensive error handling**
7. **Provide thorough documentation** with usage examples

### Testing and Quality Assurance

**Development testing workflow:**
1. **Mock device testing**: Use `pymodaq_plugins_mock` for development
2. **Hardware validation**: Test with manufacturer software first
3. **Integration testing**: Validate within PyMoDAQ environment
4. **Automated testing**: GitHub Actions for continuous integration

**Quality assurance standards:**
- **Version compatibility**: Specify minimum PyMoDAQ version requirements
- **Dependency management**: Pin critical library versions
- **Documentation completeness**: Include installation, configuration, and troubleshooting
- **Error handling robustness**: Graceful failure recovery and user feedback

### Distribution and Maintenance

**Publication workflow:**
1. **Development**: Install in editable mode (`pip install -e .`)
2. **GitHub release**: Automatic PyPI publication via GitHub Actions
3. **Plugin manager inclusion**: Automatic listing in official registry
4. **Community maintenance**: Active GitHub issue management

This comprehensive guide provides the technical foundation for implementing robust, production-ready PyMoDAQ plugins for your polarimetric SHG microscope system, with specific implementation patterns for Red Pitaya PID control, Thorlabs ELL14 rotation stages, and Photometrics Prime BSI camera integration.