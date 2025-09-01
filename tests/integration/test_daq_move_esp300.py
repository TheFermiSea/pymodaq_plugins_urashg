"""
Integration tests for the DAQ_Move_ESP300 plugin.
"""
import pytest
from unittest.mock import patch
import numpy as np

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, DataActuator
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
from pymodaq_plugins_urashg.hardware.esp300_controller import MockESP300Controller, AxisConfig

@pytest.fixture
def esp300_plugin(qtbot):
    """Fixture for the DAQ_Move_ESP300 plugin."""
    with patch.object(DAQ_Move_ESP300, 'ini_stage') as mock_ini:
        mock_ini.return_value = ('', True)
        plugin = DAQ_Move_ESP300(parent=None, params_state=None)
        axes_config = [AxisConfig(number=1, name='X'), AxisConfig(number=2, name='Y')]
        plugin.controller = MockESP300Controller(port='COM1', axes_config=axes_config)
        plugin.controller.connect()
        yield plugin
        plugin.close()

def test_esp300_plugin_initialization(esp300_plugin):
    """Test the initialization of the DAQ_Move_ESP300 plugin."""
    assert esp300_plugin.initialized
    assert esp300_plugin.controller is not None

def test_esp300_plugin_move_abs(esp300_plugin):
    """Test the move_abs method of the DAQ_Move_ESP300 plugin."""
    position = DataActuator(data=[np.array([10.0, 20.0])])
    esp300_plugin.move_abs(position)
    positions = esp300_plugin.controller.get_all_positions()
    assert positions == {1: 10.0, 2: 20.0}
