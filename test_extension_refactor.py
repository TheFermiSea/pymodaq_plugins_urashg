#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compliance verification test for the refactored PyMoDAQ URASHG extension.

This test verifies that the extension properly follows PyMoDAQ 5.x standards
and can be properly integrated with the PyMoDAQ ecosystem.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_extension_imports():
    """Test that the extension can be imported without errors."""
    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            CLASS_NAME,
            EXTENSION_NAME,
            MeasurementWorker,
            URASHGMicroscopyExtension,
        )

        logger.info("✅ Extension imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Extension import failed: {e}")
        return False


def test_extension_inheritance():
    """Test that the extension inherits from the correct PyMoDAQ base class."""
    try:
        from pymodaq.extensions.utils import CustomExt

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        if issubclass(URASHGMicroscopyExtension, CustomExt):
            logger.info("✅ Extension correctly inherits from CustomExt")
            return True
        else:
            logger.error("❌ Extension does not inherit from CustomExt")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking inheritance: {e}")
        return False


def test_extension_metadata():
    """Test that the extension has required metadata."""
    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            CLASS_NAME,
            EXTENSION_NAME,
            URASHGMicroscopyExtension,
        )

        # Check class-level metadata
        required_class_attrs = []  # CustomExt doesn't require class-level metadata
        for attr in required_class_attrs:
            if not hasattr(URASHGMicroscopyExtension, attr):
                logger.error(f"❌ Missing required attribute: {attr}")
                return False

        # Check module-level constants
        if not EXTENSION_NAME or not isinstance(EXTENSION_NAME, str):
            logger.error("❌ EXTENSION_NAME not properly defined")
            return False

        if not CLASS_NAME or not isinstance(CLASS_NAME, str):
            logger.error("❌ CLASS_NAME not properly defined")
            return False

        logger.info("✅ Extension metadata is properly defined")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking metadata: {e}")
        return False


def test_extension_methods():
    """Test that the extension has required PyMoDAQ methods."""
    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        required_methods = [
            "setup_docks",
            "setup_actions",
            "connect_things",
            "value_changed",
        ]

        for method in required_methods:
            if not hasattr(URASHGMicroscopyExtension, method):
                logger.error(f"❌ Missing required method: {method}")
                return False

        logger.info("✅ Extension has all required PyMoDAQ methods")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking methods: {e}")
        return False


def test_extension_parameters():
    """Test that the extension has proper parameter structure."""
    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Check if params attribute exists and is a list
        if not hasattr(URASHGMicroscopyExtension, "params"):
            logger.error("❌ Extension missing 'params' attribute")
            return False

        params = URASHGMicroscopyExtension.params
        if not isinstance(params, list):
            logger.error("❌ Extension 'params' should be a list")
            return False

        if len(params) == 0:
            logger.error("❌ Extension 'params' is empty")
            return False

        # Check parameter structure
        for i, param in enumerate(params):
            if not isinstance(param, dict):
                logger.error(f"❌ Parameter {i} is not a dictionary")
                return False

            required_keys = ["title", "name", "type"]
            for key in required_keys:
                if key not in param:
                    logger.error(f"❌ Parameter {i} missing required key: {key}")
                    return False

        logger.info("✅ Extension parameters are properly structured")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking parameters: {e}")
        return False


def test_extension_instantiation():
    """Test that the extension can be instantiated with mock objects."""
    try:
        from pyqtgraph.dockarea import DockArea
        from qtpy.QtWidgets import QApplication, QWidget

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # Create proper DockArea parent (required by CustomExt)
        mock_parent = DockArea()

        mock_dashboard = Mock()
        mock_dashboard.modules_manager = Mock()
        mock_dashboard.modules_manager.actuators = {}
        mock_dashboard.modules_manager.detectors_2D = {}
        mock_dashboard.modules_manager.detectors_0D = {}

        # Try to instantiate the extension
        extension = URASHGMicroscopyExtension(mock_parent, mock_dashboard)

        # Basic checks
        if not hasattr(extension, "modules_manager"):
            logger.error("❌ Extension missing modules_manager attribute")
            return False

        if not hasattr(extension, "settings"):
            logger.error("❌ Extension missing settings attribute")
            return False

        logger.info("✅ Extension can be instantiated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error instantiating extension: {e}")
        return False


