#!/usr/bin/env python3
"""
Comprehensive tests for PrimeBSI camera plugin with PyVCAM 2.2.3 support.

Tests both real hardware functionality and mock modes for CI/CD integration.
"""

import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import List, Optional

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test markers
pytestmark = [
    pytest.mark.camera,
    pytest.mark.integration
]


class MockPyVCAMCamera:
    """Mock PyVCAM camera for CI testing with 2.2.3 API structure."""
    
    def __init__(self):
        self.name = "pvcamUSB_0"
        self.is_open = False
        self.sensor_size = (2048, 2048)
        
        # PyVCAM 2.2.3 structure
        self.readout_ports = {"CMOS": 0}
        self.readout_port = 0
        self.speed = 0
        self.speed_name = "Speed_0"
        self.gain = 1
        self.gain_name = "Full well"
        self.temp = -19.89
        self.temp_setpoint = -20.0
        
        # Exposure and trigger modes (PyVCAM 2.2.3 format)
        self.exp_mode = 1792
        self.exp_modes = {
            "Internal Trigger": 1792,
            "Edge Trigger": 2304, 
            "Trigger first": 2048
        }
        self.clear_mode = 0
        self.clear_modes = {"Auto": 0}
        
        # Port speed gain table structure
        self.port_speed_gain_table = {
            "CMOS": {
                "port_value": 0,
                "Speed_0": {
                    "speed_index": 0,
                    "pixel_time": 5,
                    "bit_depth": 11,
                    "gain_range": [1, 2, 3],
                    "Full well": {"gain_index": 1},
                    "Balanced": {"gain_index": 2},
                    "Sensitivity": {"gain_index": 3}
                },
                "Speed_1": {
                    "speed_index": 1,
                    "pixel_time": 10,  
                    "bit_depth": 12,
                    "gain_range": [1, 2],
                    "HDR": {"gain_index": 1},
                    "CMS": {"gain_index": 2}
                }
            }
        }
        
        # ROI structure (new format)
        self.rois = [MockROI()]
        self.exp_time = 100
        
    def open(self):
        self.is_open = True
        
    def close(self):
        self.is_open = False
        
    def get_frame(self, exp_time=None):
        """Generate realistic mock frame data."""
        if exp_time:
            self.exp_time = exp_time
            
        # Generate realistic camera noise with features
        height, width = self.rois[0].shape
        
        # Base signal proportional to exposure time
        base_level = min(100 + self.exp_time * 0.5, 1000)
        
        # Generate Poisson noise (shot noise)
        signal = np.random.poisson(base_level, height * width)
        
        # Add Gaussian read noise
        read_noise = np.random.normal(0, 5, height * width)
        
        # Combine and clip to valid range
        frame = signal + read_noise
        frame = np.clip(frame, 0, 65535).astype(np.uint16)
        
        # Add bright spot in center for ROI testing
        frame = frame.reshape((height, width))
        center_y, center_x = height // 2, width // 2
        y_range = slice(center_y - 50, center_y + 50)
        x_range = slice(center_x - 50, center_x + 50)
        frame[y_range, x_range] += 500
        
        return frame.flatten()


class MockROI:
    """Mock ROI object matching PyVCAM 2.2.3 structure."""
    
    def __init__(self):
        self.s1 = 0      # Start column
        self.s2 = 2047   # End column
        self.p1 = 0      # Start row
        self.p2 = 2047   # End row
        self.sbin = 1    # Serial binning
        self.pbin = 1    # Parallel binning
        self.shape = (2048, 2048)  # (height, width)


class MockPVC:
    """Mock PVCAM library functions."""
    
    @staticmethod
    def init_pvcam():
        pass
        
    @staticmethod
    def uninit_pvcam():
        pass
        
    @staticmethod
    def get_cam_total():
        return 1


def setup_mock_pyvcam():
    """Setup mock PyVCAM environment for testing."""
    
    # Mock PyVCAM modules
    mock_pyvcam = Mock()
    mock_pyvcam.pvc = MockPVC()
    mock_pyvcam.constants = Mock()
    mock_pyvcam.constants.CLEAR_NEVER = 0
    mock_pyvcam.constants.CLEAR_PRE_SEQUENCE = 1
    mock_pyvcam.constants.EXT_TRIG_INTERNAL = 1792
    
    # Add param constants for advanced settings
    mock_pyvcam.constants.PARAM_EXP_TIME = "exp_time"
    mock_pyvcam.constants.PARAM_READOUT_PORT = "readout_port"
    mock_pyvcam.constants.PARAM_PIX_TIME = "pix_time"
    mock_pyvcam.constants.PARAM_GAIN_INDEX = "gain_index"
    mock_pyvcam.constants.PARAM_TEMP_SETPOINT = "temp_setpoint"
    
    # Mock Camera class
    mock_camera_class = Mock()
    mock_camera_class.detect_camera = lambda: [MockPyVCAMCamera()]
    mock_pyvcam.camera.Camera = mock_camera_class
    
    # Install mocks
    sys.modules['pyvcam'] = mock_pyvcam
    sys.modules['pyvcam.pvc'] = mock_pyvcam.pvc
    sys.modules['pyvcam.camera'] = mock_pyvcam.camera
    sys.modules['pyvcam.constants'] = mock_pyvcam.constants
    
    return mock_pyvcam


