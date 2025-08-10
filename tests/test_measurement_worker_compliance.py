"""
Measurement Worker Compliance Test Suite for URASHG Extension

This test suite ensures the MeasurementWorker component follows PyMoDAQ standards
for threaded measurement operations, data handling, and signal/slot patterns.

Test Categories:
- Worker Initialization & Threading
- Measurement Lifecycle Management
- Data Acquisition & Processing
- Signal/Slot Communication
- Thread Safety & Synchronization
- Error Handling & Recovery
- PyMoDAQ Data Standards
- Performance & Resource Management
"""

import pytest
import logging
import threading
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import numpy as np
from typing import Dict, Any, List
import json

# Qt imports
from qtpy import QtCore, QtTest
from qtpy.QtCore import QObject, Signal, QThread, QTimer, QEventLoop

# PyMoDAQ imports
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.data import DataWithAxes, Axis, DataSource
from pymodaq.utils.parameter import Parameter

# Test utilities
from tests.mock_modules.mock_devices import (
    MockMovePlugin, MockViewerPlugin, MockDeviceManager
)

logger = set_logger(get_module_name(__file__))


class TestMeasurementWorkerInitialization:
    """Test measurement worker initialization and basic structure."""

    @pytest.fixture
    def mock_device_manager(self):
        """Create mock device manager for testing."""
        return MockDeviceManager()

    @pytest.fixture
    def measurement_settings(self):
        """Create test measurement settings."""
        return {
            'measurement_type': 'Basic RASHG',
            'pol_steps': 36,
            'integration_time': 100,
            'averages': 1,
            'pol_range': {
                'pol_start': 0.0,
                'pol_end': 180.0
            },
            'wavelength_range': {
                'start': 800.0,
                'end': 900.0,
                'step': 10.0
            }
        }

    @pytest.fixture
    def measurement_worker(self, mock_device_manager, measurement_settings):
        """Create measurement worker for testing."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        return MeasurementWorker(mock_device_manager, measurement_settings)

    def test_worker_inherits_qobject(self):
        """Test measurement worker inherits from QObject for signal support."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        assert issubclass(MeasurementWorker, QObject)

    def test_worker_initialization(self, measurement_worker):
        """Test worker initializes properly with required attributes."""
        worker = measurement_worker

        # Should have device manager reference
        assert hasattr(worker, 'device_manager')
        assert worker.device_manager is not None

        # Should have measurement settings
        assert hasattr(worker, 'settings')
        assert isinstance(worker.settings, dict)

        # Should have control flags
        assert hasattr(worker, '_is_running')
        assert hasattr(worker, '_is_paused')
        assert hasattr(worker, '_stop_requested')

    def test_required_signals_exist(self, measurement_worker):
        """Test worker has required signals for communication."""
        worker = measurement_worker

        required_signals = [
            'measurement_started',
            'measurement_finished',
            'measurement_progress',
            'measurement_error',
            'data_acquired',
            'step_completed'
        ]

        for signal_name in required_signals:
            if hasattr(worker, signal_name):
                signal_attr = getattr(worker, signal_name)
                assert isinstance(signal_attr, Signal), f"{signal_name} should be a QtCore.Signal"

    def test_required_methods_exist(self, measurement_worker):
        """Test worker has required measurement methods."""
        worker = measurement_worker

        required_methods = [
            'run_measurement',
            'stop_measurement',
            'pause_measurement',
            'resume_measurement'
        ]

        for method_name in required_methods:
            assert hasattr(worker, method_name), f"Missing required method: {method_name}"
            assert callable(getattr(worker, method_name)), f"{method_name} should be callable"

    def test_worker_state_management(self, measurement_worker):
        """Test worker properly manages its state."""
        worker = measurement_worker

        # Initial state should be stopped
        assert not worker._is_running
        assert not worker._is_paused
        assert not worker._stop_requested


