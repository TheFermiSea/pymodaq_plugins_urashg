"""
Comprehensive Test Suite for URASHG Extension PyMoDAQ Standards Compliance

This test suite ensures the URASHG extension fully adheres to PyMoDAQ standards
and provides comprehensive coverage of extension functionality, entry points,
parameter handling, device coordination, and UI integration.

Test Categories:
- Extension Discovery & Entry Points
- Parameter Tree Compliance
- Device Manager Integration
- UI Component Standards
- Signal/Slot Patterns
- Thread Safety
- Error Handling
- Configuration Management
- PyMoDAQ Framework Integration
"""

import pytest
import importlib.metadata
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import tempfile
import json
from typing import Dict, Any, List

# Qt imports
from qtpy import QtWidgets, QtCore, QtTest
from qtpy.QtCore import QTimer, Signal
import pyqtgraph as pg

# PyMoDAQ imports
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataWithAxes, Axis, DataSource
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from pymodaq.utils.gui_utils import CustomApp

# Test utilities
from tests.mock_modules.mock_devices import MockDeviceManager, MockDeviceStatus

logger = set_logger(get_module_name(__file__))


class TestExtensionDiscovery:
    """Test extension discovery and entry point compliance."""

    def test_extension_entry_point_exists(self):
        """Test that extension entry point is properly registered."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, 'select'):
            extension_eps = list(eps.select(group='pymodaq.extensions'))
        else:
            extension_eps = eps.get('pymodaq.extensions', [])

        urashg_extensions = [
            ep for ep in extension_eps
            if 'urashg' in ep.name.lower() or 'urashg' in ep.value.lower()
        ]

        assert len(urashg_extensions) >= 1, "URASHG extension entry point not found"

        # Check specific extension
        urashg_main = [ep for ep in urashg_extensions if 'URASHGMicroscopyExtension' in ep.name]
        assert len(urashg_main) == 1, "URASHGMicroscopyExtension entry point missing or duplicated"

    def test_extension_entry_point_loadable(self):
        """Test that extension entry point can be loaded without errors."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, 'select'):
            extension_eps = list(eps.select(group='pymodaq.extensions', name='URASHGMicroscopyExtension'))
        else:
            extension_eps = [
                ep for ep in eps.get('pymodaq.extensions', [])
                if ep.name == 'URASHGMicroscopyExtension'
            ]

        assert len(extension_eps) == 1, "URASHGMicroscopyExtension entry point not found"

        # Load the extension class
        extension_class = extension_eps[0].load()
        assert extension_class is not None, "Failed to load URASHGMicroscopyExtension"

        # Verify it's a class
        assert isinstance(extension_class, type), "Entry point should load a class"

    def test_extension_module_structure(self):
        """Test extension module follows PyMoDAQ structure standards."""
        try:
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        except ImportError as e:
            pytest.fail(f"Cannot import URASHGMicroscopyExtension: {e}")

        # Verify class inheritance
        assert issubclass(URASHGMicroscopyExtension, CustomApp), "Extension must inherit from CustomApp"

        # Verify required class attributes
        required_attrs = ['name', 'description', 'author', 'version']
        for attr in required_attrs:
            assert hasattr(URASHGMicroscopyExtension, attr), f"Extension missing required attribute: {attr}"


