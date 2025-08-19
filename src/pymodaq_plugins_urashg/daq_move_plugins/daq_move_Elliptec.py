import time
from typing import List, Union

import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataActuator

# QTimer replaced with PyMoDAQ threading patterns


class DAQ_Move_Elliptec(DAQ_Move_base):
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
    _epsilon = 0.1  # Position precision in degrees

    # Plugin parameters
    params = comon_parameters_fun(
        is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon
    ) + [
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
                    "value": "", "placeholder": "Enter serial port e.g. /dev/ttyUSB0 or COM1"
                },
                {
                    "title": "Baudrate:",
                    "name": "baudrate",
                    "type": "int",
                    "value": 9600,
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": 2.0,
                    "min": 0.1,
                    "max": 10.0,
                },
                {
                    "title": "Mount Addresses:",
                    "name": "mount_addresses",
                    "type": "str",
                    "value": "2,3,8",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                },
            ],
        },
        # Device actions
        {
            "title": "Actions:",
            "name": "actions_group",
            "type": "group",
            "children": [
                {"title": "Home All Mounts:", "name": "home_all", "type": "action"},
                {"title": "Get Positions:", "name": "get_positions", "type": "action"},
                {
                    "title": "Test Connection:",
                    "name": "test_connection",
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

    def __init__(self, parent=None, params_state=None):
        """Initialize Elliptec PyMoDAQ plugin."""
        super().__init__(parent, params_state)

        # Hardware controller
        self.controller = None

        # PyMoDAQ will handle periodic polling via built-in poll_time parameter

    def _update_ui_from_settings(self):
        """Dynamically create UI elements based on mount addresses."""
        try:
            mount_addresses_str = self.settings.child(
                "connection_group", "mount_addresses"
            ).value()
            mount_addresses = [addr.strip() for addr in mount_addresses_str.split(",")]

            # Clear existing dynamic controls
            actions_group = self.settings.child("actions_group")
            status_group = self.settings.child("status_group")

            # Use a temporary list to avoid issues while removing
            to_remove_actions = [
                child
                for child in actions_group.children()
                if "home_mount" in child.name()
            ]
            to_remove_status = [
                child
                for child in status_group.children()
                if "mount" in child.name() and "pos" in child.name()
            ]

            for child in to_remove_actions:
                actions_group.removeChild(child)
            for child in to_remove_status:
                status_group.removeChild(child)

            # Add new controls
            for addr in mount_addresses:
                # Add home button
                home_action = {
                    "title": f"Home Mount {addr}:",
                    "name": f"home_mount_{addr}",
                    "type": "action",
                }
                actions_group.addChild(home_action)

                # Add position status
                pos_status = {
                    "title": f"Mount {addr} Position (deg):",
                    "name": f"mount_{addr}_pos",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                }
                status_group.addChild(pos_status)
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"UI Update Error: {str(e)}", "error"])
            )

    def ini_stage(self, controller=None):
        """Initialize the hardware stage."""
        try:
            # Import here to avoid issues if module not available
            from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import (
                ElliptecController,
            )

            # Update UI before initializing controller
            self._update_ui_from_settings()

            # Get connection parameters
            port = self.settings.child("connection_group", "serial_port").value()
            baudrate = self.settings.child("connection_group", "baudrate").value()
            timeout = self.settings.child("connection_group", "timeout").value()
            mount_addresses = self.settings.child(
                "connection_group", "mount_addresses"
            ).value()
            mock_mode = self.settings.child("connection_group", "mock_mode").value()

            # Create controller
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
                        "Update_Status", ["Elliptec mounts connected.", "good"]
                    )
                )
                self.update_status()
                # Status monitoring handled by PyMoDAQ polling (set poll_time in UI)
                return "Elliptec mounts initialized successfully", True
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        ["Failed to connect to Elliptec mounts.", "bad"],
                    )
                )
                return "Failed to connect to Elliptec mounts", False

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error initializing Elliptec: {str(e)}", "error"]
                )
            )
            return f"Error initializing Elliptec: {str(e)}", False

    def close(self):
        """Close the hardware connection."""
        try:
            # Status monitoring cleanup handled by PyMoDAQ
            if self.controller and self.controller.connected:
                self.controller.disconnect()
            self.settings.child("status_group", "connection_status").setValue(
                "Disconnected"
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error closing: {str(e)}", "log"])
            )

    def commit_settings(self, param):
        """Handle parameter changes."""
        if param.name() == "mount_addresses":
            self._update_ui_from_settings()
            # Re-initialize to apply changes
            self.ini_stage()

        elif param.name() == "home_all":
            self.home_all_mounts()
        elif "home_mount" in param.name():
            # Handle dynamic home buttons
            try:
                addr = param.name().split("_")[-1]
                self.home_individual_mount(addr)
            except IndexError:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [f"Invalid home button name: {param.name()}", "error"],
                    )
                )

        elif param.name() == "get_positions":
            self.update_status()
        elif param.name() == "test_connection":
            self.test_hardware_connection()

    def move_home(self, value=None):
        """
        Move all axes to home position.

        Parameters
        ----------
        value : any, optional
            Home position value (required by PyMoDAQ 5.x interface)
        """
        self.home_all_mounts()

    def home_all_mounts(self):
        """Home all rotation mounts."""
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", ["Hardware not connected. Cannot home.", "warning"]
                )
            )
            return

        try:
            self.emit_status(
                ThreadCommand("Update_Status", ["Homing all mounts...", "log"])
            )
            success = self.controller.home_all()
            if success:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["All mounts homed successfully", "good"]
                    )
                )
                self.update_status()
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Homing failed", "bad"])
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error homing: {str(e)}", "error"])
            )

    def home_individual_mount(self, mount_address: str):
        """Home individual rotation mount."""
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", ["Hardware not connected. Cannot home.", "warning"]
                )
            )
            return

        try:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Homing mount {mount_address}...", "log"]
                )
            )
            success = self.controller.home(mount_address)
            if success:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [f"Mount {mount_address} homed successfully", "good"],
                    )
                )
                self.update_status()
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", [f"Homing mount {mount_address} failed", "bad"]
                    )
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"Error homing mount {mount_address}: {str(e)}", "error"],
                )
            )

    def test_hardware_connection(self):
        """Test hardware connection and report status."""
        try:
            port = self.settings.child("connection_group", "serial_port").value()
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Testing connection to {port}...", "log"]
                )
            )

            if self.controller and self.controller.connected:
                mount_addresses = self.controller.mount_addresses
                working_mounts = []

                for addr in mount_addresses:
                    device_info = self.controller.get_device_info(addr)
                    if device_info:
                        working_mounts.append(addr)
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status",
                                [f"Mount {addr}: {device_info[:50]}...", "log"],
                            )
                        )
                    else:
                        self.emit_status(
                            ThreadCommand(
                                "Update_Status",
                                [f"Mount {addr}: No response", "warning"],
                            )
                        )

                if working_mounts:
                    msg = f"Connection OK - {len(working_mounts)}/{len(mount_addresses)} mounts responding"
                    self.emit_status(ThreadCommand("Update_Status", [msg, "good"]))
                    self.update_status()
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            ["Connection established but no mounts responding", "bad"],
                        )
                    )
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Hardware not connected", "warning"]
                    )
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Connection test error: {str(e)}", "error"]
                )
            )

    def get_actuator_value(self):
        """
        Get current positions of all mounts as DataActuator object and update status parameters.

        This method is called periodically by PyMoDAQ's polling mechanism (when poll_time > 0),
        replacing the need for custom threading for status updates.
        """
        if not self.controller or not self.controller.connected:
            default_len = len(
                self.settings.child("connection_group", "mount_addresses")
                .value()
                .split(",")
            )
            return DataActuator(data=[np.array([0.0] * default_len)])

        try:
            # Get positions and update status parameters (PyMoDAQ polling pattern)
            positions = self.controller.get_all_positions()
            position_list = [
                positions.get(addr, 0.0) for addr in self.controller.mount_addresses
            ]

            # Update UI status parameters during polling
            try:
                for i, addr in enumerate(self.controller.mount_addresses):
                    param_name = f"mount_{addr}_pos"
                    status_param = self.settings.child("status_group", param_name)
                    if status_param:
                        status_param.setValue(position_list[i])
            except Exception:
                pass  # Don't fail main operation for UI updates

            return DataActuator(data=[np.array(position_list)])
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error reading positions: {str(e)}", "error"]
                )
            )
            fallback_len = (
                len(self.controller.mount_addresses) if self.controller else 3
            )
            return DataActuator(data=[np.array([0.0] * fallback_len)])

    def move_abs(self, positions: Union[List[float], DataActuator]):
        """
        Move to absolute positions.

        Parameters
        ----------
        positions : Union[List[float], DataActuator]
            Target positions for all axes.
        """
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", ["Hardware not connected. Cannot move.", "warning"]
                )
            )
            return

        try:
            if isinstance(positions, DataActuator):
                target_positions_list = positions.data[0].tolist()
            elif isinstance(positions, (list, tuple, np.ndarray)):
                target_positions_list = list(positions)
            else:
                # Handle single float value for multi-axis controller
                # Distribute to all axes or use current position for others
                current_positions = self.get_actuator_value()[0].tolist()
                target_positions_list = [float(positions)] + current_positions[1:]
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [f"Single value {positions} applied to first axis only", "log"],
                    )
                )

            # Ensure we have the right number of values for all mounts
            num_mounts = len(self.controller.mount_addresses)
            if len(target_positions_list) < num_mounts:
                # Pad with current positions
                current_positions = self.get_actuator_value()[0].tolist()
                target_positions_list.extend(
                    current_positions[len(target_positions_list) :]
                )

            for addr, position in zip(
                self.controller.mount_addresses, target_positions_list
            ):
                success = self.controller.move_absolute(addr, position)
                if success:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            [f"Mount {addr} moving to {position:.2f} degrees", "log"],
                        )
                    )
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", [f"Failed to move mount {addr}", "warning"]
                        )
                    )

            self.move_done()

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving: {str(e)}", "error"])
            )

    def move_rel(self, positions: Union[List[float], DataActuator]):
        """
        Move to relative positions.

        Parameters
        ----------
        positions : Union[List[float], DataActuator]
            Relative position changes for all axes.
        """
        try:
            if isinstance(positions, DataActuator):
                relative_moves_list = positions.data[0].tolist()
            elif isinstance(positions, (list, tuple, np.ndarray)):
                relative_moves_list = list(positions)
            else:
                # Handle single float value for multi-axis controller
                # Apply to first axis only, others get 0 movement
                relative_moves_list = [float(positions), 0.0, 0.0][
                    : len(self.controller.mount_addresses)
                ]
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [
                            f"Relative move {positions} applied to first axis only",
                            "log",
                        ],
                    )
                )

            current_array = self.get_actuator_value()[0]
            current_list = current_array.tolist()

            # Ensure we have the right number of relative moves
            num_mounts = len(self.controller.mount_addresses)
            if len(relative_moves_list) < num_mounts:
                relative_moves_list.extend(
                    [0.0] * (num_mounts - len(relative_moves_list))
                )

            target = [c + p for c, p in zip(current_list, relative_moves_list)]

            self.move_abs(target)
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error in relative move: {str(e)}", "error"]
                )
            )

    def stop_motion(self):
        """Stop motion (not implemented for Elliptec)."""
        self.emit_status(
            ThreadCommand("Update_Status", ["Stop command received", "log"])
        )

    def update_status(self):
        """Update status parameters from hardware and notify PyMoDAQ UI."""
        if not self.controller or not self.controller.connected:
            return

        try:
            positions = self.controller.get_all_positions()

            # Update individual mount position displays in parameter tree
            for addr in self.controller.mount_addresses:
                pos = positions.get(addr, 0.0)
                self.settings.child("status_group", f"mount_{addr}_pos").setValue(pos)

            # Update current position for PyMoDAQ framework with proper DataActuator format
            position_list = [
                positions.get(addr, 0.0) for addr in self.controller.mount_addresses
            ]

            plugin_name = getattr(self, "_title", self.__class__.__name__)
            self.current_position = DataActuator(
                name=plugin_name,
                data=[np.array(position_list)],
                units=self._controller_units,
            )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Status update error: {str(e)}", "error"]
                )
            )

    # Custom threading methods removed - PyMoDAQ polling handles status updates via get_actuator_value
