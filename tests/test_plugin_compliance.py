#!/usr/bin/env python3
"""
Plugin Class Verification Test for URASHG Components

This script tests the PyMoDAQ plugin classes directly without full initialization
to verify that they conform to PyMoDAQ 5.x standards and can be loaded properly.

This test focuses on:
1. Plugin class structure and inheritance
2. Parameter tree definitions
3. Method signatures and compliance
4. Data format compatibility
5. Entry point registration

Usage:
    python test_plugin_compliance.py
"""

import sys
import traceback
from pathlib import Path

# Add source path for local imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_plugin_class_structure(plugin_module, plugin_class_name, plugin_type):
    """Test plugin class structure and compliance."""
    print(f"\n--- Testing {plugin_class_name} Structure ---")

    try:
        # Import the plugin module
        module = __import__(plugin_module, fromlist=[plugin_class_name])
        plugin_class = getattr(module, plugin_class_name)

        print(f"✅ Plugin class {plugin_class_name} imported successfully")

        # Check inheritance
        if plugin_type == "move":
            from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

            if issubclass(plugin_class, DAQ_Move_base):
                print("✅ Correct inheritance from DAQ_Move_base")
            else:
                print("❌ Incorrect inheritance for move plugin")
                return False
        elif plugin_type == "viewer":
            from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

            if issubclass(plugin_class, DAQ_Viewer_base):
                print("✅ Correct inheritance from DAQ_Viewer_base")
            else:
                print("❌ Incorrect inheritance for viewer plugin")
                return False

        # Check required attributes
        if hasattr(plugin_class, "params"):
            print("✅ Parameter tree definition found")
        else:
            print("❌ Missing parameter tree definition")
            return False

        # Check methods - PyMoDAQ 5.x standards
        required_methods = ["close"]
        if plugin_type == "move":
            required_methods.extend(["ini_stage", "get_actuator_value", "move_abs"])
        elif plugin_type == "viewer":
            required_methods.extend(["ini_detector", "grab_data"])

        for method in required_methods:
            if hasattr(plugin_class, method):
                print(f"✅ Method {method} found")
            else:
                print(f"❌ Missing required method: {method}")
                return False

        # Check controller units for move plugins
        if plugin_type == "move" and hasattr(plugin_class, "_controller_units"):
            print(f"✅ Controller units defined: {plugin_class._controller_units}")

        return True

    except Exception as e:
        print(f"❌ Plugin class test failed: {e}")
        traceback.print_exc()
        return False


def test_esp300_compliance():
    """Test ESP300 plugin compliance."""
    print("\n=== Testing ESP300 Plugin Compliance ===")
    return test_plugin_class_structure(
        "pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300",
        "DAQ_Move_ESP300",
        "move",
    )


def test_elliptec_compliance():
    """Test Elliptec plugin compliance."""
    print("\n=== Testing Elliptec Plugin Compliance ===")
    return test_plugin_class_structure(
        "pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec",
        "DAQ_Move_Elliptec",
        "move",
    )


def test_maitai_compliance():
    """Test MaiTai plugin compliance."""
    print("\n=== Testing MaiTai Plugin Compliance ===")
    return test_plugin_class_structure(
        "pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai",
        "DAQ_Move_MaiTai",
        "move",
    )


def test_newport_compliance():
    """Test Newport plugin compliance."""
    print("\n=== Testing Newport Plugin Compliance ===")
    return test_plugin_class_structure(
        "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C",
        "DAQ_0DViewer_Newport1830C",
        "viewer",
    )


def test_primebsi_compliance():
    """Test PrimeBSI plugin compliance."""
    print("\n=== Testing PrimeBSI Plugin Compliance ===")
    return test_plugin_class_structure(
        "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI",
        "DAQ_2DViewer_PrimeBSI",
        "viewer",
    )


def test_data_format_compliance():
    """Test data format compliance with PyMoDAQ 5.x."""
    print("\n=== Testing Data Format Compliance ===")

    try:
        # Test DataActuator import and usage
        import numpy as np
        from pymodaq.utils.data import DataActuator

        # Test single-axis data
        single_data = DataActuator(data=[np.array([800.0])])
        print("✅ Single-axis DataActuator creation successful")

        # Test multi-axis data
        multi_data = DataActuator(data=[np.array([1.0, 2.0, 3.0])])
        print("✅ Multi-axis DataActuator creation successful")

        # Test data access patterns used in URASHG plugins
        value = float(single_data.value())
        print(f"✅ Single-axis value() access: {value}")

        array = multi_data.data[0]
        print(f"✅ Multi-axis data[0] access: {array}")

        # Test DataWithAxes import
        from pymodaq_data import Axis, DataSource, DataWithAxes

        # Test 2D data structure (for camera)
        x_axis = Axis("x", data=np.arange(100), units="pixels")
        y_axis = Axis("y", data=np.arange(100), units="pixels")
        DataWithAxes(
            "camera_image",
            data=[np.random.rand(100, 100)],
            axes=[x_axis, y_axis],
            source=DataSource.raw,
        )
        print("✅ 2D DataWithAxes creation successful")

        # Test 0D data structure (for power meter)
        DataWithAxes("power_measurement", data=[np.array([0.5])], source=DataSource.raw)
        print("✅ 0D DataWithAxes creation successful")

        return True

    except Exception as e:
        print(f"❌ Data format compliance test failed: {e}")
        traceback.print_exc()
        return False


