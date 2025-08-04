# -*- coding: utf-8 -*-
"""
PyMoDAQ plugin for Newport ESP300 multi-axis motion controller.

Provides precision motion control for URASHG sample positioning, focusing, and
general XYZ stage movements. Supports up to 3 axes with individual configuration.

Compatible with PyMoDAQ 5.0+ multi-axis architecture.
"""

import time
from typing import List, Union

import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataActuator
from pymodaq.control_modules.thread_commands import ThreadStatusMove

from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import (
    AxisConfig,
    ESP300AxisError,
    ESP300Controller,
    ESP300GeneralError,
)


class DAQ_Move_ESP300(DAQ_Move_base):
    """
    PyMoDAQ plugin for Newport ESP300 multi-axis motion controller.

    Features:
    - Multi-axis support (1-3 axes configurable)
    - Precision positioning with software limits
    - Homing and calibration functions
    - Real-time position feedback
    - Comprehensive error handling
    - URASHG system integration ready
    """

    # Plugin metadata
    _controller_units = "millimeter"  # Default units
    _axis_names = ["X Stage", "Y Stage", "Z Focus"]  # Default axis names
    _epsilon = [0.001, 0.001, 0.0001]  # Position tolerances (mm, mm, μm)

    is_multiaxes = True  # Enable multi-axis support

    params = comon_parameters_fun(
        is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon
    ) + [
        # Connection settings
        {
            "title": "Connection:",
            "name": "connection_group",
            "type": "group",
            "children": [
                {
                    "title": "Serial Port:",
                    "name": "serial_port",
                    "type": "str",
                    "value": "/dev/ttyUSB2",
                },
                {
                    "title": "Baudrate:",
                    "name": "baudrate",
                    "type": "list",
                    "values": [9600, 19200, 38400, 57600, 115200],
                    "value": 19200,
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": 3.0,
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                },
            ],
        },
        # Axes configuration
        {
            "title": "Axes Config:",
            "name": "axes_config",
            "type": "group",
            "children": [
                {
                    "title": "Number of Axes:",
                    "name": "num_axes",
                    "type": "int",
                    "value": 3,
                    "min": 1,
                    "max": 3,
                },
                {
                    "title": "Axis 1:",
                    "name": "axis1_group",
                    "type": "group",
                    "children": [
                        {
                            "title": "Name:",
                            "name": "axis1_name",
                            "type": "str",
                            "value": "X Stage",
                        },
                        {
                            "title": "Units:",
                            "name": "axis1_units",
                            "type": "list",
                            "values": [
                                "millimeter",
                                "micrometer",
                                "degree",
                                "encoder count",
                            ],
                            "value": "millimeter",
                        },
                        {
                            "title": "Software Limits:",
                            "name": "axis1_limits",
                            "type": "bool",
                            "value": False,
                        },
                        {
                            "title": "Min Limit:",
                            "name": "axis1_min",
                            "type": "float",
                            "value": -25.0,
                            "suffix": "mm",
                        },
                        {
                            "title": "Max Limit:",
                            "name": "axis1_max",
                            "type": "float",
                            "value": 25.0,
                            "suffix": "mm",
                        },
                    ],
                },
                {
                    "title": "Axis 2:",
                    "name": "axis2_group",
                    "type": "group",
                    "children": [
                        {
                            "title": "Name:",
                            "name": "axis2_name",
                            "type": "str",
                            "value": "Y Stage",
                        },
                        {
                            "title": "Units:",
                            "name": "axis2_units",
                            "type": "list",
                            "values": [
                                "millimeter",
                                "micrometer",
                                "degree",
                                "encoder count",
                            ],
                            "value": "millimeter",
                        },
                        {
                            "title": "Software Limits:",
                            "name": "axis2_limits",
                            "type": "bool",
                            "value": False,
                        },
                        {
                            "title": "Min Limit:",
                            "name": "axis2_min",
                            "type": "float",
                            "value": -25.0,
                            "suffix": "mm",
                        },
                        {
                            "title": "Max Limit:",
                            "name": "axis2_max",
                            "type": "float",
                            "value": 25.0,
                            "suffix": "mm",
                        },
                    ],
                },
                {
                    "title": "Axis 3:",
                    "name": "axis3_group",
                    "type": "group",
                    "children": [
                        {
                            "title": "Name:",
                            "name": "axis3_name",
                            "type": "str",
                            "value": "Z Focus",
                        },
                        {
                            "title": "Units:",
                            "name": "axis3_units",
                            "type": "list",
                            "values": [
                                "millimeter",
                                "micrometer",
                                "degree",
                                "encoder count",
                            ],
                            "value": "micrometer",
                        },
                        {
                            "title": "Software Limits:",
                            "name": "axis3_limits",
                            "type": "bool",
                            "value": False,
                        },
                        {
                            "title": "Min Limit:",
                            "name": "axis3_min",
                            "type": "float",
                            "value": -1000.0,
                            "suffix": "μm",
                        },
                        {
                            "title": "Max Limit:",
                            "name": "axis3_max",
                            "type": "float",
                            "value": 1000.0,
                            "suffix": "μm",
                        },
                    ],
                },
            ],
        },
        # Motion settings
        {
            "title": "Motion:",
            "name": "motion_group",
            "type": "group",
            "children": [
                {
                    "title": "Home on Init:",
                    "name": "home_on_init",
                    "type": "bool",
                    "value": False,
                },
                {
                    "title": "Home Type:",
                    "name": "home_type",
                    "type": "list",
                    "values": list(range(7)),
                    "value": 1,
                },
                {
                    "title": "Wait for Motion:",
                    "name": "wait_motion",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Motion Timeout (s):",
                    "name": "motion_timeout",
                    "type": "float",
                    "value": 30.0,
                },
                {
                    "title": "Position Poll Rate (Hz):",
                    "name": "poll_rate",
                    "type": "float",
                    "value": 10.0,
                },
            ],
        },
        # Control actions
        {
            "title": "Actions:",
            "name": "actions_group",
            "type": "group",
            "children": [
                {"title": "Home All Axes:", "name": "home_all", "type": "action"},
                {"title": "Stop All Motion:", "name": "stop_all", "type": "action"},
                {"title": "Enable All Axes:", "name": "enable_all", "type": "action"},
                {"title": "Disable All Axes:", "name": "disable_all", "type": "action"},
                {"title": "Clear Errors:", "name": "clear_errors", "type": "action"},
            ],
        },
        # Status display
        {
            "title": "Status:",
            "name": "status_group",
            "type": "group",
            "children": [
                {
                    "title": "Connection:",
                    "name": "connection_status",
                    "type": "str",
                    "value": "Disconnected",
                    "readonly": True,
                },
                {
                    "title": "Axis 1 Position:",
                    "name": "axis1_position",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                    "suffix": "mm",
                },
                {
                    "title": "Axis 2 Position:",
                    "name": "axis2_position",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                    "suffix": "mm",
                },
                {
                    "title": "Axis 3 Position:",
                    "name": "axis3_position",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                    "suffix": "μm",
                },
                {
                    "title": "Last Error:",
                    "name": "last_error",
                    "type": "str",
                    "value": "None",
                    "readonly": True,
                },
            ],
        },
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        # Hardware controller
        self.controller: ESP300Controller = None

        # Current configuration
        self._current_axes = []
        self._position_poll_timer = None

    def ini_stage(self, controller=None):
        """Initialize the ESP300 motion controller."""
        try:
            self.emit_status(ThreadCommand("show_splash", "Initializing ESP300..."))

            # Check for mock mode
            if self.settings.child("connection_group", "mock_mode").value():
                self.emit_status(ThreadCommand("close_splash"))
                self.emit_status(
                    ThreadCommand("Update_Status", ["ESP300 in mock mode"])
                )
                self.controller = None
                return "ESP300 mock mode", True

            # Get connection parameters
            port = self.settings.child("connection_group", "serial_port").value()
            baudrate = self.settings.child("connection_group", "baudrate").value()
            timeout = self.settings.child("connection_group", "timeout").value()

            # Get axes configuration
            num_axes = self.settings.child("axes_config", "num_axes").value()
            axes_config = self._build_axes_config(num_axes)

            # Create controller
            self.controller = ESP300Controller(
                port=port, baudrate=baudrate, timeout=timeout, axes_config=axes_config
            )

            # Connect to device
            if not self.controller.connect():
                raise ConnectionError(f"Failed to connect to ESP300 on {port}")

            # Clear any existing errors
            errors = self.controller.clear_errors()
            if errors:
                self.emit_status(
                    ThreadCommand("Update_Status", [f"Cleared {len(errors)} errors"])
                )

            # Configure axes
            self._configure_axes()

            # Enable axes
            if not self.controller.enable_all_axes():
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Warning: Some axes failed to enable"]
                    )
                )

            # Home axes if requested
            if self.settings.child("motion_group", "home_on_init").value():
                home_type = self.settings.child("motion_group", "home_type").value()
                self.emit_status(ThreadCommand("Update_Status", ["Homing axes..."]))
                if self.controller.home_all_axes(home_type):
                    self.emit_status(
                        ThreadCommand("Update_Status", ["Homing completed"])
                    )
                else:
                    self.emit_status(ThreadCommand("Update_Status", ["Homing failed"]))

            # Update axis names for PyMoDAQ
            self._current_axes = [cfg.name for cfg in axes_config]

            # Start position monitoring
            self._start_position_monitoring()

            # Update status
            self._update_status_display()

            self.emit_status(ThreadCommand("close_splash"))

            info_string = f"ESP300 initialized on {port} with {num_axes} axes"
            self.emit_status(ThreadCommand("Update_Status", [info_string]))

            return info_string, True

        except Exception as e:
            error_msg = f"Error initializing ESP300: {e}"
            self.emit_status(ThreadCommand("Update_Status", [error_msg]))
            self.emit_status(ThreadCommand("close_splash"))
            if self.controller:
                self.controller.disconnect()
                self.controller = None
            return error_msg, False

    def _build_axes_config(self, num_axes: int) -> List[AxisConfig]:
        """Build axes configuration from settings."""
        axes_config = []

        for i in range(num_axes):
            axis_num = i + 1
            group_name = f"axis{axis_num}_group"

            name = self.settings.child(
                "axes_config", group_name, f"axis{axis_num}_name"
            ).value()
            units = self.settings.child(
                "axes_config", group_name, f"axis{axis_num}_units"
            ).value()

            config = AxisConfig(axis_num, name, units)

            # Set software limits if enabled
            if self.settings.child(
                "axes_config", group_name, f"axis{axis_num}_limits"
            ).value():
                config.left_limit = self.settings.child(
                    "axes_config", group_name, f"axis{axis_num}_min"
                ).value()
                config.right_limit = self.settings.child(
                    "axes_config", group_name, f"axis{axis_num}_max"
                ).value()

            axes_config.append(config)

        return axes_config

    def _configure_axes(self):
        """Apply axis-specific configuration."""
        try:
            for axis_num, axis in self.controller.axes.items():
                # Set units
                if not axis.set_units(axis.config.units):
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            [f"Warning: Failed to set units for axis {axis_num}"],
                        )
                    )

                # Set software limits if configured
                if (
                    axis.config.left_limit is not None
                    and axis.config.right_limit is not None
                ):
                    if not axis.set_software_limits(
                        axis.config.left_limit, axis.config.right_limit
                    ):
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status",
                                [f"Warning: Failed to set limits for axis {axis_num}"],
                            )
                        )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error configuring axes: {e}"])
            )

    def _start_position_monitoring(self):
        """Start periodic position monitoring."""
        # Note: In a real implementation, you might want to use a QTimer
        # For now, we'll update positions on each get_actuator_value call
        pass

    def _update_status_display(self):
        """Update status display parameters and notify PyMoDAQ UI."""
        try:
            if not self.controller or not self.controller.is_connected():
                self.settings.child("status_group", "connection_status").setValue(
                    "Disconnected"
                )
                return

            self.settings.child("status_group", "connection_status").setValue(
                "Connected"
            )

            # Update positions
            positions = self.controller.get_all_positions()
            for i, (axis_num, position) in enumerate(positions.items(), 1):
                if i <= 3:  # Only update up to 3 axes in status
                    param_name = f"axis{i}_position"
                    self.settings.child("status_group", param_name).setValue(position)

            # Create position array and notify main PyMoDAQ UI
            current_positions = self.get_actuator_value()
            plugin_name = getattr(self, 'title', self.__class__.__name__)
            if self.is_multiaxes:
                data_actuator = DataActuator(
                    name=plugin_name,
                    data=[np.array(current_positions)],
                    units=self._controller_units
                )
            else:
                data_actuator = DataActuator(
                    name=plugin_name,
                    data=[np.array([current_positions])],
                    units=self._controller_units
                )
            self.emit_status(ThreadCommand(ThreadStatusMove.GET_ACTUATOR_VALUE, data_actuator))

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error updating status: {e}"])
            )

    def close(self):
        """Close connection to ESP300."""
        try:
            if self.controller:
                self.controller.disconnect()
                self.controller = None
            self.settings.child("status_group", "connection_status").setValue(
                "Disconnected"
            )
            self.emit_status(
                ThreadCommand("Update_Status", ["ESP300 connection closed"])
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error closing connection: {e}"])
            )

    def get_actuator_value(self) -> Union[float, List[float]]:
        """Get current position(s) of the actuator(s)."""
        try:
            if not self.controller or not self.controller.is_connected():
                # Return zeros for mock mode or disconnected state
                num_axes = len(self._current_axes) if self._current_axes else 1
                return [0.0] * num_axes if self.is_multiaxes else 0.0

            positions = self.controller.get_all_positions()

            if self.is_multiaxes:
                # Return list of positions in axis order
                position_list = []
                for i in range(len(self._current_axes)):
                    axis_num = i + 1
                    position_list.append(positions.get(axis_num, 0.0))

                # Update status display
                self._update_status_display()

                return position_list
            else:
                # Single axis mode
                return positions.get(1, 0.0)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error reading positions: {e}"])
            )
            self.settings.child("status_group", "last_error").setValue(str(e))

            if self.is_multiaxes:
                return [0.0] * len(self._current_axes)
            else:
                return 0.0

    def move_abs(self, position: Union[float, List[float], DataActuator]):
        """
        Move to absolute position(s).
        
        Parameters
        ----------
        position : Union[float, List[float], DataActuator]
            Target position(s). For DataActuator objects in multi-axis mode, use position.data[0]
            to extract the numpy array (PyMoDAQ 5.x multi-axis pattern).
        """
        try:
            if not self.controller or not self.controller.is_connected():
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Cannot move: ESP300 not connected"]
                    )
                )
                return

            # Extract numerical value(s) from DataActuator
            if isinstance(position, DataActuator):
                if self.is_multiaxes:
                    # Multi-axis: position.data[0] is numpy array with multiple values
                    target_positions_array = position.data[0]
                    target_positions_list = target_positions_array.tolist() if hasattr(target_positions_array, 'tolist') else list(target_positions_array)
                else:
                    # Single axis: extract single value
                    target_positions_list = float(position.data[0][0])
            else:
                # Fallback for direct numerical input (backward compatibility)
                target_positions_list = position

            if self.is_multiaxes:
                if not isinstance(target_positions_list, (list, tuple, np.ndarray)):
                    raise ValueError("Multi-axis mode requires list of positions")

                # Build position dictionary
                target_positions = {}
                for i, pos in enumerate(target_positions_list):
                    if i < len(self._current_axes):
                        axis_num = i + 1
                        target_positions[axis_num] = float(pos)

                # Execute multi-axis move
                wait_for_motion = self.settings.child(
                    "motion_group", "wait_motion"
                ).value()
                if not self.controller.move_multiple_axes(
                    target_positions, wait=wait_for_motion
                ):
                    raise RuntimeError("Multi-axis move failed")

            else:
                # Single axis move
                axis = self.controller.get_axis(1)
                if not axis:
                    raise RuntimeError("Axis 1 not available")

                if not axis.move_absolute(float(target_positions_list)):
                    raise RuntimeError("Move command failed")

                # Wait for motion if enabled
                if self.settings.child("motion_group", "wait_motion").value():
                    timeout = self.settings.child(
                        "motion_group", "motion_timeout"
                    ).value()
                    if not axis.wait_for_stop(timeout):
                        raise RuntimeError("Motion timeout")

            self._update_status_display()

            # Emit move done signal with proper DataActuator
            current_positions = self.get_actuator_value()
            plugin_name = getattr(self, 'title', self.__class__.__name__)
            if self.is_multiaxes:
                data_actuator = DataActuator(
                    name=plugin_name,
                    data=[np.array(current_positions)],
                    units=self._controller_units
                )
            else:
                data_actuator = DataActuator(
                    name=plugin_name,
                    data=[np.array([current_positions])],
                    units=self._controller_units
                )
            self.emit_status(ThreadCommand(ThreadStatusMove.MOVE_DONE, data_actuator))

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Move error: {e}"]))
            self.settings.child("status_group", "last_error").setValue(str(e))

    def move_rel(self, position: Union[float, List[float], DataActuator]):
        """
        Move by relative distance(s).
        
        Parameters
        ----------
        position : Union[float, List[float], DataActuator]
            Relative move distance(s). For DataActuator objects in multi-axis mode, use position.data[0]
            to extract the numpy array (PyMoDAQ 5.x multi-axis pattern).
        """
        try:
            # Extract numerical value(s) from DataActuator
            if isinstance(position, DataActuator):
                if self.is_multiaxes:
                    # Multi-axis: position.data[0] is numpy array with multiple values
                    relative_moves_array = position.data[0]
                    relative_moves_list = relative_moves_array.tolist() if hasattr(relative_moves_array, 'tolist') else list(relative_moves_array)
                else:
                    # Single axis: extract single value
                    relative_moves_list = float(position.data[0][0])
            else:
                # Fallback for direct numerical input (backward compatibility)
                relative_moves_list = position

            # Get current positions and add relative moves
            current_positions = self.get_actuator_value()

            if self.is_multiaxes:
                if not isinstance(relative_moves_list, (list, tuple, np.ndarray)):
                    raise ValueError("Multi-axis mode requires list of positions")

                target_positions = []
                for i, (current, relative) in enumerate(
                    zip(current_positions, relative_moves_list)
                ):
                    target_positions.append(current + relative)

                # Create DataActuator for target positions
                plugin_name = getattr(self, 'title', self.__class__.__name__)
                target_data = DataActuator(
                    name=plugin_name,
                    data=[np.array(target_positions)],
                    units=self._controller_units
                )
                self.move_abs(target_data)
            else:
                target_position = current_positions + relative_moves_list
                
                # Create DataActuator for target position
                plugin_name = getattr(self, 'title', self.__class__.__name__)
                target_data = DataActuator(
                    name=plugin_name,
                    data=[np.array([target_position])],
                    units=self._controller_units
                )
                self.move_abs(target_data)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Relative move error: {e}"])
            )
            self.settings.child("status_group", "last_error").setValue(str(e))

    def move_home(self):
        """Move all axes to home position."""
        try:
            if not self.controller or not self.controller.is_connected():
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Cannot home: ESP300 not connected"]
                    )
                )
                return

            home_type = self.settings.child("motion_group", "home_type").value()

            self.emit_status(ThreadCommand("Update_Status", ["Homing axes..."]))

            if self.controller.home_all_axes(home_type, wait=True):
                self.emit_status(ThreadCommand("Update_Status", ["Homing completed"]))
                self._update_status_display()
            else:
                raise RuntimeError("Homing failed")

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Homing error: {e}"]))
            self.settings.child("status_group", "last_error").setValue(str(e))

    def stop_motion(self):
        """Stop all axis motion immediately."""
        try:
            if self.controller and self.controller.is_connected():
                if self.controller.stop_all_axes():
                    self.emit_status(
                        ThreadCommand("Update_Status", ["All motion stopped"])
                    )
                else:
                    self.emit_status(
                        ThreadCommand("Update_Status", ["Stop command failed"])
                    )
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["ESP300 not connected"])
                )

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Stop error: {e}"]))

    def commit_settings(self, param: Parameter):
        """Handle parameter changes."""
        try:
            param_name = param.name()

            if param_name == "home_all":
                self.move_home()

            elif param_name == "stop_all":
                self.stop_motion()

            elif param_name == "enable_all":
                if self.controller and self.controller.is_connected():
                    if self.controller.enable_all_axes():
                        self.emit_status(
                            ThreadCommand("Update_Status", ["All axes enabled"])
                        )
                    else:
                        self.emit_status(
                            ThreadCommand("Update_Status", ["Enable failed"])
                        )

            elif param_name == "disable_all":
                if self.controller and self.controller.is_connected():
                    if self.controller.disable_all_axes():
                        self.emit_status(
                            ThreadCommand("Update_Status", ["All axes disabled"])
                        )
                    else:
                        self.emit_status(
                            ThreadCommand("Update_Status", ["Disable failed"])
                        )

            elif param_name == "clear_errors":
                if self.controller and self.controller.is_connected():
                    errors = self.controller.clear_errors()
                    if errors:
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status", [f"Cleared {len(errors)} errors"]
                            )
                        )
                        self.settings.child("status_group", "last_error").setValue(
                            "Cleared"
                        )
                    else:
                        self.emit_status(
                            ThreadCommand("Update_Status", ["No errors to clear"])
                        )
                        self.settings.child("status_group", "last_error").setValue(
                            "None"
                        )

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Settings error: {e}"]))

    def check_position(self) -> bool:
        """Check if position is within tolerance."""
        try:
            # This method is called by PyMoDAQ to verify position accuracy
            # For ESP300, we can check motion_done status
            if not self.controller or not self.controller.is_connected():
                return True  # Assume OK if disconnected (mock mode)

            # Check if all axes have completed motion
            for axis in self.controller.axes.values():
                if not axis.is_motion_done():
                    return False

            return True

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Position check error: {e}"])
            )
            return False



