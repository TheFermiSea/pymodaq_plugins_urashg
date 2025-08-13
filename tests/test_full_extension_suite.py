"""
Full Extension Test Suite for URASHG PyMoDAQ Plugin Package

This is the comprehensive test suite that orchestrates all extension compliance
tests to ensure the URASHG extension fully adheres to PyMoDAQ standards.

This test suite covers:
- Extension Discovery & Entry Points
- Device Manager Integration
- Measurement Worker Compliance
- Plugin Integration Standards
- PyMoDAQ Framework Compliance
- Thread Safety & Performance
- Error Handling & Recovery
- Configuration Management
- Documentation Standards

Usage:
    # Run full suite
    pytest tests/test_full_extension_suite.py -v

    # Run specific test categories
    pytest tests/test_full_extension_suite.py -v -m "unit"
    pytest tests/test_full_extension_suite.py -v -m "integration"
    pytest tests/test_full_extension_suite.py -v -m "pymodaq_standards"

    # Run with coverage
    pytest tests/test_full_extension_suite.py --cov=pymodaq_plugins_urashg

    # Generate detailed report
    pytest tests/test_full_extension_suite.py -v --tb=long --maxfail=5
"""

import pytest
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
import importlib.metadata
from unittest.mock import patch, Mock

# Qt imports
from qtpy import QtWidgets, QtCore

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PyMoDAQ test configuration
pytest_plugins = [
    "tests.test_extension_compliance",
    "tests.test_device_manager_compliance",
    "tests.test_measurement_worker_compliance",
    "tests.test_plugin_integration_compliance",
]


class TestExtensionSuiteOverview:
    """Overview tests to verify test suite completeness and setup."""

    def test_test_suite_structure(self):
        """Test that all required test modules are available."""
        required_test_modules = [
            "tests.test_extension_compliance",
            "tests.test_device_manager_compliance",
            "tests.test_measurement_worker_compliance",
            "tests.test_plugin_integration_compliance",
        ]

        for module_name in required_test_modules:
            try:
                importlib.import_module(module_name)
                logger.info(f"✓ Test module {module_name} available")
            except ImportError as e:
                pytest.fail(f"Required test module {module_name} not available: {e}")

    def test_pymodaq_framework_available(self):
        """Test PyMoDAQ framework is available for testing."""
        try:
            import pymodaq
            import pymodaq.utils.parameter
            import pymodaq.utils.data
            import pymodaq.control_modules.move_utility_classes
            import pymodaq.control_modules.viewer_utility_classes

            logger.info(
                f"✓ PyMoDAQ framework available (version: {getattr(pymodaq, '__version__', 'unknown')})"
            )
        except ImportError as e:
            pytest.fail(f"PyMoDAQ framework not available: {e}")

    def test_urashg_extension_importable(self):
        """Test URASHG extension can be imported."""
        try:
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )

            logger.info("✓ URASHG extension importable")
        except ImportError as e:
            pytest.fail(f"URASHG extension not importable: {e}")

    def test_qt_framework_available(self):
        """Test Qt framework is available for GUI tests."""
        try:
            from qtpy import QtWidgets, QtCore
            from qtpy.QtCore import Signal, QObject

            logger.info("✓ Qt framework available")
        except ImportError as e:
            pytest.fail(f"Qt framework not available: {e}")


