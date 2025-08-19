# -*- coding: utf-8 -*-
"""
Newport 1830-C optical power meter controller.

Hardware-level communication layer for Newport 1830-C power meter.
Provides clean interface for PyMoDAQ plugin.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import serial

logger = logging.getLogger(__name__)


class Newport1830CController:
    """
    Hardware controller for Newport 1830-C optical power meter.

    Handles serial communication and basic device control.
    Based on original working implementation from ~/.qudi_urashg.
    """

    def __init__(
        self, port: str = "/dev/ttyUSB2", baudrate: int = 9600, timeout: float = 2.0, mock_mode: bool = False
    ):
        """Initialize controller with connection parameters."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.mock_mode = mock_mode

        self._serial: Optional[serial.Serial] = None
        self._connected = False

        # Current device settings
        self._current_wavelength = 800.0
        self._current_units = "W"
        self._current_range = "Auto"
        
        # Mock state for realistic simulation
        self._mock_power_base = 0.0035  # 3.5 mW baseline
        self._mock_zero_offset = 0.0
        self._mock_filter_speed = "Medium"

        logger.info(f"Newport1830C controller initialized for {port} (mock_mode: {mock_mode})")

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
                # Apply mock default settings
                self._initialize_settings()
                return True

            # Open serial connection
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
            raise ConnectionError(
                "No response from Newport 1830-C - check device and calibration module"
            )

        self._connected = True
        logger.info(
            f"Newport 1830-C connected successfully ({len(working_commands)}/{len(test_commands)} commands working)"
        )

        # Apply default settings
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

        Args:
            command: Command string to send
            expect_response: Whether to wait for and return response

        Returns:
            str or None: Response from device, or None on error
        """
        import time
        import random
        import math
        
        if self.mock_mode:
            # Enhanced mock responses based on Newport 1830-C protocol
            time.sleep(random.uniform(0.1, 0.3))  # Simulate communication delay
            
            command = command.strip().upper()
            logger.debug(f"Mock Newport 1830-C command: '{command}' (expect_response: {expect_response})")
            
            if not expect_response:
                # Handle set commands (no response expected)
                if command.startswith("W") and command[1:].isdigit():
                    # Set wavelength: W800
                    try:
                        wl = float(command[1:])
                        if 400 <= wl <= 1100:
                            self._current_wavelength = wl
                            logger.debug(f"Mock Newport wavelength set to {wl}nm")
                        else:
                            logger.warning(f"Mock Newport: Wavelength {wl}nm out of range")
                    except ValueError:
                        logger.error(f"Mock Newport: Invalid wavelength format: {command}")
                    return ""
                    
                elif command.startswith("U"):
                    # Set units: U1=Watts, U3=dBm
                    if command == "U1":
                        self._current_units = "W"
                        logger.debug("Mock Newport units set to Watts")
                    elif command == "U3":
                        self._current_units = "dBm"
                        logger.debug("Mock Newport units set to dBm")
                    else:
                        logger.warning(f"Mock Newport: Unknown units command: {command}")
                    return ""
                    
                elif command.startswith("R"):
                    # Set range: R0=Auto, R1-R7=fixed ranges
                    try:
                        range_num = int(command[1:])
                        if range_num == 0:
                            self._current_range = "Auto"
                        elif 1 <= range_num <= 7:
                            self._current_range = f"Range {range_num}"
                        else:
                            logger.warning(f"Mock Newport: Invalid range: {command}")
                        logger.debug(f"Mock Newport range set to {self._current_range}")
                    except ValueError:
                        logger.error(f"Mock Newport: Invalid range format: {command}")
                    return ""
                    
                elif command.startswith("F"):
                    # Set filter speed: F1=Slow, F2=Medium, F3=Fast
                    speed_map = {"F1": "Slow", "F2": "Medium", "F3": "Fast"}
                    if command in speed_map:
                        self._mock_filter_speed = speed_map[command]
                        logger.debug(f"Mock Newport filter speed set to {self._mock_filter_speed}")
                    else:
                        logger.warning(f"Mock Newport: Invalid filter speed: {command}")
                    return ""
                    
                elif command == "G1":
                    # Go (enable measurements)
                    logger.debug("Mock Newport measurements enabled")
                    return ""
                    
                elif command == "G0":
                    # Stop measurements
                    logger.debug("Mock Newport measurements disabled")
                    return ""
                    
                elif command == "Z1":
                    # Zero adjust on
                    logger.debug("Mock Newport zero adjust started")
                    time.sleep(0.5)  # Simulate zero adjustment time
                    return ""
                    
                elif command == "Z0":
                    # Zero adjust off (complete)
                    self._mock_zero_offset = random.uniform(-0.0001, 0.0001)  # Small random offset
                    logger.debug(f"Mock Newport zero adjust completed (offset: {self._mock_zero_offset:.6f})")
                    return ""
                    
                else:
                    logger.debug(f"Mock Newport: Unhandled set command: {command}")
                    return ""
            
            # Handle query commands (response expected)
            if command == "W?":
                # Get wavelength
                response = str(int(self._current_wavelength))
                logger.debug(f"Mock Newport wavelength query: {response}")
                return response
                
            elif command == "U?":
                # Get units
                response = "1" if self._current_units == "W" else "3"
                logger.debug(f"Mock Newport units query: {response} ({self._current_units})")
                return response
                
            elif command == "D?":
                # Get power reading - realistic simulation with noise
                base_power = self._mock_power_base
                
                # Add realistic power fluctuations and noise
                # Simulate 1/f noise common in optical power measurements
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
                measured_power = (base_power + noise_1f + white_noise + self._mock_zero_offset) * wl_factor
                
                # Ensure positive power
                measured_power = max(measured_power, 0.0)
                
                # Format based on current units
                if self._current_units == "W":
                    if measured_power >= 0.001:
                        response = f"{measured_power:.6f}"  # 6 decimal places for mW range
                    else:
                        response = f"{measured_power:.9f}"  # More precision for μW range
                else:
                    # Convert to dBm
                    if measured_power > 0:
                        dbm_value = 10 * math.log10(measured_power / 0.001)  # Convert W to dBm
                        response = f"{dbm_value:.3f}"
                    else:
                        response = "-50.000"  # Very low power in dBm
                        
                logger.debug(f"Mock Newport power reading: {response} {self._current_units}")
                return response
                
            elif command == "R?":
                # Get current range
                if self._current_range == "Auto":
                    response = "0"
                else:
                    response = self._current_range.split()[-1]  # Extract number
                logger.debug(f"Mock Newport range query: {response} ({self._current_range})")
                return response
                
            elif command == "F?":
                # Get filter speed
                speed_map = {"Slow": "1", "Medium": "2", "Fast": "3"}
                response = speed_map.get(self._mock_filter_speed, "2")
                logger.debug(f"Mock Newport filter speed query: {response} ({self._mock_filter_speed})")
                return response
                
            elif command == "G?":
                # Get measurement status (typically always enabled)
                response = "1"
                logger.debug(f"Mock Newport measurement status: {response}")
                return response
                
            else:
                # Unknown command
                logger.warning(f"Mock Newport: Unknown query command: {command}")
                return "ERROR"

        # Real hardware communication (unchanged)
        try:
            if not self._serial or not self._serial.is_open:
                logger.error("Serial connection not available")
                return None

            # Clear buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            # Send command (Newport 1830-C uses LF termination)
            cmd_bytes = (command + "\n").encode("ascii")
            self._serial.write(cmd_bytes)
            self._serial.flush()

            if expect_response:
                time.sleep(0.5)  # Give device time to respond
                response = (
                    self._serial.read(1000).decode("ascii", errors="ignore").strip()
                )
                return response if response else None
            else:
                time.sleep(0.1)  # Brief delay for command processing
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

            # Set auto range
            self.set_power_range("Auto")

            # Set medium filter speed
            self.set_filter_speed("Medium")

            # Enable measurements
            self._send_command("G1", expect_response=False)  # Go (start measurements)

            time.sleep(0.5)  # Allow settings to stabilize

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

    def get_multiple_readings(self, count: int = 5) -> List[float]:
        """
        Get multiple power readings for averaging.

        Args:
            count: Number of readings to take

        Returns:
            List of power values
        """
        readings = []
        for i in range(count):
            power = self.get_power()
            if power is not None:
                readings.append(power)
            time.sleep(0.01)  # Brief delay between readings
        return readings

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

    def set_power_range(self, power_range: str) -> bool:
        """
        Set power measurement range.

        Args:
            power_range: 'Auto' or 'Range 1' through 'Range 7'

        Returns:
            bool: True if successful
        """
        try:
            if not self._connected:
                return False

            if power_range == "Auto":
                cmd = "R0"  # Auto range
            elif power_range.startswith("Range "):
                range_num = power_range.split()[-1]
                cmd = f"R{range_num}"
            else:
                logger.error(f"Invalid power range: {power_range}")
                return False

            response = self._send_command(cmd, expect_response=False)
            if response is not None:
                self._current_range = power_range
                logger.debug(f"Power range set to {power_range}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error setting power range: {e}")
            return False

    def set_filter_speed(self, speed: str) -> bool:
        """
        Set measurement filter speed.

        Args:
            speed: 'Slow', 'Medium', or 'Fast'

        Returns:
            bool: True if successful
        """
        try:
            if not self._connected:
                return False

            speed_map = {"Slow": "F1", "Medium": "F2", "Fast": "F3"}
            cmd = speed_map.get(speed)
            if not cmd:
                logger.error(f"Invalid filter speed: {speed}")
                return False

            response = self._send_command(cmd, expect_response=False)
            if response is not None:
                logger.debug(f"Filter speed set to {speed}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error setting filter speed: {e}")
            return False

    def zero_adjust(self) -> bool:
        """
        Perform zero adjustment.

        Returns:
            bool: True if successful
        """
        try:
            if not self._connected:
                return False

            logger.info("Performing zero adjustment...")

            # Turn zero function on
            response1 = self._send_command("Z1", expect_response=False)

            # Wait for adjustment to complete
            time.sleep(2.0)

            # Turn zero function off
            response2 = self._send_command("Z0", expect_response=False)

            success = (response1 is not None) and (response2 is not None)
            if success:
                logger.info("Zero adjustment completed")
            else:
                logger.error("Zero adjustment failed")

            return success

        except Exception as e:
            logger.error(f"Error during zero adjustment: {e}")
            return False

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

    # Note: __del__ method removed to prevent QThread destruction conflicts
    # Cleanup is handled explicitly via disconnect() in the plugin's close() method


if __name__ == "__main__":
    # Test the controller
    import logging

    logging.basicConfig(level=logging.DEBUG)

    print("Testing Testing Newport 1830-C Controller")
    print("=" * 40)

    controller = Newport1830CController()

    if controller.connect():
        print("[OK] Connected to Newport 1830-C")

        # Test basic operations
        print(f"INFO: Device Info: {controller.get_device_info()}")

        # Test wavelength
        if controller.set_wavelength(795.0):
            wavelength = controller.get_wavelength()
            print(f"INFO: Wavelength: {wavelength} nm")

        # Test power reading
        power = controller.get_power()
        if power is not None:
            print(f"POWER: Power: {power} {controller.get_units()}")

        # Test multiple readings
        readings = controller.get_multiple_readings(3)
        if readings:
            avg_power = sum(readings) / len(readings)
            print(
                f"DATA: Average power ({len(readings)} readings): {avg_power:.6f} {controller.get_units()}"
            )

        controller.disconnect()
        print("[OK] Disconnected")

    else:
        print("[ERROR] Failed to connect to Newport 1830-C")
        print("   - Check device is connected to /dev/ttyUSB2")
        print("   - Check calibration module is attached")
        print("   - Check device power")