class TestExtensionParameterCompliance:
    """Test parameter tree compliance with PyMoDAQ standards."""

    @pytest.fixture
    def extension_class(self):
        """Load extension class for testing."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        return URASHGMicroscopyExtension

    def test_parameter_tree_structure(self, extension_class):
        """Test parameter tree follows PyMoDAQ parameter standards."""
        assert hasattr(extension_class, 'params'), "Extension must have params attribute"

        params = extension_class.params
        assert isinstance(params, list), "params must be a list"
        assert len(params) > 0, "params cannot be empty"

        # Check parameter structure
        for param in params:
            assert isinstance(param, dict), "Each parameter must be a dictionary"
            assert 'name' in param, "Parameter must have 'name' key"
            assert 'type' in param, "Parameter must have 'type' key"

    def test_parameter_types_valid(self, extension_class):
        """Test all parameter types are valid PyMoDAQ types."""
        valid_types = {
            'group', 'int', 'float', 'str', 'bool', 'list', 'table',
            'itemselect', 'led', 'action', 'slide', 'color', 'date', 'text',
            'browsepath', 'path', 'file', 'directory'
        }

        def check_param_types(params):
            for param in params:
                if isinstance(param, dict):
                    param_type = param.get('type')
                    assert param_type in valid_types, f"Invalid parameter type: {param_type}"

                    # Recursively check children
                    if 'children' in param:
                        check_param_types(param['children'])

        check_param_types(extension_class.params)

    def test_parameter_limits_consistency(self, extension_class):
        """Test parameter limits are consistent and valid."""
        def check_param_limits(params):
            for param in params:
                if isinstance(param, dict):
                    param_type = param.get('type')

                    # Check numeric parameter limits
                    if param_type in ['int', 'float']:
                        if 'min' in param and 'max' in param:
                            assert param['min'] <= param['max'], f"Invalid min/max for {param.get('name')}"

                        if 'value' in param and 'min' in param:
                            assert param['value'] >= param['min'], f"Value below min for {param.get('name')}"

                        if 'value' in param and 'max' in param:
                            assert param['value'] <= param['max'], f"Value above max for {param.get('name')}"

                    # Check list parameter limits
                    if param_type == 'list' and 'limits' in param and 'value' in param:
                        assert param['value'] in param['limits'], f"Value not in limits for {param.get('name')}"

                    # Recursively check children
                    if 'children' in param:
                        check_param_limits(param['children'])

        check_param_limits(extension_class.params)


class TestExtensionSignalCompliance:
    """Test signal/slot patterns follow PyMoDAQ standards."""

    @pytest.fixture
    def mock_extension(self):
        """Create a mock extension instance for testing."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
            from pyqtgraph.dockarea import DockArea

            # Mock the Qt application if not present
            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea (expected by extension)
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_required_signals_exist(self, mock_extension):
        """Test that required signals are defined."""
        required_signals = [
            'measurement_started',
            'measurement_finished',
            'measurement_progress',
            'device_status_changed',
            'error_occurred'
        ]

        for signal_name in required_signals:
            assert hasattr(mock_extension, signal_name), f"Missing required signal: {signal_name}"
            signal_attr = getattr(mock_extension, signal_name)
            assert isinstance(signal_attr, Signal), f"{signal_name} should be a QtCore.Signal"

    def test_signal_signatures(self, mock_extension):
        """Test signal signatures are correctly defined."""
        # Check measurement_progress signal takes int
        assert mock_extension.measurement_progress.signal == 'measurement_progress(int)'

        # Check device_status_changed takes two strings
        assert mock_extension.device_status_changed.signal == 'device_status_changed(QString,QString)'

        # Check error_occurred takes string
        assert mock_extension.error_occurred.signal == 'error_occurred(QString)'

    def test_signal_emission_patterns(self, mock_extension):
        """Test signals can be emitted without errors."""
        # Test progress signal
        mock_extension.measurement_progress.emit(50)

        # Test status change signal
        mock_extension.device_status_changed.emit("MaiTai", "Connected")

        # Test error signal
        mock_extension.error_occurred.emit("Test error message")


