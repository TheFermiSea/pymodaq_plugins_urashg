#!/usr/bin/env python3
"""
Setup script for PyMoDAQ URASHG plugin testing environment

This script sets up a comprehensive testing environment for all PyMoDAQ plugins
in the URASHG microscopy system, including mock hardware simulation and
dependency management.
"""

import subprocess
import sys
import os
import importlib
from pathlib import Path


def check_python_version():
    """Ensure Python 3.8+ is being used"""
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8+ is required for PyMoDAQ v5")
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor} detected")


def install_pymodaq():
    """Install PyMoDAQ version 5 and core dependencies"""
    print("Installing PyMoDAQ v5...")

    packages = [
        "pymodaq>=5.0.0",
        "numpy>=1.20.0",
        "qtpy>=2.0.0",
        "pyserial>=3.5",
        "pytest>=6.0.0",
        "pytest-mock>=3.0.0",
        "unittest-mock",
    ]

    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"[OK] {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"[WARNING]  Warning: Failed to install {package}: {e}")
            # Continue with other packages


def setup_mock_modules():
    """Setup mock modules for hardware simulation"""
    print("Setting up mock hardware modules...")

    # Create mock modules directory
    mock_dir = Path(__file__).parent / "mock_modules"
    mock_dir.mkdir(exist_ok=True)

    # Create __init__.py for mock_modules
    (mock_dir / "__init__.py").write_text(
        '"""Mock hardware modules for PyMoDAQ plugin testing"""\n'
    )

    # Create mock serial module
    mock_serial_code = '''
"""Mock serial module for testing PyMoDAQ plugins without hardware"""

class SerialException(Exception):
    """Mock serial exception"""
    pass

EIGHTBITS = 8
PARITY_NONE = 'N'
STOPBITS_ONE = 1

class Serial:
    """Mock serial port for testing"""

    def __init__(self, port, baudrate=9600, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._buffer = b''
        self._write_history = []

    def write(self, data):
        """Mock write operation"""
        self._write_history.append(data)
        return len(data)

    def readline(self):
        """Mock readline - returns test responses"""
        if self._write_history:
            last_cmd = self._write_history[-1].decode('utf-8', errors='ignore').lower()

            # Elliptec device responses
            if 'in' in last_cmd:
                return b'2IN0F14290000602019050105016800000004000\r\n'
            elif 'gp' in last_cmd:
                return b'2PO00000000\r\n'
            elif 'gs' in last_cmd:
                return b'2GS00\r\n'
            elif 'ma' in last_cmd:
                return b'2MA\r\n'
            elif 'ho' in last_cmd:
                return b'2HO1\r\n'

            # MaiTai responses
            elif 'wavelength' in last_cmd:
                return b'800.0\r\n'
            elif 'power' in last_cmd:
                return b'1.5\r\n'
            elif 'stb' in last_cmd:
                return b'66\r\n'  # Status byte with modelocking

        return b'\r\n'

    def reset_input_buffer(self):
        """Mock buffer reset"""
        self._buffer = b''

    def close(self):
        """Mock close operation"""
        self.is_open = False
'''

    # Write mock serial module
    (mock_dir / "mock_serial.py").write_text(mock_serial_code)

    # Create mock PyVCAM module
    mock_pyvcam_code = '''
"""Mock PyVCAM module for camera testing"""

import numpy as np

class MockCamera:
    """Mock camera for testing"""

    def __init__(self):
        self.name = "Prime BSI Mock Camera"
        self.is_open = False
        self.sensor_size = (2048, 2048)
        self.roi = (0, 0, 2048, 2048)
        self.readout_ports = ["Port 1", "Port 2"]
        self.speed_table_size = 3
        self.gains = [1, 2, 4]
        self.readout_port = "Port 1"
        self.speed_table_index = 1
        self.gain = 1
        self.temp = -10.0
        self.temp_setpoint = -10
        self.trigger_mode = TriggerMode.INTERNAL
        self.clear_mode = ClearMode.PRE_SEQUENCE
        self.params = {}
        self.post_processing_features = []

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def get_frame(self, exp_time=100):
        """Generate mock frame data"""
        size = self.roi[2] * self.roi[3]
        # Generate realistic camera noise pattern
        frame = np.random.poisson(100, size) + np.random.normal(10, 5, size)
        return np.clip(frame, 0, 65535).astype(np.uint16)

    def get_param(self, param_id):
        """Get parameter value"""
        return self.params.get(param_id, 0)

    def set_param(self, param_id, value):
        """Set parameter value"""
        self.params[param_id] = value

    def get_pp_param(self, param_id):
        """Get post-processing parameter"""
        return 0

    def set_pp_param(self, param_id, value):
        """Set post-processing parameter"""
        pass

class Camera:
    """Mock Camera class"""

    @staticmethod
    def detect_camera():
        """Detect mock cameras"""
        yield MockCamera()

class TriggerMode:
    INTERNAL = "Internal"
    EXTERNAL = "External"

class ClearMode:
    PRE_SEQUENCE = "Pre-Sequence"
    POST_SEQUENCE = "Post-Sequence"

class Param:
    EXP_TIME = "exp_time"
    READOUT_PORT = "readout_port"
    PIX_TIME = "pix_time"
    GAIN_INDEX = "gain_index"
    TEMP_SETPOINT = "temp_setpoint"

class pvc:
    @staticmethod
    def init_pvcam():
        """Initialize mock PVCAM"""
        pass

    @staticmethod
    def uninit_pvcam():
        """Uninitialize mock PVCAM"""
        pass
'''

    # Write mock PyVCAM module
    (mock_dir / "mock_pyvcam.py").write_text(mock_pyvcam_code)

    print("[OK] Mock hardware modules created")


