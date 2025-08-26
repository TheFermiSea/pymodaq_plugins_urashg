"""
Hardware Device Scanner for URASHG System

Automatically detects and identifies connected hardware devices by testing
communication patterns on available serial ports.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


class DeviceScanner:
    """
    Automatically scan and identify connected hardware devices.

    Tests each available serial port with device-specific communication
    patterns to identify which device is connected where.
    """

    # Device identification patterns
    DEVICE_PATTERNS = {
        "maitai": {
            "test_commands": ["?", "*IDN?", "READ:POW?"],
            "response_patterns": ["MaiTai", "Spectra-Physics", "POWER"],
            "baudrates": [9600, 19200, 115200],  # ✅ FIXED: 9600 first (correct baudrate)
            "timeout": 2.0,
        },
        "elliptec": {
            "test_commands": ["2in", "3in", "8in", "0in"],  # Device info commands for different addresses
            "response_patterns": ["ELL14", "ELL20", "Position"],
            "baudrates": [9600],  # Standard baudrate for Elliptec
            "timeout": 1.0,
        },
        "newport": {
            "test_commands": ["*IDN?", "PM:POWER?", "PM:LAMBDA?"],
            "response_patterns": ["Newport", "1830", "POWER"],
            "baudrates": [9600],  # Standard baudrate for Newport power meters
            "timeout": 2.0,
        },
        "esp300": {
            "test_commands": ["*IDN?", "VE?", "ID?"],
            "response_patterns": ["ESP300", "Newport", "Version"],
            "baudrates": [19200, 9600, 57600],  # ✅ FIXED: 19200 first (Newport standard)
            "timeout": 2.0,
        },
    } = {
        "maitai": {
            "test_commands": ["?", "*IDN?", "READ:POW?"],
            "response_patterns": ["MaiTai", "Spectra-Physics", "POWER"],
            "baudrates": [115200, 9600, 19200],
            "timeout": 2.0,
        },
        "esp300": {
            "test_commands": ["*IDN?", "ID?", "VE?"],
            "response_patterns": ["ESP300", "Newport", "ESP"],
            "baudrates": [19200, 9600, 38400],
            "timeout": 3.0,
        },
        "elliptec": {
            "test_commands": ["2in", "3in", "8in", "0in"],
            "response_patterns": ["ELL14", "Thorlabs", "PO"],
            "baudrates": [9600, 19200],
            "timeout": 2.0,
        },
        "newport1830c": {
            "test_commands": ["*IDN?", "PM:POWER?", "PM:LAMBDA?"],
            "response_patterns": ["1830-C", "Newport", "POWER METER"],
            "baudrates": [9600, 19200],
            "timeout": 2.0,
        },
    }

    def __init__(self):
        self.detected_devices = {}
        self.available_ports = []

    def scan_available_ports(self) -> List[Dict]:
        """
        Scan for available serial ports with hardware information.

        Returns:
            List of port dictionaries with hardware info
        """
        ports = []
        for port_info in serial.tools.list_ports.comports():
            port_dict = {
                "device": port_info.device,
                "description": port_info.description,
                "manufacturer": getattr(port_info, "manufacturer", "Unknown"),
                "product": getattr(port_info, "product", "Unknown"),
                "vid": getattr(port_info, "vid", None),
                "pid": getattr(port_info, "pid", None),
                "serial_number": getattr(port_info, "serial_number", "Unknown"),
            }
            ports.append(port_dict)

        self.available_ports = ports
        logger.info(f"Found {len(ports)} available serial ports")
        return ports

    def test_device_on_port(self, port: str, device_type: str) -> bool:
        """
        Test if a specific device type responds on a given port.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0')
            device_type: Device type key from DEVICE_PATTERNS

        Returns:
            True if device responds with expected pattern
        """
        if device_type not in self.DEVICE_PATTERNS:
            return False

        pattern = self.DEVICE_PATTERNS[device_type]

        for baudrate in pattern["baudrates"]:
            try:
                with serial.Serial(
                    port,
                    baudrate=baudrate,
                    timeout=pattern["timeout"],
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                ) as ser:

                    # Clear buffers
                    ser.flushInput()
                    ser.flushOutput()
                    time.sleep(0.1)

                    # Test each command
                    for cmd in pattern["test_commands"]:
                        try:
                            # Send command
                            cmd_bytes = (cmd + "\r\n").encode("ascii")
                            ser.write(cmd_bytes)
                            time.sleep(0.5)

                            # Read response
                            response = ser.read(100).decode("ascii", errors="ignore")

                            # Check for expected patterns
                            for expected in pattern["response_patterns"]:
                                if expected.lower() in response.lower():
                                    logger.info(
                                        f"Device {device_type} detected on {port} (baudrate: {baudrate})"
                                    )
                                    logger.debug(f"Response: {response.strip()}")
                                    return True

                        except Exception as e:
                            logger.debug(f"Command {cmd} failed on {port}: {e}")
                            continue

            except Exception as e:
                logger.debug(f"Failed to open {port} at {baudrate}: {e}")
                continue

        return False

    def scan_all_devices(self) -> Dict[str, str]:
        """
        Scan all available ports for all known device types.

        Returns:
            Dictionary mapping device_type -> port_path
        """
        self.scan_available_ports()
        self.detected_devices = {}

        logger.info("Starting comprehensive device scan...")

        # Get list of actual serial ports
        port_paths = [
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/ttyUSB2",
            "/dev/ttyUSB3",
            "/dev/ttyUSB4",
            "/dev/ttyUSB5",
            "/dev/ttyUSB6",
            "/dev/ttyS0",
            "/dev/ttyS1",
        ]

        # Filter to only existing ports
        existing_ports = [p for p in port_paths if self._port_exists(p)]

        logger.info(f"Testing {len(existing_ports)} ports: {existing_ports}")

        for device_type in self.DEVICE_PATTERNS.keys():
            logger.info(f"Scanning for {device_type}...")

            for port in existing_ports:
                if self.test_device_on_port(port, device_type):
                    self.detected_devices[device_type] = port
                    logger.info(f"✓ {device_type} found on {port}")
                    break
            else:
                logger.warning(f"✗ {device_type} not found on any port")

        return self.detected_devices

    def _port_exists(self, port_path: str) -> bool:
        """Check if a port exists and is accessible."""
        try:
            with serial.Serial(port_path, timeout=0.1):
                pass
            return True
        except:
            return False

    def get_device_port(self, device_type: str) -> Optional[str]:
        """
        Get the detected port for a specific device type.

        Args:
            device_type: Device type (maitai, esp300, elliptec, newport1830c)

        Returns:
            Port path if detected, None otherwise
        """
        return self.detected_devices.get(device_type)

    def print_scan_results(self):
        """Print a formatted summary of the scan results."""
        print("\n" + "=" * 50)
        print("HARDWARE DEVICE SCAN RESULTS")
        print("=" * 50)

        if not self.detected_devices:
            print("No devices detected!")
            return

        for device_type, port in self.detected_devices.items():
            print(f"{device_type.upper():15} -> {port}")

        print("\nMissing devices:")
        all_devices = set(self.DEVICE_PATTERNS.keys())
        found_devices = set(self.detected_devices.keys())
        missing = all_devices - found_devices

        if missing:
            for device in missing:
                print(f"  - {device}")
        else:
            print("  None - all devices detected!")

        print("=" * 50)


def scan_hardware() -> Dict[str, str]:
    """
    Convenience function to scan for all hardware devices.

    Returns:
        Dictionary mapping device_type -> port_path
    """
    scanner = DeviceScanner()
    return scanner.scan_all_devices()


if __name__ == "__main__":
    # Test the scanner
    logging.basicConfig(level=logging.INFO)
    scanner = DeviceScanner()
    results = scanner.scan_all_devices()
    scanner.print_scan_results()
