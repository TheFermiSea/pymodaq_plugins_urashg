"""
PyMoDAQ v5 Compliance Test Suite for URASHG Extension

This test suite verifies that the URASHG extension properly follows PyMoDAQ v5
standards and can be properly integrated with the PyMoDAQ ecosystem.

All tests use standard pytest patterns with proper assertions and fixtures.
"""

import importlib.metadata
from pathlib import Path
from unittest.mock import Mock

import pytest
from pyqtgraph.dockarea import DockArea


class TestPyMoDAQCompliance:
    """Test suite for PyMoDAQ v5 compliance verification."""

    def test_extension_imports(self):
        """Test that the extension can be imported without errors."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            CLASS_NAME,
            EXTENSION_NAME,
            MeasurementWorker,
            URASHGMicroscopyExtension,
        )

        # Verify imports succeeded
        assert URASHGMicroscopyExtension is not None
        assert MeasurementWorker is not None
        assert CLASS_NAME is not None
        assert EXTENSION_NAME is not None

    def test_extension_inheritance(self):
        """Test that the extension inherits from the correct PyMoDAQ base class."""
        from pymodaq_gui.utils.custom_app import CustomApp

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        assert issubclass(
            URASHGMicroscopyExtension, CustomApp
        ), "Extension must inherit from CustomApp for PyMoDAQ v5 compatibility"

    def test_extension_metadata(self):
        """Test that extension metadata is properly defined."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            CLASS_NAME,
            EXTENSION_NAME,
            URASHGMicroscopyExtension,
        )

        # Check required attributes exist
        required_attrs = ["params", "settings"]
        for attr in required_attrs:
            assert hasattr(
                URASHGMicroscopyExtension, attr
            ), f"Extension missing required attribute: {attr}"

        # Check metadata values
        assert (
            isinstance(EXTENSION_NAME, str) and len(EXTENSION_NAME) > 0
        ), "EXTENSION_NAME must be a non-empty string"
        assert (
            isinstance(CLASS_NAME, str) and len(CLASS_NAME) > 0
        ), "CLASS_NAME must be a non-empty string"
        assert (
            CLASS_NAME == "URASHGMicroscopyExtension"
        ), "CLASS_NAME should match the actual class name"

    def test_extension_methods(self):
        """Test that extension has all required PyMoDAQ methods."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Required PyMoDAQ extension methods
        required_methods = [
            "__init__",
            "setup_docks",
            "setup_menu",
        ]

        for method in required_methods:
            assert hasattr(
                URASHGMicroscopyExtension, method
            ), f"Extension missing required method: {method}"
            assert callable(
                getattr(URASHGMicroscopyExtension, method)
            ), f"Extension method {method} is not callable"

    def test_extension_parameters(self):
        """Test that extension parameters are properly structured."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        assert hasattr(
            URASHGMicroscopyExtension, "params"
        ), "Extension must have 'params' attribute"

        params = URASHGMicroscopyExtension.params
        assert isinstance(params, list), "Extension 'params' must be a list"
        assert len(params) > 0, "Extension 'params' cannot be empty"

        # Check parameter structure
        for i, param in enumerate(params):
            assert isinstance(param, dict), f"Parameter {i} must be a dictionary"

            required_keys = ["name", "type"]
            for key in required_keys:
                assert key in param, f"Parameter {i} missing required key: {key}"

    def test_extension_instantiation(self, mock_dashboard):
        """Test that extension can be instantiated successfully."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Create mock parent DockArea
        mock_parent = DockArea()

        # Instantiate extension
        extension = URASHGMicroscopyExtension(mock_parent, mock_dashboard)

        # Basic instantiation checks
        assert extension is not None
        assert hasattr(
            extension, "modules_manager"
        ), "Extension must have modules_manager attribute"
        assert hasattr(extension, "settings"), "Extension must have settings attribute"

    def test_preset_file_exists(self):
        """Test that the preset file exists and is accessible."""
        preset_path = Path("presets/urashg_microscopy_system.xml")

        # Check if preset file exists in the project
        project_root = Path(__file__).parent.parent
        full_preset_path = project_root / preset_path

        assert full_preset_path.exists(), f"Preset file not found at {full_preset_path}"

        # Basic XML validation
        content = full_preset_path.read_text()
        assert (
            "<preset>" in content
        ), "Preset file should contain PyMoDAQ preset configuration"
        assert (
            "<actuators>" in content or "<detectors>" in content
        ), "Preset file should contain actuators or detectors configuration"


class TestEntryPoints:
    """Test PyMoDAQ entry point configuration."""

    def test_extension_entry_point_exists(self):
        """Test that extension entry point is properly registered."""
        eps = importlib.metadata.entry_points()

        # Handle different Python versions
        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        urashg_extensions = [
            ep for ep in extension_eps if ep.name == "URASHGMicroscopyExtension"
        ]

        assert (
            len(urashg_extensions) > 0
        ), "URASHGMicroscopyExtension not found in pymodaq.extensions entry points"

    def test_extension_entry_point_loadable(self):
        """Test that extension entry point can be loaded without errors."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        for ep in extension_eps:
            if ep.name == "URASHGMicroscopyExtension":
                # Test that the entry point can be loaded
                extension_class = ep.load()
                assert extension_class is not None
                assert hasattr(extension_class, "__init__")
                break
        else:
            pytest.fail("URASHGMicroscopyExtension entry point not found")

    def test_plugin_entry_points_exist(self):
        """Test that all plugin entry points are properly registered."""
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
            viewer_eps = list(eps.select(group="pymodaq.viewer_plugins"))
        else:
            move_eps = eps.get("pymodaq.move_plugins", [])
            viewer_eps = eps.get("pymodaq.viewer_plugins", [])

        found_move = [ep.name for ep in move_eps if ep.name in expected_move_plugins]
        found_viewer = [
            ep.name for ep in viewer_eps if ep.name in expected_viewer_plugins
        ]

        assert len(found_move) == len(
            expected_move_plugins
        ), f"Missing move plugins. Expected: {expected_move_plugins}, Found: {found_move}"
        assert len(found_viewer) == len(
            expected_viewer_plugins
        ), f"Missing viewer plugins. Expected: {expected_viewer_plugins}, Found: {found_viewer}"

    def test_plugin_entry_points_loadable(self):
        """Test that all plugin entry points can be loaded."""
        eps = importlib.metadata.entry_points()

        plugin_groups = ["pymodaq.move_plugins", "pymodaq.viewer_plugins"]
        urashg_plugin_names = [
            "DAQ_Move_Elliptec",
            "DAQ_Move_MaiTai",
            "DAQ_Move_ESP300",
            "DAQ_2DViewer_PrimeBSI",
            "DAQ_0DViewer_Newport1830C",
        ]

        for group in plugin_groups:
            if hasattr(eps, "select"):
                group_eps = list(eps.select(group=group))
            else:
                group_eps = eps.get(group, [])

            for ep in group_eps:
                if ep.name in urashg_plugin_names:
                    # Test that the entry point can be loaded
                    plugin_class = ep.load()
                    assert plugin_class is not None
                    assert hasattr(plugin_class, "__init__")


class TestConfiguration:
    """Test configuration module functionality."""

    def test_config_module_importable(self):
        """Test that configuration module can be imported."""
        from pymodaq_plugins_urashg.utils.config import Config

        assert Config is not None

        # Test basic functionality
        config = Config()
        assert config is not None

    def test_config_methods_exist(self):
        """Test that configuration module has expected methods."""
        from pymodaq_plugins_urashg.utils.config import Config

        config = Config()

        # Test that key methods exist
        assert hasattr(config, "get_preset_config")
        assert hasattr(config, "get_hardware_config")

        # Test basic method calls don't fail
        preset_config = config.get_preset_config()
        hardware_config = config.get_hardware_config("elliptec")

        # Basic validation - should not raise exceptions
        assert preset_config is not None
        assert hardware_config is not None


@pytest.mark.integration
class TestPluginIntegration:
    """Integration tests for plugin compatibility."""

    def test_move_plugin_imports(self):
        """Test that all move plugins can be imported."""
        move_plugins = [
            "pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec",
            "pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai",
            "pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300",
        ]

        for plugin_module in move_plugins:
            try:
                importlib.import_module(plugin_module)
            except ImportError as e:
                pytest.fail(f"Failed to import {plugin_module}: {e}")

    def test_viewer_plugin_imports(self):
        """Test that all viewer plugins can be imported."""
        viewer_plugins = [
            "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI",
            "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C",
        ]

        for plugin_module in viewer_plugins:
            try:
                importlib.import_module(plugin_module)
            except ImportError as e:
                pytest.fail(f"Failed to import {plugin_module}: {e}")

    def test_plugin_inheritance(self):
        """Test that plugins inherit from correct PyMoDAQ base classes."""
        # Test move plugins
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
            DAQ_Move_Elliptec,
        )
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
            DAQ_Move_MaiTai,
        )

        assert issubclass(DAQ_Move_Elliptec, DAQ_Move_base)
        assert issubclass(DAQ_Move_MaiTai, DAQ_Move_base)

        # Test viewer plugins
        from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
            DAQ_0DViewer_Newport1830C,
        )
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
            DAQ_2DViewer_PrimeBSI,
        )

        assert issubclass(DAQ_2DViewer_PrimeBSI, DAQ_Viewer_base)
        assert issubclass(DAQ_0DViewer_Newport1830C, DAQ_Viewer_base)


if __name__ == "__main__":
    # Allow running as standalone script for development
    pytest.main([__file__, "-v"])
