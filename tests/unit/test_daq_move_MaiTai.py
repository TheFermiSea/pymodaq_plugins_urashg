#!/usr/bin/env python3
"""
Comprehensive unit tests for the DAQ_Move_MaiTai plugin.

Tests all the fixes implemented including:
- Basic plugin functionality
- Single-axis wavelength control
- Shutter operations
- Move operations (abs, rel, home, stop)
- Mock controller functionality
- Error handling
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [pytest.mark.unit]


@pytest.fixture
def maitai_plugin():
    """Fixture to create a DAQ_Move_MaiTai instance."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    return plugin


@pytest.fixture
def maitai_plugin_with_mock_controller():
    """Fixture to create a MaiTai plugin with a mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()

    # Create comprehensive mock controller
    mock_controller = Mock()
    mock_controller.connect.return_value = True
    mock_controller.disconnect.return_value = True
    mock_controller.close.return_value = True
    mock_controller.get_wavelength.return_value = 800.0
    mock_controller.set_wavelength.return_value = True
    mock_controller.open_shutter.return_value = True
    mock_controller.close_shutter.return_value = True

    plugin.controller = mock_controller
    plugin.initialized = True

    return plugin


@pytest.fixture
def maitai_plugin_mock_mode():
    """Fixture to create a MaiTai plugin in mock mode."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
        DAQ_Move_MaiTai,
        MockMaiTaiController,
    )

    plugin = DAQ_Move_MaiTai()
    plugin.controller = MockMaiTaiController()
    plugin.initialized = True

    yield plugin


def test_plugin_instantiation(maitai_plugin):
    """Test that the plugin can be instantiated."""
    assert maitai_plugin is not None
    assert maitai_plugin._controller_units == "nm"
    assert maitai_plugin.is_multiaxes is False
    assert len(maitai_plugin._axis_names) == 1
    assert maitai_plugin._axis_names == ["Wavelength"]
    assert maitai_plugin._epsilon == 1.0


def test_ini_attributes(maitai_plugin):
    """Test the ini_attributes method."""
    maitai_plugin.ini_attributes()
    assert maitai_plugin.controller is None