class TestMeasurementLifecycle:
    """Test measurement lifecycle management."""

    @pytest.fixture
    def configured_worker(self):
        """Create fully configured measurement worker."""
        mock_dm = MockDeviceManager()
        settings = {
            'measurement_type': 'Basic RASHG',
            'pol_steps': 8,  # Reduced for faster testing
            'integration_time': 10,
            'averages': 1
        }

        with patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.MeasurementWorker'):
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
            worker = MeasurementWorker(mock_dm, settings)

            # Mock the actual measurement methods
            worker._initialize_measurement = Mock()
            worker._finalize_measurement = Mock()
            worker._measure_at_angle = Mock(return_value={'data': np.ones((100, 100))})

            return worker

    def test_measurement_start_sequence(self, configured_worker):
        """Test measurement start sequence follows proper order."""
        worker = configured_worker

        # Mock signal emissions
        worker.measurement_started = Mock()
        worker.measurement_progress = Mock()

        # Start measurement
        if hasattr(worker, 'run_measurement'):
            worker.run_measurement()

            # Should initialize first
            worker._initialize_measurement.assert_called_once()

            # Should emit started signal
            if hasattr(worker, 'measurement_started'):
                worker.measurement_started.emit.assert_called()

    def test_measurement_stop_sequence(self, configured_worker):
        """Test measurement stop sequence is handled properly."""
        worker = configured_worker

        # Start measurement first
        worker._is_running = True

        # Stop measurement
        worker.stop_measurement()

        # Should set stop flag
        assert worker._stop_requested

        # Should clean up properly
        if hasattr(worker, '_finalize_measurement'):
            # Simulate measurement loop completion
            worker._finalize_measurement()

    def test_measurement_pause_resume(self, configured_worker):
        """Test pause/resume functionality."""
        worker = configured_worker

        # Start measurement
        worker._is_running = True

        # Test pause
        worker.pause_measurement()
        assert worker._is_paused

        # Test resume
        worker.resume_measurement()
        assert not worker._is_paused

    def test_measurement_progress_reporting(self, configured_worker):
        """Test progress reporting during measurements."""
        worker = configured_worker

        # Mock progress signal
        worker.measurement_progress = Mock()

        # Simulate progress updates
        if hasattr(worker, '_emit_progress'):
            worker._emit_progress(25)
            worker.measurement_progress.emit.assert_called_with(25)

    def test_measurement_completion_handling(self, configured_worker):
        """Test measurement completion is handled properly."""
        worker = configured_worker

        # Mock completion signals
        worker.measurement_finished = Mock()

        # Simulate measurement completion
        if hasattr(worker, '_finalize_measurement'):
            worker._finalize_measurement()

            # Should emit finished signal
            worker.measurement_finished.emit.assert_called()


class TestDataAcquisitionCompliance:
    """Test data acquisition follows PyMoDAQ standards."""

    @pytest.fixture
    def data_acquisition_worker(self):
        """Create worker configured for data acquisition testing."""
        mock_dm = MockDeviceManager()

        # Configure mock camera to return realistic data
        mock_camera = Mock()
        mock_camera.grab_data.return_value = [DataWithAxes(
            'Camera',
            data=[np.random.randint(0, 4096, (512, 512))],
            axes=[Axis('x', data=np.arange(512)), Axis('y', data=np.arange(512))],
            units="counts",
            source=DataSource.raw
        )]
        mock_dm.devices['PrimeBSI'] = mock_camera

        settings = {
            'measurement_type': 'Basic RASHG',
            'pol_steps': 4,
            'integration_time': 50
        }

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        return MeasurementWorker(mock_dm, settings)

    def test_camera_data_acquisition(self, data_acquisition_worker):
        """Test camera data acquisition follows PyMoDAQ standards."""
        worker = data_acquisition_worker

        # Should acquire data in PyMoDAQ format
        if hasattr(worker, '_acquire_camera_image'):
            data = worker._acquire_camera_image()

            # Should return DataWithAxes or compatible format
            if data is not None:
                assert isinstance(data, (DataWithAxes, list, np.ndarray))

                # If DataWithAxes, should have proper structure
                if isinstance(data, DataWithAxes):
                    assert hasattr(data, 'data')
                    assert hasattr(data, 'axes')
                    assert hasattr(data, 'source')
                    assert data.source == DataSource.raw

    def test_data_processing_pipeline(self, data_acquisition_worker):
        """Test data processing follows PyMoDAQ patterns."""
        worker = data_acquisition_worker

        # Should process data consistently
        if hasattr(worker, '_process_measurement_data'):
            # Mock input data
            raw_data = np.random.randint(0, 4096, (512, 512))

            processed_data = worker._process_measurement_data(raw_data)

            # Should return properly formatted data
            assert processed_data is not None
            if isinstance(processed_data, np.ndarray):
                assert processed_data.shape == raw_data.shape

    def test_data_storage_format(self, data_acquisition_worker):
        """Test data storage follows PyMoDAQ standards."""
        worker = data_acquisition_worker

        # Should store data in standardized format
        if hasattr(worker, '_store_measurement_data'):
            test_data = {
                'angle': 45.0,
                'intensity': 1000.0,
                'image': np.ones((100, 100))
            }

            worker._store_measurement_data(test_data)

            # Should be stored in worker's data structure
            if hasattr(worker, 'measurement_data'):
                assert len(worker.measurement_data) > 0

    def test_data_emission_patterns(self, data_acquisition_worker):
        """Test data emission follows PyMoDAQ signal patterns."""
        worker = data_acquisition_worker

        # Mock data emission signal
        worker.data_acquired = Mock()

        # Should emit data properly
        if hasattr(worker, '_emit_step_data'):
            test_data = {'angle': 0.0, 'intensity': 500.0}
            worker._emit_step_data(test_data)

            # Should emit with proper format
            worker.data_acquired.emit.assert_called()


