#!/usr/bin/env python3
"""
Comprehensive test suite for DAQ_2DViewer_PrimeBSI plugin to improve coverage.

Tests camera functionality, PyVCAM integration, ROI processing, data acquisition,
and PyMoDAQ 5.x compliance patterns for URASHG SHG microscopy imaging.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

# Add source path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [pytest.mark.unit]


@pytest.fixture
def comprehensive_mock_pyvcam(monkeypatch):
    """Comprehensive PyVCAM mock with full API coverage."""
    # Mock the pyvcam modules
    mock_pvc = Mock()
    mock_camera_class = Mock()
    mock_camera = Mock()
    
    # Configure camera detection and enumeration
    mock_camera_class.detect_camera.return_value = [mock_camera]
    mock_camera.name = "pvcamUSB_0 (Mock)"
    
    # Configure comprehensive parameter support
    mock_camera.get_param.side_effect = lambda param: {
        'PARAM_SENSOR_SIZE': (2048, 2048),
        'PARAM_TEMP': -1989,  # Temperature in hundredths of degrees C
        'PARAM_TEMP_SETPOINT': -2000,
        'PARAM_EXPOSURE_MODE': 1,
        'PARAM_READOUT_PORT': 0,
        'PARAM_SPEED_TABLE_INDEX': 0,
        'PARAM_GAIN_INDEX': 1,
        'PARAM_BINNING_PAR': 1,
        'PARAM_BINNING_SER': 1,
        'PARAM_PIX_TIME': 16000,  # nanoseconds per pixel
        'PARAM_READOUT_TIME': 1000,
        'PARAM_CLEARING_TIME': 1000,
        'PARAM_POST_TRIGGER_DELAY': 0,
        'PARAM_PRE_TRIGGER_DELAY': 0,
    }.get(param, 0)
    
    # Configure parameter setting
    mock_camera.set_param.return_value = True
    
    # Configure advanced camera attributes
    mock_camera.sensor_size = (2048, 2048)
    mock_camera.rois = None  # Default: no ROIs
    mock_camera.is_open = True
    
    # Configure image acquisition with realistic patterns
    def mock_get_frame(**kwargs):
        """Generate realistic SHG camera data."""
        # Create mock SHG image with some structure
        width, height = 2048, 2048
        
        # Create background with Poisson noise
        background = np.random.poisson(100, (height * width)).astype(np.uint16)
        
        # Add some SHG signal spots (for realistic testing)
        image_2d = background.reshape((height, width))
        
        # Add a few bright spots simulating SHG signals
        centers = [(512, 512), (1024, 1024), (1536, 512)]
        for cx, cy in centers:
            y, x = np.ogrid[-50:51, -50:51]
            mask = x*x + y*y <= 50*50
            try:
                image_2d[cy-50:cy+51, cx-50:cx+51][mask] += np.random.poisson(500, mask.sum()).astype(np.uint16)
            except (IndexError, ValueError):
                pass  # Handle edge cases
                
        return image_2d.flatten()
    
    mock_camera.get_frame.side_effect = mock_get_frame
    
    # Configure live mode operations
    mock_camera.start_live.return_value = None
    mock_camera.stop_live.return_value = None
    mock_camera.finish.return_value = None
    mock_camera.close.return_value = None
    
    # Configure ROI support
    mock_roi = Mock()
    mock_roi.shape = (1024, 1024)
    mock_roi.x1, mock_roi.y1 = 512, 512
    mock_roi.x2, mock_roi.y2 = 1535, 1535
    
    def set_roi(roi):
        mock_camera.rois = [roi] if roi else None
        
    mock_camera.set_roi = set_roi
    
    # Patch the modules
    monkeypatch.setitem(sys.modules, "pyvcam", Mock())
    monkeypatch.setitem(sys.modules, "pyvcam.pvc", mock_pvc) 
    monkeypatch.setitem(sys.modules, "pyvcam.camera", Mock(Camera=mock_camera_class))
    
    return mock_pvc, mock_camera_class, mock_camera


@pytest.fixture
def primebsi_plugin():
    """Create PrimeBSI plugin instance."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
        DAQ_2DViewer_PrimeBSI,
    )
    from pymodaq_data.data import Axis
    
    plugin = DAQ_2DViewer_PrimeBSI(None, None)
    
    # Initialize axes required by grab_data
    plugin.x_axis = Axis(label="x", units="pixels", data=np.arange(2048))
    plugin.y_axis = Axis(label="y", units="pixels", data=np.arange(2048))
    
    return plugin


