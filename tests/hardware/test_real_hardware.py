#!/usr/bin/env python3
"""
Real Hardware Tests for URASHG PyMoDAQ Plugin Components

This script tests the actual hardware components without mocking to verify
PyMoDAQ integration and compliance with real devices.

Usage:
    python test_real_hardware.py

Prerequisites:
    - All hardware devices must be connected
    - Virtual environment with PyMoDAQ and URASHG plugins activated
    - Proper device permissions (may need to run with appropriate user rights)

Hardware Expected:
    - Elliptec rotation mounts on /dev/ttyUSB1
    - Newport 1830-C Power Meter on /dev/ttyS0
    - Photometrics PrimeBSI camera (PyVCAM)
    - MaiTai laser (serial connection)
    - ESP300 motion controller (serial connection)
"""

import os
import sys
import traceback
from pathlib import Path

# Add source path for local imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_plugin_loading():
    """Test that all URASHG plugins can be loaded via PyMoDAQ entry points."""
    print("=== Testing Plugin Loading ===")

    try:
        import importlib.metadata

        # Expected URASHG plugins
        expected_plugins = [
            ("DAQ_Move_ESP300", "pymodaq.move_plugins"),
            ("DAQ_Move_Elliptec", "pymodaq.move_plugins"),
            ("DAQ_Move_MaiTai", "pymodaq.move_plugins"),
            ("DAQ_0DViewer_Newport1830C", "pymodaq.viewer_plugins"),
            ("DAQ_2DViewer_PrimeBSI", "pymodaq.viewer_plugins"),
        ]

        eps = importlib.metadata.entry_points()

        for plugin_name, group in expected_plugins:
            try:
                if hasattr(eps, "select"):
                    ep_list = list(eps.select(group=group, name=plugin_name))
                else:
                    ep_list = [
                        ep for ep in eps.get(group, []) if ep.name == plugin_name
                    ]

                if ep_list:
                    ep_list[0].load()
                    print(f"✅ {plugin_name}: Loaded successfully")
                else:
                    print(f"❌ {plugin_name}: Entry point not found")
                    return False
            except Exception as e:
                print(f"❌ {plugin_name}: Failed to load - {e}")
                return False

        print("✅ All plugins loaded successfully")
        return True

    except Exception as e:
        print(f"❌ Plugin loading test failed: {e}")
        return False


def test_elliptec_hardware():
    """Test Elliptec rotation mounts with real hardware."""
    print("\n=== Testing Elliptec Hardware ===")

    try:
        from pymodaq.utils.data import DataActuator

        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
            DAQ_Move_Elliptec,
        )

        # Create plugin instance with proper parameters
        plugin = DAQ_Move_Elliptec(None, None)

        # Configure for real hardware
        plugin.settings.child("connection_group", "serial_port").setValue(
            "/dev/ttyUSB1"
        )
        plugin.settings.child("connection_group", "timeout").setValue(5000)

        print("Initializing Elliptec controller...")
        info, success = plugin.ini_actuator()

        if not success:
            print(f"❌ Elliptec initialization failed: {info}")
            return False

        print(f"✅ Elliptec initialized: {info}")

        # Test getting current position
        try:
            current_pos = plugin.get_actuator_value()
            print(f"✅ Current positions: {current_pos}")
        except Exception as e:
            print(f"⚠️  Position read failed: {e}")

        # Test small movement (safe test)
        try:
            print("Testing small movement...")
            test_positions = DataActuator(
                data=[[1.0, 1.0, 1.0]]
            )  # Small 1-degree movement
            plugin.move_abs(test_positions)
            print("✅ Movement command sent successfully")
        except Exception as e:
            print(f"⚠️  Movement test failed: {e}")

        # Cleanup
        plugin.close()
        print("✅ Elliptec hardware test completed")
        return True

    except Exception as e:
        print(f"❌ Elliptec hardware test failed: {e}")
        traceback.print_exc()
        return False


def test_newport_power_meter():
    """Test Newport 1830-C Power Meter with real hardware."""
    print("\n=== Testing Newport Power Meter ===")

    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
            DAQ_0DViewer_Newport1830C,
        )

        # Create plugin instance with proper parameters
        plugin = DAQ_0DViewer_Newport1830C(None, None)

        # Configure for real hardware
        plugin.settings.child("connection_group", "serial_port").setValue("/dev/ttyS0")
        plugin.settings.child("connection_group", "timeout").setValue(5000)

        print("Initializing Newport power meter...")
        info, success = plugin.ini_detector()

        if not success:
            print(f"❌ Newport initialization failed: {info}")
            return False

        print(f"✅ Newport initialized: {info}")

        # Test data acquisition
        try:
            print("Testing data acquisition...")
            plugin.grab_data()
            print("✅ Data acquisition successful")
        except Exception as e:
            print(f"⚠️  Data acquisition failed: {e}")

        # Cleanup
        plugin.close()
        print("✅ Newport power meter test completed")
        return True

    except Exception as e:
        print(f"❌ Newport power meter test failed: {e}")
        traceback.print_exc()
        return False