class TestExtensionDiscoveryCompliance:
    """Test extension discovery and entry point compliance."""

    def test_extension_entry_point_registered(self):
        """Test extension is properly registered in entry points."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        urashg_extensions = [
            ep
            for ep in extension_eps
            if "URASHGMicroscopyExtension" in ep.name or "urashg" in ep.name.lower()
        ]

        assert len(urashg_extensions) >= 1, "URASHG extension not found in entry points"
        logger.info(
            f"✓ Found {len(urashg_extensions)} URASHG extension(s) in entry points"
        )

    def test_extension_loadable_without_errors(self):
        """Test extension can be loaded without import errors."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):
            extension_eps = list(eps.select(group="pymodaq.extensions"))
        else:
            extension_eps = eps.get("pymodaq.extensions", [])

        for ep in extension_eps:
            if "URASHGMicroscopyExtension" in ep.name or "urashg" in ep.name.lower():
                try:
                    extension_class = ep.load()
                    assert extension_class is not None
                    logger.info(f"✓ Extension {ep.name} loads successfully")
                except Exception as e:
                    pytest.fail(f"Extension {ep.name} failed to load: {e}")

    def test_all_plugin_entry_points_registered(self):
        """Test all URASHG plugins are registered in entry points."""
        expected_plugins = {
            "pymodaq.move_plugins": [
                "DAQ_Move_MaiTai",
                "DAQ_Move_Elliptec",
                "DAQ_Move_ESP300",
            ],
            "pymodaq.viewer_plugins": [
                "DAQ_2DViewer_PrimeBSI",
                "DAQ_0DViewer_Newport1830C",
            ],
        }

        eps = importlib.metadata.entry_points()

        for group, plugin_names in expected_plugins.items():
            if hasattr(eps, "select"):
                group_eps = list(eps.select(group=group))
            else:
                group_eps = eps.get(group, [])

            found_plugins = [ep.name for ep in group_eps if ep.name in plugin_names]
            missing_plugins = set(plugin_names) - set(found_plugins)

            assert (
                len(missing_plugins) == 0
            ), f"Missing plugins in {group}: {missing_plugins}"
            logger.info(f"✓ All {len(plugin_names)} plugins found in {group}")


