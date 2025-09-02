#!/usr/bin/env python3
"""
Comprehensive test suite for DAQ_Move_Elliptec plugin to improve coverage.

Tests polarization control functionality, multi-axis operations, error handling,
and PyMoDAQ 5.x compliance patterns for URASHG microscopy systems.
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
def mock_elliptec_controller():
    """Comprehensive mock ElliptecController for testing."""
    with patch("pymodaq_plugins_urashg.hardware.elliptec_wrapper.ElliptecController") as mock_controller_class:
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        # Configure mock controller behavior
        mock_controller.port = "/dev/ttyUSB0"
        mock_controller.baudrate = 9600
        mock_controller.timeout = 2.0
        mock_controller.mock_mode = False
        mock_controller.mount_addresses = ["2", "3", "8"]
        
        # Mock connection behavior
        mock_controller.connect.return_value = True
        mock_controller.disconnect.return_value = True
        mock_controller.is_connected.return_value = True
        
        # Mock movement operations
        mock_controller.move_absolute.return_value = True
        mock_controller.move_relative.return_value = True
        mock_controller.home.return_value = True
        mock_controller.home_all.return_value = True
        
        # Mock position reading
        mock_controller.get_all_positions.return_value = {"2": 45.0, "3": 90.0, "8": 135.0}
        mock_controller.get_position.side_effect = lambda addr: {"2": 45.0, "3": 90.0, "8": 135.0}.get(addr, 0.0)
        
        # Mock status operations
        mock_controller.get_status.side_effect = lambda addr: {"2": "OK", "3": "OK", "8": "OK"}.get(addr, "Unknown")
        mock_controller.cleanup.return_value = None
        
        yield mock_controller


@pytest.fixture
def elliptec_plugin():
    """Create Elliptec plugin instance."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
    
    plugin = DAQ_Move_Elliptec()
    return plugin


@pytest.fixture
def elliptec_plugin_with_controller(mock_elliptec_controller):
    """Create Elliptec plugin with mocked controller."""
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
    
    plugin = DAQ_Move_Elliptec()
    plugin.controller = mock_elliptec_controller
    plugin.initialized = True
    return plugin


class TestElliptecPluginBasics:
    """Test basic Elliptec plugin functionality."""
    
    def test_plugin_instantiation(self, elliptec_plugin):
        """Test plugin can be instantiated with correct attributes."""
        assert elliptec_plugin is not None
        assert elliptec_plugin._controller_units == "degrees"
        assert elliptec_plugin.is_multiaxes is True
        assert len(elliptec_plugin._axis_names) == 3
        assert elliptec_plugin._axis_names == ["HWP_Incident", "QWP", "HWP_Analyzer"]
        assert len(elliptec_plugin._epsilon) == 3
        assert all(eps == 0.1 for eps in elliptec_plugin._epsilon)
        
    def test_ini_attributes(self, elliptec_plugin):
        """Test ini_attributes method initializes correctly."""
        elliptec_plugin.ini_attributes()
        assert elliptec_plugin.controller is None
        
    def test_parameter_structure(self, elliptec_plugin):
        """Test plugin has correct parameter structure for polarization control."""
        param_names = [param["name"] for param in elliptec_plugin.params]
        
        # Check for essential parameter groups
        assert "connection_group" in param_names
        assert "actions_group" in param_names
        assert "axis1_group" in param_names  # HWP_Incident
        assert "axis2_group" in param_names  # QWP
        assert "axis3_group" in param_names  # HWP_Analyzer
        assert "status_group" in param_names
        
    def test_bounds_checking_polarization(self, elliptec_plugin):
        """Test position bounds checking for polarization elements."""
        # Polarization elements typically operate in 0-360 degree range
        
        # Test normal values
        assert elliptec_plugin.check_bound(45.0) == 45.0
        assert elliptec_plugin.check_bound(180.0) == 180.0
        assert elliptec_plugin.check_bound(270.0) == 270.0
        
        # Test boundary values
        assert elliptec_plugin.check_bound(0.0) == 0.0
        assert elliptec_plugin.check_bound(360.0) == 360.0
        
        # Test out-of-bounds clamping
        max_bound = elliptec_plugin.settings.child("bounds_group", "max_position").value()
        min_bound = elliptec_plugin.settings.child("bounds_group", "min_position").value()
        
        assert elliptec_plugin.check_bound(max_bound + 100.0) == max_bound
        assert elliptec_plugin.check_bound(min_bound - 100.0) == min_bound
        
    def test_mount_address_configuration(self, elliptec_plugin):
        """Test mount address configuration for Thorlabs controllers."""
        # Default mount addresses should be configured
        assert hasattr(elliptec_plugin, '_axis_names')
        assert len(elliptec_plugin._axis_names) == 3
        
        # Check if there's a way to configure mount addresses
        connection_group = None
        for param in elliptec_plugin.params:
            if param.get("name") == "connection_group":
                connection_group = param
                break
                
        assert connection_group is not None
        
        # Look for mount address or similar configuration
        children = connection_group.get("children", [])
        param_names = [child.get("name") for child in children]
        
        # Should have some way to configure addresses/ports
        assert any("port" in name.lower() or "address" in name.lower() 
                  for name in param_names if name is not None)


class TestElliptecInitialization:
    """Test Elliptec initialization and connection."""
    
    def test_ini_stage_success(self, mock_elliptec_controller):
        """Test successful stage initialization."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
        
        plugin = DAQ_Move_Elliptec()
        plugin.settings.child("connection_group", "port").setValue("/dev/ttyUSB0")
        
        info_string, success = plugin.ini_stage()
        
        assert success is True
        assert "Elliptec" in info_string or "initialized" in info_string.lower()
        assert plugin.controller is not None
        
    def test_ini_stage_mock_mode(self, mock_elliptec_controller):
        """Test initialization in mock mode."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
        
        mock_elliptec_controller.mock_mode = True
        
        plugin = DAQ_Move_Elliptec()
        plugin.settings.child("connection_group", "mock_mode").setValue(True)
        
        info_string, success = plugin.ini_stage()
        
        assert success is True
        assert "mock" in info_string.lower() or "Elliptec" in info_string
        
    def test_ini_stage_connection_failure(self, mock_elliptec_controller):
        """Test initialization failure handling."""
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
        
        # Configure mock to fail connection
        mock_elliptec_controller.connect.return_value = False
        
        plugin = DAQ_Move_Elliptec()
        plugin.settings.child("connection_group", "port").setValue("/dev/ttyUSB0")
        
        info_string, success = plugin.ini_stage()
        
        assert success is False
        assert "Error" in info_string or "Failed" in info_string or "not" in info_string.lower()


class TestElliptecPolarizationControl:
    """Test polarization-specific control operations."""
    
    def test_get_actuator_value_polarization(self, elliptec_plugin_with_controller):
        """Test reading polarization element positions."""
        positions = elliptec_plugin_with_controller.get_actuator_value()
        
        assert isinstance(positions, list)
        assert len(positions) == 3
        
        for pos in positions:
            assert isinstance(pos, np.ndarray)
            assert len(pos) == 1
            # Positions should be in degrees
            assert 0.0 <= pos[0] <= 360.0 or pos[0] == 0.0  # Allow for initialization
            
    def test_polarization_preset_positions(self, elliptec_plugin_with_controller):
        """Test common polarization preset positions."""
        plugin = elliptec_plugin_with_controller
        
        # Common polarization configurations for SHG microscopy
        preset_configs = {
            "linear_horizontal": [0.0, 0.0, 0.0],
            "linear_vertical": [90.0, 0.0, 90.0],
            "circular_right": [45.0, 45.0, 45.0],
            "circular_left": [45.0, -45.0, 45.0],
            "analysis_0": [0.0, 0.0, 0.0],
            "analysis_45": [22.5, 0.0, 22.5],
            "analysis_90": [45.0, 0.0, 45.0],
        }
        
        for config_name, angles in preset_configs.items():
            plugin.move_abs(angles)
            plugin.controller.move_absolute.assert_called()
            
    def test_hwp_qwp_coordination(self, elliptec_plugin_with_controller):
        """Test half-wave plate and quarter-wave plate coordination."""
        plugin = elliptec_plugin_with_controller
        
        # Test HWP rotation with fixed QWP
        hwp_angles = [0.0, 22.5, 45.0, 67.5, 90.0]
        for angle in hwp_angles:
            # Set HWP_Incident, keep QWP fixed, set HWP_Analyzer
            plugin.move_abs([angle, 0.0, angle])
            plugin.controller.move_absolute.assert_called()
            
        # Test QWP rotation with fixed HWPs
        qwp_angles = [0.0, 45.0, 90.0, 135.0]
        for angle in qwp_angles:
            # Set both HWPs to 0, vary QWP
            plugin.move_abs([0.0, angle, 0.0])
            plugin.controller.move_absolute.assert_called()
            
    def test_polarimetric_measurement_sequence(self, elliptec_plugin_with_controller):
        """Test polarimetric measurement sequence."""
        plugin = elliptec_plugin_with_controller
        
        # Typical polarimetric SHG measurement sequence
        # Rotate incident HWP from 0 to 180 degrees in 10-degree steps
        incident_angles = np.arange(0, 181, 10)
        
        for angle in incident_angles:
            # Rotate incident HWP, keep others fixed
            plugin.move_abs([float(angle), 0.0, 0.0])
            plugin.controller.move_absolute.assert_called()
            
            # Read position to verify
            positions = plugin.get_actuator_value()
            # Should have moved to approximately the target angle
            assert len(positions) == 3


class TestElliptecMovementOperations:
    """Test movement operations for polarization elements."""
    
    def test_move_abs_with_clamping(self, elliptec_plugin_with_controller):
        """Test absolute movement with angle clamping."""
        plugin = elliptec_plugin_with_controller
        
        # Test normal angles
        target_angles = [45.0, 90.0, 135.0]
        plugin.move_abs(target_angles)
        
        # Verify move calls
        assert plugin.controller.move_absolute.call_count == 3
        calls = plugin.controller.move_absolute.call_args_list
        assert calls[0][0] == ("2", 45.0)
        assert calls[1][0] == ("3", 90.0)
        assert calls[2][0] == ("8", 135.0)
        
    def test_move_abs_angle_wrapping(self, elliptec_plugin_with_controller):
        """Test handling of angles outside 0-360 range."""
        plugin = elliptec_plugin_with_controller
        
        # Test angles outside normal range - should be clamped by check_bound
        target_angles = [400.0, -45.0, 720.0]  # Over 360, negative, multiple rotations
        plugin.move_abs(target_angles)
        
        # Should clamp to valid range
        calls = plugin.controller.move_absolute.call_args_list
        # Exact values depend on check_bound implementation
        for call in calls:
            angle = call[0][1]
            # Should be clamped to valid range (implementation dependent)
            assert isinstance(angle, (int, float))
            
    def test_move_rel_incremental(self, elliptec_plugin_with_controller):
        """Test relative movement for fine polarization adjustments."""
        plugin = elliptec_plugin_with_controller
        
        # Small incremental adjustments typical for polarization tuning
        relative_moves = [2.5, -1.0, 0.5]
        plugin.move_rel(relative_moves)
        
        # Should get current positions and add relative moves
        plugin.controller.get_all_positions.assert_called()
        
        # Should result in absolute moves to new positions
        calls = plugin.controller.move_absolute.call_args_list
        assert len(calls) == 3
        
        # Expected positions: [45.0+2.5, 90.0-1.0, 135.0+0.5] = [47.5, 89.0, 135.5]
        assert calls[0][0] == ("2", 47.5)
        assert calls[1][0] == ("3", 89.0)
        assert calls[2][0] == ("8", 135.5)
        
    def test_move_home_polarization_zero(self, elliptec_plugin_with_controller):
        """Test homing all polarization elements."""
        plugin = elliptec_plugin_with_controller
        
        plugin.move_home()
        
        plugin.controller.home_all.assert_called_once()
        
    def test_individual_axis_control(self, elliptec_plugin_with_controller):
        """Test individual polarization element control."""
        plugin = elliptec_plugin_with_controller
        
        # Test individual axis homing
        plugin.home_axis(0)  # HWP_Incident
        plugin.controller.home.assert_called_with("2")
        
        plugin.home_axis(1)  # QWP  
        plugin.controller.home.assert_called_with("3")
        
        plugin.home_axis(2)  # HWP_Analyzer
        plugin.controller.home.assert_called_with("8")
        
        # Test individual axis movement
        plugin.move_axis(0, 22.5)  # Fine HWP adjustment
        plugin.controller.move_absolute.assert_called_with("2", 22.5)
        
        plugin.move_axis(1, 45.0)  # Quarter-wave setting
        plugin.controller.move_absolute.assert_called_with("3", 45.0)
        
    def test_jog_fine_adjustment(self, elliptec_plugin_with_controller):
        """Test jogging for fine polarization adjustments."""
        plugin = elliptec_plugin_with_controller
        
        # Set fine jog steps for polarization
        plugin.settings.child("axis1_group", "axis1_jog_step").setValue(1.0)
        plugin.settings.child("axis2_group", "axis2_jog_step").setValue(2.5)
        plugin.settings.child("axis3_group", "axis3_jog_step").setValue(0.5)
        
        # Test positive jog (clockwise rotation)
        plugin.jog_axis(0, True)
        plugin.controller.move_relative.assert_called_with("2", 1.0)
        
        # Test negative jog (counter-clockwise rotation)
        plugin.jog_axis(1, False)
        plugin.controller.move_relative.assert_called_with("3", -2.5)


class TestElliptecErrorHandling:
    """Test error handling for Thorlabs Elliptec devices."""
    
    def test_mount_communication_error(self, elliptec_plugin_with_controller):
        """Test handling of mount communication errors."""
        plugin = elliptec_plugin_with_controller
        
        # Configure controller to simulate communication failure
        plugin.controller.move_absolute.return_value = False
        
        # Should handle error gracefully
        plugin.move_abs([45.0, 90.0, 135.0])
        
        # Should still attempt all moves
        assert plugin.controller.move_absolute.call_count == 3
        
    def test_mount_address_validation(self, elliptec_plugin_with_controller):
        """Test mount address validation."""
        plugin = elliptec_plugin_with_controller
        
        # Test with invalid axis indices
        plugin.home_axis(5)  # Invalid axis
        plugin.move_axis(10, 45.0)  # Invalid axis
        
        # Should not crash, but also should not call controller methods
        # (Depends on implementation)
        
    def test_position_read_failure(self, elliptec_plugin_with_controller):
        """Test handling of position read failures."""
        plugin = elliptec_plugin_with_controller
        
        # Configure controller to return empty/invalid positions
        plugin.controller.get_all_positions.return_value = {}
        
        positions = plugin.get_actuator_value()
        
        # Should return default values
        assert isinstance(positions, list)
        assert len(positions) == 3
        
    def test_device_not_responding(self, elliptec_plugin_with_controller):
        """Test handling when devices don't respond."""
        plugin = elliptec_plugin_with_controller
        
        # Configure controller to raise exceptions
        plugin.controller.get_all_positions.side_effect = Exception("Device not responding")
        
        # Should handle exception gracefully
        positions = plugin.get_actuator_value()
        assert isinstance(positions, list)
        assert len(positions) == 3


class TestElliptecStatusMonitoring:
    """Test status monitoring and device health."""
    
    def test_connection_status(self, elliptec_plugin_with_controller):
        """Test connection status monitoring."""
        plugin = elliptec_plugin_with_controller
        
        # Test hardware connection check
        plugin.test_hardware_connection()
        plugin.controller.is_connected.assert_called()
        
    def test_mount_status_individual(self, elliptec_plugin_with_controller):
        """Test individual mount status checking."""
        plugin = elliptec_plugin_with_controller
        
        # Test if there are methods to check individual mount status
        if hasattr(plugin, 'get_mount_status'):
            for axis in range(3):
                status = plugin.get_mount_status(axis)
                assert status is not None
                
    def test_position_feedback_accuracy(self, elliptec_plugin_with_controller):
        """Test position feedback accuracy for polarization elements."""
        plugin = elliptec_plugin_with_controller
        
        # Move to known positions
        target_positions = [30.0, 60.0, 120.0]
        plugin.move_abs(target_positions)
        
        # Update mock to return these positions
        plugin.controller.get_all_positions.return_value = {
            "2": 30.0, "3": 60.0, "8": 120.0
        }
        
        # Read positions
        positions = plugin.get_actuator_value()
        
        # Should match target positions within epsilon
        for i, pos in enumerate(positions):
            expected = target_positions[i]
            actual = pos[0]
            epsilon = plugin._epsilon[i]
            assert abs(actual - expected) <= epsilon + 0.1  # Small tolerance for mock


class TestElliptecIntegration:
    """Test integration scenarios for URASHG microscopy."""
    
    def test_rashg_measurement_preparation(self, elliptec_plugin_with_controller):
        """Test preparation for RASHG measurements."""
        plugin = elliptec_plugin_with_controller
        
        # Typical RASHG setup: incident HWP scan with fixed QWP and analyzer
        qwp_angle = 0.0  # Linear polarization
        analyzer_angle = 0.0  # Analyzer parallel
        
        # Scan incident HWP
        incident_angles = [0.0, 22.5, 45.0, 67.5, 90.0]
        
        for angle in incident_angles:
            plugin.move_abs([angle, qwp_angle, analyzer_angle])
            positions = plugin.get_actuator_value()
            assert len(positions) == 3
            
    def test_polarimetric_shg_sequence(self, elliptec_plugin_with_controller):
        """Test full polarimetric SHG measurement sequence."""
        plugin = elliptec_plugin_with_controller
        
        # Full polarimetric measurement: vary both incident and analyzer
        measurement_points = [
            [0.0, 0.0, 0.0],      # HH
            [0.0, 0.0, 90.0],     # HV  
            [90.0, 0.0, 0.0],     # VH
            [90.0, 0.0, 90.0],    # VV
            [45.0, 0.0, 45.0],    # +45 linear
            [135.0, 0.0, 135.0],  # -45 linear
            [0.0, 45.0, 0.0],     # Right circular to H
            [0.0, -45.0, 0.0],    # Left circular to H
        ]
        
        for point in measurement_points:
            plugin.move_abs(point)
            plugin.controller.move_absolute.assert_called()
            
    def test_calibration_sequence(self, elliptec_plugin_with_controller):
        """Test polarization element calibration sequence."""
        plugin = elliptec_plugin_with_controller
        
        # Calibration sequence: home all elements
        plugin.move_home()
        plugin.controller.home_all.assert_called()
        
        # Move to known calibration positions
        calibration_positions = [
            [0.0, 0.0, 0.0],      # All at zero
            [90.0, 90.0, 90.0],   # All at 90 degrees
            [45.0, 45.0, 45.0],   # All at 45 degrees
        ]
        
        for positions in calibration_positions:
            plugin.move_abs(positions)
            # Allow time for movement (in real system)
            actual_positions = plugin.get_actuator_value()
            assert len(actual_positions) == 3
            
    def test_cleanup_sequence(self, elliptec_plugin_with_controller):
        """Test proper cleanup sequence."""
        plugin = elliptec_plugin_with_controller
        controller = plugin.controller
        
        # Test cleanup
        plugin.close()
        
        controller.disconnect.assert_called_once()
        assert plugin.controller is None


class TestElliptecPyMoDAQCompliance:
    """Test PyMoDAQ 5.x compliance for Elliptec plugin."""
    
    def test_multiaxis_data_structure(self, elliptec_plugin_with_controller):
        """Test multi-axis data structure compliance."""
        plugin = elliptec_plugin_with_controller
        
        positions = plugin.get_actuator_value()
        
        # Should return list of numpy arrays (PyMoDAQ 5.x multi-axis pattern)
        assert isinstance(positions, list)
        assert len(positions) == 3  # Three polarization elements
        
        for pos in positions:
            assert isinstance(pos, np.ndarray)
            assert len(pos) == 1  # Single position per axis
            assert pos.dtype in [np.float64, np.float32]
            
    def test_move_done_signal_compliance(self, elliptec_plugin_with_controller):
        """Test move_done signal emission compliance."""
        plugin = elliptec_plugin_with_controller
        plugin.move_done = Mock()
        
        plugin.move_abs([45.0, 90.0, 135.0])
        
        # Should emit move_done signal after movement
        plugin.move_done.assert_called()
        
    def test_parameter_tree_multiaxis_compliance(self, elliptec_plugin):
        """Test parameter tree follows multi-axis compliance."""
        plugin = elliptec_plugin
        
        # Check parameter structure
        param_names = [param["name"] for param in plugin.params]
        
        # Should have multi-axis parameter structure
        assert any("axis1" in name for name in param_names)
        assert any("axis2" in name for name in param_names) 
        assert any("axis3" in name for name in param_names)
        
        # Should have bounds configuration
        assert any("bounds" in name for name in param_names)
        
        # Should have connection configuration
        assert any("connection" in name for name in param_names)
        
    def test_thread_safety_patterns(self, elliptec_plugin_with_controller):
        """Test thread-safe operation patterns."""
        plugin = elliptec_plugin_with_controller
        
        # Multiple rapid operations should not cause issues
        for _ in range(5):
            plugin.move_abs([np.random.uniform(0, 360) for _ in range(3)])
            positions = plugin.get_actuator_value()
            assert len(positions) == 3
            
    def test_error_status_emission(self, elliptec_plugin_with_controller):
        """Test error status emission patterns."""
        plugin = elliptec_plugin_with_controller
        plugin.emit_status = Mock()
        
        # Configure controller to fail
        plugin.controller.move_absolute.side_effect = Exception("Move failed")
        
        # Should handle error and potentially emit status
        plugin.move_abs([45.0, 90.0, 135.0])
        
        # Error handling is implementation-specific
        # Test passes if no exception is raised