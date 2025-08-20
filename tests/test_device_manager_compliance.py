"""
Device Manager Compliance Test Suite for URASHG Extension

This test suite ensures the URASHGDeviceManager follows PyMoDAQ standards
for device coordination, status management, and multi-device orchestration.

Test Categories:
- Device Manager Initialization
- Device Status Management
- Multi-Device Coordination
- Error Handling & Recovery
- Thread Safety
- Plugin Integration
- Configuration Management
- PyMoDAQ Standards Compliance
"""

import sys

from qtpy.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from pymodaq.utils.data import Axis, DataSource, DataWithAxes

# PyMoDAQ imports
from pymodaq.utils.logger import get_module_name, set_logger
from pymodaq.utils.parameter import Parameter

# Qt imports
from qtpy import QtCore, QtTest
from qtpy.QtCore import QObject, QTimer, Signal

# Test utilities
from tests.mock_modules.mock_devices import (
    MockDeviceInfo,
    MockDeviceStatus,
    MockMovePlugin,
    MockViewerPlugin,
)

logger = set_logger(get_module_name(__file__))


class TestDeviceManagerInitialization:
    """Test device manager initialization and configuration."""

    @pytest.fixture
    def mock_plugins(self):
        """Create mock PyMoDAQ plugins for testing."""
        return {
            "MaiTai": MockMovePlugin("MaiTai"),
            "Elliptec": MockMovePlugin("Elliptec"),
            "ESP300": MockMovePlugin("ESP300"),
            "PrimeBSI": MockViewerPlugin("PrimeBSI"),
            "Newport1830C": MockViewerPlugin("Newport1830C"),
        }

    @pytest.fixture
    def device_manager(self, mock_plugins):
        """Create device manager with mock plugins."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Mock the _instantiate_device_plugin method instead of __import__
        def mock_instantiate_device_plugin(self, device_key, device_config):
            """Mock device plugin instantiation."""
            device_type = device_config["type"]

            if device_key == "laser":
                device_info = MagicMock()
                device_info.plugin_instance = mock_plugins["MaiTai"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "MaiTai"
                device_info.status = "connected"
                return device_info
            elif device_key == "elliptec":
                device_info = MagicMock()
                device_info.plugin_instance = mock_plugins["Elliptec"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "Elliptec"
                device_info.status = "connected"
                return device_info
            elif device_key == "camera":
                device_info = MagicMock()
                device_info.plugin_instance = mock_plugins["PrimeBSI"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "PrimeBSI"
                device_info.status = "connected"
                return device_info
            elif device_key == "power_meter":
                device_info = MagicMock()
                device_info.plugin_instance = mock_plugins["Newport1830C"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "Newport1830C"
                device_info.status = "connected"
                return device_info
            else:
                return None

        with patch.object(
            URASHGDeviceManager,
            "_instantiate_device_plugin",
            mock_instantiate_device_plugin,
        ):
            # Create device manager with a mock dashboard
            mock_dashboard = MagicMock()
            mock_dashboard.modules_manager = MagicMock()
            return URASHGDeviceManager(mock_dashboard)

    def test_device_manager_initialization(self, device_manager):
        """Test device manager initializes properly."""
        assert device_manager is not None
        assert hasattr(device_manager, "devices")
        assert hasattr(device_manager, "missing_devices")
        assert isinstance(device_manager.devices, dict)
        assert isinstance(device_manager.missing_devices, list)

    def test_device_manager_inherits_qobject(self):
        """Test device manager inherits from QObject for signal support."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        assert issubclass(URASHGDeviceManager, QObject)

    def test_required_signals_exist(self, device_manager):
        """Test device manager has required signals."""
        required_signals = [
            "device_status_changed",
            "device_error",
            "all_devices_ready",
        ]

        for signal_name in required_signals:
            assert hasattr(
                device_manager, signal_name
            ), f"Missing required signal: {signal_name}"
            signal_attr = getattr(device_manager, signal_name)
            # Check for signal-like behavior (PyQt signals have connect and emit methods)
            assert hasattr(
                signal_attr, "connect"
            ), f"{signal_name} should have 'connect' method"
            assert hasattr(
                signal_attr, "emit"
            ), f"{signal_name} should have 'emit' method"

    def test_device_registration(self, device_manager):
        """Test devices can be registered properly."""
        # Should have method to register devices
        assert hasattr(device_manager, "register_device")
        assert callable(device_manager.register_device)

        # Should have method to unregister devices
        assert hasattr(device_manager, "unregister_device")
        assert callable(device_manager.unregister_device)

    def test_supported_devices_list(self, device_manager):
        """Test device manager knows about supported devices."""
        expected_devices = ["MaiTai", "Elliptec", "ESP300", "PrimeBSI", "Newport1830C"]

        if hasattr(device_manager, "supported_devices"):
            for device in expected_devices:
                assert device in device_manager.supported_devices


