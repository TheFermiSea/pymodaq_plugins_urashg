import pytest
from unittest.mock import MagicMock, patch

# Assume the controller is in the hardware directory now
from pymodaq_plugins_urashg.hardware.maitai_control import MaiTaiController

@pytest.fixture
def mock_maitai_controller():
    """Fixture to create a MaiTaiController in mock mode."""
    # The controller's __init__ might try to log, so ensure logging is configured
    import logging
    logging.basicConfig()
    controller = MaiTaiController(mock_mode=True)
    # Mock the serial connection part even in mock mode for full control
    controller._serial_connection = MagicMock()
    controller.connect()
    return controller

def test_maitai_controller_init():
    """Test the initialization of the MaiTaiController."""
    controller = MaiTaiController(mock_mode=True)
    assert controller.mock_mode is True
    assert controller._connected is False

def test_maitai_controller_connect_disconnect(mock_maitai_controller):
    """Test the connect and disconnect methods."""
    assert mock_maitai_controller.is_connected() is True
    mock_maitai_controller.disconnect()
    assert mock_maitai_controller.is_connected() is False

def test_get_wavelength_mock(mock_maitai_controller):
    """Test getting the wavelength in mock mode."""
    # Mock the internal mock command handler to return a predictable value
    mock_maitai_controller._mock_send_command = MagicMock(return_value="800.0 nm")
    wavelength = mock_maitai_controller.get_wavelength()
    assert wavelength == 800.0
    mock_maitai_controller._mock_send_command.assert_called_with("WAVELENGTH?")

def test_set_wavelength_mock(mock_maitai_controller):
    """Test setting the wavelength in mock mode."""
    mock_maitai_controller._mock_send_command = MagicMock(return_value="") # Set commands have no response
    success = mock_maitai_controller.set_wavelength(850.5)
    assert success is True
    mock_maitai_controller._mock_send_command.assert_called_with("WAVELENGTH 850.5", expect_response=False)
    
    # Check internal state if possible (requires refactoring controller or further mocking)
    # For now, we trust the command was sent correctly.

def test_get_power_mock(mock_maitai_controller):
    """Test getting the power in mock mode."""
    mock_maitai_controller._mock_send_command = MagicMock(return_value="2.123 W")
    power = mock_maitai_controller.get_power()
    assert power == 2.123
    mock_maitai_controller._mock_send_command.assert_called_with("POWER?")

def test_shutter_control_mock(mock_maitai_controller):
    """Test opening and closing the shutter in mock mode."""
    mock_maitai_controller._mock_send_command = MagicMock(return_value="")
    
    success_open = mock_maitai_controller.open_shutter()
    assert success_open is True
    mock_maitai_controller._mock_send_command.assert_called_with("SHUTTER 1", expect_response=False)

    success_close = mock_maitai_controller.close_shutter()
    assert success_close is True
    mock_maitai_controller._mock_send_command.assert_called_with("SHUTTER 0", expect_response=False)

def test_get_status_byte_mock(mock_maitai_controller):
    """Test getting the status byte in mock mode."""
    # Bit 0 for emission, Bit 1 for modelocked
    mock_maitai_controller._mock_send_command = MagicMock(return_value="3") # 3 = 0b0011
    status_byte, status_info = mock_maitai_controller.get_status_byte()
    assert status_byte == 3
    assert status_info['emission_possible'] is True
    assert status_info['modelocked'] is True
    mock_maitai_controller._mock_send_command.assert_called_with("*STB?")

def test_check_system_errors_mock(mock_maitai_controller):
    """Test checking for system errors in mock mode."""
    # Simulate a sequence of one error then no error
    mock_maitai_controller._mock_send_command = MagicMock(side_effect=["-101,Some Error", "0,No error"])
    has_errors, errors = mock_maitai_controller.check_system_errors()
    assert has_errors is True
    assert len(errors) == 1
    assert "Error -101: Some Error" in errors[0]
    assert mock_maitai_controller._mock_send_command.call_count == 2
