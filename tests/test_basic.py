import pytest


def test_package_import():
    """Test that the main package can be imported."""
    import pymodaq_plugins_urashg
    assert hasattr(pymodaq_plugins_urashg, '__version__')


def test_move_plugins_import():
    """Test that move plugins can be imported."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300

    assert DAQ_Move_Elliptec is not None
    assert DAQ_Move_MaiTai is not None
    assert DAQ_Move_ESP300 is not None


def test_viewer_plugins_import():
    """Test that viewer plugins can be imported."""
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C

    assert DAQ_2DViewer_PrimeBSI is not None
    assert DAQ_0DViewer_Newport1830C is not None


def test_config_available():
    """Test that config can be accessed."""
    from pymodaq_plugins_urashg import config
    assert config is not None
