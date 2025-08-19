"""
MaiTai Laser Controller - Stub Implementation for Testing

This is a placeholder implementation for testing purposes.
The full implementation would provide MaiTai laser control.
"""


class MaiTaiError(Exception):
    """MaiTai specific exception"""

    pass


class MaiTaiController:
    """
    Hardware controller for Spectra-Physics MaiTai Titanium Sapphire Laser.

    Provides hardware abstraction layer between PyMoDAQ plugins and MaiTai laser.
    Based on working implementation from previous repository.
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        timeout: float = 2.0,
        mock_mode: bool = False,
    ):
        """
        Initialize MaiTai controller.

        Parameters
        ----------
        port : str
            Serial port for device communication
        baudrate : int
            Serial communication baud rate
        timeout : float
            Communication timeout in seconds
        mock_mode : bool
            Enable mock mode for testing without hardware
        """
        import logging
        import time
        from threading import Lock

        import serial

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.mock_mode = mock_mode

        # Connection state
        self._serial_connection = None
        self._connected = False
        self._lock = Lock()

        # Mock state for testing
        self._mock_wavelength = 780.0
        self._mock_power = 2.5
        self._mock_shutter = False

        self.logger = logging.getLogger(__name__)
        # Enable debug logging for troubleshooting
        self.logger.setLevel(logging.DEBUG)
        self.logger.info(
            f"MaiTaiController initialized: port={port}, mock_mode={mock_mode}"
        )

    def connect(self) -> bool:
        """
        Connect to MaiTai laser.

        Returns
        -------
        bool
            True if connection successful, False otherwise
        """
        import time

        import serial

        with self._lock:
            if self._connected:
                return True

            if self.mock_mode:
                self._connected = True
                self.logger.info("MaiTai mock mode connected")
                return True

            try:
                self._serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                    timeout=self.timeout,
                    xonxoff=True,
                )

                # Test communication
                if self._test_communication():
                    self._connected = True
                    self.logger.info(f"MaiTai connected on {self.port}")
                    return True
                else:
                    self._cleanup_connection()
                    self.logger.error("MaiTai communication test failed")
                    return False

            except Exception as e:
                self.logger.error(f"Failed to connect to MaiTai: {e}")
                self._cleanup_connection()
                return False

    def disconnect(self):
        """Disconnect from MaiTai laser."""
        with self._lock:
            self._cleanup_connection()
            self._connected = False
            self.logger.info("MaiTai disconnected")

    def _cleanup_connection(self):
        """Clean up serial connection."""
        try:
            if self._serial_connection and self._serial_connection.is_open:
                self._serial_connection.close()
        except Exception:
            pass
        finally:
            self._serial_connection = None

    def _test_communication(self) -> bool:
        """Test communication with laser."""
        try:
            # Try multiple commands for better communication test
            # Some MaiTai units respond better to different commands
            test_commands = ["WAVELENGTH?", "*IDN?", "READ:POW?"]
            
            for cmd in test_commands:
                try:
                    time.sleep(0.2)  # Longer delay between tests
                    response = self._send_command(cmd)
                    if response is not None and response.strip() != "":
                        self.logger.debug(f"MaiTai responded to {cmd}: {response}")
                        return True
                except Exception as e:
                    self.logger.debug(f"Command {cmd} failed: {e}")
                    continue
            
            self.logger.warning("MaiTai not responding to any test commands")
            return False
        except Exception:
            return False

    def _send_command(self, command: str, expect_response: bool = True):
        """
        Send command to MaiTai laser and get response.

        Parameters
        ----------
        command : str
            Command to send
        expect_response : bool
            Whether to expect a response

        Returns
        -------
        str or None
            Response from laser, None if error
        """
        import time

        if self.mock_mode:
            return self._mock_send_command(command, expect_response)

        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                self.logger.error("Serial connection not available")
                return None

            # Clear buffers
            self._serial_connection.reset_input_buffer()
            self._serial_connection.reset_output_buffer()

            # Send command
            cmd_bytes = (command + "\r\n").encode("ascii")
            self.logger.debug(f"Sending bytes: {cmd_bytes}")
            bytes_written = self._serial_connection.write(cmd_bytes)
            self._serial_connection.flush()
            self.logger.debug(f"Wrote {bytes_written} bytes")

            if expect_response:
                time.sleep(0.3)  # Longer delay for MaiTai response
                response = (
                    self._serial_connection.readline()
                    .decode("ascii", errors="ignore")
                    .strip()
                )
                self.logger.debug(f"Received response: '{response}'")
                return response
            else:
                time.sleep(0.05)  # Brief delay for command processing
                return ""

        except Exception as e:
            self.logger.error(f"Communication error with command '{command}': {e}")
            return None

    def _mock_send_command(self, command: str, expect_response: bool = True):
        """Enhanced mock command handling with realistic SCPI protocol simulation."""
        import time
        import random
        
        # Simulate realistic communication delay
        time.sleep(random.uniform(0.1, 0.3))
        
        command = command.strip().upper()
        self.logger.debug(f"Mock MaiTai command: '{command}' (expect_response: {expect_response})")
        
        if not expect_response:
            # Handle set commands (no response expected)
            if command.startswith("WAVELENGTH"):
                try:
                    parts = command.split()
                    if len(parts) >= 2:
                        wl = float(parts[1])
                        # Validate wavelength range (typical Ti:Sapphire range)
                        if 690 <= wl <= 1040:
                            old_wl = self._mock_wavelength
                            self._mock_wavelength = wl
                            # Simulate tuning time based on wavelength change
                            tune_time = abs(wl - old_wl) * 0.01  # ~10ms per nm
                            if tune_time > 0.1:
                                time.sleep(min(tune_time, 2.0))  # Max 2 seconds
                            self.logger.debug(f"Mock MaiTai wavelength set to {wl}nm (tune time: {tune_time:.2f}s)")
                        else:
                            self.logger.warning(f"Mock MaiTai: Wavelength {wl}nm out of range (690-1040nm)")
                except (ValueError, IndexError):
                    self.logger.error(f"Mock MaiTai: Invalid wavelength command format: {command}")
                return ""
                
            elif command.startswith("SHUTTER"):
                try:
                    parts = command.split()
                    if len(parts) >= 2:
                        state = parts[1].upper()
                        if state in ["OPEN", "1", "ON"]:
                            self._mock_shutter = True
                            self.logger.debug("Mock MaiTai shutter opened")
                        elif state in ["CLOSE", "0", "OFF"]:
                            self._mock_shutter = False  
                            self.logger.debug("Mock MaiTai shutter closed")
                        else:
                            self.logger.warning(f"Mock MaiTai: Invalid shutter state: {state}")
                except IndexError:
                    self.logger.error(f"Mock MaiTai: Invalid shutter command format: {command}")
                return ""
                
            elif command.startswith("*RST"):
                # Reset command - restore defaults
                self._mock_wavelength = 780.0
                self._mock_power = 2.5
                self._mock_shutter = False
                self.logger.debug("Mock MaiTai system reset")
                return ""
                
            else:
                self.logger.debug(f"Mock MaiTai: Unhandled set command: {command}")
                return ""
            
        elif command.startswith("SHUTTER"):
            try:
                parts = command.split()
                if len(parts) >= 2:
                    state = parts[1].upper()
                    if state in ["OPEN", "1", "ON"]:
                        self._mock_shutter = True
                        self.logger.debug("Mock MaiTai shutter opened")
                    elif state in ["CLOSE", "0", "OFF"]:
                        self._mock_shutter = False  
                        self.logger.debug("Mock MaiTai shutter closed")
                    else:
                        self.logger.warning(f"Mock MaiTai: Invalid shutter state: {state}")
            except IndexError:
                self.logger.error(f"Mock MaiTai: Invalid shutter command format: {command}")
            return ""
            
        elif command.startswith("*RST"):
            # Reset command - restore defaults
            self._mock_wavelength = 780.0
            self._mock_power = 2.5
            self._mock_shutter = False
            self.logger.debug("Mock MaiTai system reset")
            return ""
            
        else:
            self.logger.debug(f"Mock MaiTai: Unhandled set command: {command}")
            return ""

    # Handle query commands (response expected)
    if command == "WAVELENGTH?" or command == "WAVEL?":
        # Return wavelength with realistic format variations
        formats = [f"{self._mock_wavelength:.1f}nm", f"{self._mock_wavelength:.2f}", f"{self._mock_wavelength:g}"]
        response = random.choice(formats)
        self.logger.debug(f"Mock MaiTai wavelength query: {response}")
        return response
        
    elif command == "POWER?" or command == "POW?":
        # Simulate power fluctuations (±5% realistic for Ti:Sapphire)
        fluctuation = random.uniform(-0.05, 0.05)
        actual_power = self._mock_power * (1 + fluctuation)
        # Power depends on shutter state
        if not self._mock_shutter:
            actual_power = 0.0
        response = f"{actual_power:.3f}W"
        self.logger.debug(f"Mock MaiTai power query: {response}")
        return response
        
    elif command == "SHUTTER?" or command == "SHUT?":
        response = "1" if self._mock_shutter else "0"
        self.logger.debug(f"Mock MaiTai shutter query: {response}")
        return response
        
    elif command == "*IDN?":
        # Standard SCPI identification
        response = "Coherent,MaiTai-DeepSee,SN123456,v2.1.0"
        self.logger.debug(f"Mock MaiTai identification: {response}")
        return response
        
    elif command == "*STB?":
        # Status byte - simulate realistic laser status
        # Bit 0: Emission possible, Bit 1: Modelocked, others for various states
        status_byte = 0
        if self._mock_shutter and self._mock_power > 0.1:
            status_byte |= 1  # Emission possible
        if self._mock_power > 0.5:
            status_byte |= 2  # Modelocked
        if 750 <= self._mock_wavelength <= 850:
            status_byte |= 4  # Optimal wavelength range
            
        response = str(status_byte)
        self.logger.debug(f"Mock MaiTai status byte: {response}")
        return response
        
    elif command == "SYSTEM:ERR?" or command == "SYST:ERR?":
        # System error queue - usually empty in mock mode
        # Format: "error_code,error_message"
        # Occasionally simulate a minor warning for realism
        if random.random() < 0.05:  # 5% chance of minor warning
            warnings = [
                "100,Temperature warning - cavity",
                "101,Humidity sensor drift",  
                "102,Pump power fluctuation"
            ]
            response = random.choice(warnings)
        else:
            response = "0,No error"
        self.logger.debug(f"Mock MaiTai system error: {response}")
        return response
        
    elif command == "READ:POW?" or command == "MEAS:POW?":
        # Alternative power measurement command
        fluctuation = random.uniform(-0.02, 0.02)
        actual_power = self._mock_power * (1 + fluctuation)
        if not self._mock_shutter:
            actual_power = 0.0
        response = f"{actual_power:.4f}"
        self.logger.debug(f"Mock MaiTai power measurement: {response}")
        return response
        
    elif command == "DIAG:TEMP?":
        # Temperature diagnostics (realistic Ti:Sapphire temperatures)
        base_temp = 22.0  # Room temperature base
        laser_heating = 5.0 if self._mock_power > 1.0 else 2.0
        temp = base_temp + laser_heating + random.uniform(-1.0, 1.0)
        response = f"{temp:.1f}C"
        self.logger.debug(f"Mock MaiTai temperature: {response}")
        return response
        
    elif command == "PUMP:POW?" or command == "PUMP:CURR?":
        # Pump laser diagnostics
        if "POW" in command:
            pump_power = self._mock_power * 8.0  # ~8:1 pump to output ratio
            response = f"{pump_power:.1f}W"
        else:
            pump_current = self._mock_power * 3.2  # Realistic current scaling
            response = f"{pump_current:.2f}A"
        self.logger.debug(f"Mock MaiTai pump diagnostics: {response}")
        return response
        
    elif command == "MODE:LOCK?" or command == "MODELOCK?":
        # Mode-locking status
        modelocked = self._mock_power > 0.5 and self._mock_shutter
        response = "1" if modelocked else "0"
        self.logger.debug(f"Mock MaiTai modelock status: {response}")
        return response
        
    elif command.startswith("*"):
        # Standard SCPI commands
        if command == "*ESR?":
            response = "0"  # No standard event errors
        elif command == "*OPC?":
            response = "1"  # Operation complete
        elif command == "*TST?":
            response = "0"  # Self-test passed
        else:
            response = "1"  # Generic success for unhandled SCPI
        self.logger.debug(f"Mock MaiTai SCPI command '{command}': {response}")
        return response
        
    else:
        # Unknown command - return error or empty response
        self.logger.warning(f"Mock MaiTai: Unknown command '{command}'")
        return "ERROR: Unknown command"

    def get_wavelength(self):
        """
        Get current wavelength.

        Returns
        -------
        float or None
            Current wavelength in nm, None if error
        """
        with self._lock:
            if not self._connected:
                return None

            try:
                response = self._send_command("WAVELENGTH?")
                if response:
                    # Parse response like "801nm" -> 801.0
                    wavelength_str = response.replace("nm", "").strip()
                    wavelength = float(wavelength_str)
                    return wavelength
            except Exception as e:
                self.logger.error(f"Error getting wavelength: {e}")

            return None

    def set_wavelength(self, wavelength: float) -> bool:
        """
        Set wavelength.

        Parameters
        ----------
        wavelength : float
            Target wavelength in nm

        Returns
        -------
        bool
            True if command sent successfully, False otherwise
        """
        with self._lock:
            if not self._connected:
                self.logger.error("Cannot set wavelength - not connected")
                return False

            try:
                # MaiTai expects decimal format: "WAVELENGTH 801.0"
                wavelength_rounded = round(wavelength, 1)
                command = f"WAVELENGTH {wavelength_rounded}"
                
                self.logger.info(f"Sending command: {command}")
                response = self._send_command(command, expect_response=False)
                
                if response is not None:
                    self.logger.info(f"Wavelength set command sent successfully")
                    # Note: MaiTai laser may take several seconds to tune to new wavelength
                    # Return success immediately since command was sent successfully
                    return True
                else:
                    self.logger.error("Failed to send wavelength command")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error setting wavelength: {e}")
                return False

    def get_power(self):
        """
        Get current power level.

        Returns
        -------
        float or None
            Current power in watts, None if error
        """
        with self._lock:
            if not self._connected:
                return None

            try:
                response = self._send_command("POWER?")
                if response:
                    # Parse response like "3.000W" -> 3.0
                    power_str = response.replace("W", "").strip()
                    power = float(power_str)
                    return power
            except Exception as e:
                self.logger.error(f"Error getting power: {e}")

            return None

    def get_shutter_state(self):
        """
        Get current shutter state.

        Returns
        -------
        bool or None
            True if shutter open, False if closed, None if error
        """
        with self._lock:
            if not self._connected:
                return None

            try:
                response = self._send_command("SHUTTER?")
                if response:
                    # Parse response like "1" -> True, "0" -> False
                    state = response.strip() == "1"
                    return state
            except Exception as e:
                self.logger.error(f"Error getting shutter state: {e}")

            return None

    def set_shutter(self, open_shutter: bool) -> bool:
        """
        Set shutter state.

        Parameters
        ----------
        open_shutter : bool
            True to open shutter, False to close

        Returns
        -------
        bool
            True if command sent successfully, False otherwise
        """
        with self._lock:
            if not self._connected:
                self.logger.error("Cannot set shutter - not connected")
                return False

            try:
                command = "SHUTTER 1" if open_shutter else "SHUTTER 0"
                action = "open" if open_shutter else "close"
                
                self.logger.info(f"Sending command: {command} (to {action} shutter)")
                response = self._send_command(command, expect_response=False)
                
                if response is not None:
                    self.logger.info(f"Shutter {action} command sent successfully")
                    # Return success immediately since command was sent successfully
                    # The UI will update the actual state through periodic status updates
                    return True
                else:
                    self.logger.error(f"Failed to send shutter {action} command")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error setting shutter: {e}")
                return False

    def open_shutter(self) -> bool:
        """
        Open shutter (convenience method).
        
        Returns
        -------
        bool
            True if command sent successfully, False otherwise
        """
        return self.set_shutter(True)
    
    def close_shutter(self) -> bool:
        """
        Close shutter (convenience method).
        
        Returns
        -------
        bool
            True if command sent successfully, False otherwise
        """
        return self.set_shutter(False)

    def check_system_errors(self, quick_check: bool = False) -> tuple[bool, list[str]]:
        """
        Check for system errors using SYSTem:ERR command.
        
        Parameters
        ----------
        quick_check : bool
            If True, only check once instead of emptying full buffer
        
        Returns
        -------
        tuple[bool, list[str]]
            (has_errors, error_messages) - True if errors found, list of error descriptions
        """
        with self._lock:
            if not self._connected:
                return False, ["Not connected"]

            errors = []
            has_errors = False
            
            try:
                # Query system errors - limit iterations for quick check
                max_iterations = 1 if quick_check else 5  # Reduced from 10 to prevent blocking
                
                for _ in range(max_iterations):
                    response = self._send_command("SYSTem:ERR?")
                    if response and response.strip():
                        # Parse error code and message
                        parts = response.split(',', 1) if ',' in response else [response]
                        error_code = parts[0].strip()
                        error_msg = parts[1].strip() if len(parts) > 1 else "Unknown error"
                        
                        # Check if this is a real error (non-zero error code)
                        try:
                            code_num = int(error_code)
                            if code_num != 0:
                                has_errors = True
                                # Decode error based on Table 6-1
                                error_desc = self._decode_error_code(code_num)
                                errors.append(f"Error {code_num}: {error_desc} - {error_msg}")
                                if quick_check:  # For quick check, stop after first error
                                    break
                            else:
                                # Error code 0 means no more errors
                                break
                        except ValueError:
                            # Non-numeric error code
                            if error_code != "0":
                                has_errors = True
                                errors.append(f"Error: {response}")
                                if quick_check:
                                    break
                    else:
                        break
                        
            except Exception as e:
                self.logger.error(f"Error checking system errors: {e}")
                return True, [f"Error checking failed: {e}"]
                
            return has_errors, errors

    def _decode_error_code(self, error_code: int) -> str:
        """
        Decode MaiTai error codes based on Table 6-1.
        
        Parameters
        ----------
        error_code : int
            Binary error code from MaiTai
            
        Returns
        -------
        str
            Human-readable error description
        """
        error_descriptions = []
        
        # Check individual error bits
        if error_code & 1:  # Bit 0
            error_descriptions.append("CMD_ERR: Command format error")
        if error_code & 2:  # Bit 1  
            error_descriptions.append("EXE_ERR: Command execution error")
        if error_code & 32:  # Bit 5
            error_descriptions.append("SYS_ERR: System error (interlock/diagnostic)")
        if error_code & 64:  # Bit 6
            error_descriptions.append("LASER_ON: Laser emission possible")
        if error_code & 128:  # Bit 7
            error_descriptions.append("ANY_ERR: Error condition present")
            
        return "; ".join(error_descriptions) if error_descriptions else f"Unknown error code: {error_code}"

    def get_status_byte(self) -> tuple[int, dict]:
        """
        Get product status byte using *STB? command.
        
        Returns
        -------
        tuple[int, dict]
            (status_byte, status_info) - Raw status byte and decoded information
        """
        with self._lock:
            if not self._connected:
                return 0, {"connected": False}

            try:
                response = self._send_command("*STB?")
                if response:
                    status_byte = int(response.strip())
                    
                    # Decode status byte based on documentation
                    status_info = {
                        "connected": True,
                        "emission_possible": bool(status_byte & 1),  # Bit 0
                        "modelocked": bool(status_byte & 2),         # Bit 1
                        "raw_status": status_byte
                    }
                    
                    return status_byte, status_info
                else:
                    return 0, {"connected": False, "error": "No response"}
                    
            except Exception as e:
                self.logger.error(f"Error getting status byte: {e}")
                return 0, {"connected": False, "error": str(e)}

    def get_enhanced_shutter_state(self) -> tuple[bool, bool]:
        """
        Get enhanced shutter state using both SHUTTER? and status byte.
        
        Returns
        -------
        tuple[bool, bool]
            (shutter_open, emission_possible) - Shutter state and laser emission status
        """
        with self._lock:
            if not self._connected:
                return False, False

            try:
                # Get shutter state
                shutter_response = self._send_command("SHUTTER?")
                shutter_open = False
                if shutter_response:
                    shutter_open = shutter_response.strip() == "1"
                
                # Get emission status from status byte
                _, status_info = self.get_status_byte()
                emission_possible = status_info.get("emission_possible", False)
                
                return shutter_open, emission_possible
                
            except Exception as e:
                self.logger.error(f"Error getting enhanced shutter state: {e}")
                return False, False

    @property
    def connected(self) -> bool:
        """Check if connected to laser."""
        return self._connected

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self.mock_mode
