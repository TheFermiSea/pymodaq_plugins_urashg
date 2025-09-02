from unittest.mock import MagicMock, patch
from qtpy.QtCore import Signal

# Mock the hardware controller import before importing the plugin
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
import pytest

# It's crucial to mock the hardware imports *before* importing the plugin class
MAITAI_CONTROLLER_PATH = "pymodaq_plugins_urashg.hardware.maitai_control.MaiTaiController"
mock_maitai_controller = MagicMock()

with patch(MAITAI_CONTROLLER_PATH, mock_maitai_controller):
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

class MockUI:
    """A mock class for the custom MaiTaiUI."""
    open_shutter_signal = Signal()
    close_shutter_signal = Signal()
    set_wavelength_signal = Signal(float)
    status_update_signal = Signal()
    check_errors_signal = Signal()
    
    def update_status(self, status_dict):
        pass

@pytest.fixture
def mock_plugin_maitai(qtbot):
    """Fixture to create and initialize the plugin with a mocked controller and UI."""
    # Reset the global mock before each test
    mock_maitai_controller.reset_mock()
    
    # Configure the mock controller's behavior
    mock_controller_instance = mock_maitai_controller.return_value
    mock_controller_instance.connect.return_value = True
    mock_controller_instance.get_wavelength.return_value = 800.0
    mock_controller_instance.get_power.return_value = 2.5
    mock_controller_instance.get_enhanced_shutter_state.return_value = (False, True) # shutter_open, emission_possible
    mock_controller_instance.get_status_byte.return_value = (2, {'modelocked': True}) # status_byte, status_info
    
    # Instantiate the plugin
    plugin = DAQ_Move_MaiTai()
    
    # Replace the real UI with our mock UI
    plugin.ui = MockUI()
    
    # Initialize the plugin (this connects signals)
    plugin.ini_stage()
    qtbot.wait_signal(timeout=100) # Allow signals to process
    
    # Attach the mock controller instance for easy access in tests
    plugin.mock_controller = mock_controller_instance
    
    return plugin

def test_maitai_plugin_init(mock_plugin_maitai):
    """Test the initialization process of the plugin."""
    plugin = mock_plugin_maitai
    # Check that the controller was instantiated and connect was called
    mock_maitai_controller.assert_called_once()
    plugin.mock_controller.connect.assert_called_once()
    assert plugin.initialized is True

def test_get_actuator_value(mock_plugin_maitai):
    """Test getting the actuator's value."""
    plugin = mock_plugin_maitai
    value = plugin.get_actuator_value()
    
    plugin.mock_controller.get_wavelength.assert_called_once()
    assert value.value() == 800.0

def test_move_abs(mock_plugin_maitai):
    """Test the move_abs method."""
    plugin = mock_plugin_maitai
    plugin.move_abs(850.0)
    
    plugin.mock_controller.set_wavelength.assert_called_with(850.0)

def test_shutter_signals(mock_plugin_maitai, qtbot):
    """Test that shutter signals from the UI call the correct methods."""
    plugin = mock_plugin_maitai
    
    # Mock the plugin's methods to see if they are called
    plugin.open_shutter = MagicMock()
    plugin.close_shutter = MagicMock()
    
    # Re-connect signals to the new mocked methods
    plugin.ui.open_shutter_signal.connect(plugin.open_shutter)
    plugin.ui.close_shutter_signal.connect(plugin.close_shutter)
    
    # Emit signals
    plugin.ui.open_shutter_signal.emit()
    qtbot.wait_signal(timeout=10)
    plugin.open_shutter.assert_called_once()

    plugin.ui.close_shutter_signal.emit()
    qtbot.wait_signal(timeout=10)
    plugin.close_shutter.assert_called_once()

def test_poll_status(mock_plugin_maitai, qtbot):
    """Test the poll_status method and its signal emission."""
    plugin = mock_plugin_maitai
    
    # Mock the receiving slot for the status_signal
    mock_status_slot = MagicMock()
    plugin.status_signal.connect(mock_status_slot)
    
    plugin.poll_status()
    qtbot.wait_signal(timeout=10)
    
    # Check that all controller methods were called
    plugin.mock_controller.get_wavelength.assert_called()
    plugin.mock_controller.get_power.assert_called()
    plugin.mock_controller.get_enhanced_shutter_state.assert_called()
    plugin.mock_controller.get_status_byte.assert_called()
    
    # Check that the signal was emitted with the correct data structure
    mock_status_slot.assert_called_once()
    status_arg = mock_status_slot.call_args[0][0]
    assert isinstance(status_arg, dict)
    assert 'wavelength' in status_arg
    assert 'power' in status_arg
    assert 'shutter_open' in status_arg
    assert 'modelocked' in status_arg
    assert status_arg['wavelength'] == 800.0
    assert status_arg['modelocked'] is True
