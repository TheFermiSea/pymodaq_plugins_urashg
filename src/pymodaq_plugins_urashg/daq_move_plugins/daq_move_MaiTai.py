import time
from typing import Optional, Union
import numpy as np

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataActuator

# QTimer replaced with PyMoDAQ threading patterns


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ plugin for MaiTai laser wavelength control.

    Fully compliant with PyMoDAQ DAQ_Move_base standards:
    - Uses hardware controller for abstraction
    - Implements non-blocking operations
    - Proper error handling and status reporting
    - Thread-safe operations
    - Follows PyMoDAQ parameter management
    """

    # Plugin metadata - PyMoDAQ compliant
    _controller_units = "nm"
    is_multiaxes = False
    _axis_names = ["Wavelength"]
    _epsilon = 0.1  # Wavelength precision in nm

    # Plugin parameters - PyMoDAQ standard structure
    params = comon_parameters_fun(
        is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilon
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
                    "value": 115200,
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
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                },
            ],
        },
        # Wavelength limits (MaiTai only accepts INTEGER wavelengths)
        {
            "title": "Wavelength Range:",
            "name": "wavelength_group",
            "type": "group",
            "children": [
                {
                    "title": "Min Wavelength (nm):",
                    "name": "min_wavelength",
                    "type": "int",
                    "value": 700,
                    "readonly": True,
                },
                {
                    "title": "Max Wavelength (nm):",
                    "name": "max_wavelength",
                    "type": "int",
                    "value": 900,
                    "readonly": True,
                },
            ],
        },
        # Laser Control
        {
            "title": "Laser Control:",
            "name": "control_group",
            "type": "group",
            "children": [
                {
                    "title": "Target Wavelength (nm):",
                    "name": "target_wavelength",
                    "type": "int",
                    "value": 800,
                    "min": 690,
                    "max": 1040,
                    "suffix": "nm",
                },
                {
                    "title": "Home Wavelength (nm):",
                    "name": "home_wavelength",
                    "type": "int",
                    "value": 800,
                    "min": 690,
                    "max": 1040,
                    "suffix": "nm",
                    "tip": "Default wavelength for home position",
                },
                {
                    "title": "Tolerance (nm):",
                    "name": "tolerance",
                    "type": "float",
                    "value": 1.0,
                },
                {
                    "title": "Set Wavelength",
                    "name": "set_wavelength_btn",
                    "type": "action",
                },
                {
                    "title": "Open Shutter",
                    "name": "open_shutter_btn",
                    "type": "action",
                },
                {
                    "title": "Close Shutter",
                    "name": "close_shutter_btn",
                    "type": "action",
                },
                {
                    "title": "Go Home",
                    "name": "go_home_btn",
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
                    "title": "Current Wavelength (nm):",
                    "name": "current_wavelength",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                },
                {
                    "title": "Current Power (W):",
                    "name": "current_power",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                },
                {
                    "title": "Shutter Open:",
                    "name": "shutter_open",
                    "type": "bool",
                    "value": False,
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
        """Initialize MaiTai PyMoDAQ plugin."""
        super().__init__(parent, params_state)

        # Hardware controller
        self.controller = None

        # PyMoDAQ will handle periodic polling via built-in poll_time parameter

        # Initialization flag for enhanced status monitoring
        self._fully_initialized = False

    def ini_stage(self, controller=None):
        """Initialize the hardware stage."""
        try:
            # Import here to avoid issues if module not available
            from pymodaq_plugins_urashg.hardware.urashg.maitai_control import (
                MaiTaiController,
            )

            # Get connection parameters
            port = self.settings.child("connection_group", "serial_port").value()
            baudrate = self.settings.child("connection_group", "baudrate").value()
            timeout = self.settings.child("connection_group", "timeout").value()
            mock_mode = self.settings.child("connection_group", "mock_mode").value()

            # Create controller
            self.controller = MaiTaiController(
                port=port, baudrate=baudrate, timeout=timeout, mock_mode=mock_mode
            )

            # Connect to hardware
            if self.controller.connect():
                self.settings.child("status_group", "connection_status").setValue(
                    "Connected"
                )

                # Get initial status (simplified to avoid hanging)
                try:
                    wavelength = self.controller.get_wavelength()
                    if wavelength is not None:
                        self.settings.child(
                            "status_group", "current_wavelength"
                        ).setValue(wavelength)
                        self.current_position = wavelength
                except Exception:
                    pass  # Ignore errors during initialization

                # Status monitoring handled by PyMoDAQ polling (set poll_time in UI)

                # Enable enhanced status monitoring after initialization
                self._fully_initialized = True

                return "MaiTai laser initialized successfully", True
            else:
                return "Failed to connect to MaiTai laser", False

        except Exception as e:
            return f"Error initializing MaiTai: {str(e)}", False

    def close(self):
        """Close the hardware connection."""
        try:
            # Stop status monitoring
            # Status monitoring cleanup handled by PyMoDAQ

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

    def get_actuator_value(self):
        """
        Get current wavelength as DataActuator object and update all status parameters.

        This method is called periodically by PyMoDAQ's polling mechanism (when poll_time > 0),
        replacing the need for custom threading for status updates.
        """
        if not self.controller or not self.controller.connected:
            return DataActuator(data=[np.array([0.0])])

        try:
            # Get wavelength and update status parameters (PyMoDAQ polling pattern)
            wavelength = self.controller.get_wavelength()
            if wavelength is not None:
                self.current_position = wavelength
                # Update status parameter for UI display
                self.settings.child("status_group", "current_wavelength").setValue(
                    wavelength
                )

                # Update power status
                try:
                    power = self.controller.get_power()
                    if power is not None:
                        self.settings.child("status_group", "current_power").setValue(
                            power
                        )
                except Exception:
                    pass  # Don't fail main operation for power reading

                # Update shutter state (if fully initialized)
                if hasattr(self, "_fully_initialized") and self._fully_initialized:
                    try:
                        shutter_open, emission_possible = (
                            self.controller.get_enhanced_shutter_state()
                        )
                        self.settings.child("status_group", "shutter_open").setValue(
                            shutter_open
                        )
                    except Exception:
                        pass  # Don't fail main operation for shutter status

                return DataActuator(data=[np.array([wavelength])])
            else:
                fallback_position = (
                    self.current_position if hasattr(self, "current_position") else 0.0
                )
                return DataActuator(data=[np.array([fallback_position])])

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error reading wavelength: {str(e)}", "log"]
                )
            )
            fallback_position = (
                self.current_position if hasattr(self, "current_position") else 0.0
            )
            return DataActuator(data=[np.array([fallback_position])])

    def move_abs(self, position: Union[float, DataActuator]):
        """
        Move to absolute wavelength position.

        Parameters
        ----------
        position : Union[float, DataActuator]
            Target wavelength in nm. For DataActuator objects, use position.value()
            to extract the numerical value (PyMoDAQ 5.x single-axis pattern).
        """
        if not self.controller or not self.controller.connected:
            self.emit_status(
                ThreadCommand("Update_Status", ["Hardware not connected", "log"])
            )
            return

        try:
            # Extract numerical value from DataActuator using .value() method
            if isinstance(position, DataActuator):
                target_wavelength = float(position.value())
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [
                            f"DEBUG: DataActuator wavelength: {target_wavelength} nm",
                            "log",
                        ],
                    )
                )
            else:
                target_wavelength = float(position)

            # Validate wavelength range
            min_wl = self.settings.child("wavelength_group", "min_wavelength").value()
            max_wl = self.settings.child("wavelength_group", "max_wavelength").value()

            if not (min_wl <= target_wavelength <= max_wl):
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [
                            f"Wavelength {target_wavelength} nm outside range [{min_wl}, {max_wl}]",
                            "log",
                        ],
                    )
                )
                return

            # Set wavelength (MaiTai requires integer)
            success = self.controller.set_wavelength(int(round(target_wavelength)))

            if success:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [f"Moving to {int(round(target_wavelength))} nm", "log"],
                    )
                )

                # Update current position
                self.current_position = int(round(target_wavelength))

                # Emit move done signal with proper DataActuator
                plugin_name = getattr(self, "title", self.__class__.__name__)
                data_actuator = DataActuator(
                    name=plugin_name,
                    data=[np.array([int(round(target_wavelength))])],
                    units=self._controller_units,
                )
                self.move_done()  # Emit move_done signal
            else:
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        [f"Failed to set wavelength to {target_wavelength} nm", "log"],
                    )
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving: {str(e)}", "log"])
            )

    def move_rel(self, position: Union[float, DataActuator]):
        """
        Move to relative wavelength position.

        Parameters
        ----------
        position : Union[float, DataActuator]
            Relative wavelength change in nm. For DataActuator objects, use position.value()
            to extract the numerical value (PyMoDAQ 5.x single-axis pattern).
        """
        self.emit_status(
            ThreadCommand(
                "Update_Status",
                [f"DEBUG: move_rel called with {type(position)}", "log"],
            )
        )
        try:
            # Extract numerical value from DataActuator using .value() method
            if isinstance(position, DataActuator):
                relative_move = float(position.value())
            else:
                # Fallback for direct numerical input (backward compatibility)
                relative_move = float(position)

            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"DEBUG: Relative move of {relative_move} nm requested", "log"],
                )
            )

            current = self.get_actuator_value()
            target = current + relative_move

            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"DEBUG: Current: {current}, Target: {target}", "log"],
                )
            )

            # Create DataActuator for target position
            plugin_name = getattr(self, "title", self.__class__.__name__)
            target_data = DataActuator(
                name=plugin_name,
                data=[np.array([target])],
                units=self._controller_units,
            )
            self.move_abs(target_data)
        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Error in relative move: {str(e)}", "log"]
                )
            )

    def stop_motion(self):
        """Stop motion (not applicable for wavelength setting)."""
        self.emit_status(
            ThreadCommand("Update_Status", ["Stop command received", "log"])
        )

    def update_status(self):
        """Update status parameters from hardware and notify PyMoDAQ UI."""
        if not self.controller or not self.controller.connected:
            return

        try:
            # Update wavelength and notify main PyMoDAQ UI
            wavelength = self.controller.get_wavelength()
            if wavelength is not None:
                # Update status parameter for display
                self.settings.child("status_group", "current_wavelength").setValue(
                    wavelength
                )

                # Create DataActuator and emit to main PyMoDAQ UI
                plugin_name = getattr(self, "title", self.__class__.__name__)
                current_data = DataActuator(
                    name=plugin_name,
                    data=[np.array([wavelength])],
                    units=self._controller_units,
                )
                # Status update - no specific signal needed for GET_ACTUATOR_VALUE in PyMoDAQ 5.x

            # Update power
            power = self.controller.get_power()
            if power is not None:
                self.settings.child("status_group", "current_power").setValue(power)

            # Update shutter state only after full initialization
            if hasattr(self, "_fully_initialized") and self._fully_initialized:
                try:
                    # Full enhanced status monitoring only after initialization
                    shutter_open, emission_possible = (
                        self.controller.get_enhanced_shutter_state()
                    )
                    self.settings.child("status_group", "shutter_open").setValue(
                        shutter_open
                    )

                    # Get full status byte information periodically
                    if not hasattr(self, "_status_counter"):
                        self._status_counter = 0
                    self._status_counter += 1

                    if self._status_counter % 25 == 0:  # Even less frequent
                        status_byte, status_info = self.controller.get_status_byte()
                        if status_info.get("connected", False):
                            modelocked = status_info.get("modelocked", False)
                            self.emit_status(
                                ThreadCommand(
                                    "Update_Status",
                                    [
                                        f"Status: Emission={emission_possible}, Modelocked={modelocked}, Shutter={shutter_open}",
                                        "log",
                                    ],
                                )
                            )
                except Exception as e:
                    # Log enhanced status errors only occasionally
                    if hasattr(self, "_error_counter"):
                        self._error_counter = getattr(self, "_error_counter", 0) + 1
                        if self._error_counter % 10 == 0:  # Log every 10th error
                            self.emit_status(
                                ThreadCommand(
                                    "Update_Status",
                                    [f"Enhanced status error: {str(e)}", "log"],
                                )
                            )

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Status update error: {str(e)}", "log"]
                )
            )

    # Custom threading methods removed - PyMoDAQ polling handles status updates via get_actuator_value

    def commit_settings(self, param=None):
        """
        Commit settings changes to hardware.

        This method is called by PyMoDAQ when parameter values change.
        """
        try:
            if param is not None:
                if param.name() == "mock_mode":
                    # Reconnect if mock mode changed
                    if self.controller:
                        self.controller.disconnect()
                        self.controller = None
                        # Reinitialize with new settings
                        self.ini_stage()

                elif param.name() == "set_wavelength_btn":
                    # Set wavelength from target parameter
                    target = self.settings.child(
                        "control_group", "target_wavelength"
                    ).value()
                    self.move_abs(target)

                elif param.name() == "open_shutter_btn":
                    # Open shutter
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            ["DEBUG: Open shutter button clicked", "log"],
                        )
                    )
                    if self.controller and self.controller.connected:
                        if self.controller.open_shutter():
                            # Check for errors after shutter command (quick check)
                            has_errors, error_messages = (
                                self.controller.check_system_errors(quick_check=True)
                            )
                            if has_errors:
                                error_text = "; ".join(error_messages)
                                self.emit_status(
                                    ThreadCommand(
                                        "Update_Status",
                                        [
                                            f"Shutter command errors: {error_text}",
                                            "log",
                                        ],
                                    )
                                )
                            else:
                                # Verify shutter actually opened
                                time.sleep(0.5)  # Brief delay for shutter to respond
                                shutter_open, emission_possible = (
                                    self.controller.get_enhanced_shutter_state()
                                )
                                status_msg = f"Shutter open: {shutter_open}, Emission possible: {emission_possible}"
                                self.emit_status(
                                    ThreadCommand("Update_Status", [status_msg, "log"])
                                )
                        else:
                            self.emit_status(
                                ThreadCommand(
                                    "Update_Status",
                                    ["Failed to send open shutter command", "log"],
                                )
                            )

                elif param.name() == "close_shutter_btn":
                    # Close shutter
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            ["DEBUG: Close shutter button clicked", "log"],
                        )
                    )
                    if self.controller and self.controller.connected:
                        if self.controller.close_shutter():
                            # Check for errors after shutter command (quick check)
                            has_errors, error_messages = (
                                self.controller.check_system_errors(quick_check=True)
                            )
                            if has_errors:
                                error_text = "; ".join(error_messages)
                                self.emit_status(
                                    ThreadCommand(
                                        "Update_Status",
                                        [
                                            f"Shutter command errors: {error_text}",
                                            "log",
                                        ],
                                    )
                                )
                            else:
                                # Verify shutter actually closed
                                time.sleep(0.5)  # Brief delay for shutter to respond
                                shutter_open, emission_possible = (
                                    self.controller.get_enhanced_shutter_state()
                                )
                                status_msg = f"Shutter open: {shutter_open}, Emission possible: {emission_possible}"
                                self.emit_status(
                                    ThreadCommand("Update_Status", [status_msg, "log"])
                                )
                        else:
                            self.emit_status(
                                ThreadCommand(
                                    "Update_Status",
                                    ["Failed to send close shutter command", "log"],
                                )
                            )

                elif param.name() == "go_home_btn":
                    # Move to home wavelength
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", ["Moving to home wavelength...", "log"]
                        )
                    )
                    self.move_home()

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Settings commit error: {str(e)}", "log"]
                )
            )

    def move_home(self, value=None):
        """
        Move laser to home wavelength position.

        For MaiTai laser, home position is the default wavelength (800 nm).
        The value parameter is ignored but required for PyMoDAQ 5.x compliance.

        Parameters
        ----------
        value : Any, optional
            Ignored parameter, required for PyMoDAQ 5.x compatibility
        """
        try:
            home_wavelength = self.settings.child(
                "control_group", "home_wavelength"
            ).value()

            self.emit_status(
                ThreadCommand(
                    "Update_Status",
                    [f"Moving to home wavelength: {home_wavelength} nm", "log"],
                )
            )

            # Use move_abs to go to home position
            self.move_abs(home_wavelength)

            self.emit_status(
                ThreadCommand("Update_Status", ["Laser moved to home position", "log"])
            )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Home move error: {str(e)}", "log"])
            )

    def stop_motion(self):
        """Stop any ongoing wavelength movement."""
        try:
            if self.controller:
                # MaiTai doesn't have explicit stop command
                # Just report current status
                self.emit_status(
                    ThreadCommand(
                        "Update_Status",
                        ["Motion stop requested (MaiTai has no explicit stop)", "log"],
                    )
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Stop motion error: {str(e)}", "log"])
            )


if __name__ == "__main__":
    # This part is for testing the plugin independently
    import sys

    from pymodaq.dashboard import DashBoard
    from pymodaq.utils import daq_utils as utils
    from qtpy import QtWidgets

    app = utils.get_qapp()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    # It's good practice to have a mock version for development without hardware
    # For this example, we assume the hardware is connected.
    # To run, you would need a virtual COM port pair (e.g., com0com)
    # and a script simulating the MaiTai on the other end.

    win = QtWidgets.QMainWindow()
    area = utils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    prog = DashBoard(area)
    win.show()

    # To test, you would manually add the DAQ_Move module in the dashboard GUI
    # and select this DAQ_Move_MaiTai plugin.

    sys.exit(app.exec_())
