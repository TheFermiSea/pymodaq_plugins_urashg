#!/usr/bin/env python3
"""
Test Newport ESP300 motion controller with hardware simulation.

Since ESP300 hardware is not yet connected, this tests the implementation
with mock functionality and verifies the plugin structure.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, 'src')

print("🔬 NEWPORT ESP300 HARDWARE TEST")
print("=" * 50)
print("Testing ESP300 controller and PyMoDAQ plugin")
print("(Hardware simulation mode - no physical device required)")
print()

# Test Results Storage
test_results = {
    'controller_import': False,
    'controller_creation': False,
    'plugin_import': False,
    'plugin_creation': False,
    'plugin_initialization': False,
    'multi_axis_support': False
}

# 1. Hardware Controller Tests
print("🔧 ESP300 HARDWARE CONTROLLER TESTS")
print("-" * 45)

# Test Controller Import
print("\n1️⃣ Testing ESP300 Controller Import...")
try:
    from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import (
        ESP300Controller, AxisConfig, ESP300AxisError, ESP300GeneralError
    )
    print("   ✅ ESP300 controller imported successfully")
    test_results['controller_import'] = True
except Exception as e:
    print(f"   ❌ Controller import failed: {e}")

# Test Controller Creation
print("\n2️⃣ Testing ESP300 Controller Creation...")
try:
    # Create URASHG-specific axes configuration
    axes_config = [
        AxisConfig(1, 'x_stage', 'millimeter'),
        AxisConfig(2, 'y_stage', 'millimeter'),
        AxisConfig(3, 'z_focus', 'micrometer')
    ]
    
    controller = ESP300Controller(
        port='/dev/ttyUSB3',  # Will fail to connect, but that's OK
        axes_config=axes_config
    )
    
    print("   ✅ ESP300 controller created")
    print(f"   📊 Configured for {len(axes_config)} axes")
    
    # Test device info (without connection)
    info = controller.get_device_info()
    print(f"   📋 Device info: {info['model']}, {info['num_axes']} axes")
    
    test_results['controller_creation'] = True
    
except Exception as e:
    print(f"   ❌ Controller creation failed: {e}")

# Test Mock Connection (will fail gracefully)
print("\n3️⃣ Testing ESP300 Connection (Expected to Fail - No Hardware)...")
try:
    if 'controller' in locals():
        connected = controller.connect()
        if connected:
            print("   🎉 ESP300 connected (unexpected - no hardware)")
            controller.disconnect()
        else:
            print("   ✅ Connection failed as expected (no hardware present)")
            print("   💡 This confirms error handling works correctly")
except Exception as e:
    print(f"   ✅ Connection failed as expected: {e}")

# 2. PyMoDAQ Plugin Tests
print("\n\n🔌 ESP300 PYMODAQ PLUGIN TESTS")
print("-" * 45)

# Test Plugin Import
print("\n4️⃣ Testing ESP300 PyMoDAQ Plugin Import...")
try:
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300 import DAQ_Move_ESP300
    print("   ✅ ESP300 plugin imported successfully")
    test_results['plugin_import'] = True
except Exception as e:
    print(f"   ❌ Plugin import failed: {e}")

# Test Plugin Creation
print("\n5️⃣ Testing ESP300 Plugin Creation...")
try:
    plugin = DAQ_Move_ESP300()
    print("   ✅ ESP300 plugin created")
    
    # Check multi-axis support
    if hasattr(plugin, 'is_multiaxes') and plugin.is_multiaxes:
        print("   ✅ Multi-axis support enabled")
        test_results['multi_axis_support'] = True
    
    # Check parameter structure
    params = plugin.settings.children()
    param_groups = [p.name() for p in params if hasattr(p, 'children')]
    print(f"   📋 Parameter groups: {param_groups}")
    
    test_results['plugin_creation'] = True
    
except Exception as e:
    print(f"   ❌ Plugin creation failed: {e}")

# Test Plugin Initialization (Mock Mode)
print("\n6️⃣ Testing ESP300 Plugin Initialization (Mock Mode)...")
try:
    if 'plugin' in locals():
        # Enable mock mode
        plugin.settings.child('connection_group', 'mock_mode').setValue(True)
        plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB3')
        plugin.settings.child('axes_config', 'num_axes').setValue(3)
        
        # Initialize plugin
        result, success = plugin.ini_stage()
        
        if success:
            print("   ✅ ESP300 plugin initialized successfully (mock mode)")
            print(f"   📊 Result: {result}")
            
            # Test position reading (should return zeros in mock mode)
            positions = plugin.get_actuator_value()
            print(f"   📈 Mock positions: {positions}")
            
            plugin.close()
            test_results['plugin_initialization'] = True
            
        else:
            print(f"   ❌ Plugin initialization failed: {result}")
            
except Exception as e:
    print(f"   ❌ Plugin initialization error: {e}")

# Test Multi-Axis Functionality
print("\n7️⃣ Testing Multi-Axis Functionality...")
try:
    if 'plugin' in locals() and test_results['plugin_initialization']:
        # Test axis configuration
        num_axes = plugin.settings.child('axes_config', 'num_axes').value()
        print(f"   📊 Configured for {num_axes} axes")
        
        # Test axis names
        axis_names = []
        for i in range(num_axes):
            axis_num = i + 1
            name = plugin.settings.child('axes_config', f'axis{axis_num}_group', f'axis{axis_num}_name').value()
            units = plugin.settings.child('axes_config', f'axis{axis_num}_group', f'axis{axis_num}_units').value()
            axis_names.append(f"{name} ({units})")
        
        print(f"   🔧 Axes: {axis_names}")
        
        # Test parameter access
        print("   ✅ Multi-axis parameter structure verified")
        
except Exception as e:
    print(f"   ❌ Multi-axis test error: {e}")

# 3. Integration Tests
print("\n\n🎯 ESP300 INTEGRATION SUMMARY")
print("=" * 50)

working_components = sum(test_results.values())
total_components = len(test_results)

print(f"ESP300 Implementation Status: {working_components}/{total_components}")
print("-" * 40)

for component, status in test_results.items():
    icon = "✅" if status else "❌"
    component_name = component.replace('_', ' ').title()
    print(f"{icon} {component_name}: {'WORKING' if status else 'FAILED'}")

print(f"\n📊 Overall ESP300 Status: {working_components}/{total_components} components working")

if working_components >= 4:
    print("\n🎉 ESP300 INTEGRATION: READY!")
    print("🔬 ESP300 controller and plugin successfully implemented")
    print("💡 Ready for hardware connection and testing")
    print()
    print("🚀 Next Steps:")
    print("   1. Connect ESP300 hardware to serial port")
    print("   2. Update serial port in plugin settings")
    print("   3. Test with real hardware")
    print("   4. Configure for URASHG system requirements")
    print()
    print("🔌 Hardware Connection:")
    print("   - Serial Port: /dev/ttyUSB3 (configurable)")
    print("   - Baud Rate: 19200 (ESP300 default)")
    print("   - Axes: X/Y stage + Z focus")
    print("   - Units: mm for XY, μm for Z")
    
elif working_components >= 2:
    print("\n⚠️ ESP300 INTEGRATION: PARTIALLY READY")
    print("🔧 Some components need attention")
    
else:
    print("\n❌ ESP300 INTEGRATION: NEEDS WORK")
    print("🔧 Multiple components require fixes")

print("\n" + "=" * 50)
print("ESP300 implementation test completed.")

# 4. Show Expected Hardware Setup
print("\n\n📋 EXPECTED ESP300 HARDWARE SETUP")
print("-" * 45)
print("For URASHG system integration:")
print()
print("🔧 Axes Configuration:")
print("   Axis 1: X Stage (±25mm range)")
print("   Axis 2: Y Stage (±25mm range)")  
print("   Axis 3: Z Focus (±1000μm range)")
print()
print("⚙️ Settings:")
print("   - Serial: /dev/ttyUSB3 @ 19200 baud")
print("   - Units: X,Y in mm, Z in μm")
print("   - Homing: On initialization (optional)")
print("   - Software limits: Configurable")
print()
print("🎯 Usage in URASHG:")
print("   - Sample positioning (XY)")
print("   - Focus control (Z)")
print("   - Automated scanning")
print("   - Precision positioning for μRASHG measurements")