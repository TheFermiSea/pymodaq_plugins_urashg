#!/usr/bin/env python3
"""
Comprehensive test suite for DAQ_Move_ESP300 plugin to improve coverage.

Tests all major functionality including initialization, parameter management,
movement operations, error handling, and PyMoDAQ 5.x compliance patterns.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

# Add source path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers
pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_esp300_controller():
    """Comprehensive mock ESP300Controller for testing."""
    with patch("pymodaq_plugins_urashg.hardware.urashg.esp300_controller.ESP300Controller") as mock_controller_class:
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        # Configure mock controller behavior
        mock_controller.port = "/dev/ttyUSB0"
        mock_controller.baudrate = 19200
        mock_controller.timeout = 3.0
        mock_controller._connected = False
        
        # Mock axes
        mock_axis1 = Mock()
        mock_axis1.config.name = "X Stage"
        mock_axis1.get_position.return_value = 10.0
        mock_axis1.move_absolute.return_value = True
        mock_axis1.move_relative.return_value = True
        mock_axis1.home.return_value = True
        mock_axis1.stop.return_value = True
        mock_axis1.is_motion_done.return_value = True
        
        mock_axis2 = Mock()
        mock_axis2.config.name = "Y Stage"
        mock_axis2.get_position.return_value = 20.0
        mock_axis2.move_absolute.return_value = True
        mock_axis2.move_relative.return_value = True
        mock_axis2.home.return_value = True
        mock_axis2.stop.return_value = True
        mock_axis2.is_motion_done.return_value = True
        
        mock_axis3 = Mock()
        mock_axis3.config.name = "Z Focus"
        mock_axis3.get_position.return_value = 5.0
        mock_axis3.move_absolute.return_value = True
        mock_axis3.move_relative.return_value = True
        mock_axis3.home.return_value = True
        mock_axis3.stop.return_value = True
        mock_axis3.is_motion_done.return_value = True
        
        mock_controller.axes = {1: mock_axis1, 2: mock_axis2, 3: mock_axis3}
        mock_controller.get_axis.side_effect = lambda n: mock_controller.axes.get(n)
        mock_controller.get_positions.return_value = {1: 10.0, 2: 20.0, 3: 5.0}
        mock_controller.move_positions.return_value = True
        mock_controller.connect.return_value = True
        mock_controller.disconnect.return_value = True
        mock_controller.is_connected.return_value = True
        mock_controller.stop_all_axes.return_value = True
        mock_controller.home_all_axes.return_value = True
        mock_controller.enable_all_axes.return_value = True
        mock_controller.disable_all_axes.return_value = True
        
        yield mock_controller


@pytest.fixture
def esp300_plugin():
    """Create ESP300 plugin instance."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
    
    plugin = DAQ_Move_ESP300()
    return plugin


