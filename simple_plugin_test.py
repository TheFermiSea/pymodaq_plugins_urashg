#!/usr/bin/env python3
"""
Simple PyMoDAQ Plugin Test
=========================
Test our URASHG plugins without the full dashboard GUI.
"""

import sys
import os

# Add src to path
sys.path.insert(0, 'src')

def test_maitai_plugin():
    """Test MaiTai plugin directly."""
    print("Testing MaiTai Plugin...")
    
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        
        # Create plugin (without Qt parent)
        plugin = DAQ_Move_MaiTai(parent=None)
        
        # Set parameters for real hardware
        plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB0')
        plugin.settings.child('connection_group', 'mock_mode').setValue(False)
        
        # Initialize
        result, success = plugin.ini_stage()
        
        if success:
            print(f"✅ MaiTai plugin initialized: {result}")
            
            # Get current wavelength
            wavelength = plugin.get_actuator_value()
            print(f"✅ Current wavelength: {wavelength} nm")
            
            # Test movement (small change)
            print("✅ Testing wavelength movement...")
            plugin.move_abs(wavelength + 1)  # Move 1 nm
            
            # Clean up
            plugin.close()
            print("✅ MaiTai plugin test completed successfully")
            return True
        else:
            print(f"❌ MaiTai plugin initialization failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ MaiTai plugin test failed: {e}")
        return False

def test_elliptec_plugin():
    """Test Elliptec plugin directly."""
    print("\nTesting Elliptec Plugin...")
    
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        
        # Create plugin (without Qt parent)  
        plugin = DAQ_Move_Elliptec(parent=None)
        
        # Set parameters for real hardware
        plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB1')
        plugin.settings.child('connection_group', 'mock_mode').setValue(False)
        
        # Initialize
        result, success = plugin.ini_stage()
        
        if success:
            print(f"✅ Elliptec plugin initialized: {result}")
            
            # Get current positions
            positions = plugin.get_actuator_value()
            print(f"✅ Current positions: {positions}")
            
            # Clean up
            plugin.close()
            print("✅ Elliptec plugin test completed successfully")
            return True
        else:
            print(f"❌ Elliptec plugin initialization failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Elliptec plugin test failed: {e}")
        return False

def main():
    """Run plugin tests."""
    print("🔬 URASHG PLUGIN DIRECT TESTS")
    print("=" * 50)
    
    # Test plugins
    maitai_ok = test_maitai_plugin()
    elliptec_ok = test_elliptec_plugin()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print(f"MaiTai Plugin:   {'✅ WORKING' if maitai_ok else '❌ FAILED'}")
    print(f"Elliptec Plugin: {'✅ WORKING' if elliptec_ok else '❌ FAILED'}")
    
    if maitai_ok and elliptec_ok:
        print("\n🎉 Both plugins are working! Ready for PyMoDAQ integration.")
    elif maitai_ok:
        print("\n✅ MaiTai laser control is fully operational!")
    else:
        print("\n⚠️  Some issues detected.")

if __name__ == "__main__":
    main()