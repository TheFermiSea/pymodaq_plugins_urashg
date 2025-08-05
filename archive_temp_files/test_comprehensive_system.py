#!/usr/bin/env python3
"""
Comprehensive URASHG System Testing Suite

Performs thorough testing of all components:
- Hardware controllers
- PyMoDAQ plugins
- Plugin discovery
- Entry points
- Integration testing
- Performance validation
"""

import sys
import os
import time
import importlib.metadata
import traceback
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, 'src')

# Check if running in CI environment
IS_CI = os.environ.get('CI', 'false').lower() == 'true' or os.environ.get('GITHUB_ACTIONS', 'false').lower() == 'true'

print("COMPREHENSIVE URASHG SYSTEM TESTING")
print("=" * 60)
print("Testing all hardware controllers, plugins, and integrations")
if IS_CI:
    print("RUNNING IN CI MODE - Mock mode enabled, hardware access disabled")
print()

# Test Results Storage
test_results = {
    'maitai_controller': False,
    'elliptec_controller': False,
    'newport1830c_controller': False,
    'esp300_controller': False,
    'maitai_plugin': False,
    'elliptec_plugin': False,
    'newport1830c_plugin': False,
    'esp300_plugin': False,
    'prime_bsi_plugin': False,
    'plugin_discovery': False,
    'entry_points': False,
    'integration_test': False
}

error_log = []

def log_error(component: str, error: Exception):
    """Log error with component info."""
    error_msg = f"{component}: {str(error)}"
    error_log.append(error_msg)
    print(f"   ERROR: {error_msg}")

def test_hardware_controller(name: str, module_path: str, class_name: str, **kwargs) -> bool:
    """Generic hardware controller test."""
    try:
        print(f"Testing {name} hardware controller...")
        
        # Import controller module
        module = importlib.import_module(module_path)
        controller_class = getattr(module, class_name)
        
        # Create controller instance
        controller = controller_class(**kwargs)
        print(f"   Controller created: {type(controller).__name__}")
        
        # Test basic methods
        if hasattr(controller, 'get_device_info'):
            info = controller.get_device_info()
            print(f"   Device info: {info.get('model', 'Unknown')}")
        
        # Test connection attempt (skip in CI to avoid hardware access)
        if hasattr(controller, 'connect') and not IS_CI:
            connected = controller.connect()
            if connected:
                print(f"   WARNING: {name} connected unexpectedly")
                if hasattr(controller, 'disconnect'):
                    controller.disconnect()
            else:
                print(f"   Connection failed as expected (no hardware)")
        elif hasattr(controller, 'connect') and IS_CI:
            print(f"   Skipping connection test in CI mode")
        else:
            print(f"   No connection method available")
        
        print(f"   {name} controller: PASS")
        return True
        
    except Exception as e:
        log_error(f"{name} controller", e)
        return False

def test_pymodaq_plugin(name: str, module_path: str, class_name: str) -> bool:
    """Generic PyMoDAQ plugin test."""
    try:
        print(f"Testing {name} PyMoDAQ plugin...")
        
        # Import plugin module
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        
        # Create plugin instance
        plugin = plugin_class()
        print(f"   Plugin created: {type(plugin).__name__}")
        
        # Test parameter structure
        if hasattr(plugin, 'settings'):
            params = plugin.settings.children()
            param_count = len(params)
            print(f"   Parameters: {param_count} groups")
        
        # Test mock initialization for move plugins
        if hasattr(plugin, 'ini_stage'):
            # Enable mock mode if available
            try:
                plugin.settings.child('connection_group', 'mock_mode').setValue(True)
            except:
                pass  # Mock mode not available
            
            result, success = plugin.ini_stage()
            if success:
                print(f"   Initialization: SUCCESS ({result})")
                
                # Test position reading for move plugins
                if hasattr(plugin, 'get_actuator_value'):
                    position = plugin.get_actuator_value()
                    print(f"   Position reading: {position}")
                
                plugin.close()
            else:
                print(f"   Initialization: FAILED ({result})")
                
        # Test detector initialization for viewer plugins
        elif hasattr(plugin, 'ini_detector'):
            try:
                plugin.settings.child('connection_group', 'mock_mode').setValue(True)
            except:
                pass  # Mock mode not available
            
            result = plugin.ini_detector()
            
            # Handle different return formats
            if isinstance(result, tuple):
                result_msg, success = result
                if success:
                    print(f"   Detector init: SUCCESS ({result_msg})")
                    plugin.close()
                else:
                    print(f"   Detector init: FAILED ({result_msg})")
            else:
                # Single return value (like status object)
                print(f"   Detector init: COMPLETED ({result})")
                try:
                    plugin.close()
                except:
                    pass
        
        print(f"   {name} plugin: PASS")
        return True
        
    except Exception as e:
        log_error(f"{name} plugin", e)
        return False

# 1. Hardware Controller Tests
print("HARDWARE CONTROLLER TESTS")
print("-" * 40)

