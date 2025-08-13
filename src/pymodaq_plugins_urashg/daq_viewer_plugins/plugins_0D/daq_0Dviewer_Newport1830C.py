# -*- coding: utf-8 -*-
"""
PyMoDAQ plugin for Newport 1830-C optical power meter.

Updated for PyMoDAQ 5.0+ with DataWithAxes format.
Provides power measurement capability for URASHG calibration.
"""

from typing import Optional

import numpy as np
from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base,
    comon_parameters,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, DataToExport

from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import (
    Newport1830CController,
)


class DAQ_0DViewer_Newport1830C(DAQ_Viewer_base):
    """
    PyMoDAQ 5.0+ plugin for Newport 1830-C optical power meter.

    Provides 0D power measurements for URASHG calibration procedures.
    Uses hardware controller layer for robust serial communication.
    """

    # Plugin metadata
    params = comon_parameters + [
        # Settings group with multiaxes (required by PyMoDAQ)
        {
            "title": "Settings",
            "name": "Settings",
            "type": "group",
            "children": [
                {
                    "title": "Multi-axes",
                    "name": "multiaxes",
                    "type": "group",
                    "children": [
                        {
                            "title": "Is Multi-axes:",
                            "name": "is_multiaxes",
                            "type": "bool",
                            "value": False,
                            "readonly": True,
                        },
                        {
                            "title": "Status:",
                            "name": "multi_status",
                            "type": "list",
                            "value": "Single",
                            "values": ["Single"],
                            "readonly": True,
                        },
                    ],
                },
            ],
        },
        # Connection settings
        {
            "title": "Connection:",
            "name": "connect_settings",
            "type": "group",
            "children": [
                {
                    "title": "Serial Port:",
                    "name": "com_port",
                    "type": "str",
                    "value": "/dev/ttyS0",
                },
                {
                    "title": "Baudrate:",
                    "name": "baud_rate",
                    "type": "int",
                    "value": 9600,
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": 2.0,
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": True,
                },
            ],
        },
        # Measurement settings
        {
            "title": "Measurement:",
            "name": "measurement_group",
            "type": "group",
            "children": [
                {
                    "title": "Wavelength (nm):",
                    "name": "wavelength",
                    "type": "float",
                    "value": 780.0,
                    "min": 400.0,
                    "max": 1100.0,
                    "suffix": "nm",
                },
                {
                    "title": "Units:",
                    "name": "units",
                    "type": "list",
                    "values": ["W", "dBm"],
                    "value": "W",
                },
                {
                    "title": "Power Range:",
                    "name": "power_range",
                    "type": "list",
                    "values": [
                        "Auto",
                        "Range 1",
                        "Range 2",
                        "Range 3",
                        "Range 4",
                        "Range 5",
                        "Range 6",
                        "Range 7",
                    ],
                    "value": "Auto",
                },
                {
                    "title": "Filter Speed:",
                    "name": "filter_speed",
                    "type": "list",
                    "values": ["Slow", "Medium", "Fast"],
                    "value": "Medium",
                },
                {
                    "title": "Averaging:",
                    "name": "averaging",
                    "type": "int",
                    "value": 3,
                    "min": 1,
                    "max": 20,
                },
            ],
        },
        # Calibration actions
        {
            "title": "Calibration:",
            "name": "calibration_group",
            "type": "group",
            "children": [
                {"title": "Zero Adjust:", "name": "zero_adjust", "type": "action"},
            ],
        },
        # Status display
        {
            "title": "Status:",
            "name": "status_group",
            "type": "group",
            "children": [
                {
                    "title": "Current Power:",
                    "name": "current_power",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                    "suffix": "W",
                },
                {
                    "title": "Device Status:",
                    "name": "device_status",
                    "type": "str",
                    "value": "Disconnected",
                    "readonly": True,
                },
            ],
        },
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        # Hardware controller
        self.controller: Optional[Newport1830CController] = None

        # Data configuration
        self.x_axis = None
        self.ind_data = 0

    def ini_detector(self, controller=None):
        """Initialize the Newport 1830-C power meter."""
        try:
            self.emit_status(
                ThreadCommand("show_splash", "Initializing Newport 1830-C...")
            )

            # Check if mock mode is enabled
            mock_mode = self.settings.child("connect_settings", "mock_mode").value()

            if mock_mode:
                # Initialize mock controller
                self.controller = self._create_mock_controller()
                self.emit_status(ThreadCommand("close_splash"))
                return self.get_status(etat="Mock Newport 1830-C initialized")

            # Get connection parameters
            port = self.settings.child("connect_settings", "com_port").value()
            baud_rate = self.settings.child("connect_settings", "baud_rate").value()
            timeout = self.settings.child("connect_settings", "timeout").value()

            # Create controller
            self.controller = Newport1830CController(
                port=port, baud_rate=baud_rate, timeout=timeout
            )

            # Connect to device
            if not self.controller.connect():
                raise ConnectionError(f"Failed to connect to Newport 1830-C on {port}")

            # Apply measurement settings
            self._apply_measurement_settings()

            # Set up data structure - removed DataWithAxes as it's handled in grab_data
            current_units = self.settings.child("measurement_group", "units").value()

            # Update status
            self.settings.child("status_group", "device_status").setValue("Connected")

            self.emit_status(ThreadCommand("close_splash"))

            info_string = f"Newport 1830-C initialized on {port}"
            self.emit_status(ThreadCommand("Update_Status", [info_string]))

            return info_string, True

        except Exception as e:
            error_msg = f"Error initializing Newport 1830-C: {e}"
            self.emit_status(ThreadCommand("Update_Status", [error_msg]))
            self.emit_status(ThreadCommand("close_splash"))
            if self.controller:
                self.controller.disconnect()
                self.controller = None
            return error_msg, False

    def _create_mock_controller(self):
        """Create a mock controller for testing purposes."""

        class MockNewport1830C:
            def __init__(self):
                self.connected = True
                self.power = 0.0001  # 0.1 mW default

            def connect(self, port, baud_rate, timeout):
                self.connected = True
                return True

            def disconnect(self):
                self.connected = False

            def read_power(self):
                import random

                # Return mock power reading with some noise
                return self.power * (1 + 0.1 * (random.random() - 0.5))

            def set_wavelength(self, wavelength):
                pass

            def set_units(self, units):
                pass

            def set_range(self, range_setting):
                pass

            def get_status(self):
                return "Ready"

        return MockNewport1830C()

    def _apply_measurement_settings(self):
        """Apply current measurement settings to the power meter."""
        try:
            if not self.controller or not self.controller.is_connected():
                return

            # Set wavelength
            wavelength = self.settings.child("measurement_group", "wavelength").value()
            self.controller.set_wavelength(wavelength)

            # Set units
            units = self.settings.child("measurement_group", "units").value()
            self.controller.set_units(units)

            # Set power range
            power_range = self.settings.child(
                "measurement_group", "power_range"
            ).value()
            self.controller.set_power_range(power_range)

            # Set filter speed
            filter_speed = self.settings.child(
                "measurement_group", "filter_speed"
            ).value()
            self.controller.set_filter_speed(filter_speed)

            # Update data units
            if hasattr(self, "x_axis") and self.x_axis:
                self.x_axis.units = units

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error applying settings: {e}"])
            )

    def close(self):
        """Close connection to power meter."""
        try:
            if self.controller:
                self.controller.disconnect()
                self.controller = None
            self.settings.child("status_group", "device_status").setValue(
                "Disconnected"
            )
            self.emit_status(
                ThreadCommand("Update_Status", ["Newport 1830-C connection closed"])
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error closing connection: {e}"])
            )

    def grab_data(self, Naverage=1, **kwargs):
        """Acquire power measurement data."""
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("Power meter not connected")

            # Get averaging setting
            averaging = self.settings.child("measurement_group", "averaging").value()
            total_readings = max(Naverage, averaging)

            # Take multiple readings
            readings = self.controller.get_multiple_readings(total_readings)

            if not readings:
                # Return zero if no valid readings
                power_value = 0.0
                self.emit_status(
                    ThreadCommand("Update_Status", ["No valid power readings"])
                )
            else:
                # Calculate average
                power_value = sum(readings) / len(readings)

                # Update status display
                self.settings.child("status_group", "current_power").setValue(
                    power_value
                )

            # Create data array
            power_data = np.array([power_value])

            # Get current units for labeling
            units = self.settings.child("measurement_group", "units").value()

            # Create DataFromPlugins object for 0D data
            data_from_plugins = DataFromPlugins(
                name="Newport1830C_Power",
                data=[power_data],
                dim="Data0D",
                labels=["Power"],
            )

            # Emit data using correct PyMoDAQ format
            self.dte_signal.emit(
                DataToExport("Newport1830C_data", data=[data_from_plugins])
            )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error during measurement: {e}"])
            )
            # Emit zero data on error
            zero_data = DataFromPlugins(
                name="Newport1830C_Power",
                data=[np.array([0.0])],
                dim="Data0D",
                labels=["Power"],
            )
            self.dte_signal.emit(DataToExport("Newport1830C_data", data=[zero_data]))

    def commit_settings(self, param):
        """Handle parameter changes."""
        try:
            param_name = param.name()

            if param_name in ["wavelength", "units", "power_range", "filter_speed"]:
                self._apply_measurement_settings()
                self.emit_status(
                    ThreadCommand("Update_Status", [f"Updated {param_name}"])
                )

            elif param_name == "zero_adjust":
                self._perform_zero_adjust()

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error updating settings: {e}"])
            )

    def _perform_zero_adjust(self):
        """Perform zero adjustment on the power meter."""
        try:
            if not self.controller or not self.controller.is_connected():
                self.emit_status(
                    ThreadCommand("Update_Status", ["Power meter not connected"])
                )
                return

            self.emit_status(
                ThreadCommand("Update_Status", ["Performing zero adjustment..."])
            )

            if self.controller.zero_adjust():
                self.emit_status(
                    ThreadCommand(
                        "Update_Status", ["Zero adjustment completed successfully"]
                    )
                )
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", ["Zero adjustment failed"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error during zero adjustment: {e}"])
            )

    def stop(self):
        """Stop any ongoing operations."""
        # Newport 1830-C doesn't require explicit stop for measurements
        pass

    def get_power_reading(self) -> float:
        """
        Get single power reading for external use.

        Returns:
            float: Current power reading, or 0.0 on error
        """
        try:
            if self.controller and self.controller.is_connected():
                power = self.controller.get_power()
                return power if power is not None else 0.0
            return 0.0
        except Exception:
            return 0.0

    def calibrate_for_wavelength(self, wavelength: float) -> bool:
        """
        Set power meter for specific wavelength calibration.

        Args:
            wavelength: Wavelength in nanometers

        Returns:
            bool: True if successful
        """
        try:
            if not self.controller or not self.controller.is_connected():
                return False

            # Update wavelength setting
            self.settings.child("measurement_group", "wavelength").setValue(wavelength)
            return self.controller.set_wavelength(wavelength)

        except Exception:
            return False
