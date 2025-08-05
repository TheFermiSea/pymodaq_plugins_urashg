#!/usr/bin/env python3
"""
Real Hardware Validation Test for PyMoDAQ URASHG Plugins
========================================================

Test all URASHG hardware devices with the updated controllers:
- MaiTai Laser: /dev/ttyUSB0 (115200 baud)
- Elliptec Rotators: /dev/ttyUSB1 (9600 baud) 
- Newport 1830C: /dev/ttyUSB2 (9600 baud)
- PrimeBSI Camera: USB 3.0

This validates the working hardware controllers integrated from the previous repository.
"""

import sys
import time
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, 'src')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_maitai_hardware():
    """Test MaiTai laser using the new controller."""
    print("1. MAITAI LASER TEST (/dev/ttyUSB0)")
    print("=" * 40)
    
    try:
        from pymodaq_plugins_urashg.hardware.urashg.maitai_control import MaiTaiController
        
        # Test with real hardware
        controller = MaiTaiController(port='/dev/ttyUSB0', mock_mode=False)
        
        if controller.connect():
            print("  ✅ Connection successful")
            
            # Test getting current status
            wavelength = controller.get_wavelength()
            power = controller.get_power()
            shutter = controller.get_shutter_state()
            
            print(f"  Current wavelength: {wavelength} nm")
            print(f"  Current power: {power} W")
            print(f"  Shutter state: {'Open' if shutter else 'Closed'}")
            
            # Test setting wavelength (use integer)
            test_wavelength = 800
            print(f"  Setting wavelength to {test_wavelength} nm...")
            if controller.set_wavelength(test_wavelength):
                print("  ✅ Wavelength set command sent")
                time.sleep(1)
                new_wavelength = controller.get_wavelength()
                print(f"  New wavelength: {new_wavelength} nm")
            else:
                print("  ❌ Failed to set wavelength")
            
            controller.disconnect()
            return True
        else:
            print("  ❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"  ❌ MaiTai test failed: {e}")
        return False

def test_elliptec_hardware():
    """Test Elliptec rotators using the new controller."""
    print("\n2. ELLIPTEC ROTATORS TEST (/dev/ttyUSB1)")
    print("=" * 40)
    
    try:
        from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController
        
        # Test with real hardware
        controller = ElliptecController(port='/dev/ttyUSB1', mock_mode=False)
        
        if controller.connect():
            print("  ✅ Connection successful")
            
            # Test getting device info for all mounts
            for addr in controller.mount_addresses:
                info = controller.get_device_info(addr)
                if info:
                    print(f"  Mount {addr}: ✅ {info}")
                    
                    # Get current position
                    pos = controller.get_position(addr)
                    print(f"    Current position: {pos:.2f} degrees")
                else:
                    print(f"  Mount {addr}: ❌ No response")
            
            # Test getting all positions
            all_positions = controller.get_all_positions()
            print(f"  All positions: {all_positions}")
            
            controller.disconnect()
            return len(all_positions) == len(controller.mount_addresses)
        else:
            print("  ❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Elliptec test failed: {e}")
        return False

def test_newport_hardware():
    """Test Newport power meter (using serial directly since controller is stub)."""
    print("\n3. NEWPORT 1830C TEST (/dev/ttyUSB2)")
    print("=" * 40)
    
    import serial
    try:
        ser = serial.Serial('/dev/ttyUSB2', 9600, timeout=1.0)
        time.sleep(1)
        
        # Newport binary protocol test
        test_cmd = b'\x50\x01\x00\x00\x51'
        ser.write(test_cmd)
        time.sleep(0.5)
        response = ser.read_all()
        
        if response:
            print(f"  Newport response: ✅ {response.hex()}")
            status_msg = 'Needs calibration module' if b'\xff' in response else 'Ready'
            print(f"  Status: {status_msg}")
            working = True
        else:
            print(f"  Newport response: ❌ No response")
            working = False
        
        ser.close()
        return working
        
    except Exception as e:
        print(f"  ❌ Newport test failed: {e}")
        return False

def test_camera_availability():
    """Test PrimeBSI camera availability."""
    print("\n4. PRIMEBSI CAMERA TEST (USB 3.0)")
    print("=" * 40)
    
    try:
        # Try to import the camera controller
        from pymodaq_plugins_urashg.hardware.urashg.camera_utils import CameraController
        print("  ✅ Camera controller import successful")
        
        # Check if PyVCAM is available
        try:
            import pyvcam
            print("  ✅ PyVCAM library available")
            
            # Try to initialize PyVCAM
            pyvcam.pvc_init_pvcam()
            camera_count = pyvcam.pvc_get_cam_total()
            print(f"  Detected cameras: {camera_count}")
            
            if camera_count > 0:
                print("  ✅ PrimeBSI camera detected")
                pyvcam.pvc_uninit_pvcam()
                return True
            else:
                print("  ⚠️  No cameras detected (may need to be powered on)")
                pyvcam.pvc_uninit_pvcam()
                return False
                
        except ImportError:
            print("  ⚠️  PyVCAM not available - camera testing skipped")
            return False
        except Exception as e:
            print(f"  ⚠️  Camera initialization error: {e}")
            try:
                pyvcam.pvc_uninit_pvcam()
            except:
                pass
            return False
            
    except Exception as e:
        print(f"  ❌ Camera test failed: {e}")
        return False

def test_pymodaq_plugin_imports():
    """Test PyMoDAQ plugin imports."""
    print("\n5. PYMODAQ PLUGIN IMPORT TEST")
    print("=" * 40)
    
    plugin_results = {}
    
    # Test MaiTai plugin import
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        print("  ✅ MaiTai plugin import successful")
        plugin_results['MaiTai'] = True
    except Exception as e:
        print(f"  ❌ MaiTai plugin import failed: {e}")
        plugin_results['MaiTai'] = False
    
    # Test Elliptec plugin import
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        print("  ✅ Elliptec plugin import successful")
        plugin_results['Elliptec'] = True
    except Exception as e:
        print(f"  ❌ Elliptec plugin import failed: {e}")
        plugin_results['Elliptec'] = False
    
    # Test Camera plugin import
    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        print("  ✅ PrimeBSI camera plugin import successful")
        plugin_results['PrimeBSI'] = True
    except Exception as e:
        print(f"  ❌ PrimeBSI camera plugin import failed: {e}")
        plugin_results['PrimeBSI'] = False
    
    return plugin_results

def main():
    """Run complete URASHG system validation."""
    print("🔬 URASHG REAL HARDWARE VALIDATION - PyMoDAQ Plugin Repository")
    print("=" * 70)
    print("Testing hardware controllers integrated from working repository")
    print()
    
    # Hardware controller tests
    maitai_ok = test_maitai_hardware()
    elliptec_ok = test_elliptec_hardware() 
    newport_ok = test_newport_hardware()
    camera_ok = test_camera_availability()
    
    # Plugin import tests
    plugin_results = test_pymodaq_plugin_imports()
    
    # Summary
    print("\n" + "=" * 70)
    print("🎯 HARDWARE VALIDATION RESULTS:")
    print("=" * 70)
    
    hardware_status = [
        ("MaiTai Laser", maitai_ok, "/dev/ttyUSB0"),
        ("Elliptec Rotators", elliptec_ok, "/dev/ttyUSB1"), 
        ("Newport 1830C", newport_ok, "/dev/ttyUSB2"),
        ("PrimeBSI Camera", camera_ok, "USB 3.0"),
    ]
    
    for device, status, port in hardware_status:
        print(f"🔧 {device:20} {port:15} {'✅ WORKING' if status else '❌ FAILED'}")
    
    print("\n📦 PyMoDAQ Plugin Import Status:")
    for plugin, status in plugin_results.items():
        print(f"   {plugin:15} {'✅ READY' if status else '❌ FAILED'}")
    
    # Overall system status
    hardware_working = sum([maitai_ok, elliptec_ok, newport_ok])
    plugins_working = sum(plugin_results.values())
    
    print(f"\n🚀 SYSTEM STATUS:")
    print(f"   Hardware: {hardware_working}/3 devices working")
    print(f"   Plugins:  {plugins_working}/3 plugins imported")
    
    if hardware_working >= 2 and plugins_working >= 2:
        print("\n🎉 ✅ URASHG SYSTEM OPERATIONAL!")
        print("🔬 Hardware controllers successfully integrated")
        print("🔧 Ready for PyMoDAQ plugin testing")
    elif hardware_working >= 2:
        print("\n⚠️  Hardware working, some plugins need debugging")
    else:
        print("\n❌ System needs attention - hardware issues detected")
    
    print("=" * 70)

if __name__ == "__main__":
    main()