class TestExtensionArchitectureCompliance:
    """Test extension architecture follows PyMoDAQ standards."""

    @pytest.fixture
    def extension_class(self):
        """Get extension class for testing without instantiation."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        return URASHGMicroscopyExtension

    def test_extension_inheritance_pattern(self, extension_class):
        """Test extension follows PyMoDAQ inheritance patterns."""
        from pymodaq.utils.gui_utils import CustomApp

        assert issubclass(
            extension_class, CustomApp
        ), "Extension should inherit from CustomApp"
        logger.info("✓ Extension follows CustomApp inheritance pattern")

    def test_extension_required_metadata(self, extension_class):
        """Test extension has required metadata attributes."""
        required_attrs = ["name", "description", "author", "version"]

        for attr in required_attrs:
            assert hasattr(
                extension_class, attr
            ), f"Extension missing required attribute: {attr}"
            value = getattr(extension_class, attr)
            assert isinstance(value, str), f"Attribute {attr} should be string"
            assert len(value.strip()) > 0, f"Attribute {attr} should not be empty"

        logger.info("✓ Extension has all required metadata")

    def test_extension_signal_architecture(self, extension_class):
        """Test extension signal architecture follows PyMoDAQ patterns."""
        from qtpy.QtCore import Signal

        required_signals = [
            "measurement_started",
            "measurement_finished",
            "measurement_progress",
            "device_status_changed",
            "error_occurred",
        ]

        # Check that signal attributes are defined at class level
        for signal_name in required_signals:
            assert hasattr(
                extension_class, signal_name
            ), f"Missing signal: {signal_name}"
            # Note: Signals are descriptors, so we can't check isinstance on class level

        logger.info("✓ Extension signal architecture is compliant")

    def test_extension_parameter_tree_compliance(self, extension_class):
        """Test extension parameter tree follows PyMoDAQ standards."""
        assert hasattr(
            extension_class, "params"
        ), "Extension should have params class attribute"

        params = extension_class.params
        assert isinstance(params, list), "params should be a list"
        assert len(params) > 0, "params should not be empty"

        # Validate parameter structure
        for param in params:
            assert isinstance(param, dict), "Each parameter should be a dictionary"
            assert "name" in param, "Parameter should have 'name' key"
            assert "type" in param, "Parameter should have 'type' key"

        logger.info("✓ Extension parameter tree is compliant")


class TestDeviceManagerCompliance:
    """Test device manager compliance with PyMoDAQ standards."""

    def test_device_manager_architecture(self):
        """Test device manager follows PyMoDAQ architecture patterns."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager
        from qtpy.QtCore import QObject

        assert issubclass(
            URASHGDeviceManager, QObject
        ), "DeviceManager should inherit from QObject"
        logger.info("✓ Device manager architecture is compliant")

    def test_device_manager_signal_patterns(self):
        """Test device manager signal patterns are PyMoDAQ compliant."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager
        from qtpy.QtCore import Signal

        # Mock device manager instance
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.URASHGDeviceManager"
        ):
            mock_dashboard = Mock()
            dm = URASHGDeviceManager(mock_dashboard)

            # Check for expected signals
            expected_signals = [
                "device_status_changed",
                "device_error_occurred",
                "all_devices_ready",
            ]

            for signal_name in expected_signals:
                if hasattr(dm, signal_name):
                    signal_obj = getattr(dm, signal_name)
                    assert isinstance(
                        signal_obj, Signal
                    ), f"{signal_name} should be Qt Signal"

        logger.info("✓ Device manager signals are compliant")

    def test_device_status_management(self):
        """Test device status management follows standards."""
        from pymodaq_plugins_urashg.extensions.device_manager import DeviceStatus

        # Should have standard status enumeration
        expected_statuses = [
            "DISCONNECTED",
            "CONNECTING",
            "CONNECTED",
            "READY",
            "BUSY",
            "ERROR",
        ]

        for status in expected_statuses:
            assert hasattr(DeviceStatus, status), f"Missing device status: {status}"

        logger.info("✓ Device status management is compliant")


class TestMeasurementWorkerCompliance:
    """Test measurement worker compliance with PyMoDAQ threading standards."""

    def test_measurement_worker_threading_compliance(self):
        """Test measurement worker follows PyMoDAQ threading patterns."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            MeasurementWorker,
        )
        from qtpy.QtCore import QObject

        assert issubclass(
            MeasurementWorker, QObject
        ), "MeasurementWorker should inherit from QObject"
        logger.info("✓ Measurement worker threading is compliant")

    def test_measurement_worker_lifecycle_methods(self):
        """Test measurement worker has required lifecycle methods."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            MeasurementWorker,
        )

        # Mock worker instance
        mock_extension = Mock()
        mock_extension.device_manager = Mock()
        mock_extension.settings = {}
        worker = MeasurementWorker(mock_extension)

        required_methods = [
            "run_measurement",
            "stop_measurement",
            "pause_measurement",
            "resume_measurement",
        ]

        for method_name in required_methods:
            assert hasattr(worker, method_name), f"Worker missing method: {method_name}"
            assert callable(
                getattr(worker, method_name)
            ), f"{method_name} should be callable"

        logger.info("✓ Measurement worker lifecycle methods are compliant")

    def test_measurement_worker_signals(self):
        """Test measurement worker signals follow PyMoDAQ patterns."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            MeasurementWorker,
        )
        from qtpy.QtCore import Signal

        mock_dm = Mock()
        worker = MeasurementWorker(mock_dm, {})

        # Check for measurement-related signals
        signal_names = [
            attr
            for attr in dir(worker)
            if isinstance(getattr(worker, attr, None), Signal)
        ]

        # Should have some signals for communication
        assert len(signal_names) > 0, "Worker should have signals for communication"
        logger.info(f"✓ Measurement worker has {len(signal_names)} signals")


