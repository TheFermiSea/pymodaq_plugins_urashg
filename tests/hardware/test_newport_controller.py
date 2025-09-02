import pytest
from unittest.mock import MagicMock

from pymodaq_plugins_urashg.hardware.newport1830c_controller import Newport1830CController, MockNewport1830CController

@pytest.fixture
def mock_newport_controller():
    """Fixture to create a Newport1830CController in mock mode."""
    import logging
    logging.basicConfig()
    controller = MockNewport1830CController(port="COM_MOCK")
    controller.connect()
    # Mock the serial connection for deep control
    controller.ser = MagicMock()
    return controller

def test_newport_init_and_connect():
    """Test initialization and connection."""
    controller = MockNewport1830CController(port="COM_MOCK")
    assert controller.mock_mode is True
    assert controller.is_connected() is False
    controller.connect()
    assert controller.is_connected() is True

def test_get_power(mock_newport_controller):
    """Test the get_power method."""
    # Mock the controller's response
    mock_newport_controller._send_command = MagicMock(return_value="1.234E-3")
    power = mock_newport_controller.get_power()
    
    assert power == pytest.approx(1.234e-3)
    mock_newport_controller._send_command.assert_called_with("D?")

def test_set_wavelength(mock_newport_controller):
    """Test the set_wavelength method."""
    mock_newport_controller._send_command = MagicMock()
    success = mock_newport_controller.set_wavelength(780)
    
    assert success is True
    mock_newport_controller._send_command.assert_called_with("L=780")

def test_set_units(mock_newport_controller):
    """Test setting the measurement units."""
    mock_newport_controller._send_command = MagicMock()
    # Test setting units to Watts (U=0)
    success_w = mock_newport_controller.set_units("W")
    assert success_w is True
    mock_newport_controller._send_command.assert_called_with("U=0")

    # Test setting units to dBm (U=1)
    success_dbm = mock_newport_controller.set_units("dBm")
    assert success_dbm is True
    mock_newport_controller._send_command.assert_called_with("U=1")

def test_zero_adjust(mock_newport_controller):
    """Test the zero adjust functionality."""
    mock_newport_controller._send_command = MagicMock()
    success = mock_newport_controller.zero_adjust()
    
    assert success is True
    mock_newport_controller._send_command.assert_called_with("Z")

def test_get_multiple_readings(mock_newport_controller):
    """Test the averaging logic."""
    # Simulate a series of power readings
    mock_newport_controller._send_command = MagicMock(side_effect=["1.0E-3", "1.2E-3", "1.4E-3"])
    
    readings = mock_newport_controller.get_multiple_readings(3)
    
    assert len(readings) == 3
    assert readings[0] == 1.0e-3
    assert readings[1] == 1.2e-3
    assert readings[2] == 1.4e-3
    assert mock_newport_controller._send_command.call_count == 3
