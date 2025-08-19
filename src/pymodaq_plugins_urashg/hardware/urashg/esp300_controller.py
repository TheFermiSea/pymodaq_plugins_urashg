# -*- coding: utf-8 -*-
"""
Newport ESP300 motion controller.

Hardware-level communication layer for Newport ESP300 multi-axis motion controller.
Provides clean interface for PyMoDAQ plugin integration with URASHG system.

Based on PyMeasure ESP300 implementation with URASHG-specific adaptations.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import serial

logger = logging.getLogger(__name__)


@dataclass
class AxisConfig:
    """Configuration for an ESP300 axis."""

    number: int
    name: str
    units: str = "millimeter"
    enabled: bool = True
    left_limit: Optional[float] = None
    right_limit: Optional[float] = None


class ESP300AxisError(Exception):
    """Raised when a particular axis causes an error for the Newport ESP300."""

    MESSAGES = {
        "00": "MOTOR TYPE NOT DEFINED",
        "01": "PARAMETER OUT OF RANGE",
        "02": "AMPLIFIER FAULT DETECTED",
        "03": "FOLLOWING ERROR THRESHOLD EXCEEDED",
        "04": "POSITIVE HARDWARE LIMIT DETECTED",
        "05": "NEGATIVE HARDWARE LIMIT DETECTED",
        "06": "POSITIVE SOFTWARE LIMIT DETECTED",
        "07": "NEGATIVE SOFTWARE LIMIT DETECTED",
        "08": "MOTOR / STAGE NOT CONNECTED",
        "09": "FEEDBACK SIGNAL FAULT DETECTED",
        "10": "MAXIMUM VELOCITY EXCEEDED",
        "11": "MAXIMUM ACCELERATION EXCEEDED",
        "12": "Reserved for future use",
        "13": "MOTOR NOT ENABLED",
        "14": "Reserved for future use",
        "15": "MAXIMUM JERK EXCEEDED",
        "16": "MAXIMUM DAC OFFSET EXCEEDED",
        "17": "ESP CRITICAL SETTINGS ARE PROTECTED",
        "18": "ESP STAGE DEVICE ERROR",
        "19": "ESP STAGE DATA INVALID",
        "20": "HOMING ABORTED",
        "21": "MOTOR CURRENT NOT DEFINED",
        "22": "UNIDRIVE COMMUNICATIONS ERROR",
        "23": "UNIDRIVE NOT DETECTED",
        "24": "SPEED OUT OF RANGE",
        "25": "INVALID TRAJECTORY MASTER AXIS",
        "26": "PARAMETER CHARGE NOT ALLOWED",
        "27": "INVALID TRAJECTORY MODE FOR HOMING",
        "28": "INVALID ENCODER STEP RATIO",
        "29": "DIGITAL I/O INTERLOCK DETECTED",
        "30": "COMMAND NOT ALLOWED DURING HOMING",
        "31": "COMMAND NOT ALLOWED DUE TO GROUP",
        "32": "INVALID TRAJECTORY MODE FOR MOVING",
    }

    def __init__(self, code):
        self.axis = str(code)[0]
        self.error = str(code)[1:]
        self.message = self.MESSAGES.get(self.error, f"Unknown error {self.error}")

    def __str__(self):
        return f"Newport ESP300 axis {self.axis} error: {self.message}"


class ESP300GeneralError(Exception):
    """Raised when the Newport ESP300 has a general error."""

    MESSAGES = {
        "1": "PCI COMMUNICATION TIME-OUT",
        "4": "EMERGENCY STOP ACTIVATED",
        "6": "COMMAND DOES NOT EXIST",
        "7": "PARAMETER OUT OF RANGE",
        "8": "CABLE INTERLOCK ERROR",
        "9": "AXIS NUMBER OUT OF RANGE",
        "13": "GROUP NUMBER MISSING",
        "14": "GROUP NUMBER OUT OF RANGE",
        "15": "GROUP NUMBER NOT ASSIGNED",
        "16": "GROUP NUMBER ALREADY ASSIGNED",
        "17": "GROUP AXIS OUT OF RANGE",
        "18": "GROUP AXIS ALREADY ASSIGNED",
        "19": "GROUP AXIS DUPLICATED",
        "20": "DATA ACQUISITION IS BUSY",
        "21": "DATA ACQUISITION SETUP ERROR",
        "22": "DATA ACQUISITION NOT ENABLED",
        "23": "SERVO CYCLE TICK FAILURE",
        "25": "DOWNLOAD IN PROGRESS",
        "26": "STORED PROGRAM NOT STARTED",
        "27": "COMMAND NOT ALLOWED",
        "28": "STORED PROGRAM FLASH AREA FULL",
        "29": "GROUP PARAMETER MISSING",
        "30": "GROUP PARAMETER OUT OF RANGE",
        "31": "GROUP MAXIMUM VELOCITY EXCEEDED",
        "32": "GROUP MAXIMUM ACCELERATION EXCEEDED",
        "33": "GROUP MAXIMUM DECELERATION EXCEEDED",
        "34": "GROUP MOVE NOT ALLOWED DURING MOTION",
        "35": "PROGRAM NOT FOUND",
        "37": "AXIS NUMBER MISSING",
        "38": "COMMAND PARAMETER MISSING",
        "39": "PROGRAM LABEL NOT FOUND",
        "40": "LAST COMMAND CANNOT BE REPEATED",
        "41": "MAX NUMBER OF LABELS PER PROGRAM EXCEEDED",
    }

    def __init__(self, code):
        self.error = str(code)
        self.message = self.MESSAGES.get(self.error, f"Unknown error {self.error}")

    def __str__(self):
        return f"Newport ESP300 error: {self.message}"


class ESP300Axis:
    """Represents a single axis of the Newport ESP300 Motion Controller."""

    UNITS_MAP = {
        "encoder count": 0,
        "motor step": 1,
        "millimeter": 2,
        "micrometer": 3,
        "inches": 4,
        "milli-inches": 5,
        "micro-inches": 6,
        "degree": 7,
        "gradient": 8,
        "radian": 9,
        "milliradian": 10,
        "microradian": 11,
    }

    def __init__(
        self, axis_number: int, controller: "ESP300Controller", config: AxisConfig
    ):
        self.axis_number = axis_number
        self.controller = controller
        self.config = config
        self.prefix = str(axis_number)

    def _send_command(
        self, command: str, expect_response: bool = True
    ) -> Optional[str]:
        """Send axis-specific command."""
        full_command = self.prefix + command
        return self.controller._send_command(full_command, expect_response)

    def get_position(self) -> Optional[float]:
        """Get current axis position."""
        try:
            response = self._send_command("TP")
            if response:
                return float(response.strip())
            return None
        except (ValueError, TypeError):
            logger.error(
                f"Invalid position response for axis {self.axis_number}: {response}"
            )
            return None

    def move_absolute(self, position: float) -> bool:
        """Move axis to absolute position."""
        try:
            response = self._send_command(f"PA{position:.6f}", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error moving axis {self.axis_number} to {position}: {e}")
            return False

    def move_relative(self, distance: float) -> bool:
        """Move axis by relative distance."""
        try:
            response = self._send_command(f"PR{distance:.6f}", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error moving axis {self.axis_number} by {distance}: {e}")
            return False

    def is_motion_done(self) -> bool:
        """Check if axis motion is complete."""
        try:
            response = self._send_command("MD?")
            if response:
                return bool(int(response.strip()))
            return False
        except (ValueError, TypeError):
            logger.error(
                f"Invalid motion done response for axis {self.axis_number}: {response}"
            )
            return False

    def is_enabled(self) -> bool:
        """Check if axis motion is enabled."""
        try:
            response = self._send_command("MO?")
            if response:
                return bool(int(response.strip()))
            return False
        except (ValueError, TypeError):
            logger.error(
                f"Invalid enabled response for axis {self.axis_number}: {response}"
            )
            return False

    def enable(self) -> bool:
        """Enable axis motion."""
        try:
            response = self._send_command("MO", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error enabling axis {self.axis_number}: {e}")
            return False

    def disable(self) -> bool:
        """Disable axis motion."""
        try:
            response = self._send_command("MF", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error disabling axis {self.axis_number}: {e}")
            return False

    def home(self, home_type: int = 1) -> bool:
        """
        Home the axis.

        Args:
            home_type: Homing type (0-6)
                0: Find negative limit, move to positive edge
                1: Find negative limit, stay at negative edge
                2: Find positive limit, move to negative edge
                3: Find positive limit, stay at positive edge
                4: Find index mark
                5: Set current position as home
                6: Find positive limit, set current as home
        """
        try:
            if home_type not in range(7):
                logger.error(f"Invalid home type {home_type}, must be 0-6")
                return False

            response = self._send_command(f"OR{home_type}", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error homing axis {self.axis_number}: {e}")
            return False

    def stop(self) -> bool:
        """Stop axis motion immediately."""
        try:
            response = self._send_command("ST", expect_response=False)
            return response is not None
        except Exception as e:
            logger.error(f"Error stopping axis {self.axis_number}: {e}")
            return False

    def wait_for_stop(self, timeout: float = 30.0, poll_interval: float = 0.1) -> bool:
        """
        Wait for axis motion to complete.

        Args:
            timeout: Maximum wait time in seconds
            poll_interval: How often to check motion status

        Returns:
            True if motion completed, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_motion_done():
                return True
            time.sleep(poll_interval)

        logger.warning(
            f"Timeout waiting for axis {self.axis_number} motion to complete"
        )
        return False

    def set_units(self, units: str) -> bool:
        """Set axis units."""
        try:
            units_code = self.UNITS_MAP.get(units)
            if units_code is None:
                logger.error(f"Invalid units '{units}' for axis {self.axis_number}")
                return False

            response = self._send_command(f"SN{units_code}", expect_response=False)
            if response is not None:
                self.config.units = units
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting units for axis {self.axis_number}: {e}")
            return False

    def get_units(self) -> str:
        """Get axis units."""
        try:
            response = self._send_command("SN?")
            if response:
                units_code = int(response.strip())
                for units, code in self.UNITS_MAP.items():
                    if code == units_code:
                        return units
            return self.config.units
        except (ValueError, TypeError):
            logger.error(
                f"Invalid units response for axis {self.axis_number}: {response}"
            )
            return self.config.units

    def set_software_limits(self, left_limit: float, right_limit: float) -> bool:
        """Set software limits for the axis."""
        try:
            # Set left (negative) limit
            response1 = self._send_command(f"SL{left_limit:.6f}", expect_response=False)
            # Set right (positive) limit
            response2 = self._send_command(
                f"SR{right_limit:.6f}", expect_response=False
            )

            if response1 is not None and response2 is not None:
                self.config.left_limit = left_limit
                self.config.right_limit = right_limit
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting limits for axis {self.axis_number}: {e}")
            return False


class ESP300Controller:
    """
    Hardware controller for Newport ESP300 multi-axis motion controller.

    Provides high-level interface for URASHG system integration with
    comprehensive error handling and axis management.
    """

    def __init__(
        self,
        port: str = "",
        baudrate: int = 19200,
        timeout: float = 3.0,
        axes_config: Optional[List[AxisConfig]] = None,
    ):
        """
        Initialize ESP300 controller.

        Args:
            port: Serial port path
            baudrate: Communication baud rate (typically 19200)
            timeout: Serial timeout in seconds
            axes_config: List of axis configurations
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial: Optional[serial.Serial] = None
        self._connected = False

        # Default axes configuration (can be overridden)
        if axes_config is None:
            axes_config = [
                AxisConfig(1, "x", "millimeter"),
                AxisConfig(2, "y", "millimeter"),
                AxisConfig(3, "z", "millimeter"),
            ]

        self.axes_config = {cfg.number: cfg for cfg in axes_config}
        self.axes: Dict[int, ESP300Axis] = {}

        logger.info(
            f"ESP300 controller initialized for {port}, {len(axes_config)} axes"
        )

    def connect(self) -> bool:
        """Connect to ESP300 controller."""
        try:
            if self._connected:
                return True

            logger.info(f"Connecting to ESP300 on {self.port}...")

            # Open serial connection
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )

            # Test communication - clear any errors first
            time.sleep(0.5)  # Allow controller to settle

            # Try to get controller status
            response = self._send_command("TE?")  # Get error status
            if response is None:
                raise ConnectionError("No response from ESP300 controller")

            # Check for errors and clear them
            self.clear_errors()

            # Initialize axes
            for axis_num, config in self.axes_config.items():
                axis = ESP300Axis(axis_num, self, config)
                self.axes[axis_num] = axis
                logger.debug(f"Initialized axis {axis_num} ({config.name})")

            self._connected = True
            logger.info(f"ESP300 connected successfully with {len(self.axes)} axes")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to ESP300: {e}")
            self._cleanup_connection()
            return False

    def disconnect(self):
        """Disconnect from ESP300 controller."""
        try:
            # Disable all axes before disconnecting
            if self._connected:
                for axis in self.axes.values():
                    axis.disable()

            self._cleanup_connection()
            logger.info("ESP300 disconnected")
        except Exception as e:
            logger.error(f"Error during ESP300 disconnect: {e}")

    def _cleanup_connection(self):
        """Clean up serial connection."""
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            self._connected = False
            self.axes.clear()
        except Exception:
            pass

    def _send_command(
        self, command: str, expect_response: bool = True
    ) -> Optional[str]:
        """
        Send command to ESP300 and get response.

        Args:
            command: Command string to send
            expect_response: Whether to wait for and return response

        Returns:
            str or None: Response from device, or None on error
        """
        try:
            if not self._serial or not self._serial.is_open:
                logger.error("Serial connection not available")
                return None

            # Clear buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            # Send command (ESP300 uses CR+LF termination)
            cmd_bytes = (command + "\r\n").encode("ascii")
            self._serial.write(cmd_bytes)
            self._serial.flush()

            if expect_response:
                time.sleep(0.1)  # Give controller time to respond

                # Read response (ESP300 typically responds quickly)
                response_bytes = self._serial.readline()
                response = response_bytes.decode("ascii", errors="ignore").strip()

                # Check for error responses
                if response.startswith("ERROR"):
                    logger.error(f"ESP300 command error: {response}")
                    return None

                return response if response else None
            else:
                time.sleep(0.05)  # Brief delay for command processing
                return ""

        except Exception as e:
            logger.error(f"Communication error: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if ESP300 is connected."""
        return self._connected

    def get_error(self) -> int:
        """Get current error code."""
        try:
            response = self._send_command("TE?")
            if response:
                return int(response.strip())
            return 0
        except (ValueError, TypeError):
            logger.error(f"Invalid error response: {response}")
            return -1

    def clear_errors(self) -> List[str]:
        """Clear all error messages and return list of errors found."""
        errors = []
        try:
            error_code = self.get_error()
            while error_code != 0 and error_code != -1:
                if error_code > 100:
                    # Axis error
                    error = ESP300AxisError(error_code)
                    errors.append(str(error))
                else:
                    # General error
                    error = ESP300GeneralError(error_code)
                    errors.append(str(error))

                # Get next error
                error_code = self.get_error()

        except Exception as e:
            logger.error(f"Error clearing ESP300 errors: {e}")

        if errors:
            logger.warning(f"Cleared {len(errors)} ESP300 errors: {errors}")

        return errors

    def get_axis(self, axis_number: int) -> Optional[ESP300Axis]:
        """Get axis by number."""
        return self.axes.get(axis_number)

    def get_axis_by_name(self, name: str) -> Optional[ESP300Axis]:
        """Get axis by name."""
        for axis in self.axes.values():
            if axis.config.name == name:
                return axis
        return None

    def enable_all_axes(self) -> bool:
        """Enable all configured axes."""
        success = True
        for axis in self.axes.values():
            if not axis.enable():
                success = False
                logger.error(f"Failed to enable axis {axis.axis_number}")
        return success

    def disable_all_axes(self) -> bool:
        """Disable all configured axes."""
        success = True
        for axis in self.axes.values():
            if not axis.disable():
                success = False
                logger.error(f"Failed to disable axis {axis.axis_number}")
        return success

    def stop_all_axes(self) -> bool:
        """Stop motion on all axes immediately."""
        success = True
        for axis in self.axes.values():
            if not axis.stop():
                success = False
                logger.error(f"Failed to stop axis {axis.axis_number}")
        return success

    def get_all_positions(self) -> Dict[int, float]:
        """Get positions of all axes."""
        positions = {}
        for axis_num, axis in self.axes.items():
            pos = axis.get_position()
            if pos is not None:
                positions[axis_num] = pos
        return positions

    def move_multiple_axes(
        self, positions: Dict[int, float], wait: bool = True
    ) -> bool:
        """
        Move multiple axes simultaneously.

        Args:
            positions: Dict mapping axis number to target position
            wait: Whether to wait for all motions to complete

        Returns:
            True if all moves initiated successfully
        """
        # Start all moves
        success = True
        for axis_num, position in positions.items():
            axis = self.axes.get(axis_num)
            if axis:
                if not axis.move_absolute(position):
                    success = False
                    logger.error(f"Failed to start move for axis {axis_num}")
            else:
                success = False
                logger.error(f"Axis {axis_num} not found")

        # Wait for completion if requested
        if wait and success:
            for axis_num in positions.keys():
                axis = self.axes.get(axis_num)
                if axis and not axis.wait_for_stop():
                    success = False
                    logger.error(f"Timeout waiting for axis {axis_num}")

        return success

    def home_all_axes(self, home_type: int = 1, wait: bool = True) -> bool:
        """Home all configured axes."""
        success = True

        # Start homing on all axes
        for axis in self.axes.values():
            if not axis.home(home_type):
                success = False
                logger.error(f"Failed to start homing for axis {axis.axis_number}")

        # Wait for completion if requested
        if wait and success:
            for axis in self.axes.values():
                if not axis.wait_for_stop(timeout=60.0):  # Longer timeout for homing
                    success = False
                    logger.error(f"Timeout homing axis {axis.axis_number}")

        return success

    def get_device_info(self) -> Dict[str, Any]:
        """Get comprehensive device information."""
        info = {
            "model": "Newport ESP300",
            "port": self.port,
            "baudrate": self.baudrate,
            "connected": self._connected,
            "num_axes": len(self.axes),
            "axes": {},
        }

        if self._connected:
            # Get axis information
            for axis_num, axis in self.axes.items():
                axis_info = {
                    "name": axis.config.name,
                    "position": axis.get_position(),
                    "units": axis.get_units(),
                    "enabled": axis.is_enabled(),
                    "motion_done": axis.is_motion_done(),
                }
                info["axes"][axis_num] = axis_info

        return info

    # Note: __del__ method removed to prevent QThread destruction conflicts
    # Cleanup is handled explicitly via disconnect() in the plugin's close() method