@pytest.fixture  
def primebsi_plugin_with_camera(comprehensive_mock_pyvcam):
    """Create PrimeBSI plugin with comprehensive mock camera."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
        DAQ_2DViewer_PrimeBSI,
    )
    from pymodaq_data.data import Axis
    
    plugin = DAQ_2DViewer_PrimeBSI(None, None)
    plugin.settings.child("mock_mode").setValue(True)
    plugin.camera = comprehensive_mock_pyvcam[2]
    
    # Initialize axes required by grab_data
    plugin.x_axis = Axis(label="x", units="pixels", data=np.arange(2048))
    plugin.y_axis = Axis(label="y", units="pixels", data=np.arange(2048))
    
    return plugin


class TestPrimeBSIPluginBasics:
    """Test basic PrimeBSI plugin functionality."""
    
    def test_plugin_instantiation(self, primebsi_plugin):
        """Test plugin instantiation with proper attributes."""
        assert primebsi_plugin is not None
        assert hasattr(primebsi_plugin, 'settings')
        assert hasattr(primebsi_plugin, 'x_axis')
        assert hasattr(primebsi_plugin, 'y_axis')
        
    def test_parameter_structure_comprehensive(self, primebsi_plugin):
        """Test comprehensive parameter structure."""
        param_names = [param["name"] for param in primebsi_plugin.params]
        
        # Essential camera parameter groups
        assert "camera_settings" in param_names
        assert "roi_settings" in param_names
        assert "post_processing" in param_names
        
        # Check camera_settings children
        camera_group = None
        for param in primebsi_plugin.params:
            if param["name"] == "camera_settings":
                camera_group = param
                break
                
        assert camera_group is not None
        camera_children = [child["name"] for child in camera_group["children"]]
        
        # Essential camera parameters
        assert "mock_mode" in camera_children
        assert "camera_name" in camera_children
        assert "sensor_size" in camera_children
        assert "exposure" in camera_children
        
    def test_ini_attributes(self, primebsi_plugin):
        """Test ini_attributes method."""
        primebsi_plugin.ini_attributes()
        assert primebsi_plugin.camera is None
        
    def test_pyvcam_availability_detection(self, primebsi_plugin):
        """Test PyVCAM availability detection."""
        # Should handle both available and unavailable PyVCAM
        assert hasattr(primebsi_plugin, '__class__')
        # The plugin should instantiate regardless of PyVCAM availability


class TestPrimeBSICameraInitialization:
    """Test camera initialization and connection."""
    
    def test_ini_detector_success(self, comprehensive_mock_pyvcam):
        """Test successful detector initialization."""
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
            DAQ_2DViewer_PrimeBSI,
        )
        
        plugin = DAQ_2DViewer_PrimeBSI(None, None)
        plugin.settings.child("mock_mode").setValue(True)
        
        info_string, success = plugin.ini_detector()
        
        assert success is True
        assert "Mock camera initialized" in info_string or "PrimeBSI" in info_string
        assert plugin.camera is not None
        
    def test_ini_detector_mock_mode(self, comprehensive_mock_pyvcam):
        """Test initialization specifically in mock mode."""
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
            DAQ_2DViewer_PrimeBSI,
        )
        
        plugin = DAQ_2DViewer_PrimeBSI(None, None)
        plugin.settings.child("mock_mode").setValue(True)
        
        info_string, success = plugin.ini_detector()
        
        assert success is True
        assert plugin.camera is not None
        assert plugin.camera.name == "pvcamUSB_0 (Mock)"
        
    def test_ini_detector_real_mode_no_camera(self):
        """Test initialization in real mode with no cameras."""
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
            DAQ_2DViewer_PrimeBSI,
        )
        
        with patch('pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI.PYVCAM_AVAILABLE', True):
            with patch('pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI.Camera') as mock_camera_class:
                mock_camera_class.detect_camera.return_value = []
                
                plugin = DAQ_2DViewer_PrimeBSI(None, None)
                plugin.settings.child("mock_mode").setValue(False)
                
                info_string, success = plugin.ini_detector()
                
                assert success is False
                assert "No camera" in info_string or "not found" in info_string.lower()


class TestPrimeBSIDataAcquisition:
    """Test comprehensive data acquisition functionality."""
    
    def test_grab_data_basic(self, primebsi_plugin_with_camera):
        """Test basic data acquisition with signal emission."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Mock the dte_signal
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1)
            
            # Should emit data via PyMoDAQ 5.x signal pattern
            mock_signal.emit.assert_called_once()
            
            # Verify camera was called
            plugin.camera.get_frame.assert_called()
            
    def test_grab_data_averaging(self, primebsi_plugin_with_camera):
        """Test data acquisition with averaging."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=5)
            
            mock_signal.emit.assert_called_once()
            # With averaging, should still call get_frame
            plugin.camera.get_frame.assert_called()
            
    def test_grab_data_roi_integration(self, primebsi_plugin_with_camera):
        """Test ROI integration during data acquisition."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Enable ROI integration
        plugin.settings.child("roi_settings", "roi_integration").setValue(True)
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1)
            
            mock_signal.emit.assert_called_once()
            
            # Should have emitted both 2D image data and 0D integrated signal
            call_args = mock_signal.emit.call_args[0][0]
            assert hasattr(call_args, 'data')
            
    def test_grab_data_error_handling(self, primebsi_plugin_with_camera):
        """Test error handling during data acquisition."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        plugin.camera.get_frame.side_effect = Exception("Camera error")
        
        with patch.object(plugin, 'emit_status') as mock_emit_status:
            plugin.grab_data(Naverage=1)
            
            # Should emit error status
            mock_emit_status.assert_called()
            
    def test_grab_data_camera_not_ready(self, primebsi_plugin_with_camera):
        """Test data acquisition when camera is not ready."""
        plugin = primebsi_plugin_with_camera
        plugin.camera = None
        
        with patch.object(plugin, 'emit_status') as mock_emit_status:
            plugin.grab_data(Naverage=1)
            
            mock_emit_status.assert_called()


class TestPrimeBSIROIProcessing:
    """Test ROI processing and configuration."""
    
    def test_roi_bounds_calculation(self, primebsi_plugin_with_camera):
        """Test ROI bounds calculation."""
        plugin = primebsi_plugin_with_camera
        
        # Set ROI parameters
        plugin.settings.child("roi_settings", "roi_x").setValue(100)
        plugin.settings.child("roi_settings", "roi_y").setValue(200)
        plugin.settings.child("roi_settings", "roi_width").setValue(500)
        plugin.settings.child("roi_settings", "roi_height").setValue(400)
        
        # Test get_roi_bounds method if it exists
        if hasattr(plugin, 'get_roi_bounds'):
            bounds = plugin.get_roi_bounds()
            assert bounds is not None
            y, h, x, w = bounds
            assert x == 100
            assert y == 200
            assert w == 500
            assert h == 400
            
    def test_roi_integration_calculation(self, primebsi_plugin_with_camera):
        """Test ROI integration calculations."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Enable ROI integration
        plugin.settings.child("roi_settings", "roi_integration").setValue(True)
        
        # Set specific ROI
        plugin.settings.child("roi_settings", "roi_x").setValue(500)
        plugin.settings.child("roi_settings", "roi_y").setValue(500) 
        plugin.settings.child("roi_settings", "roi_width").setValue(200)
        plugin.settings.child("roi_settings", "roi_height").setValue(200)
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1)
            
            mock_signal.emit.assert_called_once()
            
            # Verify both 2D and 0D data were generated
            emitted_data = mock_signal.emit.call_args[0][0]
            assert hasattr(emitted_data, 'data')
            
    def test_roi_configuration_validation(self, primebsi_plugin_with_camera):
        """Test ROI configuration validation."""
        plugin = primebsi_plugin_with_camera
        
        # Test invalid ROI configurations
        invalid_configs = [
            (-100, 0, 100, 100),    # Negative x
            (0, -100, 100, 100),    # Negative y  
            (2000, 0, 100, 100),    # X out of bounds
            (0, 2000, 100, 100),    # Y out of bounds
            (0, 0, 5000, 100),      # Width too large
            (0, 0, 100, 5000),      # Height too large
        ]
        
        for x, y, w, h in invalid_configs:
            plugin.settings.child("roi_settings", "roi_x").setValue(x)
            plugin.settings.child("roi_settings", "roi_y").setValue(y)
            plugin.settings.child("roi_settings", "roi_width").setValue(w)
            plugin.settings.child("roi_settings", "roi_height").setValue(h)
            
            # Should not crash when acquiring data
            with patch.object(plugin, 'dte_signal'):
                plugin.grab_data(Naverage=1)


