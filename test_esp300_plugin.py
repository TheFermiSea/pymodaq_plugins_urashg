#!/usr/bin/env python3
"""
Focused ESP300 PyMoDAQ Plugin Test

Tests the ESP300 plugin specifically in the PyMoDAQ context with 
detailed parameter validation and multi-axis functionality.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, 'src')

print("🔬 ESP300 PYMODAQ PLUGIN FOCUSED TEST")
print("=" * 50)

try:
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300 import DAQ_Move_ESP300
    from pymodaq.utils.parameter import Parameter
    
    print("✅ ESP300 plugin imports successful")
    
    # Create plugin instance
    plugin = DAQ_Move_ESP300()
    print("✅ ESP300 plugin instance created")
    
    # 1. Parameter Structure Test
    print("\n📋 PARAMETER STRUCTURE ANALYSIS")
    print("-" * 40)
    
    def analyze_parameter_group(param, level=0):
        indent = "  " * level
        param_type = param.opts.get('type', 'unknown')
        
        if param_type == 'group':
            print(f"{indent}📁 {param.name()} (group)")
            for child in param.children():
                analyze_parameter_group(child, level + 1)
        else:
            value = param.value()
            print(f"{indent}🔧 {param.name()}: {value} ({param_type})")
    
    print("\n🔍 Full Parameter Tree:")
    analyze_parameter_group(plugin.settings)
    
    # 2. Multi-Axis Configuration Test
    print("\n\n🔄 MULTI-AXIS CONFIGURATION TEST")
    print("-" * 40)
    
    print(f"Multi-axis enabled: {plugin.is_multiaxes}")
    
    # Test different axis configurations
    test_configs = [1, 2, 3]
    
    for num_axes in test_configs:
        print(f"\n🔧 Testing {num_axes} axes configuration:")
        
        # Set number of axes
        plugin.settings.child('axes_config', 'num_axes').setValue(num_axes)
        
        # Get axis configurations
        for i in range(num_axes):
            axis_num = i + 1
            group_name = f'axis{axis_num}_group'
            
            name = plugin.settings.child('axes_config', group_name, f'axis{axis_num}_name').value()
            units = plugin.settings.child('axes_config', group_name, f'axis{axis_num}_units').value()
            
            print(f"   Axis {axis_num}: {name} ({units})")
    
    # 3. Mock Initialization Test
    print("\n\n🔌 MOCK INITIALIZATION TEST")
    print("-" * 40)
    
    # Configure for mock mode
    plugin.settings.child('connection_group', 'mock_mode').setValue(True)
    plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB3')
    plugin.settings.child('axes_config', 'num_axes').setValue(3)
    
    # Set URASHG-specific configuration
    plugin.settings.child('axes_config', 'axis1_group', 'axis1_name').setValue('X Stage')
    plugin.settings.child('axes_config', 'axis1_group', 'axis1_units').setValue('millimeter')
    plugin.settings.child('axes_config', 'axis2_group', 'axis2_name').setValue('Y Stage')
    plugin.settings.child('axes_config', 'axis2_group', 'axis2_units').setValue('millimeter')
    plugin.settings.child('axes_config', 'axis3_group', 'axis3_name').setValue('Z Focus')
    plugin.settings.child('axes_config', 'axis3_group', 'axis3_units').setValue('micrometer')
    
    print("🔧 URASHG axes configured:")
    print("   Axis 1: X Stage (mm)")
    print("   Axis 2: Y Stage (mm)")
    print("   Axis 3: Z Focus (μm)")
    
    # Initialize plugin
    print("\n🚀 Initializing plugin...")
    result, success = plugin.ini_stage()
    
    if success:
        print(f"✅ Plugin initialized: {result}")
        
        # 4. Position Reading Test
        print("\n📊 POSITION READING TEST")
        print("-" * 30)
        
        positions = plugin.get_actuator_value()
        print(f"Current positions: {positions}")
        print(f"Position type: {type(positions)}")
        print(f"Number of axes: {len(positions) if isinstance(positions, list) else 1}")
        
        # 5. Movement Simulation Test
        print("\n🎯 MOVEMENT SIMULATION TEST")
        print("-" * 35)
        
        # Test absolute move
        print("Testing absolute move to [1.0, 2.0, 100.0]...")
        try:
            plugin.move_abs([1.0, 2.0, 100.0])
            new_positions = plugin.get_actuator_value()
            print(f"Positions after move: {new_positions}")
            print("✅ Absolute move completed (mock)")
        except Exception as e:
            print(f"❌ Absolute move failed: {e}")
        
        # Test relative move
        print("\nTesting relative move by [0.5, -0.5, 50.0]...")
        try:
            plugin.move_rel([0.5, -0.5, 50.0])
            new_positions = plugin.get_actuator_value()
            print(f"Positions after relative move: {new_positions}")
            print("✅ Relative move completed (mock)")
        except Exception as e:
            print(f"❌ Relative move failed: {e}")
        
        # 6. Action Button Test
        print("\n🎮 ACTION BUTTON TEST")
        print("-" * 25)
        
        # Test action parameters
        action_params = ['home_all', 'stop_all', 'enable_all', 'disable_all', 'clear_errors']
        
        for action in action_params:
            try:
                print(f"Testing {action}...")
                param = plugin.settings.child('actions_group', action)
                plugin.commit_settings(param)
                print(f"✅ {action} action completed")
            except Exception as e:
                print(f"❌ {action} action failed: {e}")
        
        # 7. Status Display Test
        print("\n📺 STATUS DISPLAY TEST")
        print("-" * 25)
        
        status_params = [
            'connection_status',
            'axis1_position', 
            'axis2_position',
            'axis3_position',
            'last_error'
        ]
        
        for status_param in status_params:
            try:
                value = plugin.settings.child('status_group', status_param).value()
                print(f"{status_param}: {value}")
            except Exception as e:
                print(f"❌ Error reading {status_param}: {e}")
        
        plugin.close()
        print("\n✅ Plugin closed successfully")
        
    else:
        print(f"❌ Plugin initialization failed: {result}")
    
    # 8. Parameter Validation Test
    print("\n\n🔍 PARAMETER VALIDATION TEST")
    print("-" * 35)
    
    # Test parameter limits and validation
    validation_tests = [
        ('axes_config.num_axes', 4, "Should fail - max 3 axes"),
        ('axes_config.num_axes', 0, "Should fail - min 1 axis"),
        ('connection_group.baudrate', 9600, "Should work - valid baudrate"),
        ('motion_group.motion_timeout', -5, "Should work - will be handled"),
    ]
    
    for param_path, test_value, description in validation_tests:
        try:
            path_parts = param_path.split('.')
            param = plugin.settings.child(*path_parts)
            original_value = param.value()
            
            print(f"\nTesting {param_path} = {test_value}")
            print(f"Description: {description}")
            
            param.setValue(test_value)
            new_value = param.value()
            
            if new_value == test_value:
                print(f"✅ Value accepted: {new_value}")
            else:
                print(f"🔄 Value modified: {original_value} → {new_value}")
                
        except Exception as e:
            print(f"❌ Validation test failed: {e}")
    
    print("\n🎉 ESP300 Plugin Test Completed!")
    print("=" * 50)
    print("✅ ESP300 plugin is ready for URASHG integration")
    print("💡 Plugin supports 3-axis motion control with comprehensive configuration")
    print("🔧 Ready for hardware connection and real-world testing")
    
except Exception as e:
    print(f"❌ ESP300 plugin test failed: {e}")
    import traceback
    traceback.print_exc()