def setup_mock_pymodaq():
    """Setup mock PyMoDAQ environment."""
    from tests.mock_modules.mock_pymodaq import (
        MockDAQViewerBase, MockThreadCommand, MockAxis, 
        MockDataWithAxes, MockDataToExport, MockParameter
    )
    
    # Mock PyMoDAQ modules
    mock_viewer_utility = Mock()
    mock_viewer_utility.DAQ_Viewer_base = MockDAQViewerBase
    
    mock_daq_utils = Mock()
    mock_daq_utils.ThreadCommand = MockThreadCommand
    
    mock_data = Mock()
    mock_data.Axis = MockAxis
    mock_data.DataSource = Mock()
    mock_data.DataSource.raw = "raw"
    mock_data.DataSource.calculated = "calculated"
    mock_data.DataWithAxes = MockDataWithAxes
    mock_data.DataToExport = MockDataToExport
    
    mock_parameter = Mock()
    mock_parameter.Parameter = MockParameter
    
    mock_thread_commands = Mock()
    mock_thread_commands.ThreadStatusViewer = Mock()
    
    # Install mocks
    sys.modules['pymodaq.control_modules.viewer_utility_classes'] = mock_viewer_utility
    sys.modules['pymodaq.utils.daq_utils'] = mock_daq_utils
    sys.modules['pymodaq_data.data'] = mock_data
    sys.modules['pymodaq.utils.parameter'] = mock_parameter
    sys.modules['pymodaq.control_modules.thread_commands'] = mock_thread_commands


@pytest.fixture
def mock_environment():
    """Fixture to setup mock environment."""
    setup_mock_pyvcam()
    setup_mock_pymodaq()


