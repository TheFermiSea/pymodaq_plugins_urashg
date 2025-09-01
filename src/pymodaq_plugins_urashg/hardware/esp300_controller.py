# -*- coding: utf-8 -*-
"""
Refactored Newport ESP300 motion controller.

Hardware-level communication layer for Newport ESP300 multi-axis motion controller.
Provides a clean, asynchronous, and robust interface for PyMoDAQ plugin integration.
"""

import logging
import time
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

import serial

from .exceptions import ESP300Error

logger = logging.getLogger(__name__)


def connection_required(func: Callable):
    """Decorator to ensure the controller is connected before executing a method."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._connected:
            raise ESP300Error(f"{self.__class__.__name__} is not connected.")
        return func(self, *args, **kwargs)
    return wrapper


@dataclass
class AxisConfig:
    """Configuration for an ESP300 axis."""
    number: int
    name: str
    units: str = "millimeter"
    enabled: bool = True
    left_limit: Optional[float] = None
    right_limit: Optional[float] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None


class ESP300Axis:
    """Represents a single axis of the Newport ESP300 Motion Controller."""
    UNITS_MAP = {
        "encoder count": 0, "motor step": 1, "millimeter": 2, "micrometer": 3,
        "inches": 4, "milli-inches": 5, "micro-inches": 6, "degree": 7,
        "gradient": 8, "radian": 9, "milliradian": 10, "microradian": 11,
    }

    def __init__(self, axis_number: int, controller: "ESP300Controller", config: AxisConfig):
        self.axis_number = axis_number
        self.controller = controller
        self.config = config
        self.prefix = str(axis_number)

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Send axis-specific command."""
        full_command = self.prefix + command
        return self.controller._send_command(full_command, expect_response)

    async def _send_command_async(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Asynchronously send axis-specific command."""
        full_command = self.prefix + command
        return await self.controller._send_command_async(full_command, expect_response)

    @connection_required
    def get_position(self) -> float:
        """Get current axis position."""
        response = self._send_command("TP")
        if response:
            return float(response.strip())
        raise ESP300Error(f"Invalid position response for axis {self.axis_number}")

    @connection_required
    async def get_position_async(self) -> float:
        """Asynchronously get current axis position."""
        response = await self._send_command_async("TP")
        if response:
            return float(response.strip())
        raise ESP300Error(f"Invalid position response for axis {self.axis_number}")

    @connection_required
    def move_absolute(self, position: float):
        """Move axis to absolute position."""
        self._send_command(f"PA{position:.6f}", expect_response=False)

    @connection_required
    async def move_absolute_async(self, position: float):
        """Asynchronously move axis to absolute position."""
        await self._send_command_async(f"PA{position:.6f}", expect_response=False)

    @connection_required
    def is_motion_done(self) -> bool:
        """Check if axis motion is complete."""
        response = self._send_command("MD?")
        return bool(int(response.strip())) if response else False

    @connection_required
    async def wait_for_stop_async(self, timeout: float = 30.0, poll_interval: float = 0.1):
        """Asynchronously wait for motion to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.is_motion_done_async():
                return
            await asyncio.sleep(poll_interval)
        raise ESP300Error(f"Timeout waiting for axis {self.axis_number} to stop.")

    @connection_required
    async def is_motion_done_async(self) -> bool:
        """Asynchronously check if axis motion is complete."""
        response = await self._send_command_async("MD?")
        return bool(int(response.strip())) if response else False


class ESP300Controller:
    """Hardware controller for Newport ESP300 multi-axis motion controller."""
    _AXIS_ERROR_MESSAGES = {
        "00": "MOTOR TYPE NOT DEFINED", "01": "PARAMETER OUT OF RANGE",
        "02": "AMPLIFIER FAULT DETECTED", "03": "FOLLOWING ERROR THRESHOLD EXCEEDED",
        "04": "POSITIVE HARDWARE LIMIT DETECTED", "05": "NEGATIVE HARDWARE LIMIT DETECTED",
        "06": "POSITIVE SOFTWARE LIMIT DETECTED", "07": "NEGATIVE SOFTWARE LIMIT DETECTED",
    }
    _GENERAL_ERROR_MESSAGES = {
        "1": "PCI COMMUNICATION TIME-OUT", "4": "EMERGENCY STOP ACTIVATED",
        "6": "COMMAND DOES NOT EXIST", "7": "PARAMETER OUT OF RANGE",
    }

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 3.0, axes_config: List[AxisConfig] = None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self.axes_config = {cfg.number: cfg for cfg in axes_config} if axes_config else {}
        self.axes: Dict[int, ESP300Axis] = {}
        logger.info(f"ESP300 controller initialized for {port}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        """Connect to ESP300 controller."""
        if self._connected:
            return
        try:
            logger.info(f"Connecting to ESP300 on {self.port}...")
            self._serial = serial.Serial(
                port=self.port, baudrate=self.baudrate, bytesize=8,
                parity="N", stopbits=1, timeout=self.timeout
            )
            time.sleep(0.5)
            if self._send_command("TE?") is None:
                raise ConnectionError("No response from ESP300 controller")
            self.clear_errors()
            for axis_num, config in self.axes_config.items():
                self.axes[axis_num] = ESP300Axis(axis_num, self, config)
            self._connected = True
            logger.info("ESP300 connected successfully.")
        except Exception as e:
            self._cleanup_connection()
            raise ESP300Error(f"Failed to connect: {e}")

    def disconnect(self):
        """Disconnect from ESP300 controller."""
        if self._connected:
            for axis in self.axes.values():
                try:
                    axis.disable()
                except ESP300Error:
                    pass
        self._cleanup_connection()
        logger.info("ESP300 disconnected")

    def _cleanup_connection(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._connected = False
        self.axes.clear()

    @staticmethod
    def _get_error_message(code: int) -> str:
        """Translate error code to message."""
        code_str = str(code)
        if code > 100:
            axis, error_code = code_str[0], code_str[1:]
            msg = ESP300Controller._AXIS_ERROR_MESSAGES.get(error_code, f"Unknown error {error_code}")
            return f"Axis {axis} Error: {msg}"
        else:
            msg = ESP300Controller._GENERAL_ERROR_MESSAGES.get(code_str, f"Unknown error {code_str}")
            return f"General Error: {msg}"

    @connection_required
    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Send command to ESP300 and get response."""
        try:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self._serial.write((command + "\r\n").encode("ascii"))
            self._serial.flush()

            if expect_response:
                time.sleep(0.1)
                response = self._serial.readline().decode("ascii", errors="ignore").strip()
                if response.startswith("ERROR"):
                    raise ESP300Error(f"Command '{command}' failed: {response}")
                return response or None
            time.sleep(0.05)
            return ""
        except (serial.SerialException, OSError) as e:
            raise ESP300Error(f"Communication error: {e}")

    @connection_required
    async def _send_command_async(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Asynchronously send command to ESP300 and get response."""
        # This is a simplified async version. For true async serial, a library like `pyserial-asyncio` is needed.
        # Here, we yield control to the event loop during sleeps.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._send_command, command, expect_response)

    @connection_required
    def clear_errors(self):
        """Clear all error messages."""
        while True:
            error_code = int(self._send_command("TE?").strip())
            if error_code == 0:
                break
            logger.warning(f"Clearing ESP300 error: {self._get_error_message(error_code)}")

    @connection_required
    async def move_multiple_axes_async(self, positions: Dict[int, float]):
        """Asynchronously move multiple axes and wait for completion."""
        move_tasks = []
        for axis_num, position in positions.items():
            axis = self.axes.get(axis_num)
            if axis:
                move_tasks.append(axis.move_absolute_async(position))
            else:
                logger.error(f"Axis {axis_num} not found for multi-axis move.")
        await asyncio.gather(*move_tasks)

        wait_tasks = [axis.wait_for_stop_async() for axis_num in positions if (axis := self.axes.get(axis_num))]
        await asyncio.gather(*wait_tasks)


class MockESP300Controller(ESP300Controller):
    """Mock controller for testing ESP300 plugin without hardware."""

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 3.0, axes_config: List[AxisConfig] = None):
        super().__init__(port, baudrate, timeout, axes_config)
        self._mock_positions = {cfg.number: 0.0 for cfg in axes_config} if axes_config else {}

    def connect(self):
        if self._connected:
            return
        logger.info(f"Mock ESP300 connected on {self.port}")
        for axis_num, config in self.axes_config.items():
            self.axes[axis_num] = MockESP300Axis(axis_num, self, config)
        self._connected = True

    def disconnect(self):
        self._connected = False
        self.axes.clear()
        logger.info("Mock ESP300 disconnected.")

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Simulate sending a command."""
        logger.debug(f"Mock command received: {command}")
        if not expect_response:
            # Simulate movement for PA commands
            if "PA" in command:
                axis_num = int(command[0])
                position = float(command[2:])
                self._mock_positions[axis_num] = position
            return ""

        if "TP" in command:
            axis_num = int(command[0])
            return str(self._mock_positions.get(axis_num, 0.0))
        if "MD?" in command:
            return "1"  # Always done for simplicity
        if "TE?" in command:
            return "0" # No errors

        return "OK"


class MockESP300Axis(ESP300Axis):
    """Mock axis for testing."""
    def get_position(self) -> float:
        return self.controller._mock_positions.get(self.axis_number, 0.0)

    def move_absolute(self, position: float):
        self.controller._mock_positions[self.axis_number] = position
        logger.info(f"Mock Axis {self.axis_number} moving to {position}")

    async def wait_for_stop_async(self, timeout: float = 30.0, poll_interval: float = 0.1):
        await asyncio.sleep(0.2) # Simulate move time
        logger.info(f"Mock Axis {self.axis_number} move complete.")

    def is_motion_done(self) -> bool:
        return True
