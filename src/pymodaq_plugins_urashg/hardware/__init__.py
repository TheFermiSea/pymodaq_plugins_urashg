"""
URASHG Hardware Control Module

This module provides comprehensive hardware control interfaces for the URASHG
(micro Rotational Anisotropy Second Harmonic Generation) microscope system.

The module implements low-level device controllers and high-level system coordination
for all major hardware components in the μRASHG setup.

Hardware Controllers:
==================

RedPitayaController:
    FPGA-based PID controller for laser power stabilization
    - Direct memory-mapped register access (base: 0x40300000)
    - Real-time PID parameter adjustment
    - Error signal monitoring and diagnostics
    - Thread-safe operation for PyMoDAQ integration

ElliptecController:
    Multi-axis controller for Thorlabs ELL14 rotation mounts
    - Serial communication with multiple devices
    - Polarization state presets and calibration
    - Coordinated movement for complex polarization configurations
    - Home positioning and angle accuracy validation

CameraController:
    Photometrics Prime BSI sCMOS camera interface
    - PyVCAM library integration
    - Hardware ROI support for efficient acquisition
    - Real-time background subtraction
    - Multiple data export formats

MaiTaiController:
    MaiTai ultrafast laser control interface
    - EOM power control and modulation
    - Laser status monitoring
    - Safety interlocks and error handling
    - Power stabilization coordination with Red Pitaya

URASHGSystem:
    High-level system coordinator
    - Unified initialization and configuration
    - Inter-device synchronization
    - System health monitoring
    - Automated calibration routines

Usage Examples:
==============

Basic Hardware Initialization:
    from pymodaq_plugins_urashg.hardware.urashg import URASHGSystem

    system = URASHGSystem()
    system.initialize_all_hardware()
    system.run_system_diagnostics()

Individual Device Control:
    from pymodaq_plugins_urashg.hardware.urashg import RedPitayaController

    rp = RedPitayaController(ip_address="192.168.1.100")
    rp.connect()
    rp.set_pid_parameters(kp=0.1, ki=0.01, kd=0.001)
    rp.set_power_setpoint(100.0)  # mW

Polarization Control:
    from pymodaq_plugins_urashg.hardware.urashg import ElliptecController

    elliptec = ElliptecController(
        ports={"QWP": "COM3", "HWP_Inc": "COM4", "HWP_Ana": "COM5"}
    )
    elliptec.connect_all()
    elliptec.set_polarization_state("linear_h")
    elliptec.rotate_analyzer(45.0)

Camera Acquisition:
    from pymodaq_plugins_urashg.hardware.urashg import CameraController

    camera = CameraController()
    camera.initialize()
    camera.set_roi(x=500, y=500, width=100, height=100)
    frame, intensity = camera.acquire_with_roi_integration()

Error Handling:
===============

All controllers implement comprehensive error handling with custom exceptions:
- HardwareConnectionError: Communication failures
- HardwareConfigurationError: Invalid parameter settings
- HardwareTimeoutError: Operation timeout failures
- HardwareSafetyError: Safety interlock violations

Configuration Management:
=========================

Hardware configurations can be saved and loaded:
    system.save_configuration("rashg_config_001.yaml")
    system.load_configuration("rashg_config_001.yaml")

Thread Safety:
=============

All controllers are designed for thread-safe operation with PyMoDAQ:
- Mutex protection for shared resources
- Atomic parameter updates
- Safe shutdown procedures
- Exception propagation to main thread
"""

from .camera_utils import CameraController, CameraError

# Import utility functions and constants
from .constants import (
    CAMERA_DEFAULT_SETTINGS,
    ELLIPTEC_BAUD_RATE,
    MAITAI_COMMUNICATION_SETTINGS,
    PID_REGISTER_OFFSETS,
    REDPITAYA_BASE_ADDRESS,
)
from .elliptec_wrapper import ElliptecController, ElliptecError
from .maitai_control import MaiTaiController, MaiTaiError

# Import all hardware controllers
try:
    from .redpitaya_control import RedPitayaController, RedPitayaError

    REDPITAYA_AVAILABLE = True
except ImportError as e:
    # RedPitaya/PyRPL not available - provide mock classes
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"RedPitaya control not available ({e}), using mock classes for development"
    )

    class RedPitayaController:
        """Mock RedPitaya controller for development without PyRPL"""

        def __init__(self, *args, **kwargs):
            pass

    class RedPitayaError(Exception):
        """Mock RedPitaya error for development"""

        pass

    REDPITAYA_AVAILABLE = False