def test_ini_stage_mock_mode():
    """Test ini_stage in mock mode."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    plugin.settings.child("connection_group", "mock_mode").setValue(True)

    info_string, success = plugin.ini_stage()

    assert success is True
    assert "MOCK mode" in info_string
    assert plugin.initialized is True


def test_get_actuator_value_with_controller(maitai_plugin_with_mock_controller):
    """Test get_actuator_value method returns proper numpy arrays."""
    positions = maitai_plugin_with_mock_controller.get_actuator_value()

    # Should return list with single numpy array for wavelength
    assert isinstance(positions, list)
    assert len(positions) == 1

    wavelength_array = positions[0]
    assert isinstance(wavelength_array, np.ndarray)
    assert len(wavelength_array) == 1
    assert wavelength_array[0] == 800.0


def test_get_actuator_value_no_controller(maitai_plugin):
    """Test get_actuator_value when controller is None."""
    maitai_plugin.controller = None

    positions = maitai_plugin.get_actuator_value()

    assert isinstance(positions, list)
    assert len(positions) == 1
    assert positions[0][0] == 800.0  # Default wavelength


def test_move_abs_with_list(maitai_plugin_with_mock_controller):
    """Test move_abs method with list input."""
    target_wavelength = [900.0]

    maitai_plugin_with_mock_controller.move_abs(target_wavelength)

    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        900.0
    )


def test_move_abs_with_scalar(maitai_plugin_with_mock_controller):
    """Test move_abs method with scalar input."""
    target_wavelength = 750.0

    maitai_plugin_with_mock_controller.move_abs(target_wavelength)

    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        750.0
    )


def test_move_abs_with_array(maitai_plugin_with_mock_controller):
    """Test move_abs method with numpy array input."""
    target_wavelength = np.array([880.0])

    maitai_plugin_with_mock_controller.move_abs(target_wavelength)

    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        880.0
    )


def test_move_abs_empty_list(maitai_plugin_with_mock_controller):
    """Test move_abs method with empty list."""
    target_wavelength = []

    maitai_plugin_with_mock_controller.move_abs(target_wavelength)

    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        800.0
    )  # Default


def test_move_abs_controller_failure(maitai_plugin_with_mock_controller):
    """Test move_abs when controller operation fails."""
    maitai_plugin_with_mock_controller.controller.set_wavelength.return_value = False

    target_wavelength = 850.0
    maitai_plugin_with_mock_controller.move_abs(target_wavelength)

    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        850.0
    )


def test_move_abs_no_controller(maitai_plugin):
    """Test move_abs when controller is None."""
    maitai_plugin.controller = None

    # Should not raise exception
    maitai_plugin.move_abs(850.0)


def test_move_rel(maitai_plugin_with_mock_controller):
    """Test move_rel method."""
    # Mock current wavelength through get_actuator_value
    with patch.object(
        maitai_plugin_with_mock_controller,
        "get_actuator_value",
        return_value=[np.array([800.0])],
    ):

        relative_wavelength = 50.0  # Move +50nm
        maitai_plugin_with_mock_controller.move_rel(relative_wavelength)

        # Should call move_abs with current + relative = 800 + 50 = 850
        maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
            850.0
        )


def test_move_rel_with_list(maitai_plugin_with_mock_controller):
    """Test move_rel method with list input."""
    with patch.object(
        maitai_plugin_with_mock_controller,
        "get_actuator_value",
        return_value=[np.array([850.0])],
    ):

        relative_wavelength = [30.0]
        maitai_plugin_with_mock_controller.move_rel(relative_wavelength)

        # Should call move_abs with 850 + 30 = 880
        maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
            880.0
        )


def test_move_home(maitai_plugin_with_mock_controller):
    """Test move_home method."""
    maitai_plugin_with_mock_controller.move_home()

    # Should move to default 800nm
    maitai_plugin_with_mock_controller.controller.set_wavelength.assert_called_once_with(
        800.0
    )


def test_stop_motion(maitai_plugin_with_mock_controller):
    """Test stop_motion method."""
    # Should not raise exception
    maitai_plugin_with_mock_controller.stop_motion()


def test_open_shutter(maitai_plugin_with_mock_controller):
    """Test open_shutter method."""
    maitai_plugin_with_mock_controller.open_shutter()

    maitai_plugin_with_mock_controller.controller.open_shutter.assert_called_once()


def test_open_shutter_success(maitai_plugin_with_mock_controller):
    """Test successful shutter opening."""
    maitai_plugin_with_mock_controller.controller.open_shutter.return_value = True

    maitai_plugin_with_mock_controller.open_shutter()

    # Check that status parameter is updated
    status = maitai_plugin_with_mock_controller.settings.child(
        "shutter_group", "shutter_status"
    ).value()
    assert status == "Open"


def test_open_shutter_failure(maitai_plugin_with_mock_controller):
    """Test failed shutter opening."""
    maitai_plugin_with_mock_controller.controller.open_shutter.return_value = False

    maitai_plugin_with_mock_controller.open_shutter()

    maitai_plugin_with_mock_controller.controller.open_shutter.assert_called_once()


def test_close_shutter(maitai_plugin_with_mock_controller):
    """Test close_shutter method."""
    maitai_plugin_with_mock_controller.close_shutter()

    maitai_plugin_with_mock_controller.controller.close_shutter.assert_called_once()


def test_close_shutter_success(maitai_plugin_with_mock_controller):
    """Test successful shutter closing."""
    maitai_plugin_with_mock_controller.controller.close_shutter.return_value = True

    maitai_plugin_with_mock_controller.close_shutter()

    # Check that status parameter is updated
    status = maitai_plugin_with_mock_controller.settings.child(
        "shutter_group", "shutter_status"
    ).value()
    assert status == "Closed"


def test_shutter_operations_no_controller(maitai_plugin):
    """Test shutter operations when controller is None."""
    maitai_plugin.controller = None

    # Should not raise exceptions and use mock operations
    maitai_plugin.open_shutter()
    status = maitai_plugin.settings.child("shutter_group", "shutter_status").value()
    assert status == "Open"

    maitai_plugin.close_shutter()
    status = maitai_plugin.settings.child("shutter_group", "shutter_status").value()
    assert status == "Closed"


def test_commit_settings_shutter_actions():
    """Test commit_settings method for shutter actions."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    plugin.open_shutter = Mock()
    plugin.close_shutter = Mock()

    mock_param = Mock()

    # Test open shutter
    mock_param.name.return_value = "open_shutter"
    plugin.commit_settings(mock_param)
    plugin.open_shutter.assert_called_once()

    # Test close shutter
    mock_param.name.return_value = "close_shutter"
    plugin.commit_settings(mock_param)
    plugin.close_shutter.assert_called_once()


def test_commit_settings_wavelength_target():
    """Test commit_settings method for target wavelength."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    plugin.move_abs = Mock()

    mock_param = Mock()
    mock_param.name.return_value = "target_wavelength"
    mock_param.value.return_value = 850.0

    plugin.commit_settings(mock_param)

    plugin.move_abs.assert_called_once_with(850.0)


def test_close_with_close_method(maitai_plugin_with_mock_controller):
    """Test close method when controller has close method."""
    controller = maitai_plugin_with_mock_controller.controller

    maitai_plugin_with_mock_controller.close()

    controller.close.assert_called_once()
    assert maitai_plugin_with_mock_controller.controller is None


def test_close_with_disconnect_method():
    """Test close method when controller only has disconnect method."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    mock_controller = Mock()
    mock_controller.disconnect = Mock()
    # Remove close method
    del mock_controller.close

    plugin.controller = mock_controller

    plugin.close()

    mock_controller.disconnect.assert_called_once()
    assert plugin.controller is None


def test_close_no_controller(maitai_plugin):
    """Test close method when controller is None."""
    maitai_plugin.controller = None

    # Should not raise exception
    maitai_plugin.close()