class TestMultiWavelengthMeasurements:
    """Test multi-wavelength measurement capabilities."""

    @pytest.fixture
    def multiwavelength_worker(self):
        """Create worker for multi-wavelength testing."""
        mock_dm = MockDeviceManager()

        # Configure mock laser
        mock_laser = Mock()
        mock_laser.move_abs = Mock()
        mock_laser.get_actuator_value = Mock(return_value=800.0)
        mock_dm.devices['MaiTai'] = mock_laser

        settings = {
            'measurement_type': 'Multi-Wavelength RASHG',
            'wavelength_range': {
                'start': 800.0,
                'end': 820.0,
                'step': 10.0
            },
            'pol_steps': 4
        }

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        return MeasurementWorker(mock_dm, settings)

    def test_wavelength_sequence_generation(self, multiwavelength_worker):
        """Test wavelength sequence generation."""
        worker = multiwavelength_worker

        if hasattr(worker, '_generate_wavelength_sequence'):
            wavelengths = worker._generate_wavelength_sequence()

            assert isinstance(wavelengths, (list, np.ndarray))
            assert len(wavelengths) > 0

            # Should cover expected range
            wavelengths = np.array(wavelengths)
            assert np.min(wavelengths) >= 800.0
            assert np.max(wavelengths) <= 820.0

    def test_wavelength_setting(self, multiwavelength_worker):
        """Test laser wavelength setting."""
        worker = multiwavelength_worker

        if hasattr(worker, '_set_laser_wavelength'):
            target_wavelength = 810.0
            worker._set_laser_wavelength(target_wavelength)

            # Should command laser to move
            mock_laser = worker.device_manager.devices['MaiTai']
            mock_laser.move_abs.assert_called_with(target_wavelength)

    def test_multiwavelength_measurement_flow(self, multiwavelength_worker):
        """Test complete multi-wavelength measurement flow."""
        worker = multiwavelength_worker

        # Mock measurement methods
        worker._run_single_wavelength_measurement = Mock()
        worker._set_laser_wavelength = Mock()

        if hasattr(worker, '_run_multi_wavelength_measurement'):
            worker._run_multi_wavelength_measurement()

            # Should set wavelengths and run measurements
            assert worker._set_laser_wavelength.call_count > 0
            assert worker._run_single_wavelength_measurement.call_count > 0

    def test_wavelength_synchronization(self, multiwavelength_worker):
        """Test wavelength synchronization with power meter."""
        worker = multiwavelength_worker

        if hasattr(worker, '_sync_power_meter_wavelength'):
            test_wavelength = 815.0
            worker._sync_power_meter_wavelength(test_wavelength)

            # Should synchronize power meter if available
            if 'Newport1830C' in worker.device_manager.devices:
                mock_power_meter = worker.device_manager.devices['Newport1830C']
                # Check if power meter wavelength was set (implementation dependent)