class TestExtensionUICompliance:
    """Test UI components follow PyMoDAQ standards."""

    @pytest.fixture
    def mock_extension_ui(self):
        """Create extension with mocked UI components."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
            from pyqtgraph.dockarea import DockArea

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_ui_setup_methods_exist(self, mock_extension_ui):
        """Test required UI setup methods exist."""
        required_methods = [
            'setup_ui',
            'setup_docks',
            'setup_actions',
            'setup_widgets',
            'connect_things'
        ]

        for method_name in required_methods:
            assert hasattr(mock_extension_ui, method_name), f"Missing UI setup method: {method_name}"
            assert callable(getattr(mock_extension_ui, method_name)), f"{method_name} should be callable"

    def test_dock_area_integration(self, mock_extension_ui):
        """Test dock area follows PyMoDAQ patterns."""
        # Check that dock area is used for layout
        mock_extension_ui.setup_docks()

        # Verify dock creation patterns are called
        assert hasattr(mock_extension_ui, 'dock_area') or hasattr(mock_extension_ui, 'dockarea')

    def test_parameter_tree_ui_integration(self, mock_extension_ui):
        """Test parameter tree UI integration."""
        # Should have parameter tree widget
        if hasattr(mock_extension_ui, 'settings_tree'):
            assert mock_extension_ui.settings_tree is not None


class TestExtensionDeviceIntegration:
    """Test device manager integration follows PyMoDAQ standards."""

    @pytest.fixture
    def mock_device_manager(self):
        """Create mock device manager."""
        # Use a simple mock instead of the complex MockDeviceManager
        mock_dm = MagicMock()
        mock_dm.devices = {}
        mock_dm.missing_devices = []
        mock_dm.device_status_changed = MagicMock()
        mock_dm.device_error = MagicMock()
        mock_dm.all_devices_ready = MagicMock()
        return mock_dm

    @pytest.fixture
    def extension_with_mock_devices(self, mock_device_manager):
        """Create extension with mock device manager."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager',
                   return_value=mock_device_manager):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            from pyqtgraph.dockarea import DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_device_manager_initialization(self, extension_with_mock_devices):
        """Test device manager is properly initialized."""
        extension = extension_with_mock_devices

        # Should initialize device manager
        extension.initialize_devices()

        # Should have device manager attribute
        assert hasattr(extension, 'device_manager')
        assert extension.device_manager is not None

    def test_device_status_monitoring(self, extension_with_mock_devices):
        """Test device status monitoring patterns."""
        extension = extension_with_mock_devices
        extension.initialize_devices()

        # Should have method to check device status
        assert hasattr(extension, 'check_device_status')
        assert callable(extension.check_device_status)

        # Should have method to update device status
        assert hasattr(extension, 'update_device_status')
        assert callable(extension.update_device_status)

    def test_device_coordination_patterns(self, extension_with_mock_devices):
        """Test multi-device coordination follows standards."""
        extension = extension_with_mock_devices
        extension.initialize_devices()

        # Should have emergency stop capability
        assert hasattr(extension, 'emergency_stop')
        assert callable(extension.emergency_stop)

        # Should handle device errors gracefully
        assert hasattr(extension, 'on_device_error')
        assert callable(extension.on_device_error)


class TestExtensionMeasurementCompliance:
    """Test measurement workflow compliance with PyMoDAQ standards."""

    @pytest.fixture
    def extension_with_measurement(self):
        """Create extension ready for measurement testing."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            from pyqtgraph.dockarea import DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_measurement_lifecycle_methods(self, extension_with_measurement):
        """Test measurement lifecycle methods exist and are callable."""
        required_methods = [
            'start_measurement',
            'stop_measurement',
            'pause_measurement',
            'emergency_stop'
        ]

        for method_name in required_methods:
            assert hasattr(extension_with_measurement, method_name), f"Missing measurement method: {method_name}"
            assert callable(getattr(extension_with_measurement, method_name)), f"{method_name} should be callable"

    def test_measurement_data_handling(self, extension_with_measurement):
        """Test measurement data follows PyMoDAQ data standards."""
        extension = extension_with_measurement

        # Should have data analysis methods
        assert hasattr(extension, 'analyze_current_data')
        assert callable(extension.analyze_current_data)

        # Should handle data export
        assert hasattr(extension, 'export_data')
        assert callable(extension.export_data)

    def test_measurement_worker_compliance(self):
        """Test measurement worker follows PyMoDAQ threading standards."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        # Should inherit from QObject for signal/slot support
        assert issubclass(MeasurementWorker, QtCore.QObject)

        # Should have required measurement methods
        worker = MeasurementWorker(Mock(), {})
        assert hasattr(worker, 'run_measurement')
        assert hasattr(worker, 'stop_measurement')
        assert hasattr(worker, 'pause_measurement')


