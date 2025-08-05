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
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "PyMoDAQ Plugin Development Team"
__email__ = "contact@pymodaq.org"
__license__ = "MIT"

# Hardware abstraction layers
from .hardware import urashg

__all__ = ["__version__", "__author__", "__email__", "__license__", "urashg"]