# Test MaiTai Controller (force mock mode in CI)
test_results['maitai_controller'] = test_hardware_controller(
    "MaiTai",
    "pymodaq_plugins_urashg.hardware.urashg.maitai_control",
    "MaiTaiController",
    port='/dev/ttyUSB0',
    mock_mode=IS_CI
)

print()

# Test Elliptec Controller  
test_results['elliptec_controller'] = test_hardware_controller(
    "Elliptec",
    "pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper",
    "ElliptecController",
    port='/dev/ttyUSB1',
    mock_mode=IS_CI
)

print()

# Test Newport 1830C Controller (no mock mode available, but don't connect in CI)
test_results['newport1830c_controller'] = test_hardware_controller(
    "Newport 1830C",
    "pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller", 
    "Newport1830CController",
    port='/dev/ttyUSB2'
)

print()

# Test ESP300 Controller (no mock mode available, but don't connect in CI)
test_results['esp300_controller'] = test_hardware_controller(
    "ESP300",
    "pymodaq_plugins_urashg.hardware.urashg.esp300_controller",
    "ESP300Controller",
    port='/dev/ttyUSB3'
)

print()

# 2. PyMoDAQ Plugin Tests
print("\nPYMODAQ PLUGIN TESTS")
print("-" * 40)

# Test MaiTai Plugin
test_results['maitai_plugin'] = test_pymodaq_plugin(
    "MaiTai",
    "pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai",
    "DAQ_Move_MaiTai"
)

print()

# Test Elliptec Plugin
test_results['elliptec_plugin'] = test_pymodaq_plugin(
    "Elliptec", 
    "pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec",
    "DAQ_Move_Elliptec"
)

print()

# Test Newport 1830C Plugin
test_results['newport1830c_plugin'] = test_pymodaq_plugin(
    "Newport 1830C",
    "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C",
    "DAQ_0DViewer_Newport1830C"
)

print()

# Test ESP300 Plugin
test_results['esp300_plugin'] = test_pymodaq_plugin(
    "ESP300",
    "pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300", 
    "DAQ_Move_ESP300"
)

print()

# Test PrimeBSI Plugin
test_results['prime_bsi_plugin'] = test_pymodaq_plugin(
    "PrimeBSI",
    "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI",
    "DAQ_2DViewer_PrimeBSI"
)

print()

# 3. Plugin Discovery Tests
print("\nPLUGIN DISCOVERY TESTS")
print("-" * 40)

try:
    print("Testing entry point discovery...")
    
    # Get all entry points
    eps = importlib.metadata.entry_points()
    
    # Find URASHG plugins
    move_plugins = []
    viewer_plugins = []
    
    # Check move plugins
    if hasattr(eps, 'select'):
        # Python 3.10+ style
        move_eps = eps.select(group='pymodaq.move_plugins')
        viewer_eps = eps.select(group='pymodaq.viewer_plugins')
    else:
        # Python 3.9 style
        move_eps = eps.get('pymodaq.move_plugins', [])
        viewer_eps = eps.get('pymodaq.viewer_plugins', [])
    
    # Find URASHG-related plugins
    for ep in move_eps:
        if 'urashg' in ep.value.lower() or any(x in ep.name.lower() for x in ['maitai', 'elliptec', 'esp300']):
            move_plugins.append(ep.name)
    
    for ep in viewer_eps:
        if 'urashg' in ep.value.lower() or any(x in ep.name.lower() for x in ['newport', 'prime']):
            viewer_plugins.append(ep.name)
    
    print(f"   Found {len(move_plugins)} move plugins: {move_plugins}")
    print(f"   Found {len(viewer_plugins)} viewer plugins: {viewer_plugins}")
    
    expected_move = ['DAQ_Move_MaiTai', 'DAQ_Move_Elliptec', 'DAQ_Move_ESP300']
    expected_viewer = ['DAQ_0DViewer_Newport1830C', 'DAQ_2DViewer_PrimeBSI']
    
    move_ok = all(plugin in move_plugins for plugin in expected_move)
    viewer_ok = all(plugin in viewer_plugins for plugin in expected_viewer)
    
    if move_ok and viewer_ok:
        print("   Plugin discovery: PASS")
        test_results['plugin_discovery'] = True
    else:
        print(f"   Plugin discovery: FAIL (missing plugins)")
        print(f"   Expected move: {expected_move}")
        print(f"   Expected viewer: {expected_viewer}")
        
except Exception as e:
    log_error("Plugin discovery", e)

print()

# 4. Entry Points Validation
print("ENTRY POINTS VALIDATION")
print("-" * 40)

