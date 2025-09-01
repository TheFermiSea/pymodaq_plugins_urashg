"""
Unit tests for the Newport1830CController and MockNewport1830CController classes.
"""
import pytest
from unittest.mock import MagicMock, patch

from pymodaq_plugins_urashg.hardware.newport1830c_controller import Newport1830CController, MockNewport1830CController, Newport1830CError

@pytest.fixture
def mock_newport_controller():
    """Fixture for a mock Newport 1830C controller."""
    return MockNewport1830CController(port='COM1')

def test_mock_newport_controller_connect_disconnect(mock_newport_controller):
    """Test the connect and disconnect methods of the mock Newport 1830C controller."""
    mock_newport_controller.connect()
    assert mock_newport_controller._connected
    mock_newport_controller.disconnect()
    assert not mock_newport_controller._connected

def test_mock_newport_controller_get_power(mock_newport_controller):
    """Test the get_power method of the mock Newport 1830C controller."""
    mock_newport_controller.connect()
    power = mock_newport_controller.get_power()
    assert isinstance(power, float)

@patch('pymodaq_plugins_urashg.hardware.newport1830c_controller.serial')
def test_newport_controller_connect_disconnect(mock_serial):
    """Test the connect and disconnect methods of the Newport 1830C controller."""
    mock_serial.Serial.return_value = MagicMock()
    controller = Newport1830CController(port='COM1')
    with patch.object(controller, '_send_command', return_value='1'):
        controller.connect()
        assert controller._connected
    controller.disconnect()
    assert not controller._connected
