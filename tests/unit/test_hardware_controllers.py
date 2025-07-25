"""
Unit tests for hardware controllers
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_maitai_controller_import():
    """Test MaiTai controller can be imported"""
    from pymodaq_plugins_urashg.hardware.urashg.maitai_control import MaiTaiController
    assert MaiTaiController is not None

def test_elliptec_controller_import():
    """Test Elliptec controller can be imported"""
    from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController
    assert ElliptecController is not None

def test_newport1830c_controller_import():
    """Test Newport 1830C controller can be imported"""
    from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import Newport1830CController
    assert Newport1830CController is not None

def test_esp300_controller_import():
    """Test ESP300 controller can be imported"""
    from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller
    assert ESP300Controller is not None

def test_maitai_controller_mock_creation():
    """Test MaiTai controller creation in mock mode"""
    from pymodaq_plugins_urashg.hardware.urashg.maitai_control import MaiTaiController
    controller = MaiTaiController(port='/dev/ttyUSB0', mock_mode=True)
    assert controller is not None
    assert controller.mock_mode is True

def test_elliptec_controller_mock_creation():
    """Test Elliptec controller creation in mock mode"""
    from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController
    controller = ElliptecController(port='/dev/ttyUSB1', mock_mode=True)
    assert controller is not None
    assert controller.mock_mode is True

def test_newport1830c_controller_mock_creation():
    """Test Newport 1830C controller creation in mock mode"""
    from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import Newport1830CController
    # Newport controller doesn't have mock mode, but we test without connecting
    controller = Newport1830CController(port='/dev/ttyUSB2')
    assert controller is not None
    assert controller.port == '/dev/ttyUSB2'
    # Ensure it doesn't try to connect in tests
    assert not controller._connected

def test_esp300_controller_mock_creation():
    """Test ESP300 controller creation in mock mode"""  
    from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller
    # ESP300 controller doesn't have mock mode, but we test without connecting
    controller = ESP300Controller(port='/dev/ttyUSB3')
    assert controller is not None
    assert controller.port == '/dev/ttyUSB3'
    # Ensure it doesn't try to connect in tests
    assert not hasattr(controller, '_connected') or not controller._connected