#!/usr/bin/env python3
"""
Unit tests for the DAQ_2DViewer_PrimeBSI plugin.
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
def mock_pyvcam():
    """Fixture to provide a mock pyvcam module."""
    with (
        patch(
            "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI.pvc"
        ) as mock_pvc,
        patch(
            "pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI.Camera"
        ) as mock_camera,
    ):
        mock_pvc.get_cam_total.return_value = 1
        mock_camera.detect_camera.return_value = [Mock()]
        yield mock_pvc, mock_camera


@pytest.fixture
def primebsi_plugin(mock_pyvcam):
    """Fixture to create a DAQ_2DViewer_PrimeBSI instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
        DAQ_2DViewer_PrimeBSI,
    )

    plugin = DAQ_2DViewer_PrimeBSI(None, None)
    plugin.camera = mock_pyvcam[1]
    yield plugin


def test_plugin_instantiation(primebsi_plugin):
    """Test that the plugin can be instantiated."""
    assert primebsi_plugin is not None


def test_ini_detector(primebsi_plugin):
    """Test the ini_detector method."""
    info_string, success = primebsi_plugin.ini_detector()
    assert success is True
    assert "Camera Initialized" in info_string


def test_close(primebsi_plugin):
    """Test the close method."""
    primebsi_plugin.close()
    primebsi_plugin.camera.close.assert_called_once()
