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

from pathlib import Path
from .utils import Config
from pymodaq_utils.utils import get_version, PackageNotFoundError
from pymodaq_utils.logger import set_logger, get_module_name

config = Config()
try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'

# Hardware abstraction layers
from .hardware import urashg

__all__ = ["__version__", "config", "urashg"]
