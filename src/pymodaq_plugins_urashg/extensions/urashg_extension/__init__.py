# -*- coding: utf-8 -*-
"""
Entry Point Package for μRASHG Microscopy Extension

This package serves as the entry point for PyMoDAQ's extension discovery system.
It re-exports the URASHGMicroscopyExtension class to work around PyMoDAQ 5.1.0a0's
entry point parsing bug that doesn't handle the standard module:attribute format.

This allows PyMoDAQ to discover and load the extension using the standard
PyMoDAQ extension framework instead of requiring standalone launchers.
"""

# Import and re-export the extension class
from ..urashg_microscopy_extension import URASHGMicroscopyExtension

# Make the extension class available at package level
__all__ = ['URASHGMicroscopyExtension']

# Package metadata for PyMoDAQ discovery
__version__ = "1.0.0"
__author__ = "μRASHG Development Team"
__description__ = "Complete polarimetric SHG measurements with multi-device coordination"
