import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    comon_parameters_fun,
    main,
)
from pymodaq_utils.utils import ThreadCommand

# Import URASHG configuration
try:
    from pymodaq_plugins_urashg import get_config
    from pymodaq_plugins_urashg.utils.config import Config

    config = get_config()
    maitai_config = config.get_hardware_config("maitai")
except ImportError:
    maitai_config = {
        "serial_port": "/dev/ttyUSB2",
        "baudrate": 9600,
        "timeout": 2.0,
        "wavelength_range_min": 700.0,
        "wavelength_range_max": 1000.0,
    }


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ plugin for controlling MaiTai Ti:Sapphire laser.

    Provides wavelength control, power monitoring, and shutter operations
    for Spectra-Physics MaiTai femtosecond laser systems.
    """

    # Plugin identification
    _controller_units = "nm"  # Wavelength in nanometers
    _axis_names = ["Wavelength"]

    is_multiaxes = False
    _epsilon = 1.0  # 1nm resolution for wavelength

    params = comon_parameters_fun(
        is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilon
    ) + [
        # Position bounds for wavelength
        {
            "title": "Position Bounds:",
            "name": "bounds_group",
            "type": "group",
            "children": [
                {
                    "title": "Min Wavelength (nm):",
                    "name": "min_position",
                    "type": "float",
                    "value": 700.0,
                    "min": 700.0,
                    "max": 1000.0,
                    "tip": "Minimum tunable wavelength",
                },
                {
                    "title": "Max Wavelength (nm):",
                    "name": "max_position",
                    "type": "float",
                    "value": 1000.0,
                    "min": 700.0,
                    "max": 1000.0,
                    "tip": "Maximum tunable wavelength",
                },
            ],
        },
        {
            "title": "Connection Settings:",
            "name": "connection_group",
            "type": "group",
            "children": [
                {
                    "title": "Serial Port:",
                    "name": "serial_port",
                    "type": "str",
                    "value": maitai_config.get("serial_port", "/dev/ttyUSB2"),
                    "tip": "Serial port for MaiTai laser (e.g. /dev/ttyUSB2 or COM3)",
                },
                {
                    "title": "Baudrate:",
                    "name": "baudrate",
                    "type": "list",
                    "limits": [9600, 19200, 38400, 57600, 115200],
                    "value": maitai_config.get("baudrate", 9600),
                    "tip": "Serial communication baud rate for MaiTai laser",
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": maitai_config.get("timeout", 2.0),
                    "min": 0.1,
                    "max": 10.0,
                    "tip": "Communication timeout in seconds",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                    "tip": "Enable for testing without physical MaiTai laser",
                },
            ],
        },
        {
            "title": "Laser Settings:",
            "name": "laser_settings",
            "type": "group",
            "children": [
                {
                    "title": "Target Wavelength (nm):",
                    "name": "target_wavelength",
                    "type": "float",
                    "value": 800.0,
                    "min": 700.0,
                    "max": 1000.0,
                    "step": 1.0,
                    "tip": "Set target wavelength for laser",
                },
                {
                    "title": "Wavelength Range (nm):",
                    "name": "wavelength_range",
                    "type": "group",
                    "children": [
                        {
                            "title": "Min Wavelength (nm):",
                            "name": "min_wavelength",
                            "type": "float",
                            "value": maitai_config.get("wavelength_range_min", 700.0),
                            "min": 700.0,
                            "max": 1000.0,
                            "readonly": True,
                            "tip": "Minimum tunable wavelength for MaiTai laser",
                        },
                        {
                            "title": "Max Wavelength (nm):",
                            "name": "max_wavelength",
                            "type": "float",
                            "value": maitai_config.get("wavelength_range_max", 1000.0),
                            "min": 700.0,
                            "max": 1000.0,
                            "readonly": True,
                            "tip": "Maximum tunable wavelength for MaiTai laser",
                        },
                    ],
                },
                {
                    "title": "Power Limit (%):",
                    "name": "power_limit",
                    "type": "float",
                    "value": 50.0,
                    "min": 0.0,
                    "max": 100.0,
                },
            ],
        },
        {
            "title": "Shutter Control:",
            "name": "shutter_group",
            "type": "group",
            "children": [
                {
                    "title": "Shutter Status:",
                    "name": "shutter_status",
                    "type": "str",
                    "value": "Closed",
                    "readonly": True,
                    "tip": "Current shutter status",
                },
                {
                    "title": "Open Shutter:",
                    "name": "open_shutter",
                    "type": "action",
                    "tip": "Open the laser shutter",
                },
                {
                    "title": "Close Shutter:",
                    "name": "close_shutter",
                    "type": "action",
                    "tip": "Close the laser shutter",
                },
            ],
        },
    ]

    def ini_attributes(self):
        """Initialize attributes before __init__ - PyMoDAQ 5.x pattern"""
        self.controller = None

    def ini_stage(self, controller=None):
        """Initialize the MaiTai laser controller."""
        self.initialized = False
        try:
            self.emit_status(
                ThreadCommand("show_splash", "Initializing MaiTai Laser...")
            )

            # Get connection parameters
            port = self.settings.child("connection_group", "serial_port").value()
            baudrate = self.settings.child("connection_group", "baudrate").value()
            timeout = self.settings.child("connection_group", "timeout").value()
            mock_mode = self.settings.child("connection_group", "mock_mode").value()

            if mock_mode:
                # Mock controller for testing
                self.controller = MockMaiTaiController()
                info = "MaiTai Laser initialized in MOCK mode"
                self.emit_status(ThreadCommand("close_splash"))
                self.emit_status(ThreadCommand("Update_Status", [info]))
                self.initialized = True
                return info, True

            # Real hardware initialization
            try:
                from pymodaq_plugins_urashg.hardware.urashg.maitai_control import (
                    MaiTaiController,
                )

                self.controller = MaiTaiController(
                    port=port, baudrate=baudrate, timeout=timeout, mock_mode=False
                )

                if self.controller.connect():
                    info = f"MaiTai Laser connected on {port}"
                    self.emit_status(ThreadCommand("close_splash"))
                    self.emit_status(ThreadCommand("Update_Status", [info]))
                    self.initialized = True
                    return info, True
                else:
                    raise ConnectionError("Failed to connect to MaiTai hardware")

            except ImportError:
                # Fall back to mock if hardware module not available
                self.controller = MockMaiTaiController()
                info = "MaiTai hardware not available - using mock mode"
                self.emit_status(ThreadCommand("close_splash"))
                self.emit_status(ThreadCommand("Update_Status", [info]))
                self.initialized = True
                return info, True

        except Exception as e:
            error_msg = f"Error initializing MaiTai: {e}"
            self.emit_status(ThreadCommand("Update_Status", [error_msg]))
            self.emit_status(ThreadCommand("close_splash"))
            return error_msg, False

    def check_bound(self, wavelength):
        """Ensure wavelength is within valid range"""
        min_wl = self.settings.child("bounds_group", "min_position").value()
        max_wl = self.settings.child("bounds_group", "max_position").value()
        return max(min_wl, min(max_wl, wavelength))

    def get_actuator_value(self):
        """Get current wavelength position."""
        try:
            if self.controller and hasattr(self.controller, "get_wavelength"):
                wavelength = self.controller.get_wavelength()
                # PyMoDAQ expects raw numpy arrays - framework wraps in DataActuator
                return [np.array([wavelength])]
            # Default wavelength as raw numpy arrays
            return [np.array([800.0])]
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error reading position: {e}"])
            )
            # Return default wavelength as raw numpy arrays
            return [np.array([800.0])]

    def move_abs(self, position):
        """Move to absolute wavelength position."""
        try:
            if isinstance(position, DataActuator):
                target_wavelength = position.value()
            elif isinstance(position, (list, np.ndarray)):
                target_wavelength = position[0] if len(position) > 0 else 800.0
            else:
                target_wavelength = float(position)

            target_wavelength = self.check_bound(target_wavelength)

            if self.controller and hasattr(self.controller, "set_wavelength"):
                success = self.controller.set_wavelength(target_wavelength)
                if success:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status", [f"Moved to {target_wavelength} nm"]
                        )
                    )
                    self.move_done()  # Signal completion
                else:
                    self.emit_status(
                        ThreadCommand(
                            "Update_Status",
                            [f"Failed to move to {target_wavelength} nm"],
                        )
                    )
            else:
                # Mock successful move
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", [f"Mock moved to {target_wavelength} nm"]
                    )
                )
                self.move_done()  # Signal completion

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error moving: {e}"]))

    def move_rel(self, position):
        """Move relative wavelength position."""
        try:
            # Get current wavelength
            current_arrays = self.get_actuator_value()
            current_wavelength = (
                float(current_arrays[0][0])
                if len(current_arrays) > 0 and len(current_arrays[0]) > 0
                else 800.0
            )

            if isinstance(position, DataActuator):
                relative_wavelength = position.value()
            elif isinstance(position, (list, np.ndarray)):
                relative_wavelength = position[0] if len(position) > 0 else 0.0
            else:
                relative_wavelength = float(position)

            # Calculate target wavelength
            target_wavelength = current_wavelength + relative_wavelength
            self.move_abs(target_wavelength)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in relative move: {e}"])
            )

    def move_home(self):
        """Move to home wavelength position (800nm)."""
        try:
            home_wavelength = 800.0
            self.move_abs(home_wavelength)
            self.emit_status(
                ThreadCommand(
                    "Update_Status", [f"Moved to home position: {home_wavelength} nm"]
                )
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving home: {e}"])
            )

    def stop_motion(self):
        """Stop wavelength movement."""
        try:
            # For MaiTai laser, just signal completion since moves are typically fast
            self.emit_status(ThreadCommand("Update_Status", ["Motion stopped"]))
            self.move_done()
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error stopping motion: {e}"])
            )

    def close(self):
        """Close the laser controller."""
        try:
            if self.controller:
                if hasattr(self.controller, "close"):
                    self.controller.close()
                elif hasattr(self.controller, "disconnect"):
                    self.controller.disconnect()
                self.controller = None
            self.emit_status(
                ThreadCommand("Update_Status", ["MaiTai connection closed"])
            )
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error closing: {e}"]))

    def commit_settings(self, param):
        """Handle parameter changes and actions."""
        try:
            if param.name() == "open_shutter":
                self.open_shutter()
            elif param.name() == "close_shutter":
                self.close_shutter()
            elif param.name() == "target_wavelength":
                wavelength = param.value()
                self.move_abs(wavelength)
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in commit_settings: {e}"])
            )

    def open_shutter(self):
        """Open the laser shutter."""
        try:
            if self.controller and hasattr(self.controller, "open_shutter"):
                success = self.controller.open_shutter()
                if success:
                    self.settings.child("shutter_group", "shutter_status").setValue(
                        "Open"
                    )
                    self.emit_status(ThreadCommand("Update_Status", ["Shutter opened"]))
                else:
                    self.emit_status(
                        ThreadCommand("Update_Status", ["Failed to open shutter"])
                    )
            else:
                # Mock shutter operation
                self.settings.child("shutter_group", "shutter_status").setValue("Open")
                self.emit_status(
                    ThreadCommand("Update_Status", ["Mock shutter opened"])
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error opening shutter: {e}"])
            )

    def close_shutter(self):
        """Close the laser shutter."""
        try:
            if self.controller and hasattr(self.controller, "close_shutter"):
                success = self.controller.close_shutter()
                if success:
                    self.settings.child("shutter_group", "shutter_status").setValue(
                        "Closed"
                    )
                    self.emit_status(ThreadCommand("Update_Status", ["Shutter closed"]))
                else:
                    self.emit_status(
                        ThreadCommand("Update_Status", ["Failed to close shutter"])
                    )
            else:
                # Mock shutter operation
                self.settings.child("shutter_group", "shutter_status").setValue(
                    "Closed"
                )
                self.emit_status(
                    ThreadCommand("Update_Status", ["Mock shutter closed"])
                )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error closing shutter: {e}"])
            )


class MockMaiTaiController:
    """Mock controller for testing MaiTai laser plugin."""

    def __init__(self):
        self.wavelength = 800.0  # Default wavelength in nm
        self.shutter_open = False  # Shutter state

    def get_wavelength(self):
        """Get current wavelength."""
        return self.wavelength

    def set_wavelength(self, wavelength):
        """Set wavelength."""
        if 700 <= wavelength <= 1000:
            self.wavelength = wavelength
            return True
        return False

    def open_shutter(self):
        """Open the laser shutter."""
        self.shutter_open = True
        return True

    def close_shutter(self):
        """Close the laser shutter."""
        self.shutter_open = False
        return True

    def close(self):
        """Close connection."""
        pass

    def disconnect(self):
        """Disconnect from device."""
        pass


if __name__ == "__main__":
    main(__file__)