# Import system coordinator
from .system_control import SystemError, URASHGSystem
from .utils import (
    calculate_polarization_matrix,
    convert_fpga_to_physical_units,
    convert_physical_to_fpga_units,
    estimate_measurement_time,
    validate_hardware_configuration,
)

# Export all public interfaces
__all__ = [
    # Main controllers
    "RedPitayaController",
    "ElliptecController",
    "CameraController",
    "MaiTaiController",
    "URASHGSystem",
    # Exception classes
    "RedPitayaError",
    "ElliptecError",
    "CameraError",
    "MaiTaiError",
    "SystemError",
    # Constants and utilities
    "REDPITAYA_BASE_ADDRESS",
    "PID_REGISTER_OFFSETS",
    "ELLIPTEC_BAUD_RATE",
    "CAMERA_DEFAULT_SETTINGS",
    "MAITAI_COMMUNICATION_SETTINGS",
    "validate_hardware_configuration",
    "convert_physical_to_fpga_units",
    "convert_fpga_to_physical_units",
    "calculate_polarization_matrix",
    "estimate_measurement_time",
]

# Version and metadata
__version__ = "0.1.0"
__author__ = "PyMoDAQ Plugin Development Team"
__maintainer__ = "PyMoDAQ Plugin Development Team"
__email__ = "squires.b@gmail.com"

# Hardware compatibility matrix
HARDWARE_COMPATIBILITY = {
    "red_pitaya": {
        "supported_models": ["STEMlab 125-14", "STEMlab 125-10"],
        "min_firmware_version": "0.95",
        "fpga_base_address": 0x40300000,
        "communication_protocol": "TCP/IP + Memory Mapping",
        "tested_os_versions": ["Ubuntu 16.04", "Debian 9"],
    },
    "thorlabs_ell14": {
        "supported_models": ["ELL14", "ELL14K"],
        "communication_protocol": "Serial RS-232",
        "baud_rate": 9600,
        "max_devices_per_bus": 16,
        "position_accuracy": "±0.01°",
        "tested_firmware": ["v1.0.0", "v1.1.0"],
    },
    "photometrics_camera": {
        "supported_models": ["Prime BSI", "Prime BSI Express"],
        "interface": "PyVCAM",
        "min_pvcam_version": "3.0",
        "communication": ["USB 3.0", "PCIe"],
        "max_frame_rate": {"full_frame": "50 Hz", "roi": "200 Hz"},
        "bit_depth": 16,
    },
    "maitai_laser": {
        "supported_models": ["MaiTai eHP", "MaiTai HP"],
        "control_interface": "EOM",
        "communication": ["Serial", "Ethernet"],
        "power_stability": "<1% RMS",
        "response_time": "<10 ms",
    },
}

# System requirements and dependencies
SYSTEM_REQUIREMENTS = {
    "python_version": ">=3.8",
    "pymodaq_version": ">=4.0.0",
    "operating_systems": ["Windows 10/11", "Ubuntu 18.04+", "Debian 9+"],
    "hardware_requirements": {
        "ram": "8 GB minimum, 16 GB recommended",
        "storage": "1 GB for software, 100+ GB for data",
        "usb_ports": "3x USB 2.0 minimum for Elliptec controllers",
        "network": "Gigabit Ethernet for Red Pitaya communication",
    },
}

# Default configuration templates
DEFAULT_CONFIGURATIONS = {
    "standard_rashg": {
        "description": "Standard μRASHG microscopy configuration",
        "laser_power_mw": 100.0,
        "camera_exposure_ms": 100.0,
        "polarization_step_degrees": 5.0,
        "angle_range_degrees": (-45, 45),
        "averaging_frames": 3,
    },
    "high_speed": {
        "description": "High-speed acquisition for dynamic measurements",
        "laser_power_mw": 150.0,
        "camera_exposure_ms": 10.0,
        "polarization_step_degrees": 10.0,
        "angle_range_degrees": (-30, 30),
        "averaging_frames": 1,
    },
    "high_precision": {
        "description": "High-precision measurements for detailed analysis",
        "laser_power_mw": 80.0,
        "camera_exposure_ms": 500.0,
        "polarization_step_degrees": 1.0,
        "angle_range_degrees": (-90, 90),
        "averaging_frames": 10,
    },
}

# Logging configuration
import logging

# Create logger for hardware module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler if none exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

logger.info("URASHG Hardware Control Module initialized")
logger.info(f"Module version: {__version__}")
logger.info(f"Supported hardware: {list(HARDWARE_COMPATIBILITY.keys())}")
