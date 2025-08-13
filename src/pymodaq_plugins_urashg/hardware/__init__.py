"""
Hardware Abstraction Layer for URASHG Microscopy System

This module provides low-level hardware control interfaces for all components
in the URASHG microscope system. The hardware layer abstracts device-specific
communication protocols and provides unified APIs for the PyMoDAQ plugins.

Hardware Components:
- Red Pitaya: FPGA-based PID controller with memory-mapped register access
- Thorlabs ELL14: Motorized rotation mounts with serial communication
- MaiTai Laser: Ultrafast laser with EOM power control
- Photometrics Prime BSI: sCMOS camera with PyVCAM interface

The hardware layer follows these design principles:
- Device-agnostic interfaces where possible
- Robust error handling and recovery
- Thread-safe operation for PyMoDAQ integration
- Comprehensive logging for debugging and monitoring
- Configuration management for different hardware variants

Usage:
    from pymodaq_plugins_urashg.hardware import urashg

    # Initialize hardware controllers
    redpitaya = urashg.RedPitayaController(ip_address="192.168.1.100")
    elliptec = urashg.ElliptecController(ports=["COM3", "COM4", "COM5"])
    camera = urashg.CameraController()

    # High-level system control
    system = urashg.URASHGSystem()
    system.initialize_all_hardware()
"""

# Import all hardware control modules
from . import urashg

# Make commonly used classes available at package level
from .urashg import (
    CameraController,
    ElliptecController,
    MaiTaiController,
    RedPitayaController,
    URASHGSystem,
)

__all__ = [
    "urashg",
    "RedPitayaController",
    "ElliptecController",
    "CameraController",
    "MaiTaiController",
    "URASHGSystem",
]

# Hardware compatibility information
SUPPORTED_HARDWARE = {
    "red_pitaya": {
        "models": ["STEMlab 125-14", "STEMlab 125-10"],
        "fpga_base_address": 0x40300000,
        "communication": "Ethernet/Memory-mapped",
    },
    "thorlabs_ell14": {
        "models": ["ELL14", "ELL14K"],
        "communication": "Serial/USB",
        "max_devices": 16,
    },
    "photometrics_camera": {
        "models": ["Prime BSI", "Prime BSI Express"],
        "communication": "USB 3.0/PCIe",
        "interface": "PyVCAM",
    },
    "maitai_laser": {
        "models": ["MaiTai eHP", "MaiTai HP"],
        "communication": "Serial/Ethernet",
        "control_interface": "EOM",
    },
}

# Version information
__version__ = "0.1.0"
__author__ = "PyMoDAQ Plugin Development Team"