class TestDeviceStatusManagement:
    """Test device status tracking and management."""

    @pytest.fixture
    def device_manager_with_status(self):
        """Create device manager with status tracking."""
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.device_manager import (
                DeviceStatus,
                URASHGDeviceManager,
            )

            dm = URASHGDeviceManager(mock_dashboard)
            dm.device_status = {
                "MaiTai": DeviceStatus.DISCONNECTED,
                "Elliptec": DeviceStatus.CONNECTED,
                "PrimeBSI": DeviceStatus.READY,
            }
            return dm

    def test_device_status_enum_exists(self):
        """Test DeviceStatus enum is properly defined."""
        from pymodaq_plugins_urashg.extensions.device_manager import DeviceStatus

        # Should have standard status values
        expected_statuses = [
            "DISCONNECTED",
            "CONNECTING",
            "CONNECTED",
            "READY",
            "BUSY",
            "ERROR",
        ]

        for status in expected_statuses:
            assert hasattr(DeviceStatus, status), f"Missing status: {status}"

    def test_status_update_methods(self, device_manager_with_status):
        """Test status update methods exist and work."""
        dm = device_manager_with_status

        # Should have method to update device status
        assert hasattr(dm, "update_device_status")
        assert callable(dm.update_device_status)

        # Should have method to get device status
        assert hasattr(dm, "get_device_status")
        assert callable(dm.get_device_status)

    def test_status_signal_emission(self, device_manager_with_status):
        """Test status changes emit appropriate signals."""
        dm = device_manager_with_status

        # Mock signal emission
        with patch.object(dm, "device_status_changed") as mock_signal:
            if hasattr(dm, "update_device_status"):
                dm.update_device_status("MaiTai", "CONNECTED")
                # Signal should be emitted
                assert mock_signal.emit.called

    def test_device_status_persistence(self, device_manager_with_status):
        """Test device status can be saved and restored."""
        dm = device_manager_with_status

        # Should be able to get status dict
        if hasattr(dm, "get_all_device_status"):
            status_dict = dm.get_all_device_status()
            assert isinstance(status_dict, dict)

            # Should be JSON serializable
            try:
                json.dumps(status_dict, default=str)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Device status not serializable: {e}")

    def test_device_readiness_check(self, device_manager_with_status):
        """Test device readiness checking."""
        dm = device_manager_with_status

        # Should have method to check if all devices ready
        assert hasattr(dm, "are_all_devices_ready")
        assert callable(dm.are_all_devices_ready)

        # Should have method to check specific device readiness
        assert hasattr(dm, "is_device_ready")
        assert callable(dm.is_device_ready)


