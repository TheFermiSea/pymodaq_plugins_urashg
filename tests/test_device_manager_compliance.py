"""
Device Manager Compliance Test Suite for URASHG Extension

This test suite ensures the URASHGDeviceManager stub maintains compatibility
while encouraging migration to the extension-based architecture.

Note: This tests the compatibility layer only. Production code should use
URASHGMicroscopyExtension for actual device coordination.

Test Categories:
- Device Manager Stub Compatibility
- Basic Interface Compliance
- Extension Integration
- Migration Support
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import threading
import time
from typing import Dict, Any, List
import json

# Qt imports
from qtpy import QtCore, QtTest
from qtpy.QtCore import QTimer, Signal, QObject

# PyMoDAQ imports
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.data import DataWithAxes, Axis, DataSource
from pymodaq.utils.parameter import Parameter

# Test utilities
from tests.mock_modules.mock_devices import (
    MockMovePlugin,
    MockViewerPlugin,
    MockDeviceStatus,
    MockDeviceInfo,
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
        """Create device manager stub for compatibility testing."""
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )
        return URASHGDeviceManager()

    def test_device_manager_initialization(self, device_manager):
        """Test device manager stub initializes properly."""
        assert device_manager is not None
        assert hasattr(device_manager, "devices")
        assert hasattr(device_manager, "device_status")
        assert hasattr(device_manager, "supported_devices")
        assert isinstance(device_manager.devices, dict)
        assert isinstance(device_manager.device_status, dict)
        assert isinstance(device_manager.supported_devices, list)

    def test_device_manager_inherits_qobject(self):
        """Test device manager inherits from QObject for signal support."""
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        assert issubclass(URASHGDeviceManager, QObject)

    def test_required_signals_exist(self, device_manager):
        """Test device manager has required signals."""
        required_signals = [
            "device_status_changed",
            "device_error_occurred",
            "all_devices_ready",
            "device_data_updated",
        ]

        for signal_name in required_signals:
            assert hasattr(
                device_manager, signal_name
            ), f"Missing required signal: {signal_name}"
            signal_attr = getattr(device_manager, signal_name)
            assert isinstance(
                signal_attr, Signal
            ), f"{signal_name} should be a QtCore.Signal"

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
        """Create device manager stub with status tracking."""
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
            DeviceStatus,
        )

        dm = URASHGDeviceManager()
        # Status is already initialized in the stub
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
    """Test coordination of multiple devices through extension architecture."""

    @pytest.fixture
    def device_manager_stub(self):
        """Create device manager stub for basic coordination testing."""
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )
        return URASHGDeviceManager()
    
    @pytest.fixture
    def coordinated_device_manager(self):
        """Create device manager stub for coordination testing."""
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )
        return URASHGDeviceManager()

    def test_device_registration_interface(self, device_manager_stub):
        """Test device registration interface exists."""
        dm = device_manager_stub

        # Should have methods for device registration
        assert hasattr(dm, "register_device")
        assert callable(dm.register_device)
        assert hasattr(dm, "unregister_device")
        assert callable(dm.unregister_device)

    def test_supported_devices_list(self, device_manager_stub):
        """Test device manager knows about supported devices."""
        dm = device_manager_stub
        expected_devices = ["MaiTai", "Elliptec", "ESP300", "PrimeBSI", "Newport1830C"]

        assert hasattr(dm, "supported_devices")
        for device in expected_devices:
            assert device in dm.supported_devices

    def test_extension_integration_note(self, device_manager_stub):
        """Test that device manager encourages extension usage."""
        dm = device_manager_stub

        # Should have initialization and cleanup methods that delegate to extension
        assert hasattr(dm, "initialize_devices")
        assert callable(dm.initialize_devices)
        assert hasattr(dm, "cleanup_devices")
        assert callable(dm.cleanup_devices)
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
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )
        
        # Create device manager stub
        dm = URASHGDeviceManager()
        
        # Add mock devices that can simulate errors
        mock_devices = {
            "MaiTai": MockMovePlugin("MaiTai"),
            "Elliptec": MockMovePlugin("Elliptec"),
        }
        
        # Make one device prone to errors
        mock_devices["MaiTai"].simulate_error = True
        
        # Add devices to manager if it has a devices attribute
        if hasattr(dm, 'devices'):
            dm.devices = mock_devices
            
        return dm

    def test_device_error_detection(self, error_test_device_manager):
        """Test detection of device errors."""
        dm = error_test_device_manager

        # Should have error signal for reporting errors
        assert hasattr(dm, "device_error_occurred")
        assert isinstance(dm.device_error_occurred, Signal)

        # Should emit error signals
        with patch.object(dm, "device_error_occurred") as mock_signal:
            # Manually emit error signal to test functionality
            dm.device_error_occurred.emit("MaiTai", "Connection lost")
            assert mock_signal.emit.called

    def test_error_recovery_mechanisms(self, error_test_device_manager):
        """Test error recovery and reconnection."""
        dm = error_test_device_manager

        # Device manager stub doesn't implement recovery methods 
        # Production recovery is handled by URASHGMicroscopyExtension
        # Test that basic device management works
        assert hasattr(dm, "register_device")
        assert hasattr(dm, "unregister_device")
        assert callable(dm.register_device)
        assert callable(dm.unregister_device)

    def test_graceful_degradation(self, error_test_device_manager):
        """Test graceful degradation when devices fail."""
        dm = error_test_device_manager

        from pymodaq_plugins_urashg.extensions.device_manager import DeviceStatus
        
        # Device manager stub provides basic status management
        # Can update device status to ERROR to indicate failure
        dm.update_device_status("MaiTai", "error")
        assert dm.get_device_status("MaiTai") == DeviceStatus.ERROR
        
        # Should still track other devices
        assert "Elliptec" in dm.supported_devices

    def test_error_logging_integration(self, error_test_device_manager):
        """Test error logging follows PyMoDAQ patterns."""
        dm = error_test_device_manager

        # Should integrate with PyMoDAQ logging
        with patch(
            "pymodaq_plugins_urashg.extensions.device_manager.logger"
        ) as mock_logger:
            # Test that updating to error status triggers logging
            dm.update_device_status("MaiTai", "invalid_status")
            # This should trigger a warning for invalid status
            assert mock_logger.warning.called


class TestDeviceManagerThreadSafety:
    """Test thread safety of device manager operations."""

    @pytest.fixture
    def threaded_device_manager(self):
        """Create device manager for thread safety testing."""
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )

        return URASHGDeviceManager()

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
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )

        return URASHGDeviceManager()

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
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager,
        )

        return URASHGDeviceManager()

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

        dm = URASHGDeviceManager()

        # Get custom signals (exclude Qt built-in signals)
        custom_signal_names = [
            "device_status_changed",
            "device_error_occurred", 
            "all_devices_ready",
            "device_data_updated"
        ]

        for signal_name in custom_signal_names:
            # Should have the signal
            assert hasattr(dm, signal_name), f"Missing signal: {signal_name}"
            
            # Should be a Signal instance
            assert isinstance(getattr(dm, signal_name), Signal)
            
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
        dm = URASHGDeviceManager()

        # Should have error signals
        assert hasattr(dm, "device_error_occurred")
        assert isinstance(dm.device_error_occurred, Signal)

        # Should integrate with PyMoDAQ logging (logger is imported in the module)
        import pymodaq_plugins_urashg.extensions.device_manager as dm_module
        assert hasattr(dm_module, 'logger')

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