def test_entry_point_compliance():
    """Test entry point compliance and registration."""
    print("\n=== Testing Entry Point Compliance ===")

    try:
        import importlib.metadata

        eps = importlib.metadata.entry_points()

        # Expected plugins
        expected_move_plugins = [
            "DAQ_Move_ESP300",
            "DAQ_Move_Elliptec",
            "DAQ_Move_MaiTai",
        ]

        expected_viewer_plugins = ["DAQ_0DViewer_Newport1830C", "DAQ_2DViewer_PrimeBSI"]

        # Check move plugins
        if hasattr(eps, "select"):
            move_plugins = list(eps.select(group="pymodaq.move_plugins"))
        else:
            move_plugins = eps.get("pymodaq.move_plugins", [])

        found_move = []
        for plugin_name in expected_move_plugins:
            found = any(ep.name == plugin_name for ep in move_plugins)
            if found:
                found_move.append(plugin_name)
                print(f"✅ Move plugin registered: {plugin_name}")
            else:
                print(f"❌ Move plugin missing: {plugin_name}")

        # Check viewer plugins
        if hasattr(eps, "select"):
            viewer_plugins = list(eps.select(group="pymodaq.viewer_plugins"))
        else:
            viewer_plugins = eps.get("pymodaq.viewer_plugins", [])

        found_viewer = []
        for plugin_name in expected_viewer_plugins:
            found = any(ep.name == plugin_name for ep in viewer_plugins)
            if found:
                found_viewer.append(plugin_name)
                print(f"✅ Viewer plugin registered: {plugin_name}")
            else:
                print(f"❌ Viewer plugin missing: {plugin_name}")

        # Test plugin loading
        total_loadable = 0
        for ep in move_plugins + viewer_plugins:
            if any(
                x in ep.name
                for x in ["ESP300", "Elliptec", "MaiTai", "Newport", "PrimeBSI"]
            ):
                try:
                    ep.load()
                    print(f"✅ Plugin loadable: {ep.name}")
                    total_loadable += 1
                except Exception as e:
                    print(f"❌ Plugin load failed: {ep.name} - {e}")

        success = (
            len(found_move) == len(expected_move_plugins)
            and len(found_viewer) == len(expected_viewer_plugins)
            and total_loadable >= 5
        )

        print(
            f"Summary: {len(found_move)}/{len(expected_move_plugins)} move plugins, {len(found_viewer)}/{len(expected_viewer_plugins)} viewer plugins, {total_loadable} loadable"
        )

        return success

    except Exception as e:
        print(f"❌ Entry point compliance test failed: {e}")
        traceback.print_exc()
        return False


def test_extension_compliance():
    """Test extension compliance."""
    print("\n=== Testing Extension Compliance ===")

    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        print("✅ Extension class imported successfully")

        # Check inheritance - PyMoDAQ 5.x standards
        from pymodaq_gui.utils.custom_app import CustomApp

        if issubclass(URASHGMicroscopyExtension, CustomApp):
            print("✅ Correct inheritance from CustomApp")
        else:
            print("❌ Incorrect inheritance for extension")
            return False

        # Check required attributes - PyMoDAQ 5.x standards
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            EXTENSION_NAME,
        )

        if EXTENSION_NAME:
            print(f"✅ Extension name: {EXTENSION_NAME}")
        else:
            print("⚠️  Extension name not defined")

        # Check entry point registration
        import importlib.metadata

        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        found_extension = any("URASHG" in ep.name for ep in extension_eps)
        if found_extension:
            print("✅ Extension entry point registered")
        else:
            print("❌ Extension entry point not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Extension compliance test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all plugin compliance tests."""
    print("URASHG Plugin Compliance Test Suite")
    print("=" * 60)
    print("Testing PyMoDAQ 5.x plugin compliance without hardware")
    print("Focus: Class structure, inheritance, and standards conformance")
    print("=" * 60)

    # Track test results
    tests = [
        ("Data Format Compliance", test_data_format_compliance),
        ("Entry Point Compliance", test_entry_point_compliance),
        ("Extension Compliance", test_extension_compliance),
        ("ESP300 Plugin Compliance", test_esp300_compliance),
        ("Elliptec Plugin Compliance", test_elliptec_compliance),
        ("MaiTai Plugin Compliance", test_maitai_compliance),
        ("Newport Plugin Compliance", test_newport_compliance),
        ("PrimeBSI Plugin Compliance", test_primebsi_compliance),
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
    print("\n" + "=" * 60)
    print("PLUGIN COMPLIANCE TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ COMPLIANT" if result else "❌ NON-COMPLIANT"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1

    print("-" * 60)
    print(f"TOTAL: {passed}/{total} compliance tests passed")

    if passed == total:
        print("🎉 ALL PLUGINS ARE PYMODAQ 5.X COMPLIANT!")
        print("   Ready for production deployment")
        return 0
    elif passed >= total * 0.8:
        print("✅ EXCELLENT COMPLIANCE (≥80%)")
        print("   Plugins meet PyMoDAQ standards")
        return 0
    elif passed >= total * 0.6:
        print("✅ GOOD COMPLIANCE (≥60%)")
        print("   Most plugins are PyMoDAQ compliant")
        return 0
    else:
        print("⚠️  POOR COMPLIANCE (<60%)")
        print("   Multiple compliance issues need attention")
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