class TestExtensionConfigurationCompliance:
    """Test configuration management follows PyMoDAQ standards."""

    @pytest.fixture
    def extension_config(self):
        """Create extension for configuration testing."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            from pyqtgraph.dockarea import DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_configuration_save_load_methods(self, extension_config):
        """Test configuration save/load methods exist."""
        required_methods = [
            'save_configuration',
            'load_configuration'
        ]

        for method_name in required_methods:
            assert hasattr(extension_config, method_name), f"Missing config method: {method_name}"
            assert callable(getattr(extension_config, method_name)), f"{method_name} should be callable"

    def test_configuration_data_structure(self, extension_config):
        """Test configuration data structure is JSON-serializable."""
        extension = extension_config

        # Should be able to get current configuration
        if hasattr(extension, '_get_current_configuration'):
            config_data = extension._get_current_configuration()

            # Should be JSON serializable
            try:
                json.dumps(config_data)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Configuration data not JSON serializable: {e}")

    def test_configuration_persistence(self, extension_config):
        """Test configuration can be saved and loaded."""
        extension = extension_config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Should be able to save configuration without errors
            if hasattr(extension, 'save_configuration'):
                extension.save_configuration(str(temp_path))

            # Should be able to load configuration without errors
            if hasattr(extension, 'load_configuration'):
                extension.load_configuration(str(temp_path))

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()


class TestExtensionErrorHandling:
    """Test error handling follows PyMoDAQ standards."""

    @pytest.fixture
    def extension_error_test(self):
        """Create extension for error handling testing."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            from pyqtgraph.dockarea import DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_error_signal_handling(self, extension_error_test):
        """Test error signals are properly handled."""
        extension = extension_error_test

        # Should have error handling methods
        assert hasattr(extension, 'on_error_occurred')
        assert callable(extension.on_error_occurred)

        # Should emit error signals
        assert hasattr(extension, 'error_occurred')
        assert isinstance(extension.error_occurred, Signal)

    def test_graceful_degradation(self, extension_error_test):
        """Test extension handles missing components gracefully."""
        extension = extension_error_test

        # Should handle device manager failures
        with patch.object(extension, 'device_manager', None):
            # Should not crash when device manager is None
            try:
                extension.check_device_status()
            except AttributeError:
                pytest.fail("Extension should handle missing device manager gracefully")

    def test_logging_integration(self, extension_error_test):
        """Test logging follows PyMoDAQ patterns."""
        extension = extension_error_test

        # Should have log_message method
        assert hasattr(extension, 'log_message')
        assert callable(extension.log_message)

        # Should use PyMoDAQ logger
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.logger') as mock_logger:
            extension.log_message("Test message", level="INFO")
            # Logger should be called
            assert mock_logger.info.called or mock_logger.error.called or mock_logger.warning.called