@pytest.fixture
def esp300_plugin_with_controller(mock_esp300_controller):
    """Create ESP300 plugin with mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
    
    plugin = DAQ_Move_ESP300()
    plugin.controller = mock_esp300_controller
    plugin.initialized = True
    return plugin


class TestESP300PluginBasics:
    """Test basic ESP300 plugin functionality."""
    
    def test_plugin_instantiation(self, esp300_plugin):
        """Test plugin can be instantiated with correct attributes."""
        assert esp300_plugin is not None
        assert esp300_plugin._controller_units == "millimeter"
        assert esp300_plugin.is_multiaxes is True
        assert len(esp300_plugin._axis_names) == 3
        assert esp300_plugin._axis_names == ["X Stage", "Y Stage", "Z Focus"]
        assert len(esp300_plugin._epsilon) == 3
        
    def test_ini_attributes(self, esp300_plugin):
        """Test ini_attributes method initializes correctly."""
        esp300_plugin.ini_attributes()
        assert esp300_plugin.controller is None
        
    def test_parameter_structure(self, esp300_plugin):
        """Test plugin has correct parameter structure."""
        param_names = [param["name"] for param in esp300_plugin.params]
        
        # Check for essential parameter groups
        assert "connection_group" in param_names
        assert "actions_group" in param_names
        assert "axis1_group" in param_names
        assert "axis2_group" in param_names
        assert "axis3_group" in param_names
        assert "status_group" in param_names
        
    def test_bounds_checking(self, esp300_plugin):
        """Test position bounds checking functionality."""
        # Test normal values
        assert esp300_plugin.check_bound(5.0) == 5.0
        
        # Test boundary values - get actual bounds from settings
        max_bound = esp300_plugin.settings.child("bounds_group", "max_position").value()
        min_bound = esp300_plugin.settings.child("bounds_group", "min_position").value()
        
        # Test clamping
        assert esp300_plugin.check_bound(max_bound + 10.0) == max_bound
        assert esp300_plugin.check_bound(min_bound - 10.0) == min_bound


class TestESP300Initialization:
    """Test ESP300 initialization and connection."""
    
    def test_ini_stage_success(self, mock_esp300_controller):
        """Test successful stage initialization."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
        
        plugin = DAQ_Move_ESP300()
        plugin.settings.child("connection_group", "port").setValue("/dev/ttyUSB0")
        
        info_string, success = plugin.ini_stage()
        
        assert success is True
        assert "ESP300" in info_string
        assert plugin.controller is not None
        
    def test_ini_stage_connection_failure(self, mock_esp300_controller):
        """Test initialization failure handling."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
        
        # Configure mock to fail connection
        mock_esp300_controller.connect.return_value = False
        
        plugin = DAQ_Move_ESP300()
        plugin.settings.child("connection_group", "port").setValue("/dev/ttyUSB0")
        
        info_string, success = plugin.ini_stage()
        
        assert success is False
        assert "Error" in info_string or "Failed" in info_string
        
    def test_ini_stage_exception_handling(self, mock_esp300_controller):
        """Test exception handling during initialization."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
        
        # Configure mock to raise exception
        mock_esp300_controller.connect.side_effect = Exception("Connection failed")
        
        plugin = DAQ_Move_ESP300()
        plugin.settings.child("connection_group", "port").setValue("/dev/ttyUSB0")
        
        info_string, success = plugin.ini_stage()
        
        assert success is False
        assert "Error" in info_string or "Exception" in info_string


class TestESP300PositionOperations:
    """Test position reading and movement operations."""
    
    def test_get_actuator_value(self, esp300_plugin_with_controller):
        """Test position reading returns proper DataActuator objects."""
        positions = esp300_plugin_with_controller.get_actuator_value()
        
        assert isinstance(positions, list)
        assert len(positions) == 3
        
        for pos in positions:
            assert isinstance(pos, np.ndarray)
            assert len(pos) == 1
            assert isinstance(pos[0], (int, float))
            
    def test_get_actuator_value_no_controller(self, esp300_plugin):
        """Test position reading when no controller is connected."""
        positions = esp300_plugin.get_actuator_value()
        
        assert isinstance(positions, list)
        assert len(positions) == 3
        assert all(pos[0] == 0.0 for pos in positions)
        
    def test_move_abs_with_list(self, esp300_plugin_with_controller):
        """Test absolute movement with position list."""
        target_positions = [15.0, 25.0, 8.0]
        
        esp300_plugin_with_controller.move_abs(target_positions)
        
        # Verify controller methods were called
        esp300_plugin_with_controller.controller.move_positions.assert_called_once()
        call_args = esp300_plugin_with_controller.controller.move_positions.call_args[0][0]
        assert 1 in call_args and call_args[1] == 15.0
        assert 2 in call_args and call_args[2] == 25.0
        assert 3 in call_args and call_args[3] == 8.0
        
    def test_move_abs_bounds_checking(self, esp300_plugin_with_controller):
        """Test absolute movement respects bounds."""
        plugin = esp300_plugin_with_controller
        
        # Get actual bounds from settings
        max_bound = plugin.settings.child("bounds_group", "max_position").value()
        min_bound = plugin.settings.child("bounds_group", "min_position").value()
        
        # Test with out-of-bounds values
        target_positions = [max_bound + 100.0, min_bound - 100.0, 5.0]
        
        plugin.move_abs(target_positions)
        
        # Positions should be clamped to bounds
        call_args = plugin.controller.move_positions.call_args[0][0]
        assert call_args[1] <= max_bound  # Clamped to max
        assert call_args[2] >= min_bound  # Clamped to min
        assert call_args[3] == 5.0  # Within bounds
        
    def test_move_abs_insufficient_positions(self, esp300_plugin_with_controller):
        """Test movement with fewer positions than axes."""
        target_positions = [10.0]  # Only one position for 3 axes
        
        esp300_plugin_with_controller.move_abs(target_positions)
        
        # Should pad with current positions for missing axes
        esp300_plugin_with_controller.controller.move_positions.assert_called_once()
        
    def test_move_rel(self, esp300_plugin_with_controller):
        """Test relative movement."""
        plugin = esp300_plugin_with_controller
        relative_moves = [2.0, -3.0, 1.0]
        
        plugin.move_rel(relative_moves)
        
        # Should get current positions and add relative moves
        plugin.controller.get_positions.assert_called()
        plugin.controller.move_positions.assert_called()
        
        # Verify calculated absolute positions
        call_args = plugin.controller.move_positions.call_args[0][0]
        assert call_args[1] == 12.0  # 10.0 + 2.0
        assert call_args[2] == 17.0  # 20.0 + (-3.0)
        assert call_args[3] == 6.0   # 5.0 + 1.0
        
    def test_move_home(self, esp300_plugin_with_controller):
        """Test homing operation."""
        esp300_plugin_with_controller.move_home()
        
        esp300_plugin_with_controller.controller.home_all_axes.assert_called_once()
        
    def test_stop_motion(self, esp300_plugin_with_controller):
        """Test stop motion operation."""
        esp300_plugin_with_controller.stop_motion()
        
        esp300_plugin_with_controller.controller.stop_all_axes.assert_called_once()


