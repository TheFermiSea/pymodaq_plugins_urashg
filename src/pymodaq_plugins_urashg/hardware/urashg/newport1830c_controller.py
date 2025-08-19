"""
Newport 1830-C optical power meter controller.

Hardware-level communication layer for Newport 1830-C power meter.
Provides clean interface for PyMoDAQ plugin.
"""

import logging
import time
import random
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Newport1830CController:
    """
    Hardware controller for Newport 1830-C optical power meter.

    Handles serial communication and basic device control.
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB2",
        baudrate: int = 9600,
        timeout: float = 2.0,
        mock_mode: bool = False,
    ):
        """Initialize controller with connection parameters."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.mock_mode = mock_mode

        self._serial = None
        self._connected = False

        # Current device settings
        self._current_wavelength = 800.0
        self._current_units = "W"
        self._current_range = "Auto"

        # Mock state for realistic simulation
        self._mock_power_base = 0.0035  # 3.5 mW baseline
        self._mock_zero_offset = 0.0
        self._mock_filter_speed = "Medium"

        logger.info(
            f"Newport1830C controller initialized for {port} (mock_mode: {mock_mode})"
        )

    def connect(self) -> bool:
        """
        Connect to Newport 1830-C power meter.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self._connected:
                return True

            logger.info(f"Connecting to Newport 1830-C on {self.port}...")

            if self.mock_mode:
                logger.info("Mock mode: Simulating connection to Newport 1830-C")
                self._connected = True
                self._initialize_settings()
                return True

            # Real hardware connection would go here
            import serial

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.timeout,
            )

            # Test basic communication
            test_commands = ["W?", "U?", "D?"]
            working_commands = []

            for cmd in test_commands:
                response = self._send_command(cmd)
                if response is not None:
                    working_commands.append(cmd)
                    logger.debug(f"Command {cmd} -> {response}")

            if not working_commands:
                raise ConnectionError("No response from Newport 1830-C")

            self._connected = True
            logger.info(
                f"Newport 1830-C connected successfully ({len(working_commands)}/{len(test_commands)} commands working)"
            )
            self._initialize_settings()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Newport 1830-C: {e}")
            self._cleanup_connection()
            return False

    def disconnect(self):
        """Disconnect from power meter."""
        try:
            self._cleanup_connection()
            logger.info("Newport 1830-C disconnected")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def _cleanup_connection(self):
        """Clean up serial connection."""
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
            self._connected = False
        except Exception:
            pass

    def _send_command(
        self, command: str, expect_response: bool = True
    ) -> Optional[str]:
        """
        Send command to power meter and get response with realistic mock simulation.
        """
        if self.mock_mode:
            # Enhanced mock responses based on Newport 1830-C protocol
            time.sleep(random.uniform(0.1, 0.3))  # Simulate communication delay

            command = command.strip().upper()
            logger.debug(
                f"Mock Newport 1830-C command: '{command}' (expect_response: {expect_response})"
            )

            # Handle query commands (response expected)
            if command == "W?":
                # Get wavelength
                response = str(int(self._current_wavelength))
                logger.debug(f"Mock Newport wavelength query: {response}")
                return response

            elif command == "U?":
                # Get units
                response = "1" if self._current_units == "W" else "3"
                logger.debug(
                    f"Mock Newport units query: {response} ({self._current_units})"
                )
                return response

            elif command == "D?":
                # Get power reading - realistic simulation with noise
                base_power = self._mock_power_base

                # Add realistic power fluctuations and noise
                time_factor = time.time() % 100  # Slow variations
                noise_1f = 0.02 * math.sin(time_factor * 0.1) * base_power

                # Add white noise
                white_noise = random.gauss(0, 0.001 * base_power)

                # Add wavelength dependence (realistic detector response)
                wl_factor = 1.0
                if 700 <= self._current_wavelength <= 900:
                    wl_factor = 1.1  # Better response in NIR
                elif self._current_wavelength < 500:
                    wl_factor = 0.7  # Reduced response in blue

                # Calculate final power
                measured_power = (
                    base_power + noise_1f + white_noise + self._mock_zero_offset
                ) * wl_factor

                # Ensure positive power
                measured_power = max(measured_power, 0.0)

                # Format based on current units
                if self._current_units == "W":
                    if measured_power >= 0.001:
                        response = (
                            f"{measured_power:.6f}"  # 6 decimal places for mW range
                        )
                    else:
                        response = (
                            f"{measured_power:.9f}"  # More precision for μW range
                        )
                else:
                    # Convert to dBm
                    if measured_power > 0:
                        dbm_value = 10 * math.log10(
                            measured_power / 0.001
                        )  # Convert W to dBm
                        response = f"{dbm_value:.3f}"
                    else:
                        response = "-50.000"  # Very low power in dBm

                logger.debug(
                    f"Mock Newport power reading: {response} {self._current_units}"
                )
                return response

            else:
                # Handle set commands or unknown queries
                if not expect_response:
                    # Set commands
                    logger.debug(f"Mock Newport: Set command '{command}' acknowledged")
                    return ""
                else:
                    # Unknown query
                    logger.warning(f"Mock Newport: Unknown query command: {command}")
                    return "ERROR"

        # Real hardware communication would go here
        try:
            if not self._serial or not self._serial.is_open:
                logger.error("Serial connection not available")
                return None

            # Newport 1830-C communication protocol
            cmd_bytes = (command + "\n").encode("ascii")
            self._serial.write(cmd_bytes)
            self._serial.flush()

            if expect_response:
                time.sleep(0.5)
                response = (
                    self._serial.read(1000).decode("ascii", errors="ignore").strip()
                )
                return response if response else None
            else:
                time.sleep(0.1)
                return ""

        except Exception as e:
            logger.error(f"Communication error: {e}")
            return None

    def _initialize_settings(self):
        """Apply initial settings to power meter."""
        try:
            # Set default wavelength (800 nm)
            self.set_wavelength(800.0)
            # Set units to watts
            self.set_units("W")
            logger.info("Newport 1830-C initial settings applied")
        except Exception as e:
            logger.error(f"Error applying initial settings: {e}")

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connected

    def get_power(self) -> Optional[float]:
        """
        Get current power reading.

        Returns:
            float or None: Power value in current units, or None on error
        """
        try:
            if not self._connected:
                logger.error("Device not connected")
                return None

            response = self._send_command("D?")
            if response:
                try:
                    power_value = float(response.strip())
                    return power_value
                except ValueError:
                    logger.error(f"Invalid power reading: {response}")
                    return None
            else:
                logger.error("No response to power query")
                return None

        except Exception as e:
            logger.error(f"Error reading power: {e}")
            return None

    def set_wavelength(self, wavelength: float) -> bool:
        """
        Set measurement wavelength.

        Args:
            wavelength: Wavelength in nanometers (400-1100)

        Returns:
            bool: True if successful
        """
        try:
            if not self._connected:
                return False

            if not (400 <= wavelength <= 1100):
                logger.error(f"Wavelength {wavelength} out of range (400-1100 nm)")
                return False

            response = self._send_command(f"W{int(wavelength)}", expect_response=False)
            if response is not None:
                self._current_wavelength = wavelength
                logger.debug(f"Wavelength set to {wavelength} nm")
                return True
            return False

        except Exception as e:
            logger.error(f"Error setting wavelength: {e}")
            return False

    def get_wavelength(self) -> Optional[float]:
        """
        Get current wavelength setting.

        Returns:
            float or None: Current wavelength in nm
        """
        try:
            if not self._connected:
                return None

            response = self._send_command("W?")
            if response:
                try:
                    wavelength = float(response.strip())
                    self._current_wavelength = wavelength
                    return wavelength
                except ValueError:
                    logger.error(f"Invalid wavelength response: {response}")
                    return self._current_wavelength
            else:
                return self._current_wavelength

        except Exception as e:
            logger.error(f"Error reading wavelength: {e}")
            return self._current_wavelength

    def set_units(self, units: str) -> bool:
        """
        Set power measurement units.

        Args:
            units: 'W' for Watts or 'dBm' for dBm

        Returns:
            bool: True if successful
        """
        try:
            if not self._connected:
                return False

            if units == "W":
                cmd = "U1"  # Watts
            elif units == "dBm":
                cmd = "U3"  # dBm
            else:
                logger.error(f"Invalid units: {units}")
                return False

            response = self._send_command(cmd, expect_response=False)
            if response is not None:
                self._current_units = units
                logger.debug(f"Units set to {units}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error setting units: {e}")
            return False

    def get_units(self) -> str:
        """
        Get current units setting.

        Returns:
            str: Current units ('W' or 'dBm')
        """
        try:
            if not self._connected:
                return self._current_units

            response = self._send_command("U?")
            if response:
                response = response.strip()
                if response == "1":
                    self._current_units = "W"
                elif response == "3":
                    self._current_units = "dBm"

            return self._current_units

        except Exception as e:
            logger.error(f"Error reading units: {e}")
            return self._current_units

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information and status.

        Returns:
            Dict with device information
        """
        info = {
            "model": "Newport 1830-C",
            "port": self.port,
            "connected": self._connected,
            "wavelength": self._current_wavelength,
            "units": self._current_units,
            "range": self._current_range,
        }

        if self._connected:
            # Get current readings
            power = self.get_power()
            if power is not None:
                info["current_power"] = power

        return info

    @property
    def connected(self) -> bool:
        """Check if connected to device."""
        return self._connected

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self.mock_mode
