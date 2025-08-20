#!/usr/bin/env python3
"""
Unit tests for the DAQ_Move_Elliptec plugin.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_elliptec_controller():
    """Fixture to provide a mock ElliptecController."""
    with patch(
        "pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper.ElliptecController"
    ) as mock_controller:
        yield mock_controller


@pytest.fixture
def elliptec_plugin(mock_elliptec_controller):
    """Fixture to create a DAQ_Move_Elliptec instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec(None, None)
    plugin.controller = mock_elliptec_controller
    yield plugin


def test_plugin_instantiation(elliptec_plugin):
    """Test that the plugin can be instantiated."""
    assert elliptec_plugin is not None


def test_ini_stage(elliptec_plugin):
    """Test the ini_stage method."""
    elliptec_plugin.settings.child("connection_group", "serial_port").setValue(
        "/dev/ttyUSB0"
    )
    info_string, success = elliptec_plugin.ini_stage()
    assert success is True
    assert "Elliptec mounts initialized" in info_string


def test_close(elliptec_plugin):
    """Test the close method."""
    elliptec_plugin.close()
    elliptec_plugin.controller.disconnect.assert_called_once()
