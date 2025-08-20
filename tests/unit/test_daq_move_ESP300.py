#!/usr/bin/env python3
"""
Unit tests for the DAQ_Move_ESP300 plugin.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [
    pytest.mark.unit
]

@pytest.fixture
def mock_esp300_controller():
    """Fixture to provide a mock ESP300Controller."""
    with patch('pymodaq_plugins_urashg.hardware.urashg.esp300_controller.ESP300Controller') as mock_controller:
        yield mock_controller

@pytest.fixture
def esp300_plugin(mock_esp300_controller):
    """Fixture to create a DAQ_Move_ESP300 instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
    plugin = DAQ_Move_ESP300(None, None)
    plugin.controller = mock_esp300_controller
    yield plugin

def test_plugin_instantiation(esp300_plugin):
    """Test that the plugin can be instantiated."""
    assert esp300_plugin is not None

def test_ini_stage(esp300_plugin):
    """Test the ini_stage method."""
    esp300_plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB0')
    info_string, success = esp300_plugin.ini_stage()
    assert success is True
    assert "ESP300 initialized" in info_string

def test_close(esp300_plugin):
    """Test the close method."""
    esp300_plugin.close()
    if esp300_plugin.controller is not None:
        esp300_plugin.controller.disconnect.assert_called_once()
