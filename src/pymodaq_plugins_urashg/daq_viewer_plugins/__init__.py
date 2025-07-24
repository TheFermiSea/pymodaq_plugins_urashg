"""
PyMoDAQ Viewer Plugins for URASHG Microscopy

This module contains all DAQ_Viewer plugins for detection systems in the URASHG microscope:
- Photometrics Prime BSI sCMOS camera for SHG signal detection
- Future: Photodiode plugins for laser power monitoring
- Future: Spectrometer plugins for spectral analysis

Each plugin inherits from DAQ_Viewer_base and implements the standard PyMoDAQ detector interface
with hardware-specific acquisition logic, data processing, and real-time analysis capabilities.
"""

from .plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI

__all__ = [
    "DAQ_2DViewer_PrimeBSI",
]
