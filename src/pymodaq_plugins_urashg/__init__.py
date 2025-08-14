# -*- coding: utf-8 -*-
"""
PyMoDAQ Plugin Package for URASHG
(micro Rotational Anisotropy Second Harmonic Generation) Microscopy

This package provides PyMoDAQ plugins for controlling a complete μRASHG
microscope system including:
- MaiTai laser with EOM power control
- Red Pitaya FPGA-based PID control for laser stabilization
- Thorlabs ELL14 motorized rotation mounts for polarization control
- Photometrics Prime BSI sCMOS camera for SHG detection
- Galvo mirrors for beam scanning (future integration)

The package follows PyMoDAQ's modular architecture with separate plugins for:
- DAQ_Move: Actuators (laser power, polarization optics, sample positioning)
- DAQ_Viewer: Detectors (camera, photodiodes)
- Hardware: Low-level device control libraries

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

# Handle missing PyMoDAQ dependencies gracefully for CI/test environments
try:
    from pymodaq_utils.logger import get_module_name, set_logger
    from pymodaq_utils.utils import PackageNotFoundError, get_version

    from .utils import Config

    config = Config()
    try:
        __version__ = get_version(__package__)
    except PackageNotFoundError:
        __version__ = "0.0.0dev"

    # Hardware abstraction layers
    from .hardware import urashg

    __all__ = ["__version__", "config", "urashg"]

except ImportError as e:
    # PyMoDAQ not available - minimal fallback for CI/testing
    import logging

    logging.warning(f"PyMoDAQ not available: {e}. Using minimal fallback.")

    __version__ = "0.0.0dev"
    config = None
    urashg = None

    # Mock logger functions
    def get_module_name(name):
        return name.split(".")[-1] if "." in name else name

    def set_logger(name, level=logging.INFO, add_to_console=True, **kwargs):
        return logging.getLogger(name)

    __all__ = ["__version__", "config", "urashg", "get_module_name", "set_logger"]
