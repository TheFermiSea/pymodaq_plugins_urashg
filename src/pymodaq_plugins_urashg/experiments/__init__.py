"""
PyMoDAQ Experiments for μRASHG (micro Rotational Anisotropy Second Harmonic Generation)

This module provides a comprehensive suite of PyMoDAQ experiments for advanced 
polarimetric SHG measurements with precise control over:
- Laser wavelength and power via EOM control
- Multi-rotator polarization states (QWP and dual HWP system)
- 2D camera detection with ROI support
- Real-time calibration and feedback control

Available Experiments:
- EOMCalibrationExperiment: PID-based laser power calibration
- ElliptecCalibrationExperiment: Rotator alignment and Malus law fitting
- VariableAttenuatorCalibrationExperiment: Power control calibration
- PDSHGExperiment: Power-dependent RASHG measurements
- BasicURASHGExperiment: Full 4D μRASHG data collection
- WavelengthDependentRASHGExperiment: Spectroscopic measurements

Author: PyMoDAQ Plugin Development Team
Created: August 2025
"""

from .base_experiment import URASHGBaseExperiment
from .eom_calibration import EOMCalibrationExperiment
from .elliptec_calibration import ElliptecCalibrationExperiment
from .variable_attenuator_calibration import VariableAttenuatorCalibrationExperiment
from .pdshg_experiment import PDSHGExperiment

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
    'URASHGBaseExperiment',
    'EOMCalibrationExperiment', 
    'ElliptecCalibrationExperiment',
    'VariableAttenuatorCalibrationExperiment',
    'PDSHGExperiment',
    # 'BasicURASHGExperiment',  # Future implementation
    # 'WavelengthDependentRASHGExperiment'  # Future implementation
]

# Implemented experiments (ready for use)
IMPLEMENTED_EXPERIMENTS = [
    'URASHGBaseExperiment',
    'EOMCalibrationExperiment',
    'ElliptecCalibrationExperiment', 
    'VariableAttenuatorCalibrationExperiment',
    'PDSHGExperiment'
]

# Future experiments (placeholders)
FUTURE_EXPERIMENTS = [
    'BasicURASHGExperiment',
    'WavelengthDependentRASHGExperiment'
]

__version__ = "1.0.0"
__author__ = "PyMoDAQ URASHG Development Team"