if __name__ == "__main__":
    # Test the controller
    import logging

    logging.basicConfig(level=logging.DEBUG)

    print("Testing Testing Newport ESP300 Controller")
    print("=" * 45)

    # Configure for URASHG system axes
    axes_config = [
        AxisConfig(1, "x_stage", "millimeter"),
        AxisConfig(2, "y_stage", "millimeter"),
        AxisConfig(3, "focus", "micrometer"),
    ]

    controller = ESP300Controller(axes_config=axes_config)

    if controller.connect():
        print("[OK] Connected to ESP300")

        # Test basic operations
        print(f"INFO: Device Info: {controller.get_device_info()}")

        # Test axis access
        x_axis = controller.get_axis_by_name("x_stage")
        if x_axis:
            print(
                f"CONFIG: X-axis position: {x_axis.get_position()} {x_axis.get_units()}"
            )
            print(f"CONFIG: X-axis enabled: {x_axis.is_enabled()}")

        # Test multi-axis positions
        positions = controller.get_all_positions()
        print(f"DATA: All positions: {positions}")

        controller.disconnect()
        print("[OK] Disconnected")

    else:
        print("[ERROR] Failed to connect to ESP300")
        print("   - Check device is connected and powered")
        print("   - Verify correct serial port")
        print("   - Check baud rate (typically 19200)")