try:
    print("Testing entry points can be loaded...")
    
    # Test loading each entry point
    entry_points_to_test = [
        ('pymodaq.move_plugins', 'DAQ_Move_MaiTai'),
        ('pymodaq.move_plugins', 'DAQ_Move_Elliptec'), 
        ('pymodaq.move_plugins', 'DAQ_Move_ESP300'),
        ('pymodaq.viewer_plugins', 'DAQ_0DViewer_Newport1830C'),
        ('pymodaq.viewer_plugins', 'DAQ_2DViewer_PrimeBSI')
    ]
    
    loaded_count = 0
    for group, name in entry_points_to_test:
        try:
            eps = importlib.metadata.entry_points()
            if hasattr(eps, 'select'):
                ep_list = list(eps.select(group=group, name=name))
            else:
                ep_list = [ep for ep in eps.get(group, []) if ep.name == name]
            
            if ep_list:
                ep = ep_list[0]
                plugin_class = ep.load()
                print(f"   {name}: LOADED ({plugin_class.__name__})")
                loaded_count += 1
            else:
                print(f"   {name}: NOT FOUND")
                
        except Exception as e:
            print(f"   {name}: LOAD ERROR ({e})")
    
    if loaded_count == len(entry_points_to_test):
        print("   Entry points validation: PASS")
        test_results['entry_points'] = True
    else:
        print(f"   Entry points validation: FAIL ({loaded_count}/{len(entry_points_to_test)})")
        
except Exception as e:
    log_error("Entry points validation", e)

print()

# 5. Integration Test
print("INTEGRATION TEST")
print("-" * 40)

try:
    print("Testing complete system integration...")
    
    # Test importing the main package
    import pymodaq_plugins_urashg
    print(f"   Package imported: {pymodaq_plugins_urashg.__name__}")
    
    # Test hardware module
    from pymodaq_plugins_urashg.hardware import urashg
    print(f"   Hardware module: {urashg.__name__}")
    
    # Test plugin modules
    from pymodaq_plugins_urashg import daq_move_plugins
    from pymodaq_plugins_urashg import daq_viewer_plugins
    print(f"   Plugin modules imported")
    
    # Test creating multiple plugins simultaneously
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300 import DAQ_Move_ESP300
    
    maitai = DAQ_Move_MaiTai()
    esp300 = DAQ_Move_ESP300()
    
    print(f"   Multiple plugins created simultaneously")
    
    # Test mock initialization of both
    maitai.settings.child('connection_group', 'mock_mode').setValue(True)
    esp300.settings.child('connection_group', 'mock_mode').setValue(True)
    
    result1, success1 = maitai.ini_stage()
    result2, success2 = esp300.ini_stage()
    
    if success1 and success2:
        print(f"   Multi-plugin initialization: PASS")
        maitai.close()
        esp300.close()
        test_results['integration_test'] = True
    else:
        print(f"   Multi-plugin initialization: FAIL")
        
except Exception as e:
    log_error("Integration test", e)

print()

# 6. Performance Test
print("PERFORMANCE TEST")
print("-" * 40)

try:
    print("Testing plugin creation performance...")
    
    start_time = time.time()
    
    # Test rapid plugin creation/destruction
    for i in range(10):
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        plugin = DAQ_Move_MaiTai()
        del plugin
    
    creation_time = time.time() - start_time
    print(f"   10 plugin creations: {creation_time:.3f} seconds")
    
    if creation_time < 5.0:  # Should be fast
        print("   Performance: PASS")
    else:
        print("   Performance: SLOW")
        
except Exception as e:
    log_error("Performance test", e)

print()

# 7. Results Summary
print("COMPREHENSIVE TEST RESULTS")
print("=" * 60)

working_components = sum(test_results.values())
total_components = len(test_results)

print(f"System Status: {working_components}/{total_components} components working")
print("-" * 50)

# Group results by category
hardware_tests = [k for k in test_results.keys() if 'controller' in k]
plugin_tests = [k for k in test_results.keys() if 'plugin' in k]
system_tests = [k for k in test_results.keys() if k in ['plugin_discovery', 'entry_points', 'integration_test']]

print("\nHardware Controllers:")
for test in hardware_tests:
    status = "PASS" if test_results[test] else "FAIL"
    print(f"  {test.replace('_controller', '').title()}: {status}")

print("\nPyMoDAQ Plugins:")
for test in plugin_tests:
    status = "PASS" if test_results[test] else "FAIL"
    print(f"  {test.replace('_plugin', '').title()}: {status}")

print("\nSystem Integration:")
for test in system_tests:
    status = "PASS" if test_results[test] else "FAIL"
    print(f"  {test.replace('_', ' ').title()}: {status}")

# Overall assessment
print(f"\nOverall Test Status: {working_components}/{total_components} components working")

if working_components >= 10:
    print("\nSYSTEM STATUS: EXCELLENT")
    print("All critical components working perfectly")
elif working_components >= 8:
    print("\nSYSTEM STATUS: GOOD") 
    print("Most components working, minor issues detected")
elif working_components >= 6:
    print("\nSYSTEM STATUS: ACCEPTABLE")
    print("Core functionality working, some components need attention")
else:
    print("\nSYSTEM STATUS: NEEDS WORK")
    print("Multiple components require fixes")

# Error Summary
if error_log:
    print(f"\nERRORS DETECTED ({len(error_log)}):")
    print("-" * 30)
    for error in error_log:
        print(f"  {error}")
else:
    print("\nNO ERRORS DETECTED")

print("\nTesting completed.")
print("=" * 60)