def test_preset_file_exists():
    """Test that the preset file exists."""
    try:
        preset_path = Path(__file__).parent / "presets" / "urashg_microscopy_system.xml"

        if preset_path.exists():
            logger.info("✅ Preset file exists")
            return True
        else:
            logger.error(f"❌ Preset file not found: {preset_path}")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking preset file: {e}")
        return False


def test_entry_points():
    """Test that PyMoDAQ entry points are properly configured."""
    try:
        import importlib.metadata

        eps = importlib.metadata.entry_points()

        # Check extension entry point
        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        urashg_extension_found = False
        for ep in extension_eps:
            if ep.name == "URASHGMicroscopyExtension":
                urashg_extension_found = True
                break

        if urashg_extension_found:
            logger.info("✅ Extension entry point is properly configured")
            return True
        else:
            logger.error("❌ Extension entry point not found in pymodaq.extensions")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking entry points: {e}")
        return False


def test_plugin_entry_points():
    """Test that individual plugin entry points are configured."""
    try:
        import importlib.metadata

        eps = importlib.metadata.entry_points()

        # Expected plugins
        expected_move_plugins = [
            "DAQ_Move_Elliptec",
            "DAQ_Move_MaiTai",
            "DAQ_Move_ESP300",
        ]

        expected_viewer_plugins = ["DAQ_2DViewer_PrimeBSI", "DAQ_0DViewer_Newport1830C"]

        # Check move plugins
        if hasattr(eps, "select"):
            move_eps = list(eps.select(group="pymodaq.move_plugins"))
        else:
            move_eps = eps.get("pymodaq.move_plugins", [])

        found_move = [ep.name for ep in move_eps if ep.name in expected_move_plugins]

        # Check viewer plugins
        if hasattr(eps, "select"):
            viewer_eps = list(eps.select(group="pymodaq.viewer_plugins"))
        else:
            viewer_eps = eps.get("pymodaq.viewer_plugins", [])

        found_viewer = [
            ep.name for ep in viewer_eps if ep.name in expected_viewer_plugins
        ]

        if len(found_move) == len(expected_move_plugins) and len(found_viewer) == len(
            expected_viewer_plugins
        ):
            logger.info("✅ All plugin entry points are properly configured")
            return True
        else:
            logger.error(
                f"❌ Missing plugin entry points. Found move: {found_move}, Found viewer: {found_viewer}"
            )
            return False
    except Exception as e:
        logger.error(f"❌ Error checking plugin entry points: {e}")
        return False


def test_config_module():
    """Test that the configuration module works properly."""
    try:
        from pymodaq_plugins_urashg.utils.config import Config

        # Try to create config instance
        config = Config()

        # Test basic functionality
        preset_config = config.get_preset_config()
        hardware_config = config.get_hardware_config("elliptec")

        logger.info("✅ Configuration module works properly")
        return True
    except Exception as e:
        logger.error(f"❌ Error testing config module: {e}")
        return False


def run_all_tests():
    """Run all compliance tests."""
    logger.info("🔍 Starting PyMoDAQ Extension Compliance Tests")
    logger.info("=" * 60)

    tests = [
        ("Extension Imports", test_extension_imports),
        ("Extension Inheritance", test_extension_inheritance),
        ("Extension Metadata", test_extension_metadata),
        ("Extension Methods", test_extension_methods),
        ("Extension Parameters", test_extension_parameters),
        ("Extension Instantiation", test_extension_instantiation),
        ("Preset File", test_preset_file_exists),
        ("Extension Entry Points", test_entry_points),
        ("Plugin Entry Points", test_plugin_entry_points),
        ("Configuration Module", test_config_module),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n🧪 Testing: {test_name}")
        if test_func():
            passed += 1
        else:
            logger.error(f"   Test failed: {test_name}")

    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Extension is PyMoDAQ compliant.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Extension needs fixes.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