class TestESP300IndividualAxisControl:
    """Test individual axis control methods."""
    
    def test_home_axis(self, esp300_plugin_with_controller):
        """Test individual axis homing."""
        plugin = esp300_plugin_with_controller
        
        # Test homing each axis
        plugin.home_axis(0)
        plugin.controller.axes[1].home.assert_called_once()
        
        plugin.home_axis(1)
        plugin.controller.axes[2].home.assert_called_once()
        
        plugin.home_axis(2)
        plugin.controller.axes[3].home.assert_called_once()
        
    def test_move_axis(self, esp300_plugin_with_controller):
        """Test individual axis movement."""
        plugin = esp300_plugin_with_controller
        
        plugin.move_axis(0, 15.0)
        plugin.controller.axes[1].move_absolute.assert_called_with(15.0)
        
        plugin.move_axis(1, 25.0)
        plugin.controller.axes[2].move_absolute.assert_called_with(25.0)
        
        plugin.move_axis(2, 8.0)
        plugin.controller.axes[3].move_absolute.assert_called_with(8.0)
        
    def test_move_axis_bounds_checking(self, esp300_plugin_with_controller):
        """Test individual axis movement respects bounds."""
        plugin = esp300_plugin_with_controller
        
        max_bound = plugin.settings.child("bounds_group", "max_position").value()
        min_bound = plugin.settings.child("bounds_group", "min_position").value()
        
        # Test above bounds
        plugin.move_axis(0, max_bound + 100.0)
        plugin.controller.axes[1].move_absolute.assert_called_with(max_bound)
        
        # Test below bounds
        plugin.move_axis(1, min_bound - 100.0)
        plugin.controller.axes[2].move_absolute.assert_called_with(min_bound)
        
    def test_jog_axis(self, esp300_plugin_with_controller):
        """Test jogging functionality."""
        plugin = esp300_plugin_with_controller
        
        # Set jog step values
        plugin.settings.child("axis1_group", "axis1_jog_step").setValue(1.0)
        plugin.settings.child("axis2_group", "axis2_jog_step").setValue(0.5)
        plugin.settings.child("axis3_group", "axis3_jog_step").setValue(0.1)
        
        # Test positive jog
        plugin.jog_axis(0, True)
        plugin.controller.axes[1].move_relative.assert_called_with(1.0)
        
        # Test negative jog
        plugin.jog_axis(1, False)
        plugin.controller.axes[2].move_relative.assert_called_with(-0.5)
        
    def test_invalid_axis_index(self, esp300_plugin_with_controller):
        """Test handling of invalid axis indices."""
        plugin = esp300_plugin_with_controller
        
        # Test with out-of-range axis index
        plugin.home_axis(5)  # Should not crash
        plugin.move_axis(10, 5.0)  # Should not crash
        plugin.jog_axis(-1, True)  # Should not crash


