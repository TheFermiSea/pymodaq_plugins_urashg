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
    "URASHG_EOM_Calibration",
    "URASHG_Elliptec_Calibration",
    "URASHG_Variable_Attenuator",
    "URASHG_PDSHG_Experiment",
    "URASHG_Basic_Experiment",
]

# Import all extensions for PyMoDAQ discovery
try:
    # Primary comprehensive extension
    from .basic_urashg_extension import URASHG_Basic_Experiment
    from .elliptec_calibration_extension import URASHG_Elliptec_Calibration

    # Legacy individual extensions
    from .eom_calibration_extension import URASHG_EOM_Calibration
    from .pdshg_experiment_extension import URASHG_PDSHG_Experiment
    from .urashg_microscopy_extension import URASHGMicroscopyExtension
    from .variable_attenuator_extension import URASHG_Variable_Attenuator

except ImportError as e:
    # Graceful handling for development/testing
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import all URASHG extensions: {e}")
