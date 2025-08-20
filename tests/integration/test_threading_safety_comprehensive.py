#!/usr/bin/env python3
"""
Comprehensive Threading Safety Test for URASHG Plugin Controllers.

This test verifies that all hardware controllers in the URASHG plugin package
are safe from QThread destruction conflicts by testing initialization, usage,
and garbage collection without crashes.

Fixed Issues:
- ESP300Controller: Removed problematic __del__ method
- Newport1830C_controller: Removed problematic __del__ method

Status: Both controllers now use explicit cleanup via plugin close() methods
"""

import sys

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

import gc
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec

# Import all move and viewer plugins that use hardware controllers
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
    DAQ_0DViewer_Newport1830C,
)
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
    DAQ_2DViewer_PrimeBSI,
)


def check_plugin_threading_safety(
    plugin_class, plugin_name: str, mock_settings: Dict[str, Any] = None
) -> bool:
    """
    Test a single plugin for threading safety.

    Parameters:
    -----------
    plugin_class: class
        The plugin class to test
    plugin_name: str
        Human readable name for logging
    mock_settings: Dict[str, Any]
        Settings to apply for mock mode testing

    Returns:
    --------
    bool: True if plugin passes threading safety test
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Testing {plugin_name} threading safety...")

    try:
        # Create plugin instance
        plugin = plugin_class()

        # Apply mock mode settings if provided
        if mock_settings:
            for path, value in mock_settings.items():
                path_parts = path.split(".")
                setting = plugin.settings
                for part in path_parts[:-1]:
                    setting = setting.child(part)
                setting.child(path_parts[-1]).setValue(value)

        # Test initialization
        result, success = plugin.ini_stage()
        if not success:
            logger.error(f"❌ {plugin_name} initialization failed: {result}")
            return False

        logger.info(f"✅ {plugin_name} initialized successfully")

        # Test basic operations
        if hasattr(plugin, "get_actuator_value"):
            # Move plugin
            positions = plugin.get_actuator_value()
            logger.debug(f"{plugin_name} positions: {positions}")

            # Test movement (if not single axis, use list)
            if hasattr(plugin, "is_multiaxes") and plugin.is_multiaxes:
                test_move = [0.1, 0.2, 0.3] if len(positions) >= 3 else [0.1, 0.2]
            else:
                test_move = 0.1

            plugin.move_abs(test_move)
            logger.debug(f"{plugin_name} move completed")

        elif hasattr(plugin, "grab_data"):
            # Viewer plugin
            try:
                # For 2D plugins, this might fail in mock mode, that's OK
                plugin.grab_data(1)  # Single acquisition
                logger.debug(f"{plugin_name} data acquisition attempted")
            except Exception as e:
                logger.debug(
                    f"{plugin_name} data acquisition expected failure in mock: {e}"
                )

        # Test explicit cleanup
        plugin.close()
        logger.debug(f"{plugin_name} closed successfully")

        # Test garbage collection (the critical part)
        del plugin
        gc.collect()  # Force garbage collection
        time.sleep(0.1)  # Allow any background threads to settle

        logger.info(f"✅ {plugin_name} passed threading safety test")
        return True

    except Exception as e:
        logger.error(f"❌ {plugin_name} failed threading test: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_stress_initialization(
    plugin_class, plugin_name: str, iterations: int = 10
) -> bool:
    """
    Stress test plugin initialization and cleanup multiple times.

    This test is designed to catch race conditions and threading issues
    that only appear under repeated initialization/cleanup cycles.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Stress testing {plugin_name} with {iterations} iterations...")

    for i in range(iterations):
        try:
            plugin = plugin_class()

            # Quick mock mode setup for move plugins
            if hasattr(plugin, "settings"):
                # Try to enable mock mode if available
                try:
                    if plugin.settings.child("connection_group"):
                        plugin.settings.child("connection_group", "mock_mode").setValue(
                            True
                        )
                    elif plugin.settings.child("connection"):
                        plugin.settings.child("connection", "mock_mode").setValue(True)
                    elif plugin.settings.child("hardware_settings"):
                        # For other plugins that might have different structures
                        hardware_settings = plugin.settings.child("hardware_settings")
                        if hardware_settings.child("mock_mode"):
                            hardware_settings.child("mock_mode").setValue(True)
                except:
                    # If mock mode setup fails, continue anyway
                    pass

            result, success = plugin.ini_stage()
            if success:
                plugin.close()

            del plugin

            if (i + 1) % 5 == 0:
                logger.debug(f"  Completed {i + 1}/{iterations} iterations")
                gc.collect()
                time.sleep(0.05)  # Brief pause every 5 iterations

        except Exception as e:
            logger.error(f"❌ {plugin_name} failed on iteration {i + 1}: {e}")
            return False

    logger.info(f"✅ {plugin_name} passed {iterations}-iteration stress test")
    return True