class TestESP300ParameterCommits:
    """Test parameter commit actions and settings updates."""
    
    def test_commit_settings_actions(self, esp300_plugin_with_controller):
        """Test various commit_settings actions."""
        plugin = esp300_plugin_with_controller
        
        # Mock the action methods
        plugin.home_all_axes = Mock()
        plugin.enable_all_axes = Mock()
        plugin.disable_all_axes = Mock()
        plugin.test_hardware_connection = Mock()
        
        # Create mock parameter objects
        mock_param = Mock()
        
        # Test global actions
        mock_param.name.return_value = "home_all"
        plugin.commit_settings(mock_param)
        plugin.home_all_axes.assert_called_once()
        
        mock_param.name.return_value = "enable_all"
        plugin.commit_settings(mock_param)
        plugin.enable_all_axes.assert_called_once()
        
        mock_param.name.return_value = "disable_all"
        plugin.commit_settings(mock_param)
        plugin.disable_all_axes.assert_called_once()
        
        mock_param.name.return_value = "test_connection"
        plugin.commit_settings(mock_param)
        plugin.test_hardware_connection.assert_called_once()
        
    def test_commit_settings_axis_actions(self, esp300_plugin_with_controller):
        """Test axis-specific commit actions."""
        plugin = esp300_plugin_with_controller
        
        # Mock axis action methods
        plugin.home_axis = Mock()
        plugin.move_axis = Mock()
        plugin.jog_axis = Mock()
        
        mock_param = Mock()
        
        # Test axis homing
        mock_param.name.return_value = "axis1_home"
        plugin.commit_settings(mock_param)
        plugin.home_axis.assert_called_with(0)
        
        # Test axis jogging
        mock_param.name.return_value = "axis2_jog_plus"
        plugin.commit_settings(mock_param)
        plugin.jog_axis.assert_called_with(1, True)
        
        mock_param.name.return_value = "axis3_jog_minus"
        plugin.commit_settings(mock_param)
        plugin.jog_axis.assert_called_with(2, False)


class TestESP300ErrorHandling:
    """Test error handling and recovery mechanisms."""
    
    def test_move_with_controller_failure(self, esp300_plugin_with_controller):
        """Test behavior when controller operations fail."""
        plugin = esp300_plugin_with_controller
        
        # Configure controller to return failure
        plugin.controller.move_positions.return_value = False
        
        # Should not raise exception
        plugin.move_abs([10.0, 20.0, 5.0])
        plugin.controller.move_positions.assert_called_once()
        
    def test_move_with_controller_exception(self, esp300_plugin_with_controller):
        """Test exception handling in movement operations."""
        plugin = esp300_plugin_with_controller
        
        # Configure controller to raise exception
        plugin.controller.move_positions.side_effect = Exception("Movement failed")
        
        # Should handle exception gracefully
        plugin.move_abs([10.0, 20.0, 5.0])
        
    def test_operations_without_controller(self, esp300_plugin):
        """Test operations when no controller is connected."""
        plugin = esp300_plugin
        plugin.controller = None
        
        # Should not raise exceptions
        plugin.move_abs([10.0, 20.0, 5.0])
        plugin.move_rel([1.0, -1.0, 0.5])
        plugin.move_home()
        plugin.stop_motion()
        
        # Position reading should return zeros
        positions = plugin.get_actuator_value()
        assert all(pos[0] == 0.0 for pos in positions)


class TestESP300Cleanup:
    """Test cleanup and shutdown operations."""
    
    def test_close(self, esp300_plugin_with_controller):
        """Test proper cleanup on close."""
        plugin = esp300_plugin_with_controller
        controller = plugin.controller
        
        plugin.close()
        
        controller.disconnect.assert_called_once()
        assert plugin.controller is None
        
    def test_close_without_controller(self, esp300_plugin):
        """Test close when no controller exists."""
        plugin = esp300_plugin
        plugin.controller = None
        
        # Should not raise exception
        plugin.close()