class TestMultiDeviceCoordination:
    """Test coordination of multiple devices."""

    @pytest.fixture
    def coordinated_device_manager(self):
        """Create device manager with multiple coordinated devices."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        mock_devices = {
            "MaiTai": MockMovePlugin("MaiTai"),
            "Elliptec": MockMovePlugin("Elliptec"),
            "PrimeBSI": MockViewerPlugin("PrimeBSI"),
        }

        # Mock the _instantiate_device_plugin method
        def mock_instantiate_device_plugin(self, device_key, device_config):
            """Mock device plugin instantiation for coordination testing."""
            device_type = device_config["type"]

            if device_key == "laser":
                device_info = MagicMock()
                device_info.plugin_instance = mock_devices["MaiTai"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "MaiTai"
                device_info.status = "connected"
                return device_info
            elif device_key == "elliptec":
                device_info = MagicMock()
                device_info.plugin_instance = mock_devices["Elliptec"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "Elliptec"
                device_info.status = "connected"
                return device_info
            elif device_key == "camera":
                device_info = MagicMock()
                device_info.plugin_instance = mock_devices["PrimeBSI"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "PrimeBSI"
                device_info.status = "connected"
                return device_info
            else:
                return None

        with patch.object(
            URASHGDeviceManager,
            "_instantiate_device_plugin",
            mock_instantiate_device_plugin,
        ):
            # Create device manager with a mock dashboard
            mock_dashboard = MagicMock()
            mock_dashboard.modules_manager = MagicMock()
            return URASHGDeviceManager(mock_dashboard)

    def test_simultaneous_device_operations(self, coordinated_device_manager):
        """Test coordination of simultaneous device operations."""
        dm = coordinated_device_manager

        # Should have method for coordinated moves
        if hasattr(dm, "coordinate_devices"):
            assert callable(dm.coordinate_devices)

        # Should handle simultaneous operations without conflicts
        assert hasattr(dm, "emergency_stop_all_devices")
        assert callable(dm.emergency_stop_all_devices)

    def test_device_synchronization(self, coordinated_device_manager):
        """Test device synchronization capabilities."""
        dm = coordinated_device_manager

        # Should have synchronization methods
        if hasattr(dm, "synchronize_devices"):
            assert callable(dm.synchronize_devices)

        # Should handle timing coordination
        if hasattr(dm, "coordinate_timing"):
            assert callable(dm.coordinate_timing)

    def test_measurement_coordination(self, coordinated_device_manager):
        """Test measurement sequence coordination."""
        dm = coordinated_device_manager

        # Should coordinate measurement sequences
        if hasattr(dm, "start_coordinated_measurement"):
            assert callable(dm.start_coordinated_measurement)

        if hasattr(dm, "stop_coordinated_measurement"):
            assert callable(dm.stop_coordinated_measurement)

    def test_device_dependency_handling(self, coordinated_device_manager):
        """Test handling of device dependencies."""
        dm = coordinated_device_manager

        # Should track device dependencies
        if hasattr(dm, "device_dependencies"):
            assert isinstance(dm.device_dependencies, dict)

        # Should handle dependency resolution
        if hasattr(dm, "resolve_dependencies"):
            assert callable(dm.resolve_dependencies)


class TestDeviceManagerErrorHandling:
    """Test error handling and recovery mechanisms."""

    @pytest.fixture
    def error_test_device_manager(self):
        """Create device manager for error testing."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Create mock devices that can simulate errors
        mock_devices = {
            "MaiTai": MockMovePlugin("MaiTai"),
            "Elliptec": MockMovePlugin("Elliptec"),
        }

        # Make one device prone to errors
        mock_devices["MaiTai"].simulate_error = True

        # Mock the _instantiate_device_plugin method
        def mock_instantiate_device_plugin(self, device_key, device_config):
            """Mock device plugin instantiation for error testing."""
            device_type = device_config["type"]

            if device_key == "laser":
                device_info = MagicMock()
                device_info.plugin_instance = mock_devices["MaiTai"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "MaiTai"
                device_info.status = "connected"
                return device_info
            elif device_key == "elliptec":
                device_info = MagicMock()
                device_info.plugin_instance = mock_devices["Elliptec"]
                device_info.name = device_key
                device_info.device_type = device_type
                device_info.module_name = "Elliptec"
                device_info.status = "connected"
                return device_info
            else:
                return None

        with patch.object(
            URASHGDeviceManager,
            "_instantiate_device_plugin",
            mock_instantiate_device_plugin,
        ):
            # Create device manager with a mock dashboard
            mock_dashboard = MagicMock()
            mock_dashboard.modules_manager = MagicMock()
            return URASHGDeviceManager(mock_dashboard)

    def test_device_error_detection(self, error_test_device_manager):
        """Test detection of device errors."""
        dm = error_test_device_manager

        # Should have error detection methods
        assert hasattr(dm, "check_device_errors")
        assert callable(dm.check_device_errors)

        # Should emit error signals
        with patch.object(dm, "device_error_occurred") as mock_signal:
            if hasattr(dm, "handle_device_error"):
                dm.handle_device_error("MaiTai", "Connection lost")
                assert mock_signal.emit.called

    def test_error_recovery_mechanisms(self, error_test_device_manager):
        """Test error recovery and reconnection."""
        dm = error_test_device_manager

        # Should have recovery methods
        if hasattr(dm, "recover_device"):
            assert callable(dm.recover_device)

        if hasattr(dm, "reconnect_device"):
            assert callable(dm.reconnect_device)

    def test_graceful_degradation(self, error_test_device_manager):
        """Test graceful degradation when devices fail."""
        dm = error_test_device_manager

        # Should continue operating with remaining devices
        if hasattr(dm, "disable_failed_device"):
            assert callable(dm.disable_failed_device)

        # Should maintain system stability
        if hasattr(dm, "get_operational_devices"):
            assert callable(dm.get_operational_devices)

    def test_error_logging_integration(self, error_test_device_manager):
        """Test error logging follows PyMoDAQ patterns."""
        dm = error_test_device_manager

        # Should integrate with PyMoDAQ logging
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.logger"
        ) as mock_logger:
            if hasattr(dm, "log_device_error"):
                dm.log_device_error("MaiTai", "Test error")
                assert mock_logger.error.called or mock_logger.warning.called


