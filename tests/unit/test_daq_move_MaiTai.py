#!/usr/bin/env python3
"""
Unit tests for the DAQ_Move_MaiTai plugin.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_maitai_controller():
    """Fixture to provide a mock MaiTaiController."""
    with patch(
        "pymodaq_plugins_urashg.hardware.urashg.maitai_control.MaiTaiController"
    ) as mock_controller:
        yield mock_controller


@pytest.fixture
def maitai_plugin(mock_maitai_controller):
    """Fixture to create a DAQ_Move_MaiTai instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai(None, None)
    plugin.controller = mock_maitai_controller
    yield plugin


def test_plugin_instantiation(maitai_plugin):
    """Test that the plugin can be instantiated."""
    assert maitai_plugin is not None


def test_ini_stage(maitai_plugin):
    """Test the ini_stage method."""
    maitai_plugin.settings.child("connection_group", "serial_port").setValue(
        "/dev/ttyUSB0"
    )
    info_string, success = maitai_plugin.ini_stage()
    assert success is True
    assert "MaiTai laser initialized" in info_string


def test_close(maitai_plugin):
    """Test the close method."""
    maitai_plugin.close()
    maitai_plugin.controller.disconnect.assert_called_once()
