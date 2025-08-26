#!/usr/bin/env python3
"""
Comprehensive unit tests for the DAQ_Move_Elliptec plugin.

Tests all the fixes implemented including:
- Basic plugin functionality
- Multi-axis control
- Individual axis operations
- Bounds checking
- Mount address handling
- Core methods implementation
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
def elliptec_plugin():
    """Fixture to create a DAQ_Move_Elliptec instance."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()
    return plugin


@pytest.fixture
def elliptec_plugin_with_mock_controller():
    """Fixture to create a DAQ_Move_Elliptec instance with a mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()

    # Create comprehensive mock controller
    mock_controller = Mock()
    mock_controller.mount_addresses = ["2", "3", "8"]
    mock_controller.connect.return_value = True
    mock_controller.disconnect.return_value = True
    mock_controller.is_connected.return_value = True
    mock_controller.home_all.return_value = True
    mock_controller.home.return_value = True
    mock_controller.move_absolute.return_value = True
    mock_controller.move_relative.return_value = True
    mock_controller.get_all_positions.return_value = {"2": 10.0, "3": 20.0, "8": 30.0}

    plugin.controller = mock_controller
    plugin.initialized = True

    return plugin


def test_plugin_instantiation(elliptec_plugin):
    """Test that the plugin can be instantiated."""
    assert elliptec_plugin is not None
    assert elliptec_plugin._controller_units == "degrees"
    assert elliptec_plugin.is_multiaxes is True
    assert len(elliptec_plugin._axis_names) == 3
    assert elliptec_plugin._axis_names == ["HWP_Incident", "QWP", "HWP_Analyzer"]


def test_ini_attributes(elliptec_plugin):
    """Test the ini_attributes method."""
    elliptec_plugin.ini_attributes()
    assert elliptec_plugin.controller is None


def test_check_bound(elliptec_plugin):
    """Test the check_bound method for position validation."""
    # Test normal values
    assert elliptec_plugin.check_bound(45.0) == 45.0
    assert elliptec_plugin.check_bound(-45.0) == -45.0

    # Test boundary values
    assert elliptec_plugin.check_bound(180.0) == 180.0
    assert elliptec_plugin.check_bound(-180.0) == -180.0

    # Test out of bounds values
    assert elliptec_plugin.check_bound(200.0) == 180.0
    assert elliptec_plugin.check_bound(-200.0) == -180.0

    # Test string conversion
    assert elliptec_plugin.check_bound("90.5") == 90.5


def test_get_actuator_value_with_controller(elliptec_plugin_with_mock_controller):
    """Test get_actuator_value method returns proper numpy arrays."""
    positions = elliptec_plugin_with_mock_controller.get_actuator_value()

    # Should return list of numpy arrays
    assert isinstance(positions, list)
    assert len(positions) == 3

    for pos_array in positions:
        assert isinstance(pos_array, np.ndarray)
        assert len(pos_array) == 1
        assert isinstance(pos_array[0], (int, float))


def test_get_actuator_value_no_controller(elliptec_plugin):
    """Test get_actuator_value when controller is None."""
    elliptec_plugin.controller = None

    positions = elliptec_plugin.get_actuator_value()

    assert isinstance(positions, list)
    assert len(positions) == 3
    assert all(pos[0] == 0.0 for pos in positions)


def test_move_abs_with_list(elliptec_plugin_with_mock_controller):
    """Test move_abs method with list input."""
    target_positions = [30.0, 60.0, 120.0]

    elliptec_plugin_with_mock_controller.move_abs(target_positions)

    # Verify individual move_absolute calls were made
    assert elliptec_plugin_with_mock_controller.controller.move_absolute.call_count == 3

    calls = elliptec_plugin_with_mock_controller.controller.move_absolute.call_args_list
    assert calls[0][0] == ("2", 30.0)
    assert calls[1][0] == ("3", 60.0)
    assert calls[2][0] == ("8", 120.0)


def test_move_abs_bounds_checking(elliptec_plugin_with_mock_controller):
    """Test that move_abs properly applies bounds checking."""
    # Test with out-of-bounds values
    target_positions = [200.0, -200.0, 45.0]

    elliptec_plugin_with_mock_controller.move_abs(target_positions)

    calls = elliptec_plugin_with_mock_controller.controller.move_absolute.call_args_list
    assert calls[0][0] == ("2", 180.0)  # Clamped to max
    assert calls[1][0] == ("3", -180.0)  # Clamped to min
    assert calls[2][0] == ("8", 45.0)  # Within bounds


def test_move_abs_insufficient_positions(elliptec_plugin_with_mock_controller):
    """Test move_abs with fewer positions than axes."""
    target_positions = [45.0]  # Only one position for 3 axes

    elliptec_plugin_with_mock_controller.move_abs(target_positions)

    # Should pad with 0.0 for missing axes
    calls = elliptec_plugin_with_mock_controller.controller.move_absolute.call_args_list
    assert calls[0][0] == ("2", 45.0)
    assert calls[1][0] == ("3", 0.0)
    assert calls[2][0] == ("8", 0.0)


def test_move_abs_no_controller(elliptec_plugin):
    """Test move_abs when controller is None."""
    elliptec_plugin.controller = None

    # Should not raise exception
    elliptec_plugin.move_abs([45.0, 90.0, 135.0])


def test_move_rel(elliptec_plugin_with_mock_controller):
    """Test move_rel method."""
    relative_positions = [5.0, -10.0, 15.0]

    elliptec_plugin_with_mock_controller.move_rel(relative_positions)

    # Should get current positions and add relative values
    elliptec_plugin_with_mock_controller.controller.get_all_positions.assert_called()

    # With mock returning {2: 10.0, 3: 20.0, 8: 30.0}
    # Expected targets: [15.0, 10.0, 45.0]
    calls = elliptec_plugin_with_mock_controller.controller.move_absolute.call_args_list
    assert calls[0][0] == ("2", 15.0)  # 10.0 + 5.0
    assert calls[1][0] == ("3", 10.0)  # 20.0 + (-10.0)
    assert calls[2][0] == ("8", 45.0)  # 30.0 + 15.0


def test_move_home(elliptec_plugin_with_mock_controller):
    """Test move_home method."""
    elliptec_plugin_with_mock_controller.move_home()

    elliptec_plugin_with_mock_controller.controller.home_all.assert_called_once()


def test_stop_motion(elliptec_plugin_with_mock_controller):
    """Test stop_motion method."""
    # Should not raise exception
    elliptec_plugin_with_mock_controller.stop_motion()


def test_home_axis(elliptec_plugin_with_mock_controller):
    """Test home_axis method for individual axis control."""
    # Test homing axis 0 (HWP_Incident)
    elliptec_plugin_with_mock_controller.home_axis(0)
    elliptec_plugin_with_mock_controller.controller.home.assert_called_with("2")

    # Test homing axis 1 (QWP)
    elliptec_plugin_with_mock_controller.home_axis(1)
    elliptec_plugin_with_mock_controller.controller.home.assert_called_with("3")

    # Test homing axis 2 (HWP_Analyzer)
    elliptec_plugin_with_mock_controller.home_axis(2)
    elliptec_plugin_with_mock_controller.controller.home.assert_called_with("8")


def test_move_axis(elliptec_plugin_with_mock_controller):
    """Test move_axis method for individual axis control."""
    # Test moving axis 1 to 75 degrees
    elliptec_plugin_with_mock_controller.move_axis(1, 75.0)

    elliptec_plugin_with_mock_controller.controller.move_absolute.assert_called_with(
        "3", 75.0
    )


def test_move_axis_bounds_checking(elliptec_plugin_with_mock_controller):
    """Test move_axis applies bounds checking."""
    # Test moving axis 0 to out-of-bounds value
    elliptec_plugin_with_mock_controller.move_axis(0, 250.0)

    # Should be clamped to 180.0
    elliptec_plugin_with_mock_controller.controller.move_absolute.assert_called_with(
        "2", 180.0
    )


def test_jog_axis(elliptec_plugin_with_mock_controller):
    """Test jog_axis method for incremental movement."""
    plugin = elliptec_plugin_with_mock_controller

    # Set jog step values
    plugin.settings.child("axis1_group", "axis1_jog_step").setValue(5.0)
    plugin.settings.child("axis2_group", "axis2_jog_step").setValue(2.5)
    plugin.settings.child("axis3_group", "axis3_jog_step").setValue(1.0)

    # Test positive jog on axis 0
    plugin.jog_axis(0, True)
    plugin.controller.move_relative.assert_called_with("2", 5.0)

    # Test negative jog on axis 1
    plugin.jog_axis(1, False)
    plugin.controller.move_relative.assert_called_with("3", -2.5)


def test_test_hardware_connection(elliptec_plugin_with_mock_controller):
    """Test test_hardware_connection method."""
    elliptec_plugin_with_mock_controller.test_hardware_connection()

    # Should call is_connected() method
    elliptec_plugin_with_mock_controller.controller.is_connected.assert_called_once()


def test_close(elliptec_plugin_with_mock_controller):
    """Test the close method."""
    controller = elliptec_plugin_with_mock_controller.controller
    elliptec_plugin_with_mock_controller.close()

    controller.disconnect.assert_called_once()
    assert elliptec_plugin_with_mock_controller.controller is None


def test_mount_address_string_conversion(elliptec_plugin_with_mock_controller):
    """Test that mount addresses are properly converted to strings."""
    plugin = elliptec_plugin_with_mock_controller

    # Test with integer mount addresses (edge case)
    plugin.controller.mount_addresses = [2, 3, 8]

    plugin.move_axis(0, 45.0)

    # Should convert integer to string
    plugin.controller.move_absolute.assert_called_with("2", 45.0)


def test_invalid_axis_index(elliptec_plugin_with_mock_controller):
    """Test handling of invalid axis indices."""
    plugin = elliptec_plugin_with_mock_controller

    # Test with out-of-range axis index
    plugin.home_axis(5)  # Only 3 axes (0, 1, 2)

    # Should not call controller methods
    plugin.controller.home.assert_not_called()


def test_move_abs_controller_failure(elliptec_plugin_with_mock_controller):
    """Test move_abs when controller operations fail."""
    plugin = elliptec_plugin_with_mock_controller

    # Configure mock to return False (failure)
    plugin.controller.move_absolute.return_value = False

    target_positions = [45.0, 90.0, 135.0]
    plugin.move_abs(target_positions)

    # Should still make all calls even if some fail
    assert plugin.controller.move_absolute.call_count == 3


def test_plugin_parameters(elliptec_plugin):
    """Test that plugin has correct parameter structure."""
    # Check that essential parameter groups exist
    param_names = [param["name"] for param in elliptec_plugin.params]

    assert "connection_group" in param_names
    assert "actions_group" in param_names
    assert "axis1_group" in param_names
    assert "axis2_group" in param_names
    assert "axis3_group" in param_names
    assert "status_group" in param_names


def test_axis_epsilon_values(elliptec_plugin):
    """Test that epsilon values are correctly set for all axes."""
    assert len(elliptec_plugin._epsilon) == 3
    assert all(eps == 0.1 for eps in elliptec_plugin._epsilon)


def test_ini_stage_mock_mode():
    """Test ini_stage with mock mode enabled."""
    with patch(
        "pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper.ElliptecController"
    ) as mock_controller_class:
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
            DAQ_Move_Elliptec,
        )

        # Configure mock
        mock_instance = Mock()
        mock_instance.connect.return_value = True
        mock_controller_class.return_value = mock_instance

        plugin = DAQ_Move_Elliptec()
        plugin.settings.child("connection_group", "mock_mode").setValue(False)

        info_string, success = plugin.ini_stage()

        assert success is True
        assert "Elliptec mounts initialized successfully" in info_string


def test_commit_settings_actions():
    """Test commit_settings method for various actions."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()

    # Mock the action methods
    plugin.home_all_mounts = Mock()
    plugin.test_hardware_connection = Mock()
    plugin.home_axis = Mock()
    plugin.move_axis = Mock()
    plugin.jog_axis = Mock()

    # Create mock parameter objects
    mock_param = Mock()

    # Test global actions
    mock_param.name.return_value = "home_all"
    plugin.commit_settings(mock_param)
    plugin.home_all_mounts.assert_called_once()

    # Test axis actions
    mock_param.name.return_value = "axis1_home"
    plugin.commit_settings(mock_param)
    plugin.home_axis.assert_called_with(0)

    mock_param.name.return_value = "axis2_jog_plus"
    plugin.commit_settings(mock_param)
    plugin.jog_axis.assert_called_with(1, True)


def test_move_done_signal_integration():
    """Test that move_done signals are properly sent."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()
    plugin.move_done = Mock()

    # Mock controller
    mock_controller = Mock()
    mock_controller.move_absolute.return_value = True
    mock_controller.mount_addresses = ["2", "3", "8"]
    plugin.controller = mock_controller

    # Test that move_done is called after successful move
    plugin.move_abs([45.0, 90.0, 135.0])
    plugin.move_done.assert_called_once()


def test_error_handling_in_methods():
    """Test error handling in various methods."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
        DAQ_Move_Elliptec,
    )

    plugin = DAQ_Move_Elliptec()

    # Configure controller to raise exceptions
    mock_controller = Mock()
    mock_controller.move_absolute.side_effect = Exception("Test error")
    mock_controller.mount_addresses = ["2", "3", "8"]
    plugin.controller = mock_controller

    # Should not raise exception, should handle gracefully
    plugin.move_abs([45.0, 90.0, 135.0])

    # Test with None controller
    plugin.controller = None
    plugin.move_abs([45.0, 90.0, 135.0])  # Should not crash