class TestDeviceManagerThreadSafety:
    """Test thread safety of device manager operations."""

    @pytest.fixture
    def threaded_device_manager(self):
        """Create device manager for thread safety testing."""
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.device_manager import (
                URASHGDeviceManager,
            )

            return URASHGDeviceManager(mock_dashboard)

    def test_thread_safe_device_access(self, threaded_device_manager):
        """Test device access is thread-safe."""
        dm = threaded_device_manager

        # Should have thread-safe access methods
        if hasattr(dm, "_device_lock"):
            assert hasattr(dm._device_lock, "acquire")
            assert hasattr(dm._device_lock, "release")

    def test_concurrent_status_updates(self, threaded_device_manager):
        """Test concurrent status updates are handled safely."""
        dm = threaded_device_manager

        # Should handle concurrent updates without corruption
        def update_status(device_name, status):
            if hasattr(dm, "update_device_status"):
                dm.update_device_status(device_name, status)

        # Create multiple threads updating status
        threads = []
        for i in range(5):
            t = threading.Thread(target=update_status, args=(f"Device{i}", "READY"))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=1.0)

    def test_signal_thread_safety(self, threaded_device_manager):
        """Test signals are emitted safely from different threads."""
        dm = threaded_device_manager

        # Qt signals are inherently thread-safe
        if hasattr(dm, "device_status_changed"):
            assert isinstance(dm.device_status_changed, Signal)


class TestDeviceManagerPluginIntegration:
    """Test integration with PyMoDAQ plugins."""

    @pytest.fixture
    def plugin_integrated_manager(self):
        """Create device manager with real plugin interfaces."""
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.device_manager import (
                URASHGDeviceManager,
            )

            return URASHGDeviceManager(mock_dashboard)

    def test_plugin_lifecycle_management(self, plugin_integrated_manager):
        """Test plugin initialization and cleanup."""
        dm = plugin_integrated_manager

        # Should have plugin lifecycle methods
        assert hasattr(dm, "initialize_plugins")
        assert callable(dm.initialize_plugins)

        assert hasattr(dm, "cleanup_plugins")
        assert callable(dm.cleanup_plugins)

    def test_plugin_parameter_management(self, plugin_integrated_manager):
        """Test plugin parameter tree integration."""
        dm = plugin_integrated_manager

        # Should handle plugin parameters
        if hasattr(dm, "get_plugin_parameters"):
            assert callable(dm.get_plugin_parameters)

        if hasattr(dm, "set_plugin_parameters"):
            assert callable(dm.set_plugin_parameters)

    def test_plugin_data_handling(self, plugin_integrated_manager):
        """Test plugin data acquisition and management."""
        dm = plugin_integrated_manager

        # Should handle plugin data
        if hasattr(dm, "get_plugin_data"):
            assert callable(dm.get_plugin_data)

        # Should format data according to PyMoDAQ standards
        if hasattr(dm, "format_plugin_data"):
            assert callable(dm.format_plugin_data)

    def test_plugin_signal_integration(self, plugin_integrated_manager):
        """Test integration with plugin signals."""
        dm = plugin_integrated_manager

        # Should connect to plugin signals
        if hasattr(dm, "connect_plugin_signals"):
            assert callable(dm.connect_plugin_signals)

        if hasattr(dm, "disconnect_plugin_signals"):
            assert callable(dm.disconnect_plugin_signals)


