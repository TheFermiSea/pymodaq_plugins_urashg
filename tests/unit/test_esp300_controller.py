"""
Unit tests for the ESP300Controller and MockESP300Controller classes.
"""
import pytest
from unittest.mock import MagicMock, patch

from pymodaq_plugins_urashg.hardware.esp300_controller import ESP300Controller, MockESP300Controller, ESP300Error, AxisConfig

@pytest.fixture
def mock_esp300_controller():
    """Fixture for a mock ESP300 controller."""
    axes_config = [AxisConfig(number=1, name='X'), AxisConfig(number=2, name='Y')]
    return MockESP300Controller(port='COM1', axes_config=axes_config)

def test_mock_esp300_controller_connect_disconnect(mock_esp300_controller):
    """Test the connect and disconnect methods of the mock ESP300 controller."""
    mock_esp300_controller.connect()
    assert mock_esp300_controller._connected
    mock_esp300_controller.disconnect()
    assert not mock_esp300_controller._connected

def test_mock_esp300_controller_get_all_positions(mock_esp300_controller):
    """Test the get_all_positions method of the mock ESP300 controller."""
    mock_esp300_controller.connect()
    positions = mock_esp300_controller.get_all_positions()
    assert positions == {1: 0.0, 2: 0.0}

@patch('pymodaq_plugins_urashg.hardware.esp300_controller.serial')
def test_esp300_controller_connect_disconnect(mock_serial):
    """Test the connect and disconnect methods of the ESP300 controller."""
    mock_serial.Serial.return_value = MagicMock()
    controller = ESP300Controller(port='COM1')
    with patch.object(controller, '_send_command', return_value='1'):
        controller.connect()
        assert controller._connected
    controller.disconnect()
    assert not controller._connected
