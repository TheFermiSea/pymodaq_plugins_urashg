"""
Unit tests for PyMoDAQ plugins
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.mark.unit
def test_maitai_plugin_import():
    """Test MaiTai plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    assert DAQ_Move_MaiTai is not None


@pytest.mark.unit
def test_elliptec_plugin_import():
    """Test Elliptec plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    assert DAQ_Move_Elliptec is not None


@pytest.mark.unit
def test_esp300_plugin_import():
    """Test ESP300 plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300

    assert DAQ_Move_ESP300 is not None


@pytest.mark.unit
def test_newport1830c_plugin_import():
    """Test Newport 1830C plugin can be imported"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
        DAQ_0DViewer_Newport1830C,
    )

    assert DAQ_0DViewer_Newport1830C is not None


@pytest.mark.unit
def test_primebsi_plugin_import():
    """Test PrimeBSI plugin can be imported"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
        DAQ_2DViewer_PrimeBSI,
    )

    assert DAQ_2DViewer_PrimeBSI is not None


@pytest.mark.unit
def test_maitai_plugin_creation():
    """Test MaiTai plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    assert plugin is not None
    assert hasattr(plugin, "settings")


@pytest.mark.unit
def test_elliptec_plugin_creation():
    """Test Elliptec plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()
    assert plugin is not None
    assert hasattr(plugin, "settings")


@pytest.mark.unit
def test_esp300_plugin_creation():
    """Test ESP300 plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300

    plugin = DAQ_Move_ESP300()
    assert plugin is not None
    assert hasattr(plugin, "settings")


@pytest.mark.unit
def test_newport1830c_plugin_creation():
    """Test Newport 1830C plugin creation"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
        DAQ_0DViewer_Newport1830C,
    )

    plugin = DAQ_0DViewer_Newport1830C()
    assert plugin is not None
    assert hasattr(plugin, "settings")


@pytest.mark.unit
def test_primebsi_plugin_creation():
    """Test PrimeBSI plugin creation"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
        DAQ_2DViewer_PrimeBSI,
    )

    plugin = DAQ_2DViewer_PrimeBSI()
    assert plugin is not None
    assert hasattr(plugin, "settings")


@pytest.mark.unit
def test_esp300_mock_mode_initialization():
    """Test ESP300 plugin initialization in mock mode"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300

    plugin = DAQ_Move_ESP300()

    # Enable mock mode
    plugin.settings.child("connection_group", "mock_mode").setValue(True)

    # Test initialization
    result, success = plugin.ini_stage()
    assert success is True
    assert "mock mode" in result.lower()
    assert plugin._current_axes is not None
    assert len(plugin._current_axes) == 3  # Default number of axes

    # Test get_actuator_value in mock mode
    positions = plugin.get_actuator_value()
    assert isinstance(positions, list)
    assert len(positions) == 3
    assert all(pos == 0.0 for pos in positions)


@pytest.mark.unit
def test_esp300_mock_mode_move():
    """Test ESP300 plugin move operations in mock mode"""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
    from pymodaq.utils.data import DataActuator
    import numpy as np

    plugin = DAQ_Move_ESP300()
    plugin.settings.child("connection_group", "mock_mode").setValue(True)
    plugin.ini_stage()

    # Test move_abs with DataActuator
    target_positions = [1.0, 2.0, 3.0]
    data_actuator = DataActuator(
        name="test", data=[np.array(target_positions)], units="mm"
    )

    # This should not raise an exception in mock mode
    plugin.move_abs(data_actuator)

    # Test get_actuator_value still returns zeros (mock doesn't actually move)
    positions = plugin.get_actuator_value()
    assert isinstance(positions, list)
    assert len(positions) == 3
