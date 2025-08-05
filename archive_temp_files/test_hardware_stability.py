#!/usr/bin/env python3
"""
Test script to verify URASHG hardware communication stability
Tests the real Elliptec hardware connection for stability issues
"""

import time
import logging

def test_elliptec_stability():
    """Test Elliptec connection stability to diagnose disconnect issues"""
    
    print("=== URASHG Hardware Stability Test ===")
    print("Testing Elliptec connection stability...")
    
    try:
        from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController
        
        # Test parameters (matching what we saw in logs)
        port = "/dev/ttyUSB1"
        baudrate = 9600
        timeout = 2.0
        mount_addresses = "2,3,8"
        mock_mode = False
        
        print(f"Connecting to Elliptec on {port}...")
        print(f"Parameters: baudrate={baudrate}, timeout={timeout}, mounts={mount_addresses}")
        
        # Create controller
        controller = ElliptecController(
            port=port,
            baudrate=baudrate, 
            timeout=timeout,
            mount_addresses=mount_addresses,
            mock_mode=mock_mode
        )
        
        # Test connection
        start_time = time.time()
        
        if controller.connect():
            connect_time = time.time() - start_time
            print(f"✅ Connected successfully in {connect_time:.2f}s")
            
            # Test communication stability
            print("Testing communication stability...")
            
            for i in range(5):
                try:
                    # Test getting positions
                    positions = controller.get_all_positions()
                    print(f"  Test {i+1}: Positions = {positions}")
                    
                    # Small delay between commands
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  Test {i+1}: Communication error - {e}")
            
            # Test how long connection stays stable
            print("Testing connection persistence...")
            stable_duration = 0
            
            for i in range(10):  # Test for ~10 seconds
                if controller.is_connected():
                    stable_duration += 1
                    time.sleep(1)
                else:
                    print(f"⚠ Connection lost after {stable_duration} seconds")
                    break
            
            if stable_duration >= 10:
                print(f"✅ Connection remained stable for {stable_duration} seconds")
            
            # Clean disconnect
            controller.disconnect()
            print("✅ Clean disconnect completed")
            
            return True
            
        else:
            print("❌ Failed to connect to Elliptec")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plugin_lifecycle():
    """Test that all plugins have required lifecycle methods"""
    
    print("\n=== Plugin Lifecycle Method Test ===")
    
    plugins_to_test = [
        ('MaiTai', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai', 'DAQ_Move_MaiTai'),
        ('Elliptec', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec', 'DAQ_Move_Elliptec'), 
        ('ESP300', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300', 'DAQ_Move_ESP300')
    ]
    
    required_methods = ['ini_stage', 'close', 'commit_settings', 'get_actuator_value', 'move_abs']
    
    all_good = True
    
    for plugin_name, module_path, class_name in plugins_to_test:
        print(f"\n--- Testing {plugin_name} Plugin Lifecycle ---")
        
        try:
            module = __import__(module_path, fromlist=[class_name])
            plugin_class = getattr(module, class_name)
            
            for method in required_methods:
                if hasattr(plugin_class, method):
                    print(f"  ✅ {method}: Present")
                else:
                    print(f"  ❌ {method}: MISSING")
                    all_good = False
                    
        except Exception as e:
            print(f"  ❌ Error testing {plugin_name}: {e}")
            all_good = False
    
    return all_good

if __name__ == '__main__':
    print("Starting URASHG hardware and plugin stability tests...\n")
    
    # Test plugin lifecycle
    lifecycle_ok = test_plugin_lifecycle()
    
    # Test hardware if available
    hardware_ok = test_elliptec_stability()
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Plugin Lifecycle: {'✅ PASS' if lifecycle_ok else '❌ FAIL'}")
    print(f"Hardware Stability: {'✅ PASS' if hardware_ok else '❌ FAIL'}")
    
    if lifecycle_ok and hardware_ok:
        print("\n🎉 ALL TESTS PASSED - Ready for stable operation!")
    else:
        print("\n⚠ Some issues detected - check logs above")