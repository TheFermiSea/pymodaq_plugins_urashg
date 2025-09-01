"""
Hardware tests for the CameraWrapper class.
"""
import pytest
from pymodaq_plugins_urashg.hardware.camera_wrapper import CameraWrapper, HardwareError

@pytest.mark.hardware
def test_camera_hardware_connect_disconnect():
    """Test connecting to and disconnecting from the camera hardware."""
    wrapper = CameraWrapper()
    try:
        wrapper.connect()
        assert wrapper.is_connected()
    finally:
        wrapper.disconnect()
    assert not wrapper.is_connected()

@pytest.mark.hardware
def test_camera_hardware_get_frame():
    """Test acquiring a frame from the camera hardware."""
    wrapper = CameraWrapper()
    try:
        wrapper.connect()
        frame = wrapper.get_frame(10)
        assert frame is not None
        assert frame.shape == wrapper.camera.sensor_size
    finally:
        wrapper.disconnect()
