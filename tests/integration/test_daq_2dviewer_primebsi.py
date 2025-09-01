"""
Integration tests for the DAQ_2DViewer_PrimeBSI plugin.
"""
import pytest
from unittest.mock import patch

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
from pymodaq_plugins_urashg.hardware.camera_wrapper import MockCameraWrapper

@pytest.fixture
def primebsi_plugin(qtbot):
    """Fixture for the DAQ_2DViewer_PrimeBSI plugin."""
    with patch.object(DAQ_2DViewer_PrimeBSI, 'ini_detector') as mock_ini:
        mock_ini.return_value = ('', True)
        plugin = DAQ_2DViewer_PrimeBSI(parent=None, params_state=None)
        plugin.controller = MockCameraWrapper()
        plugin.controller.connect()
        yield plugin
        plugin.close()

def test_primebsi_plugin_initialization(primebsi_plugin):
    """Test the initialization of the DAQ_2DViewer_PrimeBSI plugin."""
    assert primebsi_plugin.initialized
    assert primebsi_plugin.controller is not None

def test_primebsi_plugin_grab_data(primebsi_plugin, qtbot):
    """Test the grab_data method of the DAQ_2DViewer_PrimeBSI plugin."""
    with qtbot.waitSignal(primebsi_plugin.dte_signal, timeout=1000) as blocker:
        primebsi_plugin.grab_data()
    assert blocker.args[0] is not None
