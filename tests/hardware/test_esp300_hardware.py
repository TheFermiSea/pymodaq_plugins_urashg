"""
Hardware tests for the ESP300Controller class.
"""
import pytest
from pymodaq_plugins_urashg.hardware.esp300_controller import ESP300Controller, ESP300Error, AxisConfig

@pytest.mark.hardware
def test_esp300_hardware_connect_disconnect():
    """Test connecting to and disconnecting from the ESP300 controller hardware."""
    # NOTE: Replace 'COM1' with the actual serial port of your ESP300 controller
    controller = ESP300Controller(port='COM1')
    try:
        controller.connect()
        assert controller._connected
    finally:
        controller.disconnect()
    assert not controller._connected

@pytest.mark.hardware
def test_esp300_hardware_get_all_positions():
    """Test getting all positions from the ESP300 controller hardware."""
    # NOTE: Replace 'COM1' with the actual serial port of your ESP300 controller
    axes_config = [AxisConfig(number=1, name='X'), AxisConfig(number=2, name='Y')]
    controller = ESP300Controller(port='COM1', axes_config=axes_config)
    try:
        controller.connect()
        positions = controller.get_all_positions()
        assert isinstance(positions, dict)
    finally:
        controller.disconnect()
