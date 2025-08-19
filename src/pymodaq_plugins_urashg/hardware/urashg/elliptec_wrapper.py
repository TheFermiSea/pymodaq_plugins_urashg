"""
Enhanced Elliptec Controller with Realistic Mock Implementation

This module provides comprehensive hardware abstraction for Thorlabs ELL14 rotation mounts
with realistic mock behavior that matches actual hardware responses.
"""

import logging
import time
import random
from threading import Lock
from typing import Dict, List, Optional


class ElliptecError(Exception):
    """Elliptec specific exception"""
    pass


class ElliptecController:
    """
    Hardware controller for Thorlabs Elliptec rotation mounts.

    Provides hardware abstraction layer between PyMoDAQ plugins and Elliptec devices
    with realistic mock behavior that closely mimics actual hardware responses.
    """

    # Device specifications
    units = "degrees"

    def __init__(
        self,
        port: str = "/dev/ttyUSB1",
        baudrate: int = 9600,
        timeout: float = 2.0,
        mount_addresses: str = "2,3,8",
        mock_mode: bool = False,
    ):
        """
        Initialize Elliptec controller.

        Parameters
        ----------
        port : str
            Serial port for device communication
        baudrate : int
            Serial communication baud rate
        timeout : float
            Communication timeout in seconds
        mount_addresses : str
            Comma-separated mount addresses (e.g., '2,3,8')
        mock_mode : bool
            Enable mock mode for testing without hardware
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.mock_mode = mock_mode
        self._connection = None
        self._connected = False
        self._lock = Lock()

        # Parse mount addresses
        self.mount_addresses = [addr.strip() for addr in mount_addresses.split(",")]
        self.axes = [f"Mount_{addr}" for addr in self.mount_addresses]

        # Current positions (degrees)
        self._positions = {addr: 0.0 for addr in self.mount_addresses}

        # Device parameters from working hardware tests
        self._pulses_per_rev = 23000  # ELL14 specification
        self._max_velocity = 64
        self._current_velocity = 60

        self.logger = logging.getLogger(__name__)
        self.logger.info(
            f"ElliptecController initialized: port={port}, mounts={mount_addresses}, mock={mock_mode}"
        )

    def connect(self) -> bool:
        """Establish connection to device."""
        if self.mock_mode:
            self.logger.info("Mock mode: Simulating connection to Elliptec device")
            self._connected = True
            return True

        try:
            import serial
            
            with self._lock:
                self._connection = serial.Serial(
                    self.port, self.baudrate, timeout=self.timeout
                )
                time.sleep(0.1)  # Device initialization delay

            # Test communication with first mount
            if self.mount_addresses:
                test_addr = self.mount_addresses[0]
                response = self._send_command(f"{test_addr}in")
                if response:
                    self.logger.info(
                        f"Successfully connected to Elliptec on {self.port}"
                    )
                    self._connected = True
                    return True
                else:
                    self.logger.error("No response from Elliptec device")
                    self._connected = False
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Elliptec: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Close connection to device."""
        if self.mock_mode:
            self.logger.info("Mock mode: Simulating disconnection")
            self._connected = False
            return

        try:
            with self._lock:
                if self._connection and self._connection.is_open:
                    self._connection.close()
                    self._connection = None
            self._connected = False
            self.logger.info("Disconnected from Elliptec device")
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")

    def _send_command(self, command: str):
        """Send command to device and return response with realistic simulation."""
        if self.mock_mode:
            # Realistic mock responses based on ELLx protocol documentation
            # Simulate communication delay
            time.sleep(random.uniform(0.05, 0.15))
            
            command_lower = command.lower().strip()
            
            # Parse command: address + instruction
            if len(command_lower) >= 3:
                address = command_lower[0]
                instruction = command_lower[1:]
            else:
                return b"ER01"  # Invalid command format
            
            # Validate address is in our configured mounts
            if address not in self.mount_addresses:
                return b"ER02"  # Invalid address
            
            # Handle specific commands with realistic responses
            if instruction == "in":
                # Device info command - return realistic device information
                # Format: ADDR + IN + device_type(2) + serial_number(8) + firmware(4) + year(4) + pulses_per_rev(8)
                device_responses = {
                    "2": b"2IN0E11400517202317000005A00",  # ELL14 rotator
                    "3": b"3IN0E11400284202115000005A00",  # ELL14 rotator  
                    "8": b"8IN0E11400609202317000005A00"   # ELL14 rotator
                }
                response = device_responses.get(address, b"ER03")
                self.logger.debug(f"Mock device info for mount {address}: {response}")
                return response
                
            elif instruction == "gp":
                # Get position command - return current mock position in hex format
                # Format: ADDR + PO + hex_position(8)
                current_pos_degrees = self._positions.get(address, 0.0)
                # Convert degrees to pulses (23000 pulses per revolution for ELL14)
                pulses = int((current_pos_degrees / 360.0) * self._pulses_per_rev)
                if pulses < 0:
                    pulses += 0x100000000  # Handle negative values
                hex_pos = f"{pulses:08X}"
                response = f"{address}PO{hex_pos}".encode('ascii')
                self.logger.debug(f"Mock position for mount {address}: {current_pos_degrees}° -> {response}")
                return response
                
            elif instruction == "gs":
                # Get status command - return status code
                # Format: ADDR + GS + status(2)
                # "00" = ready, "09" = moving, "0A" = homing, "0B" = homed, "0C" = tracking
                status_code = "00"  # Always ready in mock mode
                response = f"{address}GS{status_code}".encode('ascii')
                self.logger.debug(f"Mock status for mount {address}: {response}")
                return response
                
            elif instruction.startswith("ma"):
                # Move absolute command
                # Format: ADDR + ma + hex_position(8)
                if len(instruction) >= 10:  # "ma" + 8 hex chars
                    try:
                        hex_pos = instruction[2:10]
                        pulses = int(hex_pos, 16)
                        if pulses > 0x7FFFFFFF:  # Handle negative values
                            pulses -= 0x100000000
                        
                        # Convert pulses to degrees
                        degrees = (pulses / self._pulses_per_rev) * 360.0
                        
                        # Update mock position
                        self._positions[address] = degrees
                        
                        # Simulate movement delay based on distance
                        old_pos = self._positions.get(address, 0.0)
                        distance = abs(degrees - old_pos)
                        move_time = min(distance / 180.0, 2.0)  # Max 2 seconds for 180°
                        
                        self.logger.debug(f"Mock move absolute for mount {address}: {degrees}° (delay: {move_time:.1f}s)")
                        
                        # Return success (no response for move commands typically)
                        return b""
                    except ValueError:
                        return b"ER04"  # Invalid hex value
                else:
                    return b"ER05"  # Invalid command length
                    
            elif instruction.startswith("mr"):
                # Move relative command
                # Format: ADDR + mr + hex_offset(8)
                if len(instruction) >= 10:
                    try:
                        hex_offset = instruction[2:10]
                        pulses = int(hex_offset, 16)
                        if pulses > 0x7FFFFFFF:  # Handle negative values
                            pulses -= 0x100000000
                        
                        # Convert pulses to degrees
                        offset_degrees = (pulses / self._pulses_per_rev) * 360.0
                        
                        # Update mock position
                        current_pos = self._positions.get(address, 0.0)
                        new_pos = current_pos + offset_degrees
                        self._positions[address] = new_pos
                        
                        self.logger.debug(f"Mock move relative for mount {address}: {offset_degrees}° -> {new_pos}°")
                        return b""
                    except ValueError:
                        return b"ER06"  # Invalid hex value
                else:
                    return b"ER07"  # Invalid command length
                    
            elif instruction == "ho":
                # Home command - simulate homing process
                # Longer delay for homing (1-2 seconds realistic)
                time.sleep(random.uniform(0.5, 1.0))
                self._positions[address] = 0.0  # Reset to home position
                self.logger.debug(f"Mock homing complete for mount {address}")
                return b""  # No response for home command
                
            elif instruction.startswith("sv"):
                # Set velocity command
                # Format: ADDR + sv + hex_velocity(8)
                if len(instruction) >= 10:
                    try:
                        hex_vel = instruction[2:10]
                        velocity = int(hex_vel, 16)
                        self._current_velocity = min(velocity, self._max_velocity)
                        self.logger.debug(f"Mock set velocity for mount {address}: {self._current_velocity}")
                        return b""
                    except ValueError:
                        return b"ER08"  # Invalid velocity
                else:
                    return b"ER09"  # Invalid command length
                    
            elif instruction == "gv":
                # Get velocity command
                # Format: ADDR + GV + hex_velocity(8)
                hex_vel = f"{self._current_velocity:08X}"
                response = f"{address}GV{hex_vel}".encode('ascii')
                self.logger.debug(f"Mock get velocity for mount {address}: {response}")
                return response
                
            elif instruction == "st":
                # Stop command
                self.logger.debug(f"Mock stop command for mount {address}")
                return b""
                
            else:
                # Unknown command
                self.logger.warning(f"Mock: Unknown command '{instruction}' for mount {address}")
                return b"ER10"  # Unknown command

        # Real hardware communication (unchanged)
        if not self._connection or not self._connection.is_open:
            self.logger.error("Device not connected")
            return None

        try:
            with self._lock:
                # Clear buffers
                self._connection.flushInput()
                self._connection.flushOutput()

                # Send command with proper termination
                cmd_bytes = (command + "\r").encode("ascii")
                self._connection.write(cmd_bytes)
                time.sleep(0.3)  # Device processing time

                # Read response
                response = self._connection.read(100)

                if response:
                    self.logger.debug(f"Command '{command}' response: {response}")
                    return response
                else:
                    self.logger.warning(f"No response to command '{command}'")
                    return None

        except Exception as e:
            self.logger.error(f"Communication error for command '{command}': {e}")
            return None

    def get_position(self, mount_address: str):
        """Get current position of specified mount in degrees."""
        response = self._send_command(f"{mount_address}gp")

        if response:
            try:
                # Parse position from response (format: "XPOnnnnnnnn")
                response_str = response.decode("ascii").strip()
                if "PO" in response_str:
                    # Extract hex position value
                    hex_pos = response_str.split("PO")[1][:8]
                    # Convert to signed integer (pulses)
                    pulses = int(hex_pos, 16)
                    if pulses > 0x7FFFFFFF:  # Handle negative values
                        pulses -= 0x100000000

                    # Convert pulses to degrees
                    degrees = (pulses / self._pulses_per_rev) * 360.0

                    # Update cached position
                    self._positions[mount_address] = degrees

                    self.logger.debug(
                        f"Mount {mount_address} position: {degrees:.2f}degrees"
                    )
                    return degrees

            except Exception as e:
                self.logger.error(
                    f"Error parsing position for mount {mount_address}: {e}"
                )

        # Return cached position if communication failed
        return self._positions.get(mount_address, 0.0)

    def get_all_positions(self):
        """Get positions of all configured mounts."""
        positions = {}
        for addr in self.mount_addresses:
            pos = self.get_position(addr)
            if pos is not None:
                positions[addr] = pos
        return positions

    def move_absolute(self, mount_address: str, position_degrees: float) -> bool:
        """Move mount to absolute position in degrees."""
        try:
            # Convert degrees to pulses
            pulses = int((position_degrees / 360.0) * self._pulses_per_rev)

            # Format as 8-digit hex
            if pulses < 0:
                pulses += 0x100000000
            hex_pos = f"{pulses:08X}"

            # Send move command
            response = self._send_command(f"{mount_address}ma{hex_pos}")

            if response is not None:  # Empty response is success for move commands
                # Update cached position
                self._positions[mount_address] = position_degrees
                self.logger.info(
                    f"Mount {mount_address} moved to {position_degrees:.2f}degrees"
                )
                return True
            else:
                self.logger.error(f"Failed to move mount {mount_address}")
                return False

        except Exception as e:
            self.logger.error(f"Error moving mount {mount_address}: {e}")
            return False

    def move_relative(self, mount_address: str, offset_degrees: float) -> bool:
        """Move mount by relative offset in degrees."""
        current_pos = self.get_position(mount_address)
        if current_pos is not None:
            target_pos = current_pos + offset_degrees
            return self.move_absolute(mount_address, target_pos)
        return False

    def home(self, mount_address: str) -> bool:
        """Home specified mount."""
        # Send homing command (note: ho command doesn't return a response)
        try:
            if self.mock_mode:
                # Mock mode - simulate successful homing
                time.sleep(0.5)
                self._positions[mount_address] = 0.0
                self.logger.info(f"Mock: Mount {mount_address} homed")
                return True

            if not self._connection or not self._connection.is_open:
                self.logger.error("Device not connected")
                return False

            with self._lock:
                # Clear buffers
                self._connection.flushInput()
                self._connection.flushOutput()

                # Send homing command (no response expected)
                cmd_bytes = f"{mount_address}ho\r".encode("ascii")
                self._connection.write(cmd_bytes)
                self.logger.debug(f"Sent homing command: {mount_address}ho")

                # Wait for homing to complete (homing can take a few seconds)
                time.sleep(2.0)

                # Verify device is still responsive by getting device info
                self._connection.flushInput()
                info_cmd = f"{mount_address}in\r".encode("ascii")
                self._connection.write(info_cmd)
                time.sleep(0.5)
                response = self._connection.read(1000)

                if response and len(response) > 0:
                    # Reset cached position to 0 (home position)
                    self._positions[mount_address] = 0.0
                    self.logger.info(f"Mount {mount_address} homed successfully")
                    return True
                else:
                    self.logger.error(
                        f"Mount {mount_address} not responding after home command"
                    )
                    return False

        except Exception as e:
            self.logger.error(f"Error homing mount {mount_address}: {e}")
            return False

    def home_all(self) -> bool:
        """Home all configured mounts."""
        success = True
        for addr in self.mount_addresses:
            if not self.home(addr):
                success = False
        return success

    def get_device_info(self, mount_address: str = None):
        """Get device information for specified mount or all mounts."""
        if mount_address is None:
            # Return info for all mounts
            info_dict = {}
            for addr in self.mount_addresses:
                mount_info = self.get_device_info(addr)
                if mount_info:
                    info_dict[addr] = mount_info
            return {
                "model": "Thorlabs Elliptec",
                "port": self.port,
                "connected": self._connected,
                "mounts": info_dict,
                "num_mounts": len(self.mount_addresses),
            }

        # Get info for specific mount
        response = self._send_command(f"{mount_address}in")

        if response:
            try:
                info = response.decode("ascii").strip()
                self.logger.debug(f"Mount {mount_address} info: {info}")
                return info
            except Exception as e:
                self.logger.error(f"Error parsing device info: {e}")

        return None

    def is_connected(self) -> bool:
        """Check if device is connected."""
        if self.mock_mode:
            return self._connected

        return self._connection is not None and self._connection.is_open

    @property
    def connected(self) -> bool:
        """Check if connected to device."""
        return self.is_connected()

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self.mock_mode