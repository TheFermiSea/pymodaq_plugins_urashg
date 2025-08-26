# -*- coding: utf-8 -*-
"""
μRASHG PyMoDAQ Extensions

This module contains PyMoDAQ extensions for URASHG (micro Rotational Anisotropy
Second Harmonic Generation) experiments. All extensions are properly integrated
with the PyMoDAQ 5.x framework.

Available Extensions:
- URASHGMicroscopyExtension: Primary comprehensive multi-device coordination extension
- URASHG_EOM_Calibration: EOM power control calibration
- URASHG_Elliptec_Calibration: Rotator polarization calibration
- URASHG_Variable_Attenuator: Variable attenuator calibration
- URASHG_PDSHG_Experiment: Power-dependent RASHG measurements
- URASHG_Basic_Experiment: Full μRASHG measurements with camera
"""

# Extension metadata
EXTENSION_NAME = "μRASHG Microscopy System"
CLASS_NAME = "URASHGMicroscopyExtension"

__all__ = [
    "URASHGMicroscopyExtension",  # Primary extension
]

# Import available extensions for PyMoDAQ discovery
try:
    # Primary comprehensive extension
    from .urashg_microscopy_extension import URASHGMicroscopyExtension

except ImportError as e:
    # Graceful handling for development/testing
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import URASHG extensions: {e}")