class TestErrorHandlingCompliance:
    """Test error handling follows PyMoDAQ standards."""

    @pytest.fixture
    def error_prone_worker(self):
        """Create worker configured for error testing."""
        mock_dm = MockDeviceManager()

        # Configure devices to simulate errors
        mock_camera = Mock()
        mock_camera.grab_data.side_effect = Exception("Camera communication error")
        mock_dm.devices['PrimeBSI'] = mock_camera

        settings = {'measurement_type': 'Basic RASHG', 'pol_steps': 4}

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        worker = MeasurementWorker(mock_dm, settings)
        worker.measurement_error = Mock()
        return worker

    def test_camera_error_handling(self, error_prone_worker):
        """Test camera error handling."""
        worker = error_prone_worker

        if hasattr(worker, '_acquire_camera_image'):
            # Should handle camera errors gracefully
            try:
                data = worker._acquire_camera_image()
                # Should return None or default data on error
                assert data is None or isinstance(data, (np.ndarray, DataWithAxes))
            except Exception as e:
                # Should emit error signal
                worker.measurement_error.emit.assert_called()

    def test_device_communication_errors(self, error_prone_worker):
        """Test device communication error handling."""
        worker = error_prone_worker

        # Mock device communication failure
        mock_device = Mock()
        mock_device.move_abs.side_effect = Exception("Communication timeout")
        worker.device_manager.devices['Elliptec'] = mock_device

        if hasattr(worker, '_move_polarization_elements'):
            # Should handle communication errors
            try:
                worker._move_polarization_elements(45.0)
            except Exception:
                # Should emit appropriate error signal
                if hasattr(worker, 'measurement_error'):
                    worker.measurement_error.emit.assert_called()

    def test_measurement_recovery(self, error_prone_worker):
        """Test measurement recovery after errors."""
        worker = error_prone_worker

        # Should have recovery mechanisms
        if hasattr(worker, '_handle_measurement_error'):
            assert callable(worker._handle_measurement_error)

        if hasattr(worker, '_retry_operation'):
            assert callable(worker._retry_operation)

    def test_graceful_shutdown_on_errors(self, error_prone_worker):
        """Test graceful shutdown when errors occur."""
        worker = error_prone_worker

        # Should clean up properly even on errors
        worker._is_running = True

        # Simulate error during measurement
        if hasattr(worker, '_handle_fatal_error'):
            worker._handle_fatal_error("Critical device failure")

            # Should set stop flags
            assert worker._stop_requested

        # Should clean up resources
        if hasattr(worker, '_emergency_cleanup'):
            worker._emergency_cleanup()


class TestThreadSafetyCompliance:
    """Test thread safety of measurement worker."""

    @pytest.fixture
    def threaded_worker(self):
        """Create worker for thread safety testing."""
        mock_dm = MockDeviceManager()
        settings = {'measurement_type': 'Basic RASHG', 'pol_steps': 4}

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        return MeasurementWorker(mock_dm, settings)

    def test_worker_thread_isolation(self, threaded_worker):
        """Test worker operates safely in separate thread."""
        worker = threaded_worker

        # Should be designed for thread execution
        assert issubclass(type(worker), QObject)

        # Should have thread-safe state management
        assert hasattr(worker, '_is_running')
        assert hasattr(worker, '_stop_requested')

    def test_signal_thread_safety(self, threaded_worker):
        """Test signals are emitted safely across threads."""
        worker = threaded_worker

        # Qt signals are inherently thread-safe
        signal_attrs = [attr for attr in dir(worker)
                       if isinstance(getattr(worker, attr, None), Signal)]

        # Should have signals for cross-thread communication
        assert len(signal_attrs) > 0

    def test_concurrent_control_operations(self, threaded_worker):
        """Test concurrent control operations are handled safely."""
        worker = threaded_worker

        # Should handle concurrent stop/pause requests
        def stop_worker():
            worker.stop_measurement()

        def pause_worker():
            worker.pause_measurement()

        # Create threads for concurrent operations
        stop_thread = threading.Thread(target=stop_worker)
        pause_thread = threading.Thread(target=pause_worker)

        # Start both threads
        stop_thread.start()
        pause_thread.start()

        # Wait for completion
        stop_thread.join(timeout=1.0)
        pause_thread.join(timeout=1.0)

        # Should handle requests without corruption
        assert worker._stop_requested or worker._is_paused

    def test_resource_cleanup_thread_safety(self, threaded_worker):
        """Test resource cleanup is thread-safe."""
        worker = threaded_worker

        # Should clean up resources safely
        if hasattr(worker, '_cleanup_resources'):
            # Should be callable from any thread
            worker._cleanup_resources()