def test_mock_controller_functionality():
    """Test MockMaiTaiController functionality."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
        MockMaiTaiController,
    )

    mock_controller = MockMaiTaiController()

    # Test default wavelength
    assert mock_controller.get_wavelength() == 800.0

    # Test wavelength setting within range
    assert mock_controller.set_wavelength(850.0) is True
    assert mock_controller.get_wavelength() == 850.0

    # Test wavelength setting out of range
    assert mock_controller.set_wavelength(600.0) is False  # Below 700nm
    assert mock_controller.set_wavelength(1100.0) is False  # Above 1000nm

    # Test shutter operations
    assert mock_controller.shutter_open is False
    assert mock_controller.open_shutter() is True
    assert mock_controller.shutter_open is True

    assert mock_controller.close_shutter() is True
    assert mock_controller.shutter_open is False

    # Test close/disconnect methods
    mock_controller.close()
    mock_controller.disconnect()


def test_plugin_parameters(maitai_plugin):
    """Test that plugin has correct parameter structure."""
    # Check that essential parameter groups exist
    param_names = [param["name"] for param in maitai_plugin.params]

    assert "connection_group" in param_names
    assert "laser_settings" in param_names
    assert "shutter_group" in param_names

    # Check connection group parameters
    connection_group = next(
        p for p in maitai_plugin.params if p["name"] == "connection_group"
    )
    connection_param_names = [child["name"] for child in connection_group["children"]]

    assert "serial_port" in connection_param_names
    assert "baudrate" in connection_param_names
    assert "timeout" in connection_param_names
    assert "mock_mode" in connection_param_names


def test_wavelength_range_parameters(maitai_plugin):
    """Test wavelength range parameter structure."""
    # Check target wavelength parameter exists and has correct range
    target_wavelength_param = None
    for param in maitai_plugin.params:
        if param["name"] == "laser_settings":
            for child in param["children"]:
                if child["name"] == "target_wavelength":
                    target_wavelength_param = child
                    break

    assert target_wavelength_param is not None
    assert target_wavelength_param["min"] == 700.0
    assert target_wavelength_param["max"] == 1000.0
    assert target_wavelength_param["value"] == 800.0


def test_error_handling_in_methods(maitai_plugin_with_mock_controller):
    """Test error handling in various methods."""
    # Configure controller to raise exceptions
    maitai_plugin_with_mock_controller.controller.set_wavelength.side_effect = (
        Exception("Test error")
    )

    # Should not raise exception, should handle gracefully
    maitai_plugin_with_mock_controller.move_abs(850.0)

    # Configure controller to raise exception in shutter operations
    maitai_plugin_with_mock_controller.controller.open_shutter.side_effect = Exception(
        "Shutter error"
    )

    # Should not raise exception
    maitai_plugin_with_mock_controller.open_shutter()


def test_wavelength_epsilon_value(maitai_plugin):
    """Test that epsilon value is correctly set."""
    assert maitai_plugin._epsilon == 1.0  # 1nm resolution


def test_move_abs_with_mock_controller(maitai_plugin_mock_mode):
    """Test move_abs with actual MockMaiTaiController."""
    initial_wavelength = maitai_plugin_mock_mode.controller.get_wavelength()
    assert initial_wavelength == 800.0

    # Move to new wavelength
    maitai_plugin_mock_mode.move_abs(850.0)

    # Check that mock controller was updated
    new_wavelength = maitai_plugin_mock_mode.controller.get_wavelength()
    assert new_wavelength == 850.0


def test_full_workflow_mock_mode(maitai_plugin_mock_mode):
    """Test complete workflow in mock mode."""
    # Initial state
    assert maitai_plugin_mock_mode.controller.get_wavelength() == 800.0
    assert maitai_plugin_mock_mode.controller.shutter_open is False

    # Open shutter
    maitai_plugin_mock_mode.open_shutter()
    assert maitai_plugin_mock_mode.controller.shutter_open is True

    # Move to new wavelength
    maitai_plugin_mock_mode.move_abs(900.0)
    assert maitai_plugin_mock_mode.controller.get_wavelength() == 900.0

    # Relative move
    maitai_plugin_mock_mode.move_rel(-50.0)
    assert maitai_plugin_mock_mode.controller.get_wavelength() == 850.0

    # Move home
    maitai_plugin_mock_mode.move_home()
    assert maitai_plugin_mock_mode.controller.get_wavelength() == 800.0

    # Close shutter
    maitai_plugin_mock_mode.close_shutter()
    assert maitai_plugin_mock_mode.controller.shutter_open is False


def test_move_done_signal_integration():
    """Test that move_done signals are properly sent."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

    plugin = DAQ_Move_MaiTai()
    plugin.move_done = Mock()

    # Mock controller
    mock_controller = Mock()
    mock_controller.set_wavelength.return_value = True
    plugin.controller = mock_controller

    # Test that move_done is called after successful move
    plugin.move_abs(850.0)
    plugin.move_done.assert_called_once()
