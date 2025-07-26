# -*- coding: utf-8 -*-
"""
Newport 1830-C optical power meter controller.

Hardware-level communication layer for Newport 1830-C power meter.
Provides clean interface for PyMoDAQ plugin.
"""

import time
import serial
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class Newport1830CController:
    """
    Hardware controller for Newport 1830-C optical power meter.
    
    Handles serial communication and basic device control.
    Based on original working implementation from ~/.qudi_urashg.
    """
    
    def __init__(self, port: str = '/dev/ttyUSB2', baudrate: int = 9600, timeout: float = 2.0):
        """Initialize controller with connection parameters."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        
        # Current device settings
        self._current_wavelength = 800.0
        self._current_units = 'W'
        self._current_range = 'Auto'
        
        logger.info(f"Newport1830C controller initialized for {port}")

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
            
            # Open serial connection
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout
            )
            
            # Test basic communication
            test_commands = ['W?', 'U?', 'D?']
            working_commands = []
            
            for cmd in test_commands:
                response = self._send_command(cmd)
                if response is not None:
                    working_commands.append(cmd)
                    logger.debug(f"Command {cmd} -> {response}")
            
            if not working_commands:
                raise ConnectionError("No response from Newport 1830-C - check device and calibration module")
            
            self._connected = True
            logger.info(f"Newport 1830-C connected successfully ({len(working_commands)}/{len(test_commands)} commands working)")
            
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

    def _send_command(self, command: str, expect_response: bool = True) -> Optional[str]:
        """
        Send command to power meter and get response.
        
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
            
            # Send command (Newport 1830-C uses LF termination)
            cmd_bytes = (command + '\n').encode('ascii')
            self._serial.write(cmd_bytes)
            self._serial.flush()
            
            if expect_response:
                time.sleep(0.5)  # Give device time to respond
                response = self._serial.read(1000).decode('ascii', errors='ignore').strip()
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
            self.set_units('W')
            
            # Set auto range
            self.set_power_range('Auto')
            
            # Set medium filter speed
            self.set_filter_speed('Medium')
            
            # Enable measurements
            self._send_command('G1', expect_response=False)  # Go (start measurements)
            
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
                
            response = self._send_command('D?')
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
                
            response = self._send_command(f'W{int(wavelength)}', expect_response=False)
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
                
            response = self._send_command('W?')
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
                
            if units == 'W':
                cmd = 'U1'  # Watts
            elif units == 'dBm':
                cmd = 'U3'  # dBm
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
                
            response = self._send_command('U?')
            if response:
                response = response.strip()
                if response == '1':
                    self._current_units = 'W'
                elif response == '3':
                    self._current_units = 'dBm'
                
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
                
            if power_range == 'Auto':
                cmd = 'R0'  # Auto range
            elif power_range.startswith('Range '):
                range_num = power_range.split()[-1]
                cmd = f'R{range_num}'
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
                
            speed_map = {'Slow': 'F1', 'Medium': 'F2', 'Fast': 'F3'}
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
            response1 = self._send_command('Z1', expect_response=False)
            
            # Wait for adjustment to complete
            time.sleep(2.0)
            
            # Turn zero function off
            response2 = self._send_command('Z0', expect_response=False)
            
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
            'model': 'Newport 1830-C',
            'port': self.port,
            'connected': self._connected,
            'wavelength': self._current_wavelength,
            'units': self._current_units,
            'range': self._current_range
        }
        
        if self._connected:
            # Get current readings
            power = self.get_power()
            if power is not None:
                info['current_power'] = power
                
        return info

    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.disconnect()
        except Exception:
            pass


if __name__ == '__main__':
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
            print(f"DATA: Average power ({len(readings)} readings): {avg_power:.6f} {controller.get_units()}")
        
        controller.disconnect()
        print("[OK] Disconnected")
        
    else:
        print("[ERROR] Failed to connect to Newport 1830-C")
        print("   - Check device is connected to /dev/ttyUSB2")
        print("   - Check calibration module is attached")
        print("   - Check device power")