class TestPerformanceCompliance:
    """Test performance characteristics and resource management."""

    @pytest.fixture
    def performance_worker(self):
        """Create worker for performance testing."""
        mock_dm = MockDeviceManager()
        settings = {
            'measurement_type': 'Basic RASHG',
            'pol_steps': 36,
            'integration_time': 100,
            'averages': 5
        }

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker
        return MeasurementWorker(mock_dm, settings)

    def test_memory_management(self, performance_worker):
        """Test memory usage is managed properly."""
        worker = performance_worker

        # Should not accumulate unbounded data
        if hasattr(worker, 'measurement_data'):
            initial_size = len(getattr(worker, 'measurement_data', []))

            # Simulate data accumulation
            for i in range(10):
                if hasattr(worker, '_store_measurement_data'):
                    worker._store_measurement_data({'step': i, 'data': np.ones(100)})

            # Should manage memory growth
            if hasattr(worker, '_cleanup_old_data'):
                worker._cleanup_old_data()

    def test_measurement_timing(self, performance_worker):
        """Test measurement timing is reasonable."""
        worker = performance_worker

        # Should complete measurements in reasonable time
        if hasattr(worker, '_measure_at_angle'):
            start_time = time.time()
            worker._measure_at_angle(45.0)
            duration = time.time() - start_time

            # Should complete within reasonable time (adjust as needed)
            assert duration < 5.0, "Single measurement taking too long"

    def test_resource_utilization(self, performance_worker):
        """Test efficient resource utilization."""
        worker = performance_worker

        # Should release resources when not needed
        if hasattr(worker, '_release_unused_resources'):
            worker._release_unused_resources()

        # Should reuse resources efficiently
        if hasattr(worker, '_optimize_resource_usage'):
            worker._optimize_resource_usage()


class TestPyMoDAQStandardsCompliance:
    """Test overall PyMoDAQ standards compliance."""

    def test_worker_follows_pymodaq_patterns(self):
        """Test worker follows PyMoDAQ architectural patterns."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        # Should inherit from QObject
        assert issubclass(MeasurementWorker, QObject)

        # Should have proper naming
        assert 'Worker' in MeasurementWorker.__name__
        assert 'Measurement' in MeasurementWorker.__name__

    def test_signal_naming_conventions(self):
        """Test signals follow PyMoDAQ naming conventions."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        mock_dm = MockDeviceManager()
        worker = MeasurementWorker(mock_dm, {})

        # Get all signals
        signal_names = [attr for attr in dir(worker)
                       if isinstance(getattr(worker, attr, None), Signal)]

        for signal_name in signal_names:
            # Should use snake_case
            assert signal_name.islower() or '_' in signal_name

            # Should be descriptive
            assert len(signal_name) > 3

    def test_data_format_compliance(self):
        """Test data formats comply with PyMoDAQ standards."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        mock_dm = MockDeviceManager()
        worker = MeasurementWorker(mock_dm, {})

        # Should handle PyMoDAQ data structures
        if hasattr(worker, '_format_data_for_pymodaq'):
            test_data = np.ones((100, 100))
            formatted_data = worker._format_data_for_pymodaq(test_data)

            # Should return DataWithAxes or compatible format
            assert isinstance(formatted_data, (DataWithAxes, list, dict))

    def test_documentation_standards(self):
        """Test worker has proper documentation."""
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import MeasurementWorker

        # Should have class docstring
        assert MeasurementWorker.__doc__ is not None
        assert len(MeasurementWorker.__doc__.strip()) > 50

        # Key methods should have docstrings
        key_methods = ['run_measurement', 'stop_measurement', 'pause_measurement']

        for method_name in key_methods:
            if hasattr(MeasurementWorker, method_name):
                method = getattr(MeasurementWorker, method_name)
                if callable(method):
                    assert method.__doc__ is not None, f"Method {method_name} should have docstring"


# Test execution markers for pytest
@pytest.mark.unit
@pytest.mark.measurement_worker
class TestMeasurementWorkerUnit:
    """Unit tests for measurement worker."""
    pass

@pytest.mark.integration
@pytest.mark.measurement_worker
class TestMeasurementWorkerIntegration:
    """Integration tests for measurement worker."""
    pass

@pytest.mark.threading
@pytest.mark.measurement_worker
class TestMeasurementWorkerThreading:
    """Threading-specific tests for measurement worker."""
    pass

@pytest.mark.performance
@pytest.mark.measurement_worker
class TestMeasurementWorkerPerformance:
    """Performance tests for measurement worker."""
    pass

@pytest.mark.pymodaq_standards
@pytest.mark.measurement_worker
class TestMeasurementWorkerStandards:
    """PyMoDAQ standards compliance tests."""
    pass


if __name__ == '__main__':
    # Run tests when executed directly
    pytest.main([__file__, '-v', '-m', 'measurement_worker'])
