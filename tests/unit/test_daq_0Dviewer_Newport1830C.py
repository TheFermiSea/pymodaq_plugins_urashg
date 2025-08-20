#!/usr/bin/env python3
"""
Unit tests for the DAQ_0DViewer_Newport1830C plugin.
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
def mock_newport_controller():
    """Fixture to provide a mock Newport1830CController."""
    with patch(
        "pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller.Newport1830CController"
    ) as mock_controller:
        yield mock_controller


@pytest.fixture
def newport_plugin(mock_newport_controller):
    """Fixture to create a DAQ_0DViewer_Newport1830C instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
        DAQ_0DViewer_Newport1830C,
    )

    plugin = DAQ_0DViewer_Newport1830C(None, None)
    plugin.controller = mock_newport_controller
    yield plugin


def test_plugin_instantiation(newport_plugin):
    """Test that the plugin can be instantiated."""
    assert newport_plugin is not None


def test_ini_detector(newport_plugin):
    """Test the ini_detector method."""
    newport_plugin.settings.child("connection_group", "serial_port").setValue(
        "/dev/ttyS0"
    )
    info_string, success = newport_plugin.ini_detector()
    assert success is True
    assert "Newport 1830-C initialized" in info_string


def test_close(newport_plugin):
    """Test the close method."""
    newport_plugin.close()
    if newport_plugin.controller is not None:
        newport_plugin.controller.disconnect.assert_called_once()