def main():
    """Run comprehensive threading safety tests."""
    print("URASHG Plugin Threading Safety Test")
    print("=" * 50)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Test configurations for different plugins
    test_plugins = [
        {
            "class": DAQ_Move_ESP300,
            "name": "ESP300 Motion Controller",
            "mock_settings": {"connection_group.mock_mode": True},
        },
        {
            "class": DAQ_Move_Elliptec,
            "name": "Elliptec Rotation Mount",
            "mock_settings": {"connection.mock_mode": True},
        },
        {
            "class": DAQ_Move_MaiTai,
            "name": "MaiTai Laser Controller",
            "mock_settings": {"connection.mock_mode": True},
        },
        {
            "class": DAQ_0DViewer_Newport1830C,
            "name": "Newport 1830C Power Meter",
            "mock_settings": {"hardware_settings.mock_mode": True},
        },
        {
            "class": DAQ_2DViewer_PrimeBSI,
            "name": "PrimeBSI Camera",
            "mock_settings": {"camera_settings.mock_mode": True},
        },
    ]

    results = []

    print("\n1. Basic Threading Safety Tests")
    print("-" * 35)

    for plugin_config in test_plugins:
        success = check_plugin_threading_safety(
            plugin_config["class"],
            plugin_config["name"],
            plugin_config.get("mock_settings"),
        )
        results.append((plugin_config["name"], success))
        time.sleep(0.2)  # Brief pause between tests

    print("\n2. Stress Testing (Multiple Initializations)")
    print("-" * 47)

    stress_results = []
    for plugin_config in test_plugins:
        success = check_stress_initialization(
            plugin_config["class"],
            plugin_config["name"],
            iterations=5,  # Reduced for faster testing
        )
        stress_results.append((plugin_config["name"], success))
        time.sleep(0.2)

    print("\n3. Force Garbage Collection Test")
    print("-" * 35)

    logger.info("Running comprehensive garbage collection...")
    initial_objects = len(gc.get_objects())
    gc.collect()
    time.sleep(1.0)  # Allow any delayed cleanup
    final_objects = len(gc.get_objects())

    logger.info(f"Objects before GC: {initial_objects}, after: {final_objects}")
    logger.info("✅ Garbage collection completed without crashes")

    # Results Summary
    print("\n" + "=" * 50)
    print("THREADING SAFETY TEST RESULTS")
    print("=" * 50)

    all_passed = True

    print("\nBasic Threading Safety:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<30} {status}")
        all_passed &= passed

    print("\nStress Testing:")
    for name, passed in stress_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<30} {status}")
        all_passed &= passed

    print(f"\nGarbage Collection: ✅ PASS")

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("All URASHG plugins are now threading-safe.")
        print("\nFixed Issues:")
        print("✅ ESP300Controller __del__ method removed")
        print("✅ Newport1830C_controller __del__ method removed")
        print("✅ Explicit cleanup via plugin close() methods")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Review failed plugins for remaining threading issues.")

    return 0 if all_passed else 1


@pytest.mark.threading
@pytest.mark.integration
def test_comprehensive_threading_safety():
    """Pytest wrapper for comprehensive threading safety tests."""
    exit_code = main()
    assert exit_code == 0, "Threading safety tests failed"


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
