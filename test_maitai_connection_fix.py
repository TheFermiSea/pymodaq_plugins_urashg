#!/usr/bin/env python3
"""
Test script to verify MaiTai laser connection fix in URASHG microscopy extension.

This script tests the PyMoDAQ-compliant device manager implementation
that directly instantiates plugin classes rather than relying on
pre-loaded dashboard modules.

Usage:
    python test_maitai_connection_fix.py [--mock] [--verbose]

Options:
    --mock      Run in mock mode (simulated hardware)
    --verbose   Enable detailed logging
"""

import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_device_manager_instantiation():
    """Test that DeviceManager can be created without dashboard."""
    print("\n" + "="*60)
    print("TEST 1: DeviceManager Instantiation")
    print("="*60)

    try:
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Test with None dashboard (edge case)
        print("Creating DeviceManager with None dashboard...")
        device_manager = URASHGDeviceManager(dashboard=None)

        print("✅ DeviceManager created successfully")
        print(f"   Devices discovered: {len(device_manager.devices)}")
        print(f"   Missing devices: {device_manager.missing_devices}")

        return True

    except Exception as e:
        print(f"❌ DeviceManager instantiation failed: {e}")
        return False

def test_mock_dashboard_creation():
    """Test creating a mock dashboard for plugin instantiation."""
    print("\n" + "="*60)
    print("TEST 2: Mock Dashboard Creation")
    print("="*60)

    try:
        # Create minimal mock dashboard
        class MockDashboard:
            def __init__(self):
                self.modules_manager = None

        mock_dashboard = MockDashboard()
        print("✅ Mock dashboard created")

        return mock_dashboard

    except Exception as e:
        print(f"❌ Mock dashboard creation failed: {e}")
        return None

def test_maitai_plugin_import():
    """Test that MaiTai plugin can be imported."""
    print("\n" + "="*60)
    print("TEST 3: MaiTai Plugin Import")
    print("="*60)

    try:
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
        print("✅ MaiTai plugin imported successfully")
        print(f"   Plugin class: {DAQ_Move_MaiTai}")

        return DAQ_Move_MaiTai

    except ImportError as e:
        print(f"❌ MaiTai plugin import failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error importing MaiTai plugin: {e}")
        return None

def test_direct_plugin_instantiation(mock_dashboard, plugin_class, mock_mode=False):
    """Test direct instantiation of MaiTai plugin."""
    print("\n" + "="*60)
    print("TEST 4: Direct Plugin Instantiation")
    print("="*60)

    try:
        print(f"Creating MaiTai plugin instance (mock_mode={mock_mode})...")

        # Create plugin instance
        plugin_instance = plugin_class(parent=mock_dashboard)
        print("✅ Plugin instance created")

        # Check basic attributes
        if hasattr(plugin_instance, 'settings'):
            print("✅ Plugin has settings attribute")

        if hasattr(plugin_instance, 'controller'):
            print("✅ Plugin has controller attribute")

        return plugin_instance

    except Exception as e:
        print(f"❌ Plugin instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_plugin_initialization(plugin_instance, mock_mode=False):
    """Test PyMoDAQ plugin initialization lifecycle."""
    print("\n" + "="*60)
    print("TEST 5: Plugin Initialization")
    print("="*60)

    try:
        print("Calling ini_stage()...")

        # Set mock mode if requested
        if mock_mode and hasattr(plugin_instance, 'settings'):
            try:
                mock_param = plugin_instance.settings.child('mock_mode')
                if mock_param:
                    mock_param.setValue(True)
                    print("✅ Mock mode enabled")
            except:
                print("⚠️  Could not set mock mode (parameter may not exist)")

        # Initialize plugin
        init_result = plugin_instance.ini_stage()

        if init_result:
            if len(init_result) >= 2 and init_result[1]:
                print("✅ Plugin initialization successful")
                print(f"   Result: {init_result}")
                return True
            else:
                print(f"❌ Plugin initialization failed: {init_result}")
                return False
        else:
            print("❌ Plugin initialization returned None")
            return False

    except Exception as e:
        print(f"❌ Plugin initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_device_manager_with_dashboard(mock_dashboard):
    """Test DeviceManager with mock dashboard."""
    print("\n" + "="*60)
    print("TEST 6: DeviceManager with Dashboard")
    print("="*60)

    try:
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        print("Creating DeviceManager with mock dashboard...")
        device_manager = URASHGDeviceManager(dashboard=mock_dashboard)

        print("✅ DeviceManager created with dashboard")
        print(f"   Total devices discovered: {len(device_manager.devices)}")

        # Check for MaiTai specifically
        laser_device = device_manager.get_laser()
        if laser_device:
            print("✅ MaiTai laser device available!")
            print(f"   Laser device type: {type(laser_device)}")

            # Test basic laser operations
            if hasattr(laser_device, 'get_actuator_value'):
                print("✅ Laser has get_actuator_value method")

            if hasattr(laser_device, 'move_abs'):
                print("✅ Laser has move_abs method")

            return device_manager, laser_device
        else:
            print("❌ MaiTai laser device not available")
            print("   Available devices:")
            for device_key, device_info in device_manager.devices.items():
                print(f"     - {device_key}: {device_info.status.value}")
            return device_manager, None

    except Exception as e:
        print(f"❌ DeviceManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_wavelength_control(laser_device):
    """Test MaiTai wavelength control functionality."""
    print("\n" + "="*60)
    print("TEST 7: Wavelength Control")
    print("="*60)

    if not laser_device:
        print("❌ No laser device available for wavelength control test")
        return False

    try:
        # Test getting current wavelength
        print("Testing get_actuator_value()...")
        current_wavelength = laser_device.get_actuator_value()
        print(f"✅ Current wavelength: {current_wavelength}")

        # Test setting wavelength (using DataActuator pattern)
        print("Testing wavelength setting with DataActuator...")
        from pymodaq.utils.data import DataActuator

        target_wavelength = 800.0  # nm
        position_data = DataActuator(data=[target_wavelength])

        print(f"Setting wavelength to {target_wavelength} nm...")
        laser_device.move_abs(position_data)
        print("✅ Wavelength setting command executed")

        return True

    except Exception as e:
        print(f"❌ Wavelength control test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extension_integration():
    """Test integration with URASHG microscopy extension."""
    print("\n" + "="*60)
    print("TEST 8: Extension Integration")
    print("="*60)

    try:
        # Import extension class
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        print("✅ Extension class imported")

        # Note: Full extension testing would require Qt application
        print("ℹ️  Full extension testing requires Qt application context")
        print("   This test only verifies the class can be imported")

        return True

    except Exception as e:
        print(f"❌ Extension integration test failed: {e}")
        return False

def test_cleanup(device_manager, plugin_instance):
    """Test proper cleanup of resources."""
    print("\n" + "="*60)
    print("TEST 9: Resource Cleanup")
    print("="*60)

    try:
        # Clean up plugin
        if plugin_instance and hasattr(plugin_instance, 'close'):
            print("Closing plugin instance...")
            plugin_instance.close()
            print("✅ Plugin closed")

        # Clean up device manager
        if device_manager and hasattr(device_manager, 'cleanup'):
            print("Cleaning up device manager...")
            device_manager.cleanup()
            print("✅ Device manager cleaned up")

        return True

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test MaiTai connection fix')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    setup_logging(args.verbose)

    print("URASHG MaiTai Connection Fix Test Suite")
    print("="*60)
    print(f"Mock mode: {args.mock}")
    print(f"Verbose: {args.verbose}")

    test_results = []
    device_manager = None
    plugin_instance = None
    laser_device = None

    # Run tests
    test_results.append(test_device_manager_instantiation())

    mock_dashboard = test_mock_dashboard_creation()
    if mock_dashboard:
        test_results.append(True)
    else:
        test_results.append(False)

    plugin_class = test_maitai_plugin_import()
    if plugin_class:
        test_results.append(True)

        plugin_instance = test_direct_plugin_instantiation(mock_dashboard, plugin_class, args.mock)
        if plugin_instance:
            test_results.append(True)

            init_success = test_plugin_initialization(plugin_instance, args.mock)
            test_results.append(init_success)

            device_manager, laser_device = test_device_manager_with_dashboard(mock_dashboard)
            if device_manager:
                test_results.append(True)

                wavelength_success = test_wavelength_control(laser_device)
                test_results.append(wavelength_success)
            else:
                test_results.append(False)
                test_results.append(False)
        else:
            test_results.extend([False, False, False, False])
    else:
        test_results.extend([False, False, False, False, False])

    extension_success = test_extension_integration()
    test_results.append(extension_success)

    cleanup_success = test_cleanup(device_manager, plugin_instance)
    test_results.append(cleanup_success)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    test_names = [
        "DeviceManager Instantiation",
        "Mock Dashboard Creation",
        "MaiTai Plugin Import",
        "Direct Plugin Instantiation",
        "Plugin Initialization",
        "DeviceManager with Dashboard",
        "Wavelength Control",
        "Extension Integration",
        "Resource Cleanup"
    ]

    passed = sum(test_results)
    total = len(test_results)

    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1:2d}. {name:<30} {status}")

    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! MaiTai connection fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