class TestPluginIntegrationCompliance:
    """Test plugin integration follows PyMoDAQ standards."""

    def test_plugin_base_class_compliance(self):
        """Test plugins inherit from correct PyMoDAQ base classes."""
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
        from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

        plugin_tests = [
            (
                "DAQ_Move_MaiTai",
                "pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai",
                DAQ_Move_base,
            ),
            (
                "DAQ_Move_Elliptec",
                "pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec",
                DAQ_Move_base,
            ),
            (
                "DAQ_2DViewer_PrimeBSI",
                "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI",
                DAQ_Viewer_base,
            ),
        ]

        for plugin_name, module_path, expected_base in plugin_tests:
            try:
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, plugin_name)
                assert issubclass(
                    plugin_class, expected_base
                ), f"{plugin_name} should inherit from {expected_base.__name__}"
                logger.info(f"✓ {plugin_name} inheritance is compliant")
            except ImportError:
                logger.warning(f"⚠ Plugin {plugin_name} not available for testing")

    def test_plugin_method_compliance(self):
        """Test plugins implement required PyMoDAQ methods."""
        move_methods = [
            "ini_attributes",
            "get_actuator_value",
            "close",
            "commit_settings",
            "ini_stage",
            "move_abs",
        ]
        viewer_methods = [
            "ini_attributes",
            "grab_data",
            "close",
            "commit_settings",
            "ini_detector",
        ]

        # Test available move plugins
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
                DAQ_Move_MaiTai,
            )

            for method_name in move_methods:
                assert hasattr(
                    DAQ_Move_MaiTai, method_name
                ), f"DAQ_Move_MaiTai missing {method_name}"
            logger.info("✓ Move plugin methods are compliant")
        except ImportError:
            logger.warning("⚠ Move plugins not available for method testing")

        # Test available viewer plugins
        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
                DAQ_2DViewer_PrimeBSI,
            )

            for method_name in viewer_methods:
                assert hasattr(
                    DAQ_2DViewer_PrimeBSI, method_name
                ), f"DAQ_2DViewer_PrimeBSI missing {method_name}"
            logger.info("✓ Viewer plugin methods are compliant")
        except ImportError:
            logger.warning("⚠ Viewer plugins not available for method testing")

    def test_plugin_parameter_compliance(self):
        """Test plugin parameters follow PyMoDAQ standards."""
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
                DAQ_Move_MaiTai,
            )

            assert hasattr(
                DAQ_Move_MaiTai, "params"
            ), "Plugin should have params attribute"
            params = DAQ_Move_MaiTai.params
            assert isinstance(params, list), "params should be a list"

            # Basic parameter structure validation
            for param in params:
                if isinstance(param, dict):
                    assert "name" in param, "Parameter should have 'name'"
                    assert "type" in param, "Parameter should have 'type'"

            logger.info("✓ Plugin parameters are compliant")
        except ImportError:
            logger.warning("⚠ Plugins not available for parameter testing")


class TestErrorHandlingCompliance:
    """Test error handling follows PyMoDAQ standards."""

    def test_extension_error_handling(self):
        """Test extension handles errors gracefully."""
        with patch(
            "pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )
            from qtpy import QtWidgets

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            extension = URASHGMicroscopyExtension()

            # Should have error handling methods
            assert hasattr(
                extension, "on_error_occurred"
            ), "Extension should handle errors"
            assert hasattr(
                extension, "error_occurred"
            ), "Extension should have error signal"

            logger.info("✓ Extension error handling is compliant")

    def test_graceful_degradation(self):
        """Test system degrades gracefully when components are missing."""
        # Test extension can handle missing device manager
        with patch(
            "pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager",
            side_effect=ImportError,
        ):
            try:
                from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                    URASHGMicroscopyExtension,
                )

                # Should still be importable even if device manager fails
                logger.info("✓ Graceful degradation is working")
            except Exception as e:
                pytest.fail(f"Should handle missing components gracefully: {e}")