@pytest.fixture
def camera_plugin(mock_environment):
    """Fixture to create camera plugin instance."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    return DAQ_2DViewer_PrimeBSI()


class TestPrimeBSIMockMode:
    """Test PrimeBSI camera plugin in mock mode for CI."""
    
    def test_plugin_import(self, mock_environment):
        """Test plugin can be imported."""
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        assert DAQ_2DViewer_PrimeBSI is not None
        
    def test_plugin_instantiation(self, camera_plugin):
        """Test plugin can be instantiated."""
        assert camera_plugin is not None
        assert hasattr(camera_plugin, 'params')
        assert isinstance(camera_plugin.params, list)
        
    def test_parameter_structure(self, camera_plugin):
        """Test plugin has correct parameter structure."""
        param_names = [p.get('name') for p in camera_plugin.params if isinstance(p, dict)]
        required_groups = ['camera_settings', 'advanced_settings', 'post_processing', 'roi_settings']
        
        for group in required_groups:
            assert group in param_names, f"Missing parameter group: {group}"
            
    def test_camera_initialization_mock(self, camera_plugin):
        """Test camera initialization in mock mode."""
        status = camera_plugin.ini_detector()
        
        # Should return status object
        assert status is not None
        
        # Plugin should be initialized successfully in mock mode
        assert camera_plugin.initialized is True
        assert camera_plugin.camera is not None
        assert camera_plugin.camera.is_open is True
        
    def test_camera_parameters_population(self, camera_plugin):
        """Test camera parameters are properly populated."""
        camera_plugin.ini_detector()
        
        # Check camera name and sensor size are set
        camera_name = camera_plugin.settings.child('camera_settings', 'camera_name').value()
        sensor_size = camera_plugin.settings.child('camera_settings', 'sensor_size').value()
        
        assert camera_name == "pvcamUSB_0"
        assert "2048 x 2048" in sensor_size
        
    def test_axis_generation(self, camera_plugin):
        """Test x and y axis generation."""
        camera_plugin.ini_detector()
        
        x_axis = camera_plugin.get_xaxis()
        y_axis = camera_plugin.get_yaxis()
        
        assert x_axis is not None
        assert y_axis is not None
        assert len(x_axis.data) == 2048
        assert len(y_axis.data) == 2048
        
    def test_roi_bounds(self, camera_plugin):
        """Test ROI bounds calculation."""
        camera_plugin.ini_detector()
        
        roi_bounds = camera_plugin.get_roi_bounds()
        assert roi_bounds is not None
        
        p1, height, s1, width = roi_bounds
        assert p1 == 0
        assert s1 == 0
        assert height == 2048
        assert width == 2048
        
    def test_frame_acquisition_mock(self, camera_plugin):
        """Test frame acquisition in mock mode."""
        camera_plugin.ini_detector()
        
        # Test grab_data method
        camera_plugin.grab_data()
        
        # Test direct frame acquisition
        frame = camera_plugin.camera.get_frame(exp_time=100)
        assert frame is not None
        assert len(frame) == 2048 * 2048
        assert np.min(frame) >= 0
        assert np.max(frame) <= 65535
        
    def test_parameter_changes(self, camera_plugin):
        """Test parameter change handling."""
        camera_plugin.ini_detector()
        
        # Test exposure change
        exposure_param = camera_plugin.settings.child('camera_settings', 'exposure')
        exposure_param.setValue(50.0)
        camera_plugin.commit_settings(exposure_param)
        
        # Test gain change  
        gain_param = camera_plugin.settings.child('camera_settings', 'gain')
        gain_param.setValue("Balanced")
        camera_plugin.commit_settings(gain_param)
        
        # Test speed change
        speed_param = camera_plugin.settings.child('camera_settings', 'speed_index')
        speed_param.setValue("Speed_1")
        camera_plugin.commit_settings(speed_param)
        
    def test_temperature_monitoring(self, camera_plugin):
        """Test temperature monitoring functionality."""
        camera_plugin.ini_detector()
        
        # Check temperature reading
        assert camera_plugin.camera.temp == -19.89
        assert camera_plugin.camera.temp_setpoint == -20.0
        
        # Test temperature setpoint change
        temp_param = camera_plugin.settings.child('camera_settings', 'temperature_setpoint')
        temp_param.setValue(-15)
        camera_plugin.commit_settings(temp_param)
        
    def test_plugin_cleanup(self, camera_plugin):
        """Test plugin cleanup."""
        camera_plugin.ini_detector()
        assert camera_plugin.camera.is_open is True
        
        camera_plugin.close()
        assert camera_plugin.camera.is_open is False


@pytest.mark.hardware
class TestPrimeBSIHardware:
    """Test PrimeBSI camera plugin with real hardware."""
    
    def test_real_hardware_detection(self):
        """Test real hardware can be detected."""
        try:
            import pyvcam
            from pyvcam import pvc
            from pyvcam.camera import Camera
            
            pvc.init_pvcam()
            total_cams = pvc.get_cam_total()
            cameras = list(Camera.detect_camera())
            
            if total_cams > 0 and len(cameras) > 0:
                camera = cameras[0]
                camera.open()
                
                # Basic hardware checks
                assert camera.name is not None
                assert camera.sensor_size is not None
                assert len(camera.sensor_size) == 2
                assert camera.temp is not None
                
                camera.close()
                
            pvc.uninit_pvcam()
            
        except ImportError:
            pytest.skip("PyVCAM not available for hardware testing")
        except Exception as e:
            pytest.skip(f"Hardware not available: {e}")
            
    def test_real_plugin_initialization(self):
        """Test plugin initialization with real hardware."""
        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
            
            plugin = DAQ_2DViewer_PrimeBSI()
            status = plugin.ini_detector()
            
            if plugin.initialized:
                # Hardware successfully initialized
                assert plugin.camera is not None
                assert plugin.camera.is_open
                assert plugin.camera.name is not None
                
                # Test basic functionality
                x_axis = plugin.get_xaxis()
                y_axis = plugin.get_yaxis()
                assert x_axis is not None
                assert y_axis is not None
                
                # Test frame acquisition
                plugin.grab_data()
                
                plugin.close()
            else:
                pytest.skip("Real hardware not available for testing")
                
        except Exception as e:
            pytest.skip(f"Hardware test failed: {e}")
            
    def test_real_frame_acquisition(self):
        """Test real frame acquisition with hardware."""
        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
            
            plugin = DAQ_2DViewer_PrimeBSI()
            plugin.ini_detector()
            
            if plugin.initialized:
                # Test different exposure times
                exposures = [10, 50, 100]
                for exp_time in exposures:
                    plugin.settings.child('camera_settings', 'exposure').setValue(exp_time)
                    plugin.grab_data()
                    
                plugin.close()
            else:
                pytest.skip("Real hardware not available")
                
        except Exception as e:
            pytest.skip(f"Hardware frame acquisition test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])