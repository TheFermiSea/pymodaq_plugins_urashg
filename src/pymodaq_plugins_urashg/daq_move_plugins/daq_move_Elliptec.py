import time
from typing import List, Union
import numpy as np

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataActuator
from pymodaq.control_modules.thread_commands import ThreadStatusMove
from qtpy.QtCore import QTimer


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
                    "value": "/dev/ttyUSB0",
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
            ],
        },
        # Status monitoring
        {
            "title": "Status:",
            "name": "status_group",
            "type": "group",
            "children": [
                {
                    "title": "Mount 2 Position (deg):",
                    "name": "mount_2_pos",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                },
                {
                    "title": "Mount 3 Position (deg):",
                    "name": "mount_3_pos",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                },
                {
                    "title": "Mount 8 Position (deg):",
                    "name": "mount_8_pos",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                },
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

        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.setInterval(2000)  # Update every 2 seconds

    def ini_stage(self, controller=None):
        """Initialize the hardware stage."""
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

                # Get initial status
                self.update_status()

                # Start status monitoring
                self.status_timer.start()

                

                return "Elliptec mounts initialized successfully", True
            else:
                return "Failed to connect to Elliptec mounts", False

        except Exception as e:
            return f"Error initializing Elliptec: {str(e)}", False

    def close(self):
        """Close the hardware connection."""
        try:
            # Stop status monitoring
            if self.status_timer.isActive():
                self.status_timer.stop()

            # Disconnect hardware
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
        if param.name() == "home_all":
            self.home_all_mounts()

    def home_all_mounts(self):
        """Home all rotation mounts."""
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand("Update_Status", ["Hardware not connected", "log"])
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
                        "Update_Status", ["All mounts homed successfully", "log"]
                    )
                )
                self.update_status()
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Homing failed", "log"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error homing: {str(e)}", "log"])
            )

    def get_actuator_value(self):
        """Get current positions of all mounts."""
        if not self.controller or not self.controller.connected:
            return (
                [0.0] * len(self.controller.mount_addresses)
                if self.controller
                else [0.0, 0.0, 0.0]
            )

        try:
            positions = self.controller.get_all_positions()
            # Convert dict to list in correct order
            position_list = []
            for addr in self.controller.mount_addresses:
                position_list.append(positions.get(addr, 0.0))

            
            return position_list

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error reading positions: {str(e)}", "log"]
                )
            )
            return (
                self.current_position
                if hasattr(self, "current_position")
                else [0.0, 0.0, 0.0]
            )

    def move_abs(self, positions: Union[List[float], DataActuator]):
        """
        Move to absolute positions.
        
        Parameters
        ----------
        positions : Union[List[float], DataActuator]
            Target positions for all axes. For DataActuator objects in multi-axis mode, 
            use positions.data[0] to extract the numpy array (PyMoDAQ 5.x multi-axis pattern).
        """
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand("Update_Status", ["Hardware not connected", "log"])
            )
            return

        try:
            # Extract numerical values from DataActuator
            if isinstance(positions, DataActuator):
                # Multi-axis: positions.data[0] is numpy array with multiple values
                target_positions_array = positions.data[0]
                target_positions_list = target_positions_array.tolist() if hasattr(target_positions_array, 'tolist') else list(target_positions_array)
            else:
                # Fallback for direct numerical input (backward compatibility)
                target_positions_list = positions

            # Move each mount to its target position
            for i, (addr, position) in enumerate(
                zip(self.controller.mount_addresses, target_positions_list)
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
                            "Update_Status", [f"Failed to move mount {addr}", "log"]
                        )
                    )

            

            # Emit move done signal with proper DataActuator
            plugin_name = getattr(self, 'title', self.__class__.__name__)
            data_actuator = DataActuator(
                name=plugin_name,
                data=[np.array(target_positions_list)],
                units=self._controller_units
            )
            self.emit_status(ThreadCommand(ThreadStatusMove.MOVE_DONE, data_actuator))

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving: {str(e)}", "log"])
            )

    def move_rel(self, positions: Union[List[float], DataActuator]):
        """
        Move to relative positions.
        
        Parameters
        ----------
        positions : Union[List[float], DataActuator]
            Relative position changes for all axes. For DataActuator objects in multi-axis mode,
            use positions.data[0] to extract the numpy array (PyMoDAQ 5.x multi-axis pattern).
        """
        try:
            # Extract numerical values from DataActuator
            if isinstance(positions, DataActuator):
                # Multi-axis: positions.data[0] is numpy array with multiple values
                relative_moves_array = positions.data[0]
                relative_moves_list = relative_moves_array.tolist() if hasattr(relative_moves_array, 'tolist') else list(relative_moves_array)
            else:
                # Fallback for direct numerical input (backward compatibility)
                relative_moves_list = positions

            current = self.get_actuator_value()
            target = [c + p for c, p in zip(current, relative_moves_list)]
            
            # Create DataActuator for target positions
            plugin_name = getattr(self, 'title', self.__class__.__name__)
            target_data = DataActuator(
                name=plugin_name,
                data=[np.array(target)],
                units=self._controller_units
            )
            self.move_abs(target_data)
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in relative move: {str(e)}", "log"])
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
            # Update positions
            positions = self.controller.get_all_positions()

            # Update individual mount positions in UI parameters
            if "2" in positions:
                self.settings.child("status_group", "mount_2_pos").setValue(
                    positions["2"]
                )
            if "3" in positions:
                self.settings.child("status_group", "mount_3_pos").setValue(
                    positions["3"]
                )
            if "8" in positions:
                self.settings.child("status_group", "mount_8_pos").setValue(
                    positions["8"]
                )

            # Create position array in correct order and notify main PyMoDAQ UI
            position_list = []
            for addr in self.controller.mount_addresses:
                position_list.append(positions.get(addr, 0.0))
            
            # Create DataActuator and emit to main PyMoDAQ UI
            plugin_name = getattr(self, 'title', self.__class__.__name__)
            current_data = DataActuator(
                name=plugin_name,
                data=[np.array(position_list)],
                units=self._controller_units
            )
            self.emit_status(ThreadCommand(ThreadStatusMove.GET_ACTUATOR_VALUE, current_data))

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Status update error: {str(e)}", "log"]
                )
            )



