# -*- coding: utf-8 -*-
"""
μRASHG PyMoDAQ Extensions

This module contains PyMoDAQ extensions for URASHG (micro Rotational Anisotropy
Second Harmonic Generation) experiments following PyMoDAQ 5.x standards.

PyMoDAQ-Compliant Architecture:
- Single primary extension for multi-device coordination
- Integrated experiment workflows within extensions
- Proper PyMoDAQ extension patterns and lifecycle management
- No wrapper extensions around standalone experiments

Available Extensions:
- URASHGMicroscopyExtension: Comprehensive URASHG microscopy system control

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

# Primary extension metadata
EXTENSION_NAME = 'μRASHG Microscopy System'
EXTENSION_CLASS = 'URASHGMicroscopyExtension'

__all__ = [
    'URASHGMicroscopyExtension',
]

# Import primary extension for PyMoDAQ discovery
try:
    from .urashg_microscopy_extension import URASHGMicroscopyExtension

except ImportError as e:
    # Graceful handling for development/testing
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import URASHG microscopy extension: {e}")
    URASHGMicroscopyExtension = None

__version__ = "1.0.0"
__author__ = "PyMoDAQ Plugin Development Team"
