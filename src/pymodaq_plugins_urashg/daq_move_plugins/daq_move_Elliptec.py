from typing import List, Union

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
    DataActuator,
    main,
)
from pymodaq_utils.utils import ThreadCommand

# Import URASHG configuration
try:
    from pymodaq_plugins_urashg.utils.config import Config
    from pymodaq_plugins_urashg import get_config

    config = get_config()
    elliptec_config = config.get_hardware_config("elliptec")
except ImportError:
    elliptec_config = {
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "timeout": 2.0,
        "mount_addresses": "2,3,8",
    }


from pymodaq_plugins_urashg.daq_move_plugins.elliptec_ui import ElliptecUI

class DAQ_Move_Elliptec(DAQ_Move_base):
    widget = ElliptecUI
    """
    PyMoDAQ plugin for Thorlabs Elliptec rotation mounts (ELL14).

    Supports multi-axis control of up to 3 rotation mounts:
    - HWP incident polarizer (address 2)
    - QWP quarter wave plate (address 3)
    - HWP analyzer (address 8)
    """

    # Plugin metadata
    _controller_units = "degrees"
    is_multiaxes = True
    _axis_names = ["HWP_Incident", "QWP", "HWP_Analyzer"]  # Physical names
    _epsilon = [0.1, 0.1, 0.1]  # Position precision in degrees for each axis

    # Plugin parameters following PyMoDAQ 5.x standards
    params = comon_parameters_fun(
        is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon
    ) + [
        # Position bounds for each axis (degrees)
        {
            "title": "Position Bounds:",
            "name": "bounds_group",
            "type": "group",
            "children": [
                {
                    "title": "Min Position (°):",
                    "name": "min_position",
                    "type": "float",
                    "value": 0.0,
                    "min": 0.0,
                    "max": 360.0,
                    "tip": "Minimum rotation position in degrees",
                },
                {
                    "title": "Max Position (°):",
                    "name": "max_position",
                    "type": "float",
                    "value": 360.0,
                    "min": 0.0,
                    "max": 360.0,
                    "tip": "Maximum rotation position in degrees",
                },
            ],
        },
        # Hardware connection
        {
            "title": "Connection:",
            "name": "connection_group",
            "type": "group",
            "children": [
                {
                    "title": "Serial Port:",
                    "name": "serial_port",
                    "type": "str",
                    "value": elliptec_config.get("serial_port", "/dev/ttyUSB0"),
                    "tip": "Serial port for Elliptec controller (e.g. /dev/ttyUSB0 or COM1)",
                },
                {
                    "title": "Baudrate:",
                    "name": "baudrate",
                    "type": "list",
                    "limits": [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200],
                    "value": elliptec_config.get("baudrate", 9600),
                    "tip": "Serial communication baud rate",
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": elliptec_config.get("timeout", 2.0),
                    "min": 0.1,
                    "max": 10.0,
                    "tip": "Communication timeout in seconds",
                },
                {
                    "title": "Mount Addresses:",
                    "name": "mount_addresses",
                    "type": "str",
                    "value": elliptec_config.get("mount_addresses", "2,3,8"),
                    "tip": "Comma-separated Elliptec addresses: HWP_Incident(2), QWP(3), HWP_Analyzer(8)",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                    "tip": "Enable for testing without physical hardware",
                },
            ],
        },
        # Device actions
        {
            "title": "Global Actions:",
            "name": "actions_group",
            "type": "group",
            "children": [
                {
                    "title": "Home All Mounts:",
                    "name": "home_all",
                    "type": "action",
                },
                {
                    "title": "Get Positions:",
                    "name": "get_positions",
                    "type": "action",
                },
                {
                    "title": "Test Connection:",
                    "name": "test_connection",
                    "type": "action",
                },
            ],
        },
        # Individual axis controls
        {
            "title": "HWP Incident (Axis 1):",
            "name": "axis1_group",
            "type": "group",
            "children": [
                {
                    "title": "Target Angle (°):",
                    "name": "axis1_target",
                    "type": "float",
                    "value": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 0.1,
                },
                {
                    "title": "Jog Step (°):",
                    "name": "axis1_jog_step",
                    "type": "float",
                    "value": 1.0,
                    "min": 0.1,
                    "max": 45.0,
                    "step": 0.1,
                },
                {
                    "title": "Home Axis 1:",
                    "name": "axis1_home",
                    "type": "action",
                },
                {
                    "title": "Set Angle:",
                    "name": "axis1_set_angle",
                    "type": "action",
                },
                {
                    "title": "Jog +:",
                    "name": "axis1_jog_plus",
                    "type": "action",
                },
                {
                    "title": "Jog -:",
                    "name": "axis1_jog_minus",
                    "type": "action",
                },
            ],
        },
        {
            "title": "QWP (Axis 2):",
            "name": "axis2_group",
            "type": "group",
            "children": [
                {
                    "title": "Target Angle (°):",
                    "name": "axis2_target",
                    "type": "float",
                    "value": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 0.1,
                },
                {
                    "title": "Jog Step (°):",
                    "name": "axis2_jog_step",
                    "type": "float",
                    "value": 1.0,
                    "min": 0.1,
                    "max": 45.0,
                    "step": 0.1,
                },
                {
                    "title": "Home Axis 2:",
                    "name": "axis2_home",
                    "type": "action",
                },
                {
                    "title": "Set Angle:",
                    "name": "axis2_set_angle",
                    "type": "action",
                },
                {
                    "title": "Jog +:",
                    "name": "axis2_jog_plus",
                    "type": "action",
                },
                {
                    "title": "Jog -:",
                    "name": "axis2_jog_minus",
                    "type": "action",
                },
            ],
        },
        {
            "title": "HWP Analyzer (Axis 3):",
            "name": "axis3_group",
            "type": "group",
            "children": [
                {
                    "title": "Target Angle (°):",
                    "name": "axis3_target",
                    "type": "float",
                    "value": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 0.1,
                },
                {
                    "title": "Jog Step (°):",
                    "name": "axis3_jog_step",
                    "type": "float",
                    "value": 1.0,
                    "min": 0.1,
                    "max": 45.0,
                    "step": 0.1,
                },
                {
                    "title": "Home Axis 3:",
                    "name": "axis3_home",
                    "type": "action",
                },
                {
                    "title": "Set Angle:",
                    "name": "axis3_set_angle",
                    "type": "action",
                },
                {
                    "title": "Jog +:",
                    "name": "axis3_jog_plus",
                    "type": "action",
                },
                {
                    "title": "Jog -:",
                    "name": "axis3_jog_minus",
                    "type": "action",
                },
            ],
        },
        # Status monitoring
        {
            "title": "Status:",
            "name": "status_group",
            "type": "group",
            "children": [
                {
                    "title": "Connection Status:",
                    "name": "connection_status",
                    "type": "str",
                    "value": "Disconnected",
                    "readonly": True,
                },
            ],
        },
    ]

    def ini_attributes(self):
        """Initialize attributes before __init__ - PyMoDAQ 5.x pattern"""
        self.controller = None

    def check_bound(self, position):
        """Ensure position is within valid range for rotation mounts"""
        min_pos = self.settings.child("bounds_group", "min_position").value()
        max_pos = self.settings.child("bounds_group", "max_position").value()
        return max(min_pos, min(max_pos, float(position)))

    def get_actuator_value(self):
        """Get current position of all axes"""
        try:
            if self.controller is None:
                # Return raw numpy arrays - PyMoDAQ framework wraps in DataActuator
                import numpy as np

                return [np.array([0.0]) for _ in self._axis_names]

            # Use get_all_positions() instead of get_positions()
            positions = self.controller.get_all_positions()
            if isinstance(positions, dict):
                # Convert dict to list in axis order (mount addresses to axis names)
                position_list = []
                for i, axis_name in enumerate(self._axis_names):
                    # Ensure mount address is string - fix for "8]gp" error
                    mount_addr = (
                        str(self.controller.mount_addresses[i])
                        if i < len(self.controller.mount_addresses)
                        else "2"
                    )
                    position_list.append(positions.get(mount_addr, 0.0))
            else:
                position_list = (
                    positions if isinstance(positions, list) else [positions]
                )

            # Ensure we have the right number of values
            while len(position_list) < len(self._axis_names):
                position_list.append(0.0)

            # Convert to numpy arrays for PyMoDAQ framework
            import numpy as np

            # Ensure we have valid positions and create non-empty numpy arrays
            position_list = position_list[: len(self._axis_names)]
            if not position_list:  # If empty, fill with zeros
                position_list = [0.0] * len(self._axis_names)

            numpy_arrays = []
            for pos in position_list:
                if isinstance(pos, (int, float)):
                    numpy_arrays.append(np.array([float(pos)]))
                else:
                    numpy_arrays.append(
                        np.array([0.0])
                    )  # Fallback for invalid positions

            # Return raw numpy arrays - PyMoDAQ framework handles DataActuator wrapping
            return numpy_arrays

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error getting position: {str(e)}", "log"]
                )
            )
            # Return raw numpy arrays - PyMoDAQ framework wraps in DataActuator
            import numpy as np

            return [np.array([0.0]) for _ in self._axis_names]

    def close(self):
        """Close the hardware connection"""
        try:
            if self.controller is not None:
                self.controller.disconnect()
                self.controller = None
            self.emit_status(
                ThreadCommand("Update_Status", ["Elliptec disconnected", "log"])
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error closing: {str(e)}", "log"])
            )

    def commit_settings(self, param):
        """Handle parameter changes"""
        try:
            # Global actions
            if param.name() == "home_all":
                self.home_all_mounts()
            elif param.name() == "get_positions":
                self.get_actuator_value()
                self.emit_status(
                    ThreadCommand("Update_Status", ["Positions updated", "log"])
                )
            elif param.name() == "test_connection":
                self.test_hardware_connection()

            # Axis 1 (HWP Incident) controls
            elif param.name() == "axis1_home":
                self.home_axis(0)
            elif param.name() == "axis1_set_angle":
                angle = self.settings.child("axis1_group", "axis1_target").value()
                self.move_axis(0, angle)
            elif param.name() == "axis1_jog_plus":
                self.jog_axis(0, True)
            elif param.name() == "axis1_jog_minus":
                self.jog_axis(0, False)

            # Axis 2 (QWP) controls
            elif param.name() == "axis2_home":
                self.home_axis(1)
            elif param.name() == "axis2_set_angle":
                angle = self.settings.child("axis2_group", "axis2_target").value()
                self.move_axis(1, angle)
            elif param.name() == "axis2_jog_plus":
                self.jog_axis(1, True)
            elif param.name() == "axis2_jog_minus":
                self.jog_axis(1, False)

            # Axis 3 (HWP Analyzer) controls
            elif param.name() == "axis3_home":
                self.home_axis(2)
            elif param.name() == "axis3_set_angle":
                angle = self.settings.child("axis3_group", "axis3_target").value()
                self.move_axis(2, angle)
            elif param.name() == "axis3_jog_plus":
                self.jog_axis(2, True)
            elif param.name() == "axis3_jog_minus":
                self.jog_axis(2, False)

            # Configuration changes
            elif param.name() in [
                "serial_port",
                "baudrate",
                "timeout",
                "mount_addresses",
                "mock_mode",
            ]:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Settings updated - restart to apply", "log"]
                    )
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error in commit_settings: {str(e)}", "log"]
                )
            )

    def ini_stage(self, controller=None):
        """Initialize the hardware stage - PyMoDAQ 5.x standard method"""
        self.initialized = False
        try:
            # Import here to avoid issues if module not available
            from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import (
                ElliptecController,
            )

            # Get connection parameters
            port = self.settings.child("connection_group", "serial_port").value()
            baudrate = self.settings.child("connection_group", "baudrate").value()
            timeout = self.settings.child("connection_group", "timeout").value()
            mount_addresses = self.settings.child(
                "connection_group", "mount_addresses"
            ).value()
            mock_mode = self.settings.child("connection_group", "mock_mode").value()

            # Use existing controller if provided (slave mode)
            if controller is not None:
                self.controller = controller
            else:
                # Create new controller
                self.controller = ElliptecController(
                    port=port,
                    baudrate=baudrate,
                    timeout=timeout,
                    mount_addresses=mount_addresses,
                    mock_mode=mock_mode,
                )

            # Connect to hardware
            if self.controller.connect():
                self.settings.child("status_group", "connection_status").setValue(
                    "Connected"
                )
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Elliptec mounts connected.", "log"]
                    )
                )

                # Set units for all axes
                for axis in self._axis_names:
                    self.settings.child("units").setValue(self._controller_units)

                self.initialized = True
                return "Elliptec mounts initialized successfully", True
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        ["Failed to connect to Elliptec mounts.", "log"],
                    )
                )
                return "Failed to connect to Elliptec mounts", False

        except ImportError as e:
            msg = f"ElliptecController not available: {str(e)}"
            self.emit_status(ThreadCommand("Update_Status", [msg, "log"]))
            return msg, False
        except Exception as e:
            msg = f"Error initializing Elliptec: {str(e)}"
            self.emit_status(ThreadCommand("Update_Status", [msg, "log"]))
            return msg, False

    def move_abs(self, positions: Union[List[float], DataActuator]):
        """Move to absolute positions"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            # Handle DataActuator input (PyMoDAQ 5.x pattern)
            if isinstance(positions, DataActuator):
                # Use value() method for DataActuator
                target_positions = positions.value()
                if not isinstance(target_positions, list):
                    target_positions = [target_positions]
            else:
                target_positions = (
                    positions if isinstance(positions, list) else [positions]
                )

            # Ensure we have the right number of positions
            while len(target_positions) < len(self._axis_names):
                target_positions.append(0.0)

            # Apply bounds checking
            for i, pos in enumerate(target_positions):
                target_positions[i] = self.check_bound(pos)

            # Move all axes individually (no move_absolute_all method exists)
            success = True
            for i, pos in enumerate(target_positions):
                if i < len(self.controller.mount_addresses):
                    mount_addr = str(self.controller.mount_addresses[i])
                    if not self.controller.move_absolute(mount_addr, pos):
                        success = False
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status",
                                [
                                    f"Failed to move {self._axis_names[i]} to {pos}°",
                                    "log",
                                ],
                            )
                        )

            if success:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Move completed", "log"])
                )
                self.move_done()  # Signal completion
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Some moves failed", "log"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in move_abs: {str(e)}", "log"])
            )

    def move_rel(self, positions: Union[List[float], DataActuator]):
        """Move relative positions"""
        try:
            # Get current positions as numpy arrays
            current_arrays = self.get_actuator_value()

            # Extract values from numpy arrays
            current_values = []
            for arr in current_arrays:
                if len(arr) > 0:
                    current_values.append(float(arr[0]))
                else:
                    current_values.append(0.0)

            # Handle relative position input
            if isinstance(positions, DataActuator):
                rel_positions = positions.value()
                if not isinstance(rel_positions, list):
                    rel_positions = [rel_positions]
            else:
                rel_positions = (
                    positions if isinstance(positions, list) else [positions]
                )

            # Calculate absolute target positions
            target_positions = []
            for i in range(len(self._axis_names)):
                current = current_values[i] if i < len(current_values) else 0.0
                relative = rel_positions[i] if i < len(rel_positions) else 0.0
                target_positions.append(current + relative)

            self.move_abs(target_positions)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in move_rel: {str(e)}", "log"])
            )

    def move_home(self):
        """Move all axes to home position"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            success = self.controller.home_all()
            if success:
                self.emit_status(
                    ThreadCommand("Update_Status", ["All axes homed", "log"])
                )
                self.move_done()  # Signal completion
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Homing failed", "log"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in move_home: {str(e)}", "log"])
            )

    def stop_motion(self):
        """Stop all motion"""
        try:
            # Elliptec devices may not have explicit stop command
            # Just signal that motion is complete
            self.emit_status(ThreadCommand("Update_Status", ["Motion stopped", "log"]))
            self.move_done()  # Signal that motion is complete
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error stopping motion: {str(e)}", "log"]
                )
            )

    def home_all_mounts(self):
        """Home all mounts - convenience method"""
        self.move_home()

    def test_hardware_connection(self):
        """Test hardware connection"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            # Use is_connected instead of test_connection
            if self.controller.is_connected():
                self.emit_status(
                    ThreadCommand("Update_Status", ["Connection test passed", "log"])
                )
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Connection test failed", "log"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Connection test error: {str(e)}", "log"]
                )
            )

    def home_axis(self, axis_index):
        """Home a specific axis"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            if axis_index < len(self._axis_names):
                # Ensure mount address is string
                mount_addr = str(self.controller.mount_addresses[axis_index])
                success = self.controller.home(mount_addr)
                axis_name = self._axis_names[axis_index]

                if success:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", [f"{axis_name} homed successfully", "log"]
                        )
                    )
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", [f"Failed to home {axis_name}", "log"]
                        )
                    )
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", [f"Invalid axis index: {axis_index}", "log"]
                    )
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"Error homing axis {axis_index}: {str(e)}", "log"],
                )
            )

    def move_axis(self, axis_index, angle):
        """Move a specific axis to an angle"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            if axis_index < len(self._axis_names):
                # Apply bounds checking
                angle = self.check_bound(angle)

                # Ensure mount address is string
                mount_addr = str(self.controller.mount_addresses[axis_index])
                success = self.controller.move_absolute(mount_addr, angle)
                axis_name = self._axis_names[axis_index]

                if success:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", [f"{axis_name} moved to {angle}°", "log"]
                        )
                    )
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            [f"Failed to move {axis_name} to {angle}°", "log"],
                        )
                    )
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", [f"Invalid axis index: {axis_index}", "log"]
                    )
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"Error moving axis {axis_index}: {str(e)}", "log"],
                )
            )

    def jog_axis(self, axis_index, positive_direction):
        """Jog a specific axis by the step amount"""
        try:
            if self.controller is None:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Controller not initialized", "log"]
                    )
                )
                return

            if axis_index < len(self._axis_names):
                # Get jog step from settings
                group_names = ["axis1_group", "axis2_group", "axis3_group"]
                step_names = ["axis1_jog_step", "axis2_jog_step", "axis3_jog_step"]

                if axis_index < len(group_names):
                    jog_step = self.settings.child(
                        group_names[axis_index], step_names[axis_index]
                    ).value()
                    if not positive_direction:
                        jog_step = -jog_step

                    # Ensure mount address is string
                    mount_addr = str(self.controller.mount_addresses[axis_index])
                    success = self.controller.move_relative(mount_addr, jog_step)
                    axis_name = self._axis_names[axis_index]

                    direction = "+" if positive_direction else "-"
                    if success:
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status",
                                [
                                    f"{axis_name} jogged {direction}{abs(jog_step)}°",
                                    "log",
                                ],
                            )
                        )
                    else:
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status", [f"Failed to jog {axis_name}", "log"]
                            )
                        )
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            [f"Invalid axis index: {axis_index}", "log"],
                        )
                    )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"Error jogging axis {axis_index}: {str(e)}", "log"],
                )
            )


if __name__ == "__main__":
    main(__file__)
