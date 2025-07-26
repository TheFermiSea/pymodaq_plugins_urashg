"""
Unit tests for PyMoDAQ plugins
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_maitai_plugin_import():
    """Test MaiTai plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
    assert DAQ_Move_MaiTai is not None

def test_elliptec_plugin_import():
    """Test Elliptec plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
    assert DAQ_Move_Elliptec is not None

def test_esp300_plugin_import():
    """Test ESP300 plugin can be imported"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300 import DAQ_Move_ESP300
    assert DAQ_Move_ESP300 is not None

def test_newport1830c_plugin_import():
    """Test Newport 1830C plugin can be imported"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C
    assert DAQ_0DViewer_Newport1830C is not None

def test_primebsi_plugin_import():
    """Test PrimeBSI plugin can be imported"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    assert DAQ_2DViewer_PrimeBSI is not None

def test_maitai_plugin_creation():
    """Test MaiTai plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
    plugin = DAQ_Move_MaiTai()
    assert plugin is not None
    assert hasattr(plugin, 'settings')

def test_elliptec_plugin_creation():
    """Test Elliptec plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
    plugin = DAQ_Move_Elliptec()
    assert plugin is not None
    assert hasattr(plugin, 'settings')

def test_esp300_plugin_creation():
    """Test ESP300 plugin creation"""
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_ESP300 import DAQ_Move_ESP300
    plugin = DAQ_Move_ESP300()
    assert plugin is not None
    assert hasattr(plugin, 'settings')

def test_newport1830c_plugin_creation():
    """Test Newport 1830C plugin creation"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C
    plugin = DAQ_0DViewer_Newport1830C()
    assert plugin is not None
    assert hasattr(plugin, 'settings')

def test_primebsi_plugin_creation():
    """Test PrimeBSI plugin creation"""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    plugin = DAQ_2DViewer_PrimeBSI()
    assert plugin is not None
    assert hasattr(plugin, 'settings')