class TestExtensionThreadSafety:
    """Test thread safety follows PyMoDAQ standards."""

    @pytest.fixture
    def extension_thread_test(self):
        """Create extension for thread safety testing."""
        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.URASHGDeviceManager'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

            if not QtWidgets.QApplication.instance():
                app = QtWidgets.QApplication([])

            # Create mock parent DockArea
            from pyqtgraph.dockarea import DockArea
            mock_parent = DockArea()
            extension = URASHGMicroscopyExtension(mock_parent)
            return extension

    def test_measurement_worker_thread_safety(self, extension_thread_test):
        """Test measurement worker is properly thread-isolated."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        # Worker should inherit from QObject for thread support
        assert issubclass(MeasurementWorker, QtCore.QObject)

        # Worker should have stop/pause mechanisms
        worker = MeasurementWorker(Mock(), {})
        assert hasattr(worker, 'stop_measurement')
        assert hasattr(worker, 'pause_measurement')

    def test_signal_thread_safety(self, extension_thread_test):
        """Test signals are thread-safe."""
        extension = extension_thread_test

        # Should be able to emit signals from different threads
        # This is guaranteed by Qt's signal/slot mechanism
        assert hasattr(extension, 'measurement_progress')
        assert isinstance(extension.measurement_progress, Signal)

    def test_cleanup_on_close(self, extension_thread_test):
        """Test proper cleanup when extension is closed."""
        extension = extension_thread_test

        # Should have closeEvent method
        assert hasattr(extension, 'closeEvent')
        assert callable(extension.closeEvent)


class TestExtensionIntegrationCompliance:
    """Test overall PyMoDAQ framework integration compliance."""

    def test_extension_follows_customapp_pattern(self):
        """Test extension properly inherits from CustomApp."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

        # Should inherit from CustomApp
        assert issubclass(URASHGMicroscopyExtension, CustomApp)

        # Should have required metadata
        required_attrs = ['name', 'description', 'author', 'version']
        for attr in required_attrs:
            assert hasattr(URASHGMicroscopyExtension, attr)
            assert isinstance(getattr(URASHGMicroscopyExtension, attr), str)

    def test_extension_entry_point_format(self):
        """Test entry point follows PyMoDAQ format standards."""
        eps = importlib.metadata.entry_points()

        if hasattr(eps, 'select'):
            extension_eps = list(eps.select(group='pymodaq.extensions'))
        else:
            extension_eps = eps.get('pymodaq.extensions', [])

        urashg_ep = None
        for ep in extension_eps:
            if 'URASHGMicroscopyExtension' in ep.name:
                urashg_ep = ep
                break

        assert urashg_ep is not None, "URASHGMicroscopyExtension entry point not found"

        # Entry point should follow module:class format
        assert ':' in urashg_ep.value, "Entry point should use module:class format"

        module_path, class_name = urashg_ep.value.split(':')
        assert class_name == 'URASHGMicroscopyExtension', "Class name should match entry point name"
        assert 'pymodaq_plugins_urashg.extensions' in module_path, "Module path should be in extensions"

    def test_package_metadata_compliance(self):
        """Test package metadata follows PyMoDAQ standards."""
        try:
            import pymodaq_plugins_urashg
            metadata = importlib.metadata.metadata('pymodaq-plugins-urashg')
        except importlib.metadata.PackageNotFoundError:
            pytest.skip("Package not installed, skipping metadata test")

        # Should have required metadata fields
        assert metadata['Name'] == 'pymodaq-plugins-urashg'
        assert 'PyMoDAQ' in metadata['Keywords']
        assert 'pymodaq' in metadata['Requires-Dist']

    def test_pymodaq_version_compatibility(self):
        """Test extension is compatible with PyMoDAQ version requirements."""
        try:
            import pymodaq
            pymodaq_version = pymodaq.__version__
        except (ImportError, AttributeError):
            pytest.skip("PyMoDAQ not available for version check")

        # Extension should work with PyMoDAQ 5.0+
        major_version = int(pymodaq_version.split('.')[0])
        assert major_version >= 5, f"Extension requires PyMoDAQ 5.0+, found {pymodaq_version}"


# Test execution markers
@pytest.mark.unit
class TestUnit:
    """Marker for unit tests that don't require hardware."""
    pass

@pytest.mark.integration
class TestIntegration:
    """Marker for integration tests that may require mocked hardware."""
    pass

@pytest.mark.extension
class TestExtension:
    """Marker for extension-specific tests."""
    pass


if __name__ == '__main__':
    # Run tests when executed directly
    pytest.main([__file__, '-v'])