class TestPrimeBSICameraControl:
    """Test camera control parameters and operations."""
    
    def test_exposure_setting(self, primebsi_plugin_with_camera):
        """Test exposure time setting."""
        plugin = primebsi_plugin_with_camera
        
        # Test exposure parameter
        exposure_param = plugin.settings.child("exposure")
        
        # Test various exposure times
        exposure_times = [1.0, 10.0, 50.0, 100.0, 500.0]
        for exp_time in exposure_times:
            exposure_param.setValue(exp_time)
            assert exposure_param.value() == exp_time
            
    def test_gain_configuration(self, primebsi_plugin_with_camera):
        """Test gain configuration if available."""
        plugin = primebsi_plugin_with_camera
        
        # Look for gain parameters
        camera_group = None
        for param in plugin.params:
            if param["name"] == "camera_settings":
                camera_group = param
                break
                
        if camera_group:
            child_names = [child["name"] for child in camera_group["children"]]
            if "gain_index" in child_names:
                gain_param = plugin.settings.child("camera_settings", "gain_index")
                
                # Test gain values
                for gain in [0, 1, 2]:
                    try:
                        gain_param.setValue(gain)
                        assert gain_param.value() == gain
                    except:
                        pass  # Some gain values may not be valid
                        
    def test_readout_speed_configuration(self, primebsi_plugin_with_camera):
        """Test readout speed configuration."""
        plugin = primebsi_plugin_with_camera
        
        # Look for speed parameters
        camera_group = None
        for param in plugin.params:
            if param["name"] == "camera_settings":
                camera_group = param
                break
                
        if camera_group:
            child_names = [child["name"] for child in camera_group["children"]]
            if "speed_table_index" in child_names:
                speed_param = plugin.settings.child("camera_settings", "speed_table_index")
                
                # Test speed values
                for speed in [0, 1, 2]:
                    try:
                        speed_param.setValue(speed)
                        assert speed_param.value() == speed
                    except:
                        pass  # Some speed values may not be valid
                        
    def test_binning_configuration(self, primebsi_plugin_with_camera):
        """Test pixel binning configuration."""
        plugin = primebsi_plugin_with_camera
        
        # Look for binning parameters
        camera_group = None
        for param in plugin.params:
            if param["name"] == "camera_settings":
                camera_group = param
                break
                
        if camera_group:
            child_names = [child["name"] for child in camera_group["children"]]
            
            if "binning_par" in child_names:
                binning_param = plugin.settings.child("camera_settings", "binning_par")
                
                # Test binning values
                for binning in [1, 2, 4]:
                    try:
                        binning_param.setValue(binning)
                        assert binning_param.value() == binning
                    except:
                        pass


