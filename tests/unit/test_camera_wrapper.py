"""
Unit tests for the CameraWrapper and MockCameraWrapper classes.
"""
import pytest
from unittest.mock import MagicMock, patch

from pymodaq_plugins_urashg.hardware.camera_wrapper import CameraWrapper, MockCameraWrapper, HardwareError

@pytest.fixture
def mock_camera_wrapper():
    """Fixture for a mock camera wrapper."""
    return MockCameraWrapper()

def test_mock_camera_wrapper_connect_disconnect(mock_camera_wrapper):
    """Test the connect and disconnect methods of the mock camera wrapper."""
    mock_camera_wrapper.connect()
    assert mock_camera_wrapper.is_connected()
    mock_camera_wrapper.disconnect()
    assert not mock_camera_wrapper.is_connected()

def test_mock_camera_wrapper_get_frame(mock_camera_wrapper):
    """Test the get_frame method of the mock camera wrapper."""
    frame = mock_camera_wrapper.get_frame(100)
    assert frame.shape == (2048, 2048)
    assert frame.dtype == 'uint16'

def test_mock_camera_wrapper_get_camera_properties(mock_camera_wrapper):
    """Test the get_camera_properties method of the mock camera wrapper."""
    props = mock_camera_wrapper.get_camera_properties()
    assert props['name'] == 'MockCamera'
    assert props['sensor_size'] == (2048, 2048)

@patch('pymodaq_plugins_urashg.hardware.camera_wrapper.pvc')
@patch('pymodaq_plugins_urashg.hardware.camera_wrapper.Camera')
def test_camera_wrapper_connect_disconnect(mock_camera, mock_pvc):
    """Test the connect and disconnect methods of the camera wrapper."""
    mock_camera.detect_camera.return_value = [MagicMock()]
    wrapper = CameraWrapper()
    wrapper.connect()
    assert wrapper.is_connected()
    wrapper.disconnect()
    assert not wrapper.is_connected()
