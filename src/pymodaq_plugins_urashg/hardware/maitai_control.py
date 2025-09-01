"""
Refactored MaiTai Laser Controller with Improved Asynchronous and Mocking Capabilities.

This module provides a robust hardware abstraction for the Spectra-Physics MaiTai
Titanium Sapphire laser, featuring asynchronous operations and a clean, decoupled
mock implementation for reliable testing.
"""

import logging
import random
import time
import asyncio
from threading import Lock
from typing import List, Tuple, Callable, Optional
from functools import wraps

from .exceptions import MaiTaiError

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
            raise MaiTaiError(f"{self.__class__.__name__} is not connected.")
        return func(self, *args, **kwargs)
    return wrapper


class MaiTaiController:
    """
    Hardware controller for Spectra-Physics MaiTai Titanium Sapphire Laser.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        if serial is None:
            raise ImportError("pyserial is not installed. Please install it to use the MaiTai controller.")
        
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial_connection: Optional[serial.Serial] = None
        self._connected = False
        self._lock = Lock()
        logger.info(f"MaiTai controller initialized for {port} at {baudrate} baud")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        """Connect to the MaiTai laser."""
        with self._lock:
            if self._connected:
                return
            try:
                self._serial_connection = serial.Serial(
                    port=self.port, baudrate=self.baudrate, bytesize=8,
                    parity='N', stopbits=1, timeout=self.timeout, xonxoff=True
                )
                if not self._test_communication():
                    self._cleanup_connection()
                    raise MaiTaiError("MaiTai communication test failed.")
                self._connected = True
                logger.info(f"MaiTai connected on {self.port}")
            except (serial.SerialException, OSError, MaiTaiError) as e:
                self._cleanup_connection()
                raise MaiTaiError(f"Failed to connect to MaiTai: {e}")

    def disconnect(self):
        """Disconnect from the MaiTai laser."""
        with self._lock:
            self._cleanup_connection()
            self._connected = False
            logger.info("MaiTai disconnected")

    def _cleanup_connection(self):
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
        self._serial_connection = None

    def _test_communication(self) -> bool:
        """Test communication with the laser using a single reliable command."""
        try:
            response = self._send_command("*IDN?")
            return response is not None and "Coherent" in response
        except MaiTaiError:
            return False

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Send a command to the MaiTai laser and get the response."""
        if not self._serial_connection or not self._serial_connection.is_open:
            raise MaiTaiError("Serial connection not available.")
        
        try:
            self._serial_connection.reset_input_buffer()
            self._serial_connection.reset_output_buffer()
            self._serial_connection.write((command + "\r\n").encode("ascii"))
            self._serial_connection.flush()

            if expect_response:
                time.sleep(0.1)
                response = self._serial_connection.readline().decode("ascii", errors="ignore").strip()
                logger.debug(f"Received response for '{command}': '{response}'")
                return response
            return ""
        except (serial.SerialException, OSError) as e:
            raise MaiTaiError(f"Communication error with command '{command}': {e}")

    async def _send_command_async(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Asynchronously send a command to the MaiTai laser."""
        loop = asyncio.get_running_loop()
        with self._lock:
            return await loop.run_in_executor(None, self._send_command, command, expect_response)

    @connection_required
    def get_wavelength(self) -> float:
        """Get the current wavelength in nm."""
        response = self._send_command("WAVELENGTH?")
        if response:
            return float(response.replace("nm", "").strip())
        raise MaiTaiError("Failed to get wavelength.")

    @connection_required
    async def get_wavelength_async(self) -> float:
        """Asynchronously get the current wavelength in nm."""
        response = await self._send_command_async("WAVELENGTH?")
        if response:
            return float(response.replace("nm", "").strip())
        raise MaiTaiError("Failed to get wavelength.")

    @connection_required
    def set_wavelength(self, wavelength: float):
        """Set the laser wavelength in nm."""
        command = f"WAVELENGTH {round(wavelength, 1)}"
        self._send_command(command, expect_response=False)
        logger.info(f"Wavelength set to {wavelength} nm.")

    @connection_required
    async def set_wavelength_async(self, wavelength: float):
        """Asynchronously set the laser wavelength in nm."""
        command = f"WAVELENGTH {round(wavelength, 1)}"
        await self._send_command_async(command, expect_response=False)
        logger.info(f"Wavelength set to {wavelength} nm.")

    @connection_required
    def set_shutter(self, open_shutter: bool):
        """Set the shutter state."""
        command = "SHUTTER 1" if open_shutter else "SHUTTER 0"
        self._send_command(command, expect_response=False)
        logger.info(f"Shutter {'opened' if open_shutter else 'closed'}.")

    @connection_required
    async def set_shutter_async(self, open_shutter: bool):
        """Asynchronously set the shutter state."""
        command = "SHUTTER 1" if open_shutter else "SHUTTER 0"
        await self._send_command_async(command, expect_response=False)
        logger.info(f"Shutter {'opened' if open_shutter else 'closed'}.")


class MockMaiTaiController(MaiTaiController):
    """Mock controller for testing the MaiTai laser plugin without hardware."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        # Override parent __init__ to avoid serial requirement
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._connected = False
        self._lock = Lock()
        self._mock_wavelength = 780.0
        self._mock_power = 2.5
        self._mock_shutter = False
        logger.info("MaiTai controller initialized in mock mode.")

    def connect(self):
        with self._lock:
            if not self._connected:
                self._connected = True
                logger.info("Mock MaiTai connected.")

    def disconnect(self):
        with self._lock:
            self._connected = False
            logger.info("Mock MaiTai disconnected.")

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """Simulate sending a command with realistic behavior."""
        time.sleep(random.uniform(0.05, 0.1))
        command = command.strip().upper()
        logger.debug(f"Mock MaiTai command received: '{command}'")

        if not expect_response:
            if command.startswith("WAVELENGTH"):
                wl = float(command.split()[1])
                if 690 <= wl <= 1040:
                    self._mock_wavelength = wl
            elif command.startswith("SHUTTER"):
                state = command.split()[1]
                self._mock_shutter = state in ["1", "OPEN", "ON"]
            return ""

        if "WAVELENGTH?" in command:
            return f"{self._mock_wavelength:.2f}"
        if "POWER?" in command:
            return f"{self._mock_power if self._mock_shutter else 0.0:.3f}W"
        if "SHUTTER?" in command:
            return "1" if self._mock_shutter else "0"
        if "*IDN?" in command:
            return "Coherent,MockMaiTai,SN_MOCK,v1.0"
        
        return "ERROR: Mock command not recognized"