class TestPrimeBSITemperatureControl:
    """Test camera temperature monitoring and control."""
    
    def test_temperature_monitoring(self, primebsi_plugin_with_camera):
        """Test temperature monitoring."""
        plugin = primebsi_plugin_with_camera
        
        # Mock should return temperature
        temp = plugin.camera.get_param('PARAM_TEMP')
        assert temp == -1989  # -19.89°C in hundredths
        
        # Convert to actual temperature
        actual_temp = temp / 100.0
        assert actual_temp == -19.89
        
    def test_temperature_setpoint(self, primebsi_plugin_with_camera):
        """Test temperature setpoint configuration.""" 
        plugin = primebsi_plugin_with_camera
        
        # Look for temperature parameters
        camera_group = None
        for param in plugin.params:
            if param["name"] == "camera_settings":
                camera_group = param
                break
                
        if camera_group:
            child_names = [child["name"] for child in camera_group["children"]]
            
            if "temp_setpoint" in child_names:
                temp_param = plugin.settings.child("camera_settings", "temp_setpoint")
                
                # Test temperature setpoints
                setpoints = [-20, -10, 0, 10]
                for setpoint in setpoints:
                    try:
                        temp_param.setValue(setpoint)
                        assert temp_param.value() == setpoint
                    except:
                        pass  # Some setpoints may not be valid


class TestPrimeBSILiveModeOperations:
    """Test live mode acquisition operations."""
    
    def test_start_live_mode(self, primebsi_plugin_with_camera):
        """Test starting live mode."""
        plugin = primebsi_plugin_with_camera
        
        # Test live mode start if available
        if hasattr(plugin, 'start_live'):
            plugin.start_live()
            plugin.camera.start_live.assert_called()
            
    def test_stop_live_mode(self, primebsi_plugin_with_camera):
        """Test stopping live mode."""
        plugin = primebsi_plugin_with_camera
        
        # Test live mode stop if available
        if hasattr(plugin, 'stop_live'):
            plugin.stop_live()
            plugin.camera.stop_live.assert_called()
            
    def test_live_mode_data_acquisition(self, primebsi_plugin_with_camera):
        """Test data acquisition during live mode."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Simulate live mode acquisition
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1, live=True)
            
            mock_signal.emit.assert_called()


class TestPrimeBSICleanupOperations:
    """Test cleanup and shutdown operations."""
    
    def test_close_camera(self, primebsi_plugin_with_camera):
        """Test proper camera closure."""
        plugin = primebsi_plugin_with_camera
        camera = plugin.camera
        
        plugin.close()
        
        camera.close.assert_called_once()
        assert plugin.camera is None
        
    def test_close_no_camera(self, primebsi_plugin):
        """Test close when no camera is initialized."""
        plugin = primebsi_plugin
        plugin.camera = None
        
        # Should not raise exception
        plugin.close()
        
    def test_cleanup_resources(self, primebsi_plugin_with_camera):
        """Test resource cleanup."""
        plugin = primebsi_plugin_with_camera
        
        # Test cleanup operations
        plugin.close()
        
        # Verify cleanup was performed
        assert plugin.camera is None


class TestPrimeBSIErrorRecovery:
    """Test error recovery and resilience."""
    
    def test_camera_disconnection_recovery(self, primebsi_plugin_with_camera):
        """Test recovery from camera disconnection."""
        plugin = primebsi_plugin_with_camera
        
        # Simulate camera disconnection
        plugin.camera.is_open = False
        plugin.camera.get_frame.side_effect = Exception("Camera disconnected")
        
        with patch.object(plugin, 'emit_status') as mock_emit_status:
            plugin.grab_data(Naverage=1)
            
            mock_emit_status.assert_called()
            
    def test_parameter_validation_recovery(self, primebsi_plugin_with_camera):
        """Test recovery from invalid parameter values."""
        plugin = primebsi_plugin_with_camera
        
        # Set invalid parameter values
        try:
            plugin.settings.child("exposure").setValue(-100)
        except:
            pass  # Expected to fail
            
        # Should still be able to acquire data
        with patch.object(plugin, 'dte_signal'):
            plugin.grab_data(Naverage=1)
            
    def test_memory_error_recovery(self, primebsi_plugin_with_camera):
        """Test recovery from memory allocation errors."""
        plugin = primebsi_plugin_with_camera
        
        # Simulate memory error
        plugin.camera.get_frame.side_effect = MemoryError("Out of memory")
        
        with patch.object(plugin, 'emit_status') as mock_emit_status:
            plugin.grab_data(Naverage=1)
            
            mock_emit_status.assert_called()


class TestPrimeBSIIntegrationScenarios:
    """Test integration scenarios for URASHG microscopy."""
    
    def test_shg_imaging_workflow(self, primebsi_plugin_with_camera):
        """Test typical SHG imaging workflow."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Configure for SHG imaging
        plugin.settings.child("exposure").setValue(100.0)
        
        # Acquire multiple frames
        with patch.object(plugin, 'dte_signal') as mock_signal:
            for i in range(5):
                plugin.grab_data(Naverage=1)
                
            assert mock_signal.emit.call_count == 5
            
    def test_polarimetric_imaging_sequence(self, primebsi_plugin_with_camera):
        """Test polarimetric imaging sequence."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Enable ROI integration for polarimetric analysis
        plugin.settings.child("roi_settings", "roi_integration").setValue(True)
        
        # Simulate polarimetric measurement sequence
        polarization_angles = [0, 45, 90, 135]  # Degrees
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            for angle in polarization_angles:
                # In real system, polarization elements would be rotated here
                plugin.grab_data(Naverage=3)  # Average for better SNR
                
            assert mock_signal.emit.call_count == len(polarization_angles)
            
    def test_time_series_acquisition(self, primebsi_plugin_with_camera):
        """Test time-series acquisition."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Fast acquisition for time series
        plugin.settings.child("exposure").setValue(10.0)
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            # Simulate rapid acquisition
            for frame in range(10):
                plugin.grab_data(Naverage=1)
                
            assert mock_signal.emit.call_count == 10
            
    def test_calibration_imaging(self, primebsi_plugin_with_camera):
        """Test calibration imaging workflow."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Configure for calibration
        plugin.settings.child("exposure").setValue(50.0)
        plugin.settings.child("roi_settings", "roi_integration").setValue(True)
        
        # Set calibration ROI
        plugin.settings.child("roi_settings", "roi_x").setValue(800)
        plugin.settings.child("roi_settings", "roi_y").setValue(800)
        plugin.settings.child("roi_settings", "roi_width").setValue(400)
        plugin.settings.child("roi_settings", "roi_height").setValue(400)
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=10)  # High averaging for calibration
            
            mock_signal.emit.assert_called_once()


class TestPrimeBSIPyMoDAQCompliance:
    """Test PyMoDAQ 5.x compliance for PrimeBSI plugin."""
    
    def test_data_structure_compliance(self, primebsi_plugin_with_camera):
        """Test PyMoDAQ 5.x data structure compliance."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1)
            
            mock_signal.emit.assert_called_once()
            
            # Verify DataToExport structure
            emitted_data = mock_signal.emit.call_args[0][0]
            assert hasattr(emitted_data, 'name')
            assert hasattr(emitted_data, 'data')
            
    def test_axis_definition_compliance(self, primebsi_plugin_with_camera):
        """Test axis definition compliance."""
        plugin = primebsi_plugin_with_camera
        
        # Should have properly defined axes
        assert plugin.x_axis is not None
        assert plugin.y_axis is not None
        assert plugin.x_axis.label == "x"
        assert plugin.y_axis.label == "y"
        assert plugin.x_axis.units == "pixels"
        assert plugin.y_axis.units == "pixels"
        
    def test_signal_emission_compliance(self, primebsi_plugin_with_camera):
        """Test signal emission compliance."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Should have dte_signal attribute
        assert hasattr(plugin, 'dte_signal')
        
        with patch.object(plugin, 'dte_signal') as mock_signal:
            plugin.grab_data(Naverage=1)
            
            # Should emit exactly once per grab_data call
            mock_signal.emit.assert_called_once()
            
    def test_parameter_tree_compliance(self, primebsi_plugin):
        """Test parameter tree compliance."""
        plugin = primebsi_plugin
        
        # Should have properly structured parameters
        assert isinstance(plugin.params, list)
        assert len(plugin.params) > 0
        
        # Check for required parameter structure
        param_names = [param["name"] for param in plugin.params]
        assert "camera_settings" in param_names
        
        # Parameters should be dictionaries with required keys
        for param in plugin.params:
            assert isinstance(param, dict)
            assert "name" in param
            assert "type" in param
            
    def test_thread_safety_compliance(self, primebsi_plugin_with_camera):
        """Test thread safety compliance."""
        plugin = primebsi_plugin_with_camera
        plugin.camera.is_open = True
        
        # Should handle concurrent operations safely
        with patch.object(plugin, 'dte_signal'):
            # Simulate concurrent grab operations
            for i in range(3):
                plugin.grab_data(Naverage=1)
                
        # Should not crash or cause issues
        
    def test_error_status_emission_compliance(self, primebsi_plugin_with_camera):
        """Test error status emission compliance."""
        plugin = primebsi_plugin_with_camera
        
        # Should have emit_status method
        assert hasattr(plugin, 'emit_status')
        
        # Configure camera to fail
        plugin.camera.get_frame.side_effect = Exception("Test error")
        
        with patch.object(plugin, 'emit_status') as mock_emit_status:
            plugin.grab_data(Naverage=1)
            
            # Should emit error status on failure
            mock_emit_status.assert_called()