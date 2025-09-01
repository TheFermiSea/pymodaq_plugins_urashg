"""
Hardware tests for the MaiTaiController class.
"""
import pytest
from pymodaq_plugins_urashg.hardware.maitai_control import MaiTaiController, MaiTaiError

@pytest.mark.hardware
def test_maitai_hardware_connect_disconnect():
    """Test connecting to and disconnecting from the MaiTai laser hardware."""
    # NOTE: Replace 'COM1' with the actual serial port of your MaiTai laser
    controller = MaiTaiController(port='COM1')
    try:
        controller.connect()
        assert controller._connected
    finally:
        controller.disconnect()
    assert not controller._connected

@pytest.mark.hardware
def test_maitai_hardware_get_wavelength():
    """Test getting the wavelength from the MaiTai laser hardware."""
    # NOTE: Replace 'COM1' with the actual serial port of your MaiTai laser
    controller = MaiTaiController(port='COM1')
    try:
        controller.connect()
        wavelength = controller.get_wavelength()
        assert isinstance(wavelength, float)
    finally:
        controller.disconnect()
