import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq.utils.conftests import qtbotsleep
from pymodaq_data.data import DataToExport, DataWithAxes

# Import the plugin class
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C

# Determine if we can run hardware tests
# This is a placeholder; a real implementation might check a config file or environment variable
# For now, we assume hardware is not available unless a specific pytest option is passed.
def is_hardware_available():
    # In a real CI/testing environment, you'd have a better way to check this.
    # For example, `return os.getenv("TEST_HW") == "1"`
    return False

# Conditionally mark tests that require hardware
hardware_test = pytest.mark.skipif(not is_hardware_available(), reason="Hardware not available for testing")

@pytest.fixture(params=["mock", "hardware"])
def newport_plugin_and_controller(qtbot, request):
    """
    Fixture to initialize the plugin in both mock and real hardware modes.
    """
    mode = request.param
    
    if mode == "hardware" and not is_hardware_available():
        pytest.skip("Hardware test skipped")

    if mode == "mock":
        # For mock tests, we patch the controller to ensure no real hardware is touched
        with patch('pymodaq_plugins_urashg.hardware.newport1830c_controller.Newport1830CController') as MockController:
            mock_instance = MockController.return_value
            mock_instance.connect.return_value = True
            mock_instance.get_multiple_readings.return_value = [1.23e-3, 1.24e-3]

            plugin = DAQ_0DViewer_Newport1830C()
            plugin.settings.child('connection_group', 'mock_mode').setValue(True)
            
            yield plugin, mock_instance
    else: # mode == "hardware"
        # For hardware tests, we use the real controller
        plugin = DAQ_0DViewer_Newport1830C()
        plugin.settings.child('connection_group', 'mock_mode').setValue(False)
        # You would configure the real serial port here if needed, e.g.:
        # plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB_NEWPORT')
        
        yield plugin, None # No mock controller instance

def test_newport_plugin_init(qtbot, newport_plugin_and_controller):
    """Test the initialization of the plugin in both modes."""
    plugin, mock_controller = newport_plugin_and_controller
    
    info, initialized = plugin.ini_detector()
    qtbotsleep(100)
    
    assert initialized is True
    if mock_controller: # Mock mode assertions
        mock_controller.connect.assert_called_once()

def test_grab_data(qtbot, newport_plugin_and_controller):
    """Test the grab_data method."""
    plugin, mock_controller = newport_plugin_and_controller
    
    # Initialize the detector first
    plugin.ini_detector()
    qtbotsleep(100)

    # Mock the dte_signal to capture the emitted data
    mock_dte_slot = MagicMock()
    plugin.dte_signal.connect(mock_dte_slot)
    
    plugin.grab_data(Naverage=2)
    qtbotsleep(100)

    # Check that the signal was emitted
    mock_dte_slot.assert_called_once()
    
    # Check the content of the emitted data
    emitted_dte = mock_dte_slot.call_args[0][0]
    assert isinstance(emitted_dte, DataToExport)
    assert len(emitted_dte.data) == 1
    
    data_with_axes = emitted_dte.data[0]
    assert isinstance(data_with_axes, DataWithAxes)
    
    # Extract the numerical data
    emitted_data = data_with_axes.data[0]
    assert isinstance(emitted_data, np.ndarray)
    
    if mock_controller: # Mock mode assertions
        # Check that the controller was called correctly
        mock_controller.get_multiple_readings.assert_called_with(2)
        # Check that the emitted value is the average of the mocked readings
        assert emitted_data[0] == pytest.approx(1.235e-3)
    else: # Hardware mode assertions
        # For real hardware, we can't know the exact value, but we can check the type and shape
        assert emitted_data.shape == (1,)
        assert isinstance(emitted_data[0], float)
        print(f"Hardware returned power: {emitted_data[0]}")

def test_commit_settings(qtbot, newport_plugin_and_controller):
    """Test changing settings like wavelength."""
    plugin, mock_controller = newport_plugin_and_controller

    plugin.ini_detector()
    qtbotsleep(100)

    # Get the wavelength parameter from the settings tree
    wavelength_param = plugin.settings.child('measurement_group', 'wavelength')
    
    # Change the wavelength
    wavelength_param.setValue(810.0)
    qtbotsleep(100)

    if mock_controller: # Mock mode assertions
        mock_controller.set_wavelength.assert_called_with(810.0)
    else: # Hardware mode assertions
        # In hardware mode, we can't easily verify, but this ensures the code runs without error.
        # A more advanced test could query the device again to check if the setting was applied.
        pass