def validate_installation():
    """Validate that required components are properly installed"""
    print("Validating installation...")

    required_modules = [
        "numpy",
        "pytest",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"[OK] {module} available")
        except ImportError:
            missing_modules.append(module)
            print(f"ERROR: {module} not available")

    if missing_modules:
        print(f"[WARNING]  Missing modules: {', '.join(missing_modules)}")
        return False

    return True


def create_test_config():
    """Create test configuration file"""
    config_content = """
# PyMoDAQ URASHG Plugin Test Configuration

[test_settings]
mock_mode = true
verbose_output = true
timeout_seconds = 30

[elliptec_test]
test_axes = ["HWP_inc", "QWP", "HWP_ana"]
test_addresses = ["2", "3", "8"]
test_positions = [0.0, 45.0, 90.0, -45.0]
position_tolerance = 0.01

[maitai_test]
test_wavelengths = [700, 800, 900, 1000]
test_powers = [0.5, 1.0, 1.5, 2.0]
status_check_interval = 0.1

[camera_test]
test_exposures = [10, 50, 100, 500]
test_roi_sizes = [(100, 100), (500, 500), (1000, 1000)]
frame_timeout = 5.0

[mock_hardware]
elliptec_response_delay = 0.05
maitai_response_delay = 0.1
camera_frame_generation_time = 0.02
"""

    config_path = Path(__file__).parent / "test_config.ini"
    config_path.write_text(config_content)
    print(f"[OK] Test configuration created: {config_path}")


def main():
    """Main setup function"""
    print("=== PyMoDAQ URASHG Plugin Test Environment Setup ===")

    try:
        # Step 1: Check Python version
        check_python_version()

        # Step 2: Install PyMoDAQ and dependencies
        install_pymodaq()

        # Step 3: Setup mock modules
        setup_mock_modules()

        # Step 4: Create test configuration
        create_test_config()

        # Step 5: Validate installation
        if validate_installation():
            print("\n[SUCCESS] Test environment setup completed successfully!")
            print("\nNext steps:")
            print("1. Run individual plugin tests: python test_plugin_name.py")
            print("2. Run all tests: python run_all_tests.py")
            print("3. View test results in the console output")
            return 0
        else:
            print("\n[WARNING] Test environment setup completed with warnings")
            print("Some modules may not be available - tests may fail")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
