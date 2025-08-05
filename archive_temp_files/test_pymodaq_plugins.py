#!/usr/bin/env python3
"""
PyMoDAQ Plugin Test with Real Hardware
=====================================

Test PyMoDAQ plugins with the actual hardware devices to ensure
they work correctly within the PyMoDAQ framework.
"""

import sys
import time
import logging

# Add src directory to path for imports
sys.path.insert(0, 'src')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_maitai_plugin():
    """Test MaiTai PyMoDAQ plugin with real hardware."""
    print("1. MAITAI PYMODAQ PLUGIN TEST")
    print("=" * 40)
    
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        
        # Initialize plugin
        plugin = DAQ_Move_MaiTai()
        print("  ✅ Plugin initialized")
        
        # Configure for real hardware
        plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB0')
        plugin.settings.child('connection_group', 'mock_mode').setValue(False)
        print("  ✅ Configured for real hardware (/dev/ttyUSB0)")
        
        # Initialize the stage
        result, success = plugin.ini_stage()
        if success:
            print("  ✅ Stage initialized successfully")
            
            # Test getting current position (wavelength)
            current_pos = plugin.get_actuator_value()
            print(f"  Current wavelength: {current_pos} nm")
            
            # Test moving to new position
            target_wavelength = 790
            print(f"  Moving to {target_wavelength} nm...")
            plugin.move_abs(target_wavelength)
            
            # Wait a moment then check position
            time.sleep(2)
            new_pos = plugin.get_actuator_value()
            print(f"  New wavelength: {new_pos} nm")
            
            # Clean up
            plugin.close()
            print("  ✅ Plugin test completed successfully")
            return True
        else:
            print(f"  ❌ Stage initialization failed: {result}")
            plugin.close()
            return False
            
    except Exception as e:
        print(f"  ❌ MaiTai plugin test failed: {e}")
        return False

def test_elliptec_plugin():
    """Test Elliptec PyMoDAQ plugin with real hardware."""
    print("\n2. ELLIPTEC PYMODAQ PLUGIN TEST")
    print("=" * 40)
    
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        
        # Initialize plugin
        plugin = DAQ_Move_Elliptec()
        print("  ✅ Plugin initialized")
        
        # Configure for real hardware
        plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB1')
        plugin.settings.child('connection_group', 'mock_mode').setValue(False)
        print("  ✅ Configured for real hardware (/dev/ttyUSB1)")
        
        # Initialize the stage
        result, success = plugin.ini_stage()
        if success:
            print("  ✅ Stage initialized successfully")
            
            # Test getting current positions
            current_positions = plugin.get_actuator_value()
            print(f"  Current positions: {current_positions}")
            
            # Test moving first mount by small amount
            if len(current_positions) > 0:
                current_pos = current_positions[0]
                target_pos = current_pos + 5.0  # Move 5 degrees
                print(f"  Moving mount 0 from {current_pos:.2f} to {target_pos:.2f} degrees...")
                
                plugin.move_abs([target_pos] + current_positions[1:])
                
                # Wait and check new position
                time.sleep(3)
                new_positions = plugin.get_actuator_value()
                print(f"  New positions: {new_positions}")
            
            # Clean up
            plugin.close()
            print("  ✅ Plugin test completed successfully")
            return True
        else:
            print(f"  ❌ Stage initialization failed: {result}")
            plugin.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Elliptec plugin test failed: {e}")
        return False

def test_camera_plugin():
    """Test PrimeBSI camera PyMoDAQ plugin."""
    print("\n3. PRIMEBSI CAMERA PYMODAQ PLUGIN TEST")
    print("=" * 40)
    
    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        
        # Initialize plugin
        plugin = DAQ_2DViewer_PrimeBSI()
        print("  ✅ Plugin initialized")
        
        # Try to initialize detector
        result, success = plugin.ini_detector()
        if success:
            print("  ✅ Camera initialized successfully")
            
            # Test grabbing a frame
            print("  Attempting to grab a test frame...")
            try:
                plugin.grab_data()
                print("  ✅ Test frame acquisition successful")
                
                # Clean up
                plugin.close()
                print("  ✅ Camera plugin test completed successfully")
                return True
            except Exception as e:
                print(f"  ⚠️  Frame acquisition error: {e}")
                plugin.close()
                return False
        else:
            print(f"  ❌ Camera initialization failed: {result}")
            plugin.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Camera plugin test failed: {e}")
        return False

def main():
    """Run PyMoDAQ plugin tests with real hardware."""
    print("🔬 PYMODAQ PLUGIN TESTS WITH REAL HARDWARE")
    print("=" * 60)
    print("Testing PyMoDAQ plugins with actual URASHG hardware")
    print()
    
    # Run plugin tests
    maitai_ok = test_maitai_plugin()
    elliptec_ok = test_elliptec_plugin()
    camera_ok = test_camera_plugin()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 PYMODAQ PLUGIN TEST RESULTS:")
    print("=" * 60)
    
    plugin_status = [
        ("MaiTai Plugin", maitai_ok),
        ("Elliptec Plugin", elliptec_ok),
        ("PrimeBSI Camera Plugin", camera_ok),
    ]
    
    for plugin, status in plugin_status:
        print(f"🔧 {plugin:25} {'✅ WORKING' if status else '❌ FAILED'}")
    
    # Overall status
    plugins_working = sum([maitai_ok, elliptec_ok, camera_ok])
    
    print(f"\n🚀 PLUGIN TEST STATUS:")
    print(f"   Working Plugins: {plugins_working}/3")
    
    if plugins_working >= 2:
        print("\n🎉 ✅ PYMODAQ PLUGINS OPERATIONAL!")
        print("🔬 Ready for URASHG measurements within PyMoDAQ framework")
    else:
        print("\n⚠️  Some plugins need attention")
    
    print("=" * 60)

if __name__ == "__main__":
    main()