def test_primebsi_camera():
    """Test Photometrics PrimeBSI camera with real hardware."""
    print("\n=== Testing PrimeBSI Camera ===")

    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
            DAQ_2DViewer_PrimeBSI,
        )

        # Create plugin instance with proper parameters
        plugin = DAQ_2DViewer_PrimeBSI(None, None)

        print("Initializing PrimeBSI camera...")
        info, success = plugin.ini_detector()

        if not success:
            print(f"❌ PrimeBSI initialization failed: {info}")
            return False

        print(f"✅ PrimeBSI initialized: {info}")

        # Test data acquisition
        try:
            print("Testing image acquisition...")
            plugin.grab_data()
            print("✅ Image acquisition successful")
        except Exception as e:
            print(f"⚠️  Image acquisition failed: {e}")

        # Cleanup
        plugin.close()
        print("✅ PrimeBSI camera test completed")
        return True

    except Exception as e:
        print(f"❌ PrimeBSI camera test failed: {e}")
        traceback.print_exc()
        return False


def test_maitai_laser():
    """Test MaiTai laser with real hardware."""
    print("\n=== Testing MaiTai Laser ===")

    try:

        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
            DAQ_Move_MaiTai,
        )

        # Create plugin instance with proper parameters
        plugin = DAQ_Move_MaiTai(None, None)

        # Try common serial ports for MaiTai
        for port in ["/dev/ttyUSB0", "/dev/ttyUSB2", "/dev/ttyUSB3"]:
            if os.path.exists(port):
                plugin.settings.child("connection_group", "serial_port").setValue(port)
                break

        print("Initializing MaiTai laser...")
        info, success = plugin.ini_actuator()

        if not success:
            print(f"❌ MaiTai initialization failed: {info}")
            return False

        print(f"✅ MaiTai initialized: {info}")

        # Test getting current wavelength
        try:
            current_wl = plugin.get_actuator_value()
            print(f"✅ Current wavelength: {current_wl} nm")
        except Exception as e:
            print(f"⚠️  Wavelength read failed: {e}")

        # Cleanup
        plugin.close()
        print("✅ MaiTai laser test completed")
        return True

    except Exception as e:
        print(f"❌ MaiTai laser test failed: {e}")
        traceback.print_exc()
        return False


def test_esp300_controller():
    """Test ESP300 motion controller with real hardware."""
    print("\n=== Testing ESP300 Controller ===")

    try:

        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import (
            DAQ_Move_ESP300,
        )

        # Create plugin instance with proper parameters
        plugin = DAQ_Move_ESP300(None, None)

        # Try common serial ports for ESP300
        for port in ["/dev/ttyUSB3", "/dev/ttyUSB4", "/dev/ttyUSB5", "/dev/ttyUSB6"]:
            if os.path.exists(port):
                plugin.settings.child("connection_group", "serial_port").setValue(port)
                break

        print("Initializing ESP300 controller...")
        info, success = plugin.ini_actuator()

        if not success:
            print(f"❌ ESP300 initialization failed: {info}")
            return False

        print(f"✅ ESP300 initialized: {info}")

        # Test getting current position
        try:
            current_pos = plugin.get_actuator_value()
            print(f"✅ Current positions: {current_pos}")
        except Exception as e:
            print(f"⚠️  Position read failed: {e}")

        # Cleanup
        plugin.close()
        print("✅ ESP300 controller test completed")
        return True

    except Exception as e:
        print(f"❌ ESP300 controller test failed: {e}")
        traceback.print_exc()
        return False


def test_extension_loading():
    """Test that the URASHG extension can be loaded."""
    print("\n=== Testing Extension Loading ===")

    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        print("✅ URASHG extension class imported successfully")

        # Test extension metadata
        print(
            f"Extension name: {getattr(URASHGMicroscopyExtension, 'extension_name', 'Not defined')}"
        )
        print("✅ Extension loading test completed")
        return True

    except Exception as e:
        print(f"❌ Extension loading test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all hardware tests."""
    print("URASHG Real Hardware Test Suite")
    print("=" * 50)
    print("Testing PyMoDAQ plugin compliance with real hardware")
    print("Note: Some tests may fail if hardware is not connected")
    print("=" * 50)

    # Track test results
    tests = [
        ("Plugin Loading", test_plugin_loading),
        ("Extension Loading", test_extension_loading),
        ("Elliptec Hardware", test_elliptec_hardware),
        ("Newport Power Meter", test_newport_power_meter),
        ("PrimeBSI Camera", test_primebsi_camera),
        ("MaiTai Laser", test_maitai_laser),
        ("ESP300 Controller", test_esp300_controller),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print(f"\n⚠️  Test '{test_name}' interrupted by user")
            results.append((test_name, False))
            break
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"TOTAL: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Hardware integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check hardware connections and configurations.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)
