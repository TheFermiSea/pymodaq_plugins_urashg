"""
Refactored Newport 1830-C optical power meter controller.

This module provides a robust, asynchronous hardware abstraction layer for the
Newport 1830-C power meter, with a clean, decoupled mock implementation.
"""

import logging
import math
import random
import time
import asyncio
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from .exceptions import Newport1830CError

# Conditional import for real hardware
try:
    import serial
except ImportError:
    serial = None

logger = logging.getLogger(__name__)


def connection_required(func: Callable):
    """Decorator to ensure the controller is connected before executing a method."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._connected:
            raise Newport1830CError(f"{self.__class__.__name__} is not connected.")
        return func(self, *args, **kwargs)
    return wrapper


class Newport1830CController:
    """
    Hardware controller for Newport 1830-C optical power meter.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        if serial is None:
            raise ImportError("pyserial is not installed. Please install it to use the Newport1830C controller.")
            
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._current_wavelength = 800.0
        self._current_units = "W"
        logger.info(f"Newport1830C controller initialized for {port}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        """Connect to the Newport 1830-C power meter."""
        if self._connected:
            return
        try:
            logger.info(f"Connecting to Newport 1830-C on {self.port}...")
            self._serial = serial.Serial(
                port=self.port, baudrate=self.baudrate, bytesize=8,
                parity='N', stopbits=1, timeout=self.timeout
            )
            if self._send_command("W?") is None:
                raise ConnectionError("No response from Newport 1830-C")
            self._connected = True
            logger.info("Newport 1830-C connected successfully.")
            self._initialize_settings()
        except (serial.SerialException, OSError, ConnectionError) as e:
            self._cleanup_connection()
            raise Newport1830CError(f"Failed to connect: {e}")

    def disconnect(self):
        """Disconnect from the power meter."""
        self._cleanup_connection()
        logger.info("Newport 1830-C disconnected")

    def _cleanup_connection(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._connected = False

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Send a command to the power meter and get the response."""
        try:
            self._serial.write((command + "\n").encode("ascii"))
            self._serial.flush()
            if expect_response:
                time.sleep(0.1)
                response = self._serial.read_until(b'\r').decode("ascii", errors="ignore").strip()
                return response or None
            return ""
        except (serial.SerialException, OSError) as e:
            raise Newport1830CError(f"Communication error: {e}")

    async def _send_command_async(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Asynchronously send a command to the power meter."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._send_command, command, expect_response)

    def _initialize_settings(self):
        """Apply initial settings to the power meter."""
        self.set_wavelength(800.0)
        self.set_units("W")
        logger.info("Newport 1830-C initial settings applied")

    @connection_required
    def get_power(self) -> float:
        """Get the current power reading."""
        response = self._send_command("D?")
        if response:
            return float(response)
        raise Newport1830CError("Failed to get power reading.")

    @connection_required
    async def get_power_async(self) -> float:
        """Asynchronously get the current power reading."""
        response = await self._send_command_async("D?")
        if response:
            return float(response)
        raise Newport1830CError("Failed to get power reading.")

    @connection_required
    def set_wavelength(self, wavelength: float):
        """Set the measurement wavelength."""
        if not (400 <= wavelength <= 1100):
            raise ValueError("Wavelength out of range (400-1100 nm)")
        self._send_command(f"W{int(wavelength)}", expect_response=False)
        self._current_wavelength = wavelength

    @connection_required
    def set_units(self, units: str):
        """Set the power measurement units."""
        if units not in ["W", "dBm"]:
            raise ValueError("Invalid units. Must be 'W' or 'dBm'.")
        cmd = "U1" if units == "W" else "U3"
        self._send_command(cmd, expect_response=False)
        self._current_units = units


class MockNewport1830CController(Newport1830CController):
    """Mock controller for testing the Newport 1830-C plugin without hardware."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        # Override parent __init__ to avoid serial requirement
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._connected = False
        self._current_wavelength = 800.0
        self._current_units = "W"
        self._mock_power_base = 0.0035
        logger.info("Newport1830C controller initialized in mock mode.")

    def connect(self):
        if not self._connected:
            self._connected = True
            logger.info("Mock Newport 1830-C connected.")

    def disconnect(self):
        self._connected = False
        logger.info("Mock Newport 1830-C disconnected.")

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Simulate sending a command."""
        time.sleep(random.uniform(0.05, 0.1))
        command = command.strip().upper()
        logger.debug(f"Mock Newport 1830-C command received: '{command}'")

        if not expect_response:
            if command.startswith("W"):
                self._current_wavelength = float(command[1:])
            elif command.startswith("U"):
                self._current_units = "W" if command[1:] == "1" else "dBm"
            return ""

        if command == "D?":
            noise = self._mock_power_base * 0.01 * random.uniform(-1, 1)
            power = self._mock_power_base + noise
            if self._current_units == "dBm":
                return str(10 * math.log10(power / 0.001))
            return str(power)
        if command == "W?":
            return str(self._current_wavelength)
        if command == "U?":
            return "1" if self._current_units == "W" else "3"

        return "OK"