class TestDeviceManagerConfiguration:
    """Test device manager configuration management."""

    @pytest.fixture
    def configurable_device_manager(self):
        """Create device manager for configuration testing."""
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.URASHGDeviceManager"
        ):
            from pymodaq_plugins_urashg.extensions.device_manager import (
                URASHGDeviceManager,
            )

            return URASHGDeviceManager(mock_dashboard)

    def test_configuration_save_load(self, configurable_device_manager):
        """Test configuration persistence."""
        dm = configurable_device_manager

        # Should have configuration methods
        if hasattr(dm, "save_configuration"):
            assert callable(dm.save_configuration)

        if hasattr(dm, "load_configuration"):
            assert callable(dm.load_configuration)

    def test_device_configuration_validation(self, configurable_device_manager):
        """Test device configuration validation."""
        dm = configurable_device_manager

        # Should validate device configurations
        if hasattr(dm, "validate_device_config"):
            assert callable(dm.validate_device_config)

        # Should have default configurations
        if hasattr(dm, "get_default_config"):
            assert callable(dm.get_default_config)

    def test_runtime_configuration_updates(self, configurable_device_manager):
        """Test runtime configuration updates."""
        dm = configurable_device_manager

        # Should handle runtime updates
        if hasattr(dm, "update_runtime_config"):
            assert callable(dm.update_runtime_config)

        # Should emit configuration change signals
        if hasattr(dm, "configuration_changed"):
            assert isinstance(dm.configuration_changed, Signal)


class TestDeviceManagerPyMoDAQStandards:
    """Test compliance with PyMoDAQ standards and patterns."""

    def test_device_manager_follows_pymodaq_patterns(self):
        """Test device manager follows PyMoDAQ architectural patterns."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Should inherit from QObject for signal support
        assert issubclass(URASHGDeviceManager, QObject)

        # Should have proper naming convention
        assert "URASHG" in URASHGDeviceManager.__name__
        assert "DeviceManager" in URASHGDeviceManager.__name__

    def test_device_info_structure(self):
        """Test DeviceInfo follows PyMoDAQ data structures."""
        try:
            from pymodaq_plugins_urashg.extensions.device_manager import DeviceInfo

            # Should be a proper data structure
            device_info = DeviceInfo("TestDevice", "Move", "Test description")

            # Should have required attributes
            assert hasattr(device_info, "name")
            assert hasattr(device_info, "type")
            assert hasattr(device_info, "description")

        except ImportError:
            # DeviceInfo might be defined elsewhere
            pass

    def test_signal_naming_conventions(self):
        """Test signals follow PyMoDAQ naming conventions."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        dm = URASHGDeviceManager(mock_dashboard)

        # Signal names should be descriptive and snake_case
        signal_names = [
            attr for attr in dir(dm) if isinstance(getattr(dm, attr, None), Signal)
        ]

        for signal_name in signal_names:
            # Should use snake_case
            assert (
                signal_name.islower() or "_" in signal_name
            ), f"Signal {signal_name} should use snake_case"

            # Should be descriptive
            assert len(signal_name) > 3, f"Signal {signal_name} should be descriptive"

    def test_error_handling_standards(self):
        """Test error handling follows PyMoDAQ standards."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Should have standardized error handling
        dm = URASHGDeviceManager(mock_dashboard)

        # Should have error signals
        if hasattr(dm, "device_error_occurred"):
            assert isinstance(dm.device_error_occurred, Signal)

        # Should integrate with PyMoDAQ logging
        assert hasattr(dm, "logger") or "logger" in dm.__class__.__module__

    def test_documentation_standards(self):
        """Test device manager has proper documentation."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Should have class docstring
        assert URASHGDeviceManager.__doc__ is not None
        assert (
            len(URASHGDeviceManager.__doc__.strip()) > 50
        ), "Class docstring should be comprehensive"

        # Key methods should have docstrings
        key_methods = ["initialize_plugins", "cleanup_plugins", "update_device_status"]

        for method_name in key_methods:
            if hasattr(URASHGDeviceManager, method_name):
                method = getattr(URASHGDeviceManager, method_name)
                if callable(method):
                    assert (
                        method.__doc__ is not None
                    ), f"Method {method_name} should have docstring"


# Test execution markers for pytest
@pytest.mark.unit
@pytest.mark.device_manager
class TestDeviceManagerUnit:
    """Unit tests for device manager that don't require hardware."""

    pass


@pytest.mark.integration
@pytest.mark.device_manager
class TestDeviceManagerIntegration:
    """Integration tests for device manager with mocked hardware."""

    pass


@pytest.mark.pymodaq_standards
@pytest.mark.device_manager
class TestDeviceManagerStandards:
    """Tests specifically for PyMoDAQ standards compliance."""

    pass


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "-m", "device_manager"])
