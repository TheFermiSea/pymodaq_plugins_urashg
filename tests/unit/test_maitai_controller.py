"""
Unit tests for the MaiTaiController and MockMaiTaiController classes.
"""
import pytest
from unittest.mock import MagicMock, patch

from pymodaq_plugins_urashg.hardware.maitai_control import MaiTaiController, MockMaiTaiController, MaiTaiError

@pytest.fixture
def mock_maitai_controller():
    """Fixture for a mock MaiTai controller."""
    return MockMaiTaiController(port='COM1')

def test_mock_maitai_controller_connect_disconnect(mock_maitai_controller):
    """Test the connect and disconnect methods of the mock MaiTai controller."""
    mock_maitai_controller.connect()
    assert mock_maitai_controller._connected
    mock_maitai_controller.disconnect()
    assert not mock_maitai_controller._connected

def test_mock_maitai_controller_get_set_wavelength(mock_maitai_controller):
    """Test the get_wavelength and set_wavelength methods of the mock MaiTai controller."""
    mock_maitai_controller.connect()
    mock_maitai_controller.set_wavelength(800.0)
    assert mock_maitai_controller.get_wavelength() == 800.0

def test_mock_maitai_controller_get_set_shutter(mock_maitai_controller):
    """Test the set_shutter and get_shutter_state methods of the mock MaiTai controller."""
    mock_maitai_controller.connect()
    mock_maitai_controller.set_shutter(True)
    assert mock_maitai_controller.get_shutter_state() is True
    mock_maitai_controller.set_shutter(False)
    assert mock_maitai_controller.get_shutter_state() is False

@patch('pymodaq_plugins_urashg.hardware.maitai_control.serial')
def test_maitai_controller_connect_disconnect(mock_serial):
    """Test the connect and disconnect methods of the MaiTai controller."""
    mock_serial.Serial.return_value = MagicMock()
    controller = MaiTaiController(port='COM1')
    with patch.object(controller, '_test_communication', return_value=True):
        controller.connect()
        assert controller._connected
    controller.disconnect()
    assert not controller._connected
