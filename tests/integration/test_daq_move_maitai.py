"""
Integration tests for the DAQ_Move_MaiTai plugin.
"""
import pytest
from unittest.mock import patch

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
from pymodaq_plugins_urashg.hardware.maitai_control import MockMaiTaiController

@pytest.fixture
def maitai_plugin(qtbot):
    """Fixture for the DAQ_Move_MaiTai plugin."""
    with patch.object(DAQ_Move_MaiTai, 'ini_stage') as mock_ini:
        mock_ini.return_value = ('', True)
        plugin = DAQ_Move_MaiTai(parent=None, params_state=None)
        plugin.controller = MockMaiTaiController(port='COM1')
        plugin.controller.connect()
        yield plugin
        plugin.close()

def test_maitai_plugin_initialization(maitai_plugin):
    """Test the initialization of the DAQ_Move_MaiTai plugin."""
    assert maitai_plugin.initialized
    assert maitai_plugin.controller is not None

def test_maitai_plugin_move_abs(maitai_plugin):
    """Test the move_abs method of the DAQ_Move_MaiTai plugin."""
    maitai_plugin.move_abs(800.0)
    assert maitai_plugin.controller.get_wavelength() == 800.0