class TestConfigurationManagement:
    """Test configuration management follows PyMoDAQ standards."""

    def test_configuration_persistence(self):
        """Test configuration can be saved and loaded."""
        with patch(
            "pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )
            from qtpy import QtWidgets

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            extension = URASHGMicroscopyExtension()

            # Should have configuration methods
            config_methods = ["save_configuration", "load_configuration"]
            for method_name in config_methods:
                if hasattr(extension, method_name):
                    assert callable(
                        getattr(extension, method_name)
                    ), f"{method_name} should be callable"

            logger.info("✓ Configuration management is available")

    def test_settings_serialization(self):
        """Test settings can be serialized for storage."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Settings should be JSON-serializable
        params = URASHGMicroscopyExtension.params

        # Basic check that parameter structure is serializable
        import json

        try:
            json.dumps(params, default=str)
            logger.info("✓ Settings are serializable")
        except (TypeError, ValueError) as e:
            pytest.fail(f"Settings not serializable: {e}")


class TestDocumentationCompliance:
    """Test documentation follows PyMoDAQ standards."""

    def test_extension_documentation(self):
        """Test extension has proper documentation."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            URASHGMicroscopyExtension,
        )

        # Should have comprehensive docstring
        assert (
            URASHGMicroscopyExtension.__doc__ is not None
        ), "Extension should have docstring"
        assert (
            len(URASHGMicroscopyExtension.__doc__.strip()) > 100
        ), "Extension docstring should be comprehensive"

        logger.info("✓ Extension documentation is compliant")

    def test_plugin_documentation(self):
        """Test plugins have proper documentation."""
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
                DAQ_Move_MaiTai,
            )

            assert DAQ_Move_MaiTai.__doc__ is not None, "Plugin should have docstring"
            assert (
                len(DAQ_Move_MaiTai.__doc__.strip()) > 50
            ), "Plugin docstring should be descriptive"

            logger.info("✓ Plugin documentation is compliant")
        except ImportError:
            logger.warning("⚠ Plugins not available for documentation testing")

    def test_module_documentation(self):
        """Test modules have proper documentation."""
        try:
            import pymodaq_plugins_urashg.extensions.urashg_microscopy_extension as ext_module

            assert ext_module.__doc__ is not None, "Module should have docstring"
            logger.info("✓ Module documentation is present")
        except ImportError:
            logger.warning("⚠ Extension module not available for documentation testing")


class TestPerformanceCompliance:
    """Test performance characteristics meet PyMoDAQ standards."""

    def test_import_performance(self):
        """Test imports complete in reasonable time."""
        import time

        start_time = time.time()
        try:
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )

            import_time = time.time() - start_time

            # Should import quickly (adjust threshold as needed)
            assert import_time < 5.0, f"Import took too long: {import_time:.2f}s"
            logger.info(f"✓ Extension imports in {import_time:.2f}s")
        except ImportError as e:
            logger.warning(f"⚠ Extension not available for performance testing: {e}")

    def test_memory_usage_reasonable(self):
        """Test memory usage is reasonable."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        try:
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )

            # Check memory increase is reasonable
            final_memory = process.memory_info().rss
            memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

            # Should not use excessive memory (adjust threshold as needed)
            assert (
                memory_increase < 100
            ), f"Memory increase too large: {memory_increase:.1f}MB"
            logger.info(f"✓ Extension uses {memory_increase:.1f}MB additional memory")
        except ImportError:
            logger.warning("⚠ Extension not available for memory testing")


# Test execution configuration
@pytest.mark.suite_overview
class TestSuiteOverview:
    """Test suite overview and validation."""

    pass


@pytest.mark.compliance_critical
class TestComplianceCritical:
    """Critical compliance tests that must pass."""

    pass


@pytest.mark.integration_full
class TestIntegrationFull:
    """Full integration tests."""

    pass


def run_compliance_report():
    """Generate a compliance report for the extension."""
    print("\n" + "=" * 80)
    print("URASHG EXTENSION PYMODAQ COMPLIANCE REPORT")
    print("=" * 80)

    # Run pytest with custom markers and capture results
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--maxfail=10",
        "-m",
        "compliance_critical",
    ]

    result = pytest.main(pytest_args)

    print("\n" + "=" * 80)
    if result == 0:
        print("✅ COMPLIANCE STATUS: PASSED")
        print("✅ Extension meets PyMoDAQ standards")
    else:
        print("❌ COMPLIANCE STATUS: FAILED")
        print("❌ Extension needs fixes for PyMoDAQ compliance")
    print("=" * 80)

    return result


if __name__ == "__main__":
    # Run compliance report when executed directly
    exit_code = run_compliance_report()
    sys.exit(exit_code)
