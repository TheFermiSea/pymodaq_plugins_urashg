import pytest
from unittest.mock import MagicMock

# Assume the controller is in the hardware directory
from pymodaq_plugins_urashg.hardware.elliptec_wrapper import ElliptecController

@pytest.fixture
def mock_elliptec_controller():
    """Fixture to create an ElliptecController in mock mode."""
    import logging
    logging.basicConfig()
    # Initialize with 3 mock axes
    controller = ElliptecController(mount_addresses="2,3,8", mock_mode=True)
    controller.connect()
    # Mock the serial connection for deep control
    controller.serial = MagicMock()
    return controller

def test_elliptec_init_and_connect():
    """Test initialization and connection."""
    controller = ElliptecController(mount_addresses="2,3,8", mock_mode=True)
    assert controller.mock_mode is True
    assert controller.is_connected() is False
    assert controller.mount_addresses == [2, 3, 8]
    controller.connect()
    assert controller.is_connected() is True

def test_move_absolute(mock_elliptec_controller):
    """Test the move_absolute method."""
    mock_elliptec_controller.send_command = MagicMock(return_value="OK")
    
    # Address '2' is the first axis in the list
    success = mock_elliptec_controller.move_absolute('2', 90.0)
    
    assert success is True
    # Elliptec protocol: 'a' for absolute move, address, position in hex motor steps
    # We just check that a command was sent with the right address.
    # The conversion to motor steps is a detail of the implementation.
    mock_elliptec_controller.send_command.assert_called()
    call_args = mock_elliptec_controller.send_command.call_args[0][0]
    assert call_args.startswith('2a')

def test_move_relative(mock_elliptec_controller):
    """Test the move_relative method."""
    mock_elliptec_controller.send_command = MagicMock(return_value="OK")
    
    # Address '3' is the second axis
    success = mock_elliptec_controller.move_relative('3', -10.5)
    
    assert success is True
    # Elliptec protocol: 'c' for relative move
    mock_elliptec_controller.send_command.assert_called()
    call_args = mock_elliptec_controller.send_command.call_args[0][0]
    assert call_args.startswith('3c')

def test_get_position(mock_elliptec_controller):
    """Test the get_position method."""
    # The response is address, 'i', and position in hex motor steps
    # '2i' + position for 45 degrees
    mock_elliptec_controller.send_command = MagicMock(return_value='2i' + '0' * 14 + '2000000') 
    
    pos = mock_elliptec_controller.get_position('2')
    
    assert pos == pytest.approx(45.0)
    mock_elliptec_controller.send_command.assert_called_with('2i')

def test_get_all_positions(mock_elliptec_controller):
    """Test getting positions for all registered axes."""
    def command_side_effect(cmd):
        if cmd == '2i':
            return '2i' + '0' * 14 + '2000000' # 45 deg
        if cmd == '3i':
            return '3i' + '0' * 14 + '4000000' # 90 deg
        if cmd == '8i':
            return '8i' + '0' * 15 + '0' # 0 deg
        return ""
        
    mock_elliptec_controller.send_command = MagicMock(side_effect=command_side_effect)
    
    positions = mock_elliptec_controller.get_all_positions()
    
    assert isinstance(positions, dict)
    assert '2' in positions
    assert '3' in positions
    assert '8' in positions
    assert positions['2'] == pytest.approx(45.0)
    assert positions['3'] == pytest.approx(90.0)
    assert positions['8'] == pytest.approx(0.0)

def test_home_axis(mock_elliptec_controller):
    """Test homing a single axis."""
    mock_elliptec_controller.send_command = MagicMock(return_value="OK")
    
    success = mock_elliptec_controller.home('8')
    assert success is True
    mock_elliptec_controller.send_command.assert_called_with('8h')

def test_home_all(mock_elliptec_controller):
    """Test homing all axes."""
    mock_elliptec_controller.send_command = MagicMock(return_value="OK")
    
    success = mock_elliptec_controller.home_all()
    assert success is True
    # It should have called home for each address
    assert mock_elliptec_controller.send_command.call_count == 3
    calls = mock_elliptec_controller.send_command.call_args_list
    assert any('2h' in call[0][0] for call in calls)
    assert any('3h' in call[0][0] for call in calls)
    assert any('8h' in call[0][0] for call in calls)
