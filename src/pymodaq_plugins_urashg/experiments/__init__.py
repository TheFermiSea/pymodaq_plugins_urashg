"""
PyMoDAQ URASHG Experiments Module

This module contains specialized scientific experiment workflows for μRASHG
(micro Rotational Anisotropy Second Harmonic Generation) microscopy measurements.

NOTE: This experiments module is part of the pymodaq_plugins_urashg package and
provides domain-specific measurement protocols for polarimetric SHG microscopy.
While PyMoDAQ plugins typically focus on hardware drivers, this package includes
these experiments due to their tight integration with the URASHG hardware ecosystem.

The experiments are designed to work with the URASHGMicroscopyExtension and provide:
- Calibration workflows for multi-device polarimetric systems
- Complex measurement protocols requiring hardware coordination
- Scientific analysis tools specific to RASHG techniques

Available Experiment Classes:
- EOMCalibrationExperiment: Laser power control calibration with PID feedback
- ElliptecCalibrationExperiment: Multi-rotator polarization alignment and Malus law fitting
- VariableAttenuatorCalibrationExperiment: Continuous power control calibration
- PDSHGExperiment: Power-dependent RASHG measurements with real-time analysis
- BasicURASHGExperiment: Complete 4D μRASHG data collection with camera integration
- WavelengthDependentRASHGExperiment: Spectroscopic RASHG measurements

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

from .base_experiment import URASHGBaseExperiment
from .elliptec_calibration import ElliptecCalibrationExperiment
from .eom_calibration import EOMCalibrationExperiment
from .pdshg_experiment import PDSHGExperiment
from .variable_attenuator_calibration import VariableAttenuatorCalibrationExperiment

# Placeholder imports for future implementations
try:
    from .basic_urashg_experiment import BasicURASHGExperiment
except NotImplementedError:
    BasicURASHGExperiment = None

try:
    from .wavelength_dependent_rashg import WavelengthDependentRASHGExperiment
except NotImplementedError:
    WavelengthDependentRASHGExperiment = None

__all__ = [
    "URASHGBaseExperiment",
    "EOMCalibrationExperiment",
    "ElliptecCalibrationExperiment",
    "VariableAttenuatorCalibrationExperiment",
    "PDSHGExperiment",
    # 'BasicURASHGExperiment',  # Future implementation
    # 'WavelengthDependentRASHGExperiment'  # Future implementation
]

# Implemented experiments (ready for use)
IMPLEMENTED_EXPERIMENTS = [
    "URASHGBaseExperiment",
    "EOMCalibrationExperiment",
    "ElliptecCalibrationExperiment",
    "VariableAttenuatorCalibrationExperiment",
    "PDSHGExperiment",
]

# Future experiments (placeholders)
FUTURE_EXPERIMENTS = ["BasicURASHGExperiment", "WavelengthDependentRASHGExperiment"]

# Module metadata
__version__ = "1.0.0"
__author__ = "PyMoDAQ Plugin Development Team"
__license__ = "MIT"

# Package integration note
INTEGRATION_NOTE = """
This experiments module is included in the pymodaq_plugins_urashg package due to
the specialized nature of RASHG measurements which require tight coordination between
multiple hardware devices and complex measurement protocols. These are not general-purpose
experiments but domain-specific workflows for polarimetric SHG microscopy.
"""