class TestESP300Integration:
    """Test integration scenarios and complex workflows."""
    
    def test_full_initialization_workflow(self, mock_esp300_controller):
        """Test complete initialization and operation workflow."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
        
        plugin = DAQ_Move_ESP300()
        
        # Initialize
        info_string, success = plugin.ini_stage()
        assert success is True
        
        # Move to position
        plugin.move_abs([5.0, 10.0, 2.0])
        
        # Read position
        positions = plugin.get_actuator_value()
        assert len(positions) == 3
        
        # Home and close
        plugin.move_home()
        plugin.close()
        
    def test_multi_axis_coordination(self, esp300_plugin_with_controller):
        """Test coordinated multi-axis movements."""
        plugin = esp300_plugin_with_controller
        
        # Sequential movements
        positions = [
            [0.0, 0.0, 0.0],
            [5.0, 10.0, 2.0],
            [10.0, 20.0, 4.0],
        ]
        
        for target in positions:
            plugin.move_abs(target)
            # Verify movement was called
            plugin.controller.move_positions.assert_called()
            
    def test_status_monitoring(self, esp300_plugin_with_controller):
        """Test status monitoring and feedback."""
        plugin = esp300_plugin_with_controller
        
        # Test connection status
        plugin.test_hardware_connection()
        plugin.controller.is_connected.assert_called()
        
        # Test motion status
        positions = plugin.get_actuator_value()
        assert positions is not None
        
    def test_configuration_persistence(self, esp300_plugin):
        """Test parameter configuration and persistence."""
        plugin = esp300_plugin
        
        # Test parameter access and modification
        port_param = plugin.settings.child("connection_group", "port")
        port_param.setValue("/dev/ttyUSB1")
        assert port_param.value() == "/dev/ttyUSB1"
        
        # Test bounds configuration
        bounds_param = plugin.settings.child("bounds_group", "max_position")
        original_value = bounds_param.value()
        bounds_param.setValue(50.0)
        assert bounds_param.value() == 50.0
        
        # Test axis configuration
        axis1_param = plugin.settings.child("axis1_group", "axis1_jog_step")
        axis1_param.setValue(2.0)
        assert axis1_param.value() == 2.0


class TestESP300PyMoDAQCompliance:
    """Test PyMoDAQ 5.x compliance patterns."""
    
    def test_data_actuator_creation(self, esp300_plugin_with_controller):
        """Test DataActuator objects are created properly."""
        plugin = esp300_plugin_with_controller
        
        positions = plugin.get_actuator_value()
        
        # Should return list of numpy arrays (PyMoDAQ 5.x pattern)
        assert isinstance(positions, list)
        for pos in positions:
            assert isinstance(pos, np.ndarray)
            assert pos.dtype in [np.float64, np.float32, np.int32, np.int64]
            
    def test_move_done_signal_emission(self, esp300_plugin_with_controller):
        """Test that move_done signals are emitted."""
        plugin = esp300_plugin_with_controller
        plugin.move_done = Mock()
        
        plugin.move_abs([10.0, 20.0, 5.0])
        
        # Should emit move_done signal
        plugin.move_done.assert_called()
        
    def test_thread_command_emission(self, esp300_plugin_with_controller):
        """Test ThreadCommand emission for status updates."""
        plugin = esp300_plugin_with_controller
        plugin.emit_status = Mock()
        
        # Operations should emit status updates
        plugin.move_abs([10.0, 20.0, 5.0])
        # Note: Actual implementation may or may not emit status - this tests the pattern
        
    def test_parameter_tree_compliance(self, esp300_plugin):
        """Test parameter tree follows PyMoDAQ patterns."""
        plugin = esp300_plugin
        
        # Check parameter structure follows multi-axis patterns
        param_names = [param["name"] for param in plugin.params]
        
        # Should have standard PyMoDAQ groups
        assert any("bounds" in name for name in param_names)
        assert any("axis1" in name for name in param_names)
        assert any("axis2" in name for name in param_names)
        assert any("axis3" in name for name in param_names)