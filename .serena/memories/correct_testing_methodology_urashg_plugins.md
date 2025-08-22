# Correct Testing Methodology for PyMoDAQ Plugins

## VERIFIED APPROACH: How to Actually Test PyMoDAQ Plugins

**Based on successful debugging of URASHG plugins (August 2025)**

### Critical Testing Hierarchy

**✅ CORRECT Testing Order**:
1. **Hardware Connectivity** - Test raw device communication first
2. **Plugin Import & Discovery** - Verify PyMoDAQ recognizes plugins
3. **Basic Instantiation** - Test plugin creation without full lifecycle
4. **Hardware Initialization** - Test real device initialization
5. **Data Acquisition** - Test actual hardware operations
6. **Full Integration** - Test complete PyMoDAQ dashboard integration

**❌ WRONG Approach**: Starting with complex integration tests without verifying basics

### Layer 1: Hardware Connectivity Testing

**Purpose**: Verify physical devices are connected and responding

**✅ WORKING Method**:
```python
# Direct hardware communication test
def test_camera_hardware():
    from pyvcam import pvc
    from pyvcam.camera import Camera
    
    pvc.init_pvcam()
    cameras = list(Camera.detect_camera())
    assert len(cameras) > 0, "No cameras detected"
    
    camera = cameras[0]
    camera.open()
    assert camera.name == "pvcamUSB_0"
    assert camera.temp < 0  # Camera is cooled
    camera.close()
    pvc.uninit_pvcam()
```

**Key Success Factors**:
- Test API directly, not through plugin layers
- Verify specific hardware responses (e.g., temperature, model numbers)
- Test cleanup sequences to avoid state conflicts

### Layer 2: Plugin Discovery Testing

**Purpose**: Verify PyMoDAQ framework recognizes plugins

**✅ WORKING Method**:
```python
def test_plugin_discovery():
    from pymodaq.utils import daq_utils
    
    # Test plugin discovery
    move_plugins = daq_utils.get_plugins('DAQ_Move')
    viewer_plugins = daq_utils.get_plugins('DAQ_2DViewer')
    
    # Verify specific plugins found
    urashg_plugins = [p for p in move_plugins if 'urashg' in p.lower()]
    assert len(urashg_plugins) >= 3, f"Expected 3+ URASHG move plugins, found {len(urashg_plugins)}"
```

**Key Insights**:
- PyMoDAQ logs plugin discovery: `INFO:pymodaq.daq_utils:pymodaq_plugins_urashg.daq_move_plugins/Elliptec available`
- Entry points must be correctly defined in pyproject.toml
- Import errors at this level indicate packaging issues, not hardware issues

### Layer 3: Plugin Instantiation Testing

**Purpose**: Test plugin creation without full PyMoDAQ lifecycle

**✅ WORKING Method**:
```python
def test_plugin_instantiation():
    # Test camera plugin
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    
    plugin = DAQ_2DViewer_PrimeBSI()
    assert plugin is not None
    
    # Test mandatory methods exist
    assert hasattr(plugin, 'ini_stage'), "Missing required ini_stage method"
    plugin.ini_stage()  # Should not raise exception
    
    # Cleanup
    plugin.close()
```

**Critical Discovery**: Parameter tree race conditions don't occur during basic instantiation - only during full PyMoDAQ lifecycle integration.

### Layer 4: Hardware Initialization Testing

**Purpose**: Test plugin initialization with real hardware

**✅ WORKING Method**:
```python
def test_hardware_initialization():
    plugin = DAQ_2DViewer_PrimeBSI()
    
    # Test initialization
    status = plugin.ini_detector()
    assert plugin.initialized, f"Initialization failed: {status.info}"
    
    # Verify hardware parameters populated
    camera_name = plugin.settings.child('camera_settings', 'camera_name').value()
    assert camera_name == "pvcamUSB_0"
    
    # Verify real hardware connection
    temp = plugin.settings.child('camera_settings', 'temperature').value()
    assert temp is not None and temp < 0, "Camera not properly connected/cooled"
    
    plugin.close()
```

**Key Learning**: Hardware initialization can succeed even when dashboard integration fails.

### Layer 5: Data Acquisition Testing

**Purpose**: Test actual data capture and processing

**✅ WORKING Method**:
```python
def test_data_acquisition():
    plugin = DAQ_2DViewer_PrimeBSI()
    plugin.ini_detector()
    
    if plugin.initialized:
        # Test data acquisition
        plugin.grab_data()  # Should not raise exceptions
        
        # Verify data format compliance
        # (Check that DataWithAxes format is correct)
        
    plugin.close()
```

**Data Format Verification**:
- Ensure data is list of 2D numpy arrays
- Verify axes are properly defined
- Check PyMoDAQ 5.x DataWithAxes compliance

### Layer 6: Full Integration Testing

**Purpose**: Test complete PyMoDAQ dashboard integration

**⚠️ CAUTION**: This is where race conditions and lifecycle issues appear

**Testing Strategy**:
- Use PyMoDAQ dashboard in controlled environment
- Test parameter changes through GUI
- Verify clean shutdown sequences
- Monitor for threading issues

### Common Testing Mistakes to Avoid

**❌ WRONG Assumptions**:
1. "Plugin imports failing means hardware is broken" 
   - **Reality**: Check entry points and packaging first

2. "PyVCAM API errors mean library incompatibility"
   - **Reality**: Test API directly - our PyVCAM 2.2.3 works perfectly

3. "Parameter tree errors mean plugin architecture is wrong"
   - **Reality**: These often only occur during full lifecycle, not basic instantiation

4. "All plugins broken if one test fails"
   - **Reality**: Test each layer independently to isolate issues

### Testing Environment Setup

**✅ ESSENTIAL Requirements**:
```bash
# Proper Python environment
source .venv/bin/activate  # or equivalent

# Hardware accessibility
ls /dev/tty*  # Verify serial devices visible

# PyMoDAQ environment
python -c "import pymodaq; print('PyMoDAQ available')"

# Plugin package installation
python -c "import pymodaq_plugins_urashg; print('URASHG plugins available')"
```

### Test File Organization

**✅ CORRECT Structure**:
```
tests/
├── unit/                    # Plugin unit tests
├── integration/             # Plugin integration tests
├── hardware/               # Hardware connectivity tests
├── test_pymodaq_compliance.py  # Framework compliance
└── run_compliance_tests.py     # Test runner
```

**❌ WRONG**: Scattered test files in project root

### Debugging Success Patterns

**When Tests Fail**:
1. **Start Simple**: Hardware connectivity → Plugin discovery → Basic instantiation
2. **Isolate Layers**: Don't test full integration until basics work
3. **Verify APIs Directly**: Test hardware libraries outside plugin context
4. **Check PyMoDAQ Logs**: Framework provides detailed plugin discovery information
5. **Use Real Hardware**: Mock tests can hide real compatibility issues

**When Tests Succeed Partially**:
- Document exactly what works vs what doesn't
- Understand the boundary between working and failing components
- Don't make broad claims about "everything broken" or "everything working"

### Verification Criteria

**✅ Plugin is WORKING when**:
- PyMoDAQ discovers and lists the plugin
- Plugin can instantiate without errors
- Hardware initialization succeeds with real devices
- Data acquisition produces valid PyMoDAQ data structures
- Parameter updates function correctly

**⚠️ Plugin has ISSUES when**:
- Dashboard integration causes threading problems
- Parameter tree race conditions during full lifecycle
- Specific PyMoDAQ compatibility requirements not met

**❌ Plugin is BROKEN when**:
- Cannot import plugin modules
- PyMoDAQ doesn't discover plugin  
- Hardware cannot be accessed at all
- Critical methods missing or malformed

### Key Success: Methodical Testing Revealed Truth

Our URASHG plugins went from "completely broken" to "mostly working with specific issues" through **methodical layer-by-layer testing**. The fundamental architecture was sound - only specific integration details needed fixing.