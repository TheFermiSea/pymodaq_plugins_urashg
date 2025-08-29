#!/usr/bin/env python3
"""
Unit tests for the DAQ_2DViewer_PrimeBSI plugin.
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
def mock_pyvcam(monkeypatch):
    """Fixture to provide a mock pyvcam module."""
    mock_pvc = Mock()
    mock_pvc.get_cam_total.return_value = 1
    
    mock_camera_class = Mock()
    mock_camera_instance = Mock()
    mock_camera_class.open.return_value = mock_camera_instance
    
    # Mock the modules in sys.modules so they are used on import
    monkeypatch.setitem(sys.modules, "pyvcam", Mock(pvc=mock_pvc, Camera=mock_camera_class))
    monkeypatch.setitem(sys.modules, "pyvcam.pvc", mock_pvc)
    monkeypatch.setitem(sys.modules, "pyvcam.camera", Mock(Camera=mock_camera_class))
    
    yield mock_pvc, mock_camera_class


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
    assert "Mock camera initialized" in info_string


def test_close(primebsi_plugin):
    """Test the close method."""
    primebsi_plugin.close()
    primebsi_plugin.camera.close.assert_called_once()
