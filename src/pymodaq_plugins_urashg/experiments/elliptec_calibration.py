"""
Elliptec Rotator Calibration Experiment for μRASHG System

This module implements calibration procedures for the Thorlabs Elliptec rotation
mounts used in the μRASHG polarimetric system. The experiment performs:

1. Homing sequences to establish reference positions
2. Malus law fitting (cos²(θ)) for each rotator
3. Multi-rotator coordination and offset calibration
4. Polarization state verification and validation

Hardware Components:
- H800: Half-wave plate at 800nm (incident polarization control)
- H400: Half-wave plate at 400nm (analyzer polarization control)
- Q800: Quarter-wave plate at 800nm (ellipticity control)

Each rotator requires individual calibration to account for:
- Mechanical offset from optical axis
- Wavelength-dependent phase retardation
- Cross-coupling between rotators
- Power transmission characteristics

The calibration generates lookup tables and fitting parameters essential
for precise polarization control in all μRASHG experiments.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import h5py
import numpy as np
from pymodaq.utils.data import Axis, DataActuator, DataToExport, DataWithAxes
from pymodaq.utils.parameter import Parameter
from qtpy import QtCore, QtWidgets
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit

from .base_experiment import ExperimentError, ExperimentState, URASHGBaseExperiment

logger = logging.getLogger(__name__)


def malus_law(angle, amplitude, phase, offset):
    """
    Malus law function: I = A * cos²(θ - φ) + C

    Args:
        angle (array): Rotation angles in degrees
        amplitude (float): Maximum transmission amplitude
        phase (float): Phase offset (optical axis alignment) in degrees
        offset (float): Baseline transmission offset

    Returns:
        array: Transmitted power following Malus law
    """
    angle_rad = np.radians(angle - phase)
    return amplitude * np.cos(angle_rad) ** 2 + offset


def inverse_malus_law(power, amplitude, phase, offset):
    """
    Inverse Malus law to calculate angle from power.

    Args:
        power (float): Measured power
        amplitude (float): Amplitude parameter from fit
        phase (float): Phase parameter from fit
        offset (float): Offset parameter from fit

    Returns:
        float: Angle in degrees (primary solution)
    """
    if power < offset or power > (amplitude + offset):
        raise ValueError(
            f"Power {power} outside valid range [{offset}, {amplitude + offset}]"
        )

    normalized_power = (power - offset) / amplitude
    angle_rad = np.arccos(np.sqrt(np.clip(normalized_power, 0, 1)))
    angle_deg = np.degrees(angle_rad) + phase

    return angle_deg


class ElliptecCalibrationExperiment(URASHGBaseExperiment):
    """
    Elliptec Rotator Calibration Experiment for precise polarization control.

    This experiment calibrates all three Elliptec rotation mounts in the μRASHG
    system to establish accurate polarization state control. The calibration process:

    1. Home all rotators to establish reference positions
    2. Individual rotator characterization with Malus law fitting
    3. Cross-rotator interference and offset measurement
    4. Multi-wavelength calibration for chromatic dispersion
    5. Polarization state verification and validation

    The calibration generates several critical data products:
    - Individual rotator Malus law parameters (A, φ, C)
    - Cross-rotator offset and interference coefficients
    - Wavelength-dependent correction factors
    - Polarization state lookup tables
    - Runtime-ready calibration files

    Required Hardware:
    - H800, H400, Q800: Elliptec rotation mounts
    - MaiTai laser for wavelength control
    - Power meter for transmission measurements
    - Photodiode for real-time monitoring (optional)
    """

    experiment_name = "Elliptec Rotator Calibration"
    experiment_type = "elliptec_calibration"
    required_modules = ["H800", "H400", "Q800", "MaiTai", "Newport1830C"]
    optional_modules = []

    def __init__(self, dashboard=None):
        super().__init__(dashboard)

        # Rotator information
        self.rotators = {
            "H800": {"type": "HWP", "wavelength": 800, "description": "Incident HWP"},
            "H400": {"type": "HWP", "wavelength": 400, "description": "Analyzer HWP"},
            "Q800": {
                "type": "QWP",
                "wavelength": 800,
                "description": "Quarter-wave plate",
            },
        }

        # Calibration results storage
        self.individual_calibrations = {}
        self.cross_calibrations = {}
        self.wavelength_calibrations = {}

        # Current calibration state
        self.reference_positions = {}
        self.current_rotator = None

        # Add Elliptec-specific parameters
        self.add_elliptec_parameters()

    def add_elliptec_parameters(self):
        """Add Elliptec calibration specific parameters."""
        elliptec_params = {
            "name": "elliptec_calibration",
            "type": "group",
            "children": [
                {
                    "name": "homing_settings",
                    "type": "group",
                    "children": [
                        {
                            "name": "home_on_start",
                            "type": "bool",
                            "value": True,
                            "tip": "Home all rotators before calibration",
                        },
                        {
                            "name": "homing_timeout",
                            "type": "float",
                            "value": 30.0,
                            "limits": [5, 120],
                            "suffix": "s",
                        },
                        {
                            "name": "verify_homed_position",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "name": "position_tolerance",
                            "type": "float",
                            "value": 0.1,
                            "limits": [0.01, 1.0],
                            "suffix": "°",
                        },
                    ],
                },
                {
                    "name": "individual_calibration",
                    "type": "group",
                    "children": [
                        {
                            "name": "angle_range",
                            "type": "float",
                            "value": 360.0,
                            "limits": [180, 720],
                            "suffix": "°",
                        },
                        {
                            "name": "angle_step",
                            "type": "float",
                            "value": 5.0,
                            "limits": [1, 45],
                            "suffix": "°",
                        },
                        {
                            "name": "settling_time",
                            "type": "float",
                            "value": 0.5,
                            "limits": [0.1, 5.0],
                            "suffix": "s",
                        },
                        {
                            "name": "averaging_samples",
                            "type": "int",
                            "value": 10,
                            "limits": [1, 100],
                        },
                    ],
                },
                {
                    "name": "cross_calibration",
                    "type": "group",
                    "children": [
                        {
                            "name": "enable_cross_calibration",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "name": "test_angles",
                            "type": "str",
                            "value": "0, 45, 90, 135, 180, 225, 270, 315",
                            "tip": "Comma-separated test angles for cross-calibration",
                        },
                        {
                            "name": "cross_angle_step",
                            "type": "float",
                            "value": 15.0,
                            "limits": [5, 90],
                            "suffix": "°",
                        },
                    ],
                },
                {
                    "name": "wavelength_calibration",
                    "type": "group",
                    "children": [
                        {
                            "name": "enable_wavelength_cal",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "name": "wavelength_range",
                            "type": "group",
                            "children": [
                                {
                                    "name": "start_nm",
                                    "type": "float",
                                    "value": 750.0,
                                    "limits": [700, 950],
                                    "suffix": "nm",
                                },
                                {
                                    "name": "stop_nm",
                                    "type": "float",
                                    "value": 850.0,
                                    "limits": [750, 1000],
                                    "suffix": "nm",
                                },
                                {
                                    "name": "step_nm",
                                    "type": "float",
                                    "value": 25.0,
                                    "limits": [5, 100],
                                    "suffix": "nm",
                                },
                            ],
                        },
                        {
                            "name": "test_polarizations",
                            "type": "str",
                            "value": "0, 90, 180, 270",
                            "tip": "Test polarization angles for wavelength calibration",
                        },
                    ],
                },
                {
                    "name": "fitting_settings",
                    "type": "group",
                    "children": [
                        {
                            "name": "fit_function",
                            "type": "list",
                            "limits": ["malus_law", "cosine_squared"],
                            "value": "malus_law",
                        },
                        {
                            "name": "initial_guess_amplitude",
                            "type": "float",
                            "value": 1.0,
                            "limits": [0.1, 10.0],
                        },
                        {
                            "name": "initial_guess_phase",
                            "type": "float",
                            "value": 0.0,
                            "limits": [-180, 180],
                            "suffix": "°",
                        },
                        {
                            "name": "initial_guess_offset",
                            "type": "float",
                            "value": 0.1,
                            "limits": [0.0, 1.0],
                        },
                        {
                            "name": "max_iterations",
                            "type": "int",
                            "value": 1000,
                            "limits": [100, 10000],
                        },
                        {
                            "name": "tolerance",
                            "type": "float",
                            "value": 1e-8,
                            "limits": [1e-12, 1e-4],
                        },
                    ],
                },
                {
                    "name": "validation",
                    "type": "group",
                    "children": [
                        {"name": "validate_calibration", "type": "bool", "value": True},
                        {
                            "name": "validation_angles",
                            "type": "str",
                            "value": "22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5",
                            "tip": "Validation angles between calibration points",
                        },
                        {
                            "name": "max_residual_percent",
                            "type": "float",
                            "value": 2.0,
                            "limits": [0.1, 10.0],
                            "suffix": "%",
                        },
                        {
                            "name": "repeatability_tests",
                            "type": "int",
                            "value": 3,
                            "limits": [1, 10],
                        },
                    ],
                },
            ],
        }

        # Add to existing parameters
        self.settings.addChild(elliptec_params)

    def initialize_specific_hardware(self):
        """Initialize Elliptec calibration specific hardware."""
        logger.info("Initializing Elliptec calibration hardware")

        # Verify all required rotators are available
        for rotator_name in ["H800", "H400", "Q800"]:
            if rotator_name not in self.modules:
                raise ExperimentError(f"Rotator {rotator_name} not available")

        # Verify other required modules
        if "MaiTai" not in self.modules:
            raise ExperimentError("MaiTai laser not available")
        if "Newport1830C" not in self.modules:
            raise ExperimentError("Newport power meter not available")

        # Test rotator communication
        for rotator_name, rotator_info in self.rotators.items():
            try:
                rotator = self.modules[rotator_name]
                # Get current position to test communication
                current_pos = rotator.get_actuator_value()
                logger.info(
                    f"{rotator_name} ({rotator_info['description']}) at {current_pos}°"
                )
            except Exception as e:
                raise ExperimentError(f"Failed to communicate with {rotator_name}: {e}")

        # Test laser and power meter
        try:
            maitai = self.modules["MaiTai"]
            current_wl = maitai.get_actuator_value()
            logger.info(f"MaiTai wavelength: {current_wl} nm")

            power_meter = self.modules["Newport1830C"]
            current_power = power_meter.get_actuator_value()
            logger.info(f"Power meter reading: {current_power} W")

        except Exception as e:
            raise ExperimentError(f"Failed to communicate with laser/power meter: {e}")

        logger.info("Elliptec calibration hardware initialized successfully")

    def validate_parameters(self):
        """Validate Elliptec calibration parameters."""
        # Check angle parameters
        angle_range = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_range"
        ).value()
        angle_step = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_step"
        ).value()

        if angle_step <= 0:
            raise ExperimentError("Angle step must be positive")
        if angle_range <= angle_step:
            raise ExperimentError("Angle range must be larger than angle step")
        if angle_range > 720:
            logger.warning("Large angle range may cause rotator wear")

        # Check wavelength parameters if enabled
        if self.settings.child(
            "elliptec_calibration", "wavelength_calibration", "enable_wavelength_cal"
        ).value():
            wl_start = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "start_nm",
            ).value()
            wl_stop = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "stop_nm",
            ).value()
            wl_step = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "step_nm",
            ).value()

            if wl_start >= wl_stop:
                raise ExperimentError("Wavelength start must be less than stop")
            if wl_step <= 0:
                raise ExperimentError("Wavelength step must be positive")

        logger.info("Elliptec calibration parameters validated successfully")

    def create_data_structures(self):
        """Create data structures for Elliptec calibration results."""
        # Get calibration parameters
        angle_range = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_range"
        ).value()
        angle_step = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_step"
        ).value()

        # Create angle array
        angles = np.arange(0, angle_range + angle_step, angle_step)

        # Initialize individual calibration data structures
        for rotator_name in self.rotators.keys():
            self.individual_calibrations[rotator_name] = {
                "angles": angles,
                "powers": np.zeros_like(angles),
                "timestamps": np.zeros_like(angles),
                "fit_params": {},
                "fit_quality": {},
                "validation_results": {},
            }

        # Calculate total steps for progress tracking
        total_individual_steps = len(self.rotators) * len(angles)

        # Add cross-calibration steps if enabled
        total_cross_steps = 0
        if self.settings.child(
            "elliptec_calibration", "cross_calibration", "enable_cross_calibration"
        ).value():
            test_angles_str = self.settings.child(
                "elliptec_calibration", "cross_calibration", "test_angles"
            ).value()
            test_angles = [float(x.strip()) for x in test_angles_str.split(",")]
            cross_step = self.settings.child(
                "elliptec_calibration", "cross_calibration", "cross_angle_step"
            ).value()
            cross_range = 360  # Full rotation for cross-calibration
            cross_angles = np.arange(0, cross_range + cross_step, cross_step)
            total_cross_steps = len(test_angles) * len(cross_angles)

        # Add wavelength calibration steps if enabled
        total_wavelength_steps = 0
        if self.settings.child(
            "elliptec_calibration", "wavelength_calibration", "enable_wavelength_cal"
        ).value():
            wl_start = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "start_nm",
            ).value()
            wl_stop = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "stop_nm",
            ).value()
            wl_step = self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "step_nm",
            ).value()
            wavelengths = np.arange(wl_start, wl_stop + wl_step, wl_step)
            test_pol_str = self.settings.child(
                "elliptec_calibration", "wavelength_calibration", "test_polarizations"
            ).value()
            test_polarizations = [float(x.strip()) for x in test_pol_str.split(",")]
            total_wavelength_steps = (
                len(wavelengths) * len(test_polarizations) * len(self.rotators)
            )

        # Add homing and validation steps
        homing_steps = (
            len(self.rotators)
            if self.settings.child(
                "elliptec_calibration", "homing_settings", "home_on_start"
            ).value()
            else 0
        )
        validation_steps = 0
        if self.settings.child(
            "elliptec_calibration", "validation", "validate_calibration"
        ).value():
            val_angles_str = self.settings.child(
                "elliptec_calibration", "validation", "validation_angles"
            ).value()
            val_angles = [float(x.strip()) for x in val_angles_str.split(",")]
            repeatability = self.settings.child(
                "elliptec_calibration", "validation", "repeatability_tests"
            ).value()
            validation_steps = len(val_angles) * len(self.rotators) * repeatability

        self.total_steps = (
            homing_steps
            + total_individual_steps
            + total_cross_steps
            + total_wavelength_steps
            + validation_steps
        )

        logger.info(
            f"Created data structures: {len(self.rotators)} rotators, {len(angles)} angles per rotator"
        )
        logger.info(f"Total experiment steps: {self.total_steps}")

    def run_experiment(self):
        """Execute the Elliptec calibration experiment."""
        try:
            self.log_status("Starting Elliptec rotator calibration")
            current_step = 0

            # Phase 1: Homing (if enabled)
            if self.settings.child(
                "elliptec_calibration", "homing_settings", "home_on_start"
            ).value():
                self.log_status("Phase 1: Homing rotators to reference positions")
                current_step = self.home_all_rotators(current_step)

            # Phase 2: Individual rotator calibration
            self.log_status("Phase 2: Individual rotator calibration")
            current_step = self.calibrate_individual_rotators(current_step)

            # Phase 3: Cross-calibration (if enabled)
            if self.settings.child(
                "elliptec_calibration", "cross_calibration", "enable_cross_calibration"
            ).value():
                self.log_status("Phase 3: Cross-rotator calibration")
                current_step = self.calibrate_cross_rotators(current_step)

            # Phase 4: Wavelength calibration (if enabled)
            if self.settings.child(
                "elliptec_calibration",
                "wavelength_calibration",
                "enable_wavelength_cal",
            ).value():
                self.log_status("Phase 4: Wavelength-dependent calibration")
                current_step = self.calibrate_wavelength_dependence(current_step)

            # Phase 5: Validation (if enabled)
            if self.settings.child(
                "elliptec_calibration", "validation", "validate_calibration"
            ).value():
                self.log_status("Phase 5: Calibration validation")
                current_step = self.validate_calibration_accuracy(current_step)

            # Phase 6: Generate lookup tables and save results
            self.log_status("Phase 6: Generating calibration tables and saving results")
            self.generate_calibration_tables()
            self.save_calibration_results()

            self.log_status("Elliptec calibration completed successfully")

        except Exception as e:
            logger.error(f"Elliptec calibration failed: {e}")
            raise ExperimentError(f"Elliptec calibration failed: {e}")

    def home_all_rotators(self, current_step):
        """Home all rotators to establish reference positions."""
        timeout = self.settings.child(
            "elliptec_calibration", "homing_settings", "homing_timeout"
        ).value()
        verify_position = self.settings.child(
            "elliptec_calibration", "homing_settings", "verify_homed_position"
        ).value()
        tolerance = self.settings.child(
            "elliptec_calibration", "homing_settings", "position_tolerance"
        ).value()

        for rotator_name in self.rotators.keys():
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Homing {rotator_name}")
            rotator = self.modules[rotator_name]

            try:
                # Send home command
                start_time = time.time()
                rotator.home()  # Assuming home() method exists

                # Wait for homing to complete with timeout
                while time.time() - start_time < timeout:
                    if self._check_stop_requested():
                        return current_step

                    # Check if homing is complete (implementation depends on hardware)
                    # For now, assume fixed homing time
                    time.sleep(1.0)

                    # Check if at home position
                    current_pos = rotator.get_actuator_value()
                    if isinstance(current_pos, DataActuator):
                        pos_value = current_pos.value()
                    else:
                        pos_value = float(current_pos)

                    if abs(pos_value) < tolerance:  # Assuming home is at 0°
                        break
                else:
                    raise ExperimentError(f"Homing timeout for {rotator_name}")

                # Verify final position if enabled
                if verify_position:
                    final_pos = rotator.get_actuator_value()
                    if isinstance(final_pos, DataActuator):
                        pos_value = final_pos.value()
                    else:
                        pos_value = float(final_pos)

                    if abs(pos_value) > tolerance:
                        raise ExperimentError(
                            f"{rotator_name} not at home position: {pos_value}°"
                        )

                self.reference_positions[rotator_name] = 0.0
                logger.info(f"{rotator_name} homed successfully")

            except Exception as e:
                raise ExperimentError(f"Failed to home {rotator_name}: {e}")

            # Update progress
            current_step += 1
            progress = (current_step / self.total_steps) * 100
            self.update_progress(progress)

        self.log_status("All rotators homed successfully")
        return current_step

    def calibrate_individual_rotators(self, current_step):
        """Calibrate each rotator individually using Malus law fitting."""
        angle_range = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_range"
        ).value()
        angle_step = self.settings.child(
            "elliptec_calibration", "individual_calibration", "angle_step"
        ).value()
        settling_time = self.settings.child(
            "elliptec_calibration", "individual_calibration", "settling_time"
        ).value()
        averaging_samples = self.settings.child(
            "elliptec_calibration", "individual_calibration", "averaging_samples"
        ).value()

        angles = np.arange(0, angle_range + angle_step, angle_step)

        for rotator_name in self.rotators.keys():
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Calibrating {rotator_name} individually")
            self.current_rotator = rotator_name

            # Set other rotators to known positions
            self.set_other_rotators_to_reference(rotator_name)

            rotator = self.modules[rotator_name]
            power_meter = self.modules["Newport1830C"]

            powers = []
            timestamps = []

            for angle in angles:
                if self._check_stop_requested():
                    return current_step

                # Move rotator to target angle
                target_position = DataActuator(data=[angle])
                rotator.move_abs(target_position)

                # Wait for settling
                time.sleep(settling_time)

                # Measure power with averaging
                power_readings = []
                for _ in range(averaging_samples):
                    power = power_meter.get_actuator_value()
                    if isinstance(power, DataActuator):
                        power_value = power.value()
                    else:
                        power_value = float(power)
                    power_readings.append(power_value)
                    time.sleep(0.01)

                avg_power = np.mean(power_readings)
                powers.append(avg_power)
                timestamps.append(time.time())

                logger.debug(f"{rotator_name} at {angle}° -> {avg_power:.6f} W")

                # Update progress
                current_step += 1
                progress = (current_step / self.total_steps) * 100
                self.update_progress(progress)

            # Store results
            self.individual_calibrations[rotator_name]["angles"] = angles
            self.individual_calibrations[rotator_name]["powers"] = np.array(powers)
            self.individual_calibrations[rotator_name]["timestamps"] = np.array(
                timestamps
            )

            # Fit Malus law
            self.fit_individual_rotator(rotator_name)

            logger.info(f"{rotator_name} individual calibration completed")

        return current_step

    def set_other_rotators_to_reference(self, active_rotator):
        """Set non-active rotators to reference positions."""
        reference_angles = {
            "H800": 0.0,  # HWP at 0° for maximum transmission
            "H400": 0.0,  # HWP at 0° for maximum transmission
            "Q800": 45.0,  # QWP at 45° for circular polarization
        }

        for rotator_name in self.rotators.keys():
            if rotator_name != active_rotator:
                rotator = self.modules[rotator_name]
                ref_angle = reference_angles.get(rotator_name, 0.0)

                target_position = DataActuator(data=[ref_angle])
                rotator.move_abs(target_position)

                logger.debug(f"Set {rotator_name} to reference position {ref_angle}°")

    def fit_individual_rotator(self, rotator_name):
        """Fit Malus law to individual rotator calibration data."""
        angles = self.individual_calibrations[rotator_name]["angles"]
        powers = self.individual_calibrations[rotator_name]["powers"]

        # Initial parameter guesses
        amplitude_guess = self.settings.child(
            "elliptec_calibration", "fitting_settings", "initial_guess_amplitude"
        ).value()
        phase_guess = self.settings.child(
            "elliptec_calibration", "fitting_settings", "initial_guess_phase"
        ).value()
        offset_guess = self.settings.child(
            "elliptec_calibration", "fitting_settings", "initial_guess_offset"
        ).value()

        # Estimate better initial guesses from data
        power_max = np.max(powers)
        power_min = np.min(powers)
        amplitude_guess = power_max - power_min
        offset_guess = power_min

        # Find phase by locating maximum
        max_idx = np.argmax(powers)
        phase_guess = angles[max_idx]

        initial_guess = [amplitude_guess, phase_guess, offset_guess]

        try:
            # Perform curve fitting
            popt, pcov = curve_fit(
                malus_law,
                angles,
                powers,
                p0=initial_guess,
                maxfev=self.settings.child(
                    "elliptec_calibration", "fitting_settings", "max_iterations"
                ).value(),
            )

            amplitude, phase, offset = popt
            amplitude_err, phase_err, offset_err = np.sqrt(np.diag(pcov))

            # Calculate fit quality metrics
            fitted_powers = malus_law(angles, *popt)
            residuals = powers - fitted_powers
            rms_residual = np.sqrt(np.mean(residuals**2))
            r_squared = 1 - np.sum(residuals**2) / np.sum(
                (powers - np.mean(powers)) ** 2
            )
            max_residual_percent = np.max(np.abs(residuals)) / np.mean(powers) * 100

            # Store fit results
            self.individual_calibrations[rotator_name]["fit_params"] = {
                "amplitude": amplitude,
                "phase": phase,
                "offset": offset,
                "amplitude_error": amplitude_err,
                "phase_error": phase_err,
                "offset_error": offset_err,
            }

            self.individual_calibrations[rotator_name]["fit_quality"] = {
                "rms_residual": rms_residual,
                "r_squared": r_squared,
                "max_residual_percent": max_residual_percent,
                "residuals": residuals,
                "fitted_powers": fitted_powers,
            }

            logger.info(
                f"{rotator_name} Malus law fit: A={amplitude:.4f}±{amplitude_err:.4f}, "
                f"φ={phase:.2f}±{phase_err:.2f}°, C={offset:.4f}±{offset_err:.4f}"
            )
            logger.info(
                f"{rotator_name} fit quality: R²={r_squared:.4f}, "
                f"RMS residual={rms_residual:.6f}, Max error={max_residual_percent:.2f}%"
            )

        except Exception as e:
            logger.error(f"Failed to fit {rotator_name}: {e}")
            # Store error information
            self.individual_calibrations[rotator_name]["fit_params"] = {}
            self.individual_calibrations[rotator_name]["fit_quality"] = {
                "error": str(e)
            }

    def calibrate_cross_rotators(self, current_step):
        """Calibrate cross-rotator interference and coupling effects."""
        test_angles_str = self.settings.child(
            "elliptec_calibration", "cross_calibration", "test_angles"
        ).value()
        test_angles = [float(x.strip()) for x in test_angles_str.split(",")]
        cross_step = self.settings.child(
            "elliptec_calibration", "cross_calibration", "cross_angle_step"
        ).value()
        cross_range = 360
        cross_angles = np.arange(0, cross_range + cross_step, cross_step)

        self.log_status("Measuring cross-rotator coupling effects")

        # Initialize cross-calibration data storage
        self.cross_calibrations = {}

        power_meter = self.modules["Newport1830C"]

        for test_angle in test_angles:
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Cross-calibration at reference angle {test_angle}°")

            # Set primary rotators to test angle
            for rotator_name in ["H800", "H400"]:
                rotator = self.modules[rotator_name]
                target_position = DataActuator(data=[test_angle])
                rotator.move_abs(target_position)

            # Sweep Q800 and measure coupling
            q800 = self.modules["Q800"]
            powers = []

            for angle in cross_angles:
                if self._check_stop_requested():
                    return current_step

                # Move Q800 to test angle
                target_position = DataActuator(data=[angle])
                q800.move_abs(target_position)
                time.sleep(0.2)  # Settling time

                # Measure power
                power = power_meter.get_actuator_value()
                if isinstance(power, DataActuator):
                    power_value = power.value()
                else:
                    power_value = float(power)
                powers.append(power_value)

                # Update progress
                current_step += 1
                progress = (current_step / self.total_steps) * 100
                self.update_progress(progress)

            # Store cross-calibration data
            self.cross_calibrations[f"reference_{test_angle}"] = {
                "reference_angle": test_angle,
                "q800_angles": cross_angles,
                "powers": np.array(powers),
            }

        logger.info("Cross-rotator calibration completed")
        return current_step

    def calibrate_wavelength_dependence(self, current_step):
        """Calibrate wavelength-dependent effects for rotators."""
        wl_start = self.settings.child(
            "elliptec_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "start_nm",
        ).value()
        wl_stop = self.settings.child(
            "elliptec_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "stop_nm",
        ).value()
        wl_step = self.settings.child(
            "elliptec_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "step_nm",
        ).value()

        test_pol_str = self.settings.child(
            "elliptec_calibration", "wavelength_calibration", "test_polarizations"
        ).value()
        test_polarizations = [float(x.strip()) for x in test_pol_str.split(",")]

        wavelengths = np.arange(wl_start, wl_stop + wl_step, wl_step)

        self.log_status("Measuring wavelength-dependent rotator effects")

        # Initialize wavelength calibration data
        self.wavelength_calibrations = {}

        maitai = self.modules["MaiTai"]
        power_meter = self.modules["Newport1830C"]
        stabilization_time = self.settings.child(
            "hardware_settings", "stabilization_time"
        ).value()

        for wavelength in wavelengths:
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Wavelength calibration at {wavelength} nm")

            # Set wavelength and wait for stabilization
            target_wl = DataActuator(data=[wavelength])
            maitai.move_abs(target_wl)
            time.sleep(stabilization_time)

            wavelength_data = {}

            for rotator_name in self.rotators.keys():
                if self._check_stop_requested():
                    return current_step

                rotator = self.modules[rotator_name]
                polarization_data = {}

                for pol_angle in test_polarizations:
                    # Set rotator to test polarization
                    target_position = DataActuator(data=[pol_angle])
                    rotator.move_abs(target_position)
                    time.sleep(0.5)  # Settling time

                    # Measure power
                    power = power_meter.get_actuator_value()
                    if isinstance(power, DataActuator):
                        power_value = power.value()
                    else:
                        power_value = float(power)

                    polarization_data[pol_angle] = power_value

                    # Update progress
                    current_step += 1
                    progress = (current_step / self.total_steps) * 100
                    self.update_progress(progress)

                wavelength_data[rotator_name] = polarization_data

            self.wavelength_calibrations[wavelength] = wavelength_data

        logger.info("Wavelength-dependent calibration completed")
        return current_step

    def validate_calibration_accuracy(self, current_step):
        """Validate calibration accuracy using independent test points."""
        val_angles_str = self.settings.child(
            "elliptec_calibration", "validation", "validation_angles"
        ).value()
        validation_angles = [float(x.strip()) for x in val_angles_str.split(",")]
        repeatability_tests = self.settings.child(
            "elliptec_calibration", "validation", "repeatability_tests"
        ).value()
        max_residual_percent = self.settings.child(
            "elliptec_calibration", "validation", "max_residual_percent"
        ).value()

        self.log_status("Validating calibration accuracy")

        power_meter = self.modules["Newport1830C"]

        for rotator_name in self.rotators.keys():
            if self._check_stop_requested():
                return current_step

            if "fit_params" not in self.individual_calibrations[rotator_name]:
                logger.warning(
                    f"No fit parameters for {rotator_name}, skipping validation"
                )
                continue

            self.log_status(f"Validating {rotator_name}")

            rotator = self.modules[rotator_name]
            fit_params = self.individual_calibrations[rotator_name]["fit_params"]

            if not fit_params:  # Check if fit failed
                logger.warning(f"Fit failed for {rotator_name}, skipping validation")
                continue

            # Set other rotators to reference positions
            self.set_other_rotators_to_reference(rotator_name)

            validation_results = []

            for val_angle in validation_angles:
                if self._check_stop_requested():
                    return current_step

                # Predict power using calibration
                predicted_power = malus_law(
                    val_angle,
                    fit_params["amplitude"],
                    fit_params["phase"],
                    fit_params["offset"],
                )

                # Measure actual power multiple times for repeatability
                measured_powers = []
                for rep in range(repeatability_tests):
                    # Move to validation angle
                    target_position = DataActuator(data=[val_angle])
                    rotator.move_abs(target_position)
                    time.sleep(0.5)  # Settling time

                    # Measure power
                    power = power_meter.get_actuator_value()
                    if isinstance(power, DataActuator):
                        power_value = power.value()
                    else:
                        power_value = float(power)
                    measured_powers.append(power_value)

                    # Update progress
                    current_step += 1
                    progress = (current_step / self.total_steps) * 100
                    self.update_progress(progress)

                # Calculate validation metrics
                mean_measured = np.mean(measured_powers)
                std_measured = np.std(measured_powers)
                residual_percent = (
                    abs(mean_measured - predicted_power) / predicted_power * 100
                )
                repeatability_percent = std_measured / mean_measured * 100

                validation_result = {
                    "angle": val_angle,
                    "predicted_power": predicted_power,
                    "measured_powers": measured_powers,
                    "mean_measured": mean_measured,
                    "std_measured": std_measured,
                    "residual_percent": residual_percent,
                    "repeatability_percent": repeatability_percent,
                    "passed": residual_percent < max_residual_percent,
                }

                validation_results.append(validation_result)

                logger.debug(
                    f"{rotator_name} validation at {val_angle}°: "
                    f"Predicted={predicted_power:.6f}W, "
                    f"Measured={mean_measured:.6f}±{std_measured:.6f}W "
                    f"(Error: {residual_percent:.2f}%)"
                )

            # Store validation results
            self.individual_calibrations[rotator_name]["validation_results"] = {
                "validation_points": validation_results,
                "summary": {
                    "total_points": len(validation_results),
                    "passed_points": sum(1 for r in validation_results if r["passed"]),
                    "pass_rate": sum(1 for r in validation_results if r["passed"])
                    / len(validation_results)
                    * 100,
                    "mean_error_percent": np.mean(
                        [r["residual_percent"] for r in validation_results]
                    ),
                    "max_error_percent": np.max(
                        [r["residual_percent"] for r in validation_results]
                    ),
                    "mean_repeatability_percent": np.mean(
                        [r["repeatability_percent"] for r in validation_results]
                    ),
                },
            }

            summary = self.individual_calibrations[rotator_name]["validation_results"][
                "summary"
            ]
            logger.info(
                f"{rotator_name} validation: {summary['passed_points']}/{summary['total_points']} points passed"
            )
            logger.info(
                f"{rotator_name} mean error: {summary['mean_error_percent']:.2f}%, "
                f"max error: {summary['max_error_percent']:.2f}%"
            )

        return current_step

    def generate_calibration_tables(self):
        """Generate lookup tables and interpolation functions for runtime use."""
        self.log_status("Generating calibration lookup tables")

        # Generate angle-to-power lookup tables for each rotator
        self.calibration_tables = {}

        for rotator_name in self.rotators.keys():
            if "fit_params" not in self.individual_calibrations[rotator_name]:
                continue

            fit_params = self.individual_calibrations[rotator_name]["fit_params"]
            if not fit_params:
                continue

            # Create high-resolution angle array for lookup table
            angles_hr = np.linspace(0, 360, 3601)  # 0.1° resolution
            powers_hr = malus_law(
                angles_hr,
                fit_params["amplitude"],
                fit_params["phase"],
                fit_params["offset"],
            )

            # Create interpolation function for inverse lookup (power -> angle)
            # Handle the double-valued nature of cos² function
            try:
                angle_interpolator = interp1d(
                    powers_hr,
                    angles_hr,
                    kind="linear",
                    bounds_error=False,
                    fill_value="extrapolate",
                )

                self.calibration_tables[rotator_name] = {
                    "angles": angles_hr,
                    "powers": powers_hr,
                    "fit_params": fit_params,
                    "angle_interpolator": angle_interpolator,
                    "power_to_angle_func": lambda p: inverse_malus_law(
                        p,
                        fit_params["amplitude"],
                        fit_params["phase"],
                        fit_params["offset"],
                    ),
                }

                logger.info(f"Generated lookup table for {rotator_name}")

            except Exception as e:
                logger.warning(
                    f"Failed to create interpolation for {rotator_name}: {e}"
                )

        logger.info("Calibration lookup tables generated successfully")

    def save_calibration_results(self):
        """Save all calibration results to HDF5 file."""
        try:
            with h5py.File(self.data_filepath, "w") as f:
                # Save individual calibration data
                individual_group = f.create_group("individual_calibrations")
                for rotator_name, calib_data in self.individual_calibrations.items():
                    rotator_group = individual_group.create_group(rotator_name)

                    # Save arrays
                    rotator_group.create_dataset("angles", data=calib_data["angles"])
                    rotator_group.create_dataset("powers", data=calib_data["powers"])
                    rotator_group.create_dataset(
                        "timestamps", data=calib_data["timestamps"]
                    )

                    # Save fit parameters
                    if calib_data["fit_params"]:
                        fit_group = rotator_group.create_group("fit_params")
                        for key, value in calib_data["fit_params"].items():
                            fit_group.attrs[key] = value

                    # Save fit quality metrics
                    if calib_data["fit_quality"]:
                        quality_group = rotator_group.create_group("fit_quality")
                        for key, value in calib_data["fit_quality"].items():
                            if isinstance(value, np.ndarray):
                                quality_group.create_dataset(key, data=value)
                            else:
                                quality_group.attrs[key] = value

                    # Save validation results
                    if (
                        "validation_results" in calib_data
                        and calib_data["validation_results"]
                    ):
                        val_group = rotator_group.create_group("validation")

                        # Save validation points
                        for i, point in enumerate(
                            calib_data["validation_results"]["validation_points"]
                        ):
                            point_group = val_group.create_group(f"point_{i}")
                            for key, value in point.items():
                                if isinstance(value, (list, np.ndarray)):
                                    point_group.create_dataset(key, data=value)
                                else:
                                    point_group.attrs[key] = value

                        # Save validation summary
                        summary_group = val_group.create_group("summary")
                        for key, value in calib_data["validation_results"][
                            "summary"
                        ].items():
                            summary_group.attrs[key] = value

                # Save cross-calibration data
                if self.cross_calibrations:
                    cross_group = f.create_group("cross_calibrations")
                    for key, cross_data in self.cross_calibrations.items():
                        cross_subgroup = cross_group.create_group(key)
                        cross_subgroup.attrs["reference_angle"] = cross_data[
                            "reference_angle"
                        ]
                        cross_subgroup.create_dataset(
                            "q800_angles", data=cross_data["q800_angles"]
                        )
                        cross_subgroup.create_dataset(
                            "powers", data=cross_data["powers"]
                        )

                # Save wavelength calibration data
                if self.wavelength_calibrations:
                    wl_group = f.create_group("wavelength_calibrations")
                    for wavelength, wl_data in self.wavelength_calibrations.items():
                        wl_subgroup = wl_group.create_group(f"wl_{wavelength:.0f}nm")
                        wl_subgroup.attrs["wavelength"] = wavelength

                        for rotator_name, rotator_data in wl_data.items():
                            rotator_subgroup = wl_subgroup.create_group(rotator_name)
                            for pol_angle, power in rotator_data.items():
                                rotator_subgroup.attrs[f"pol_{pol_angle:.0f}deg"] = (
                                    power
                                )

                # Save calibration tables
                if hasattr(self, "calibration_tables"):
                    tables_group = f.create_group("calibration_tables")
                    for rotator_name, table_data in self.calibration_tables.items():
                        table_subgroup = tables_group.create_group(rotator_name)
                        table_subgroup.create_dataset(
                            "angles", data=table_data["angles"]
                        )
                        table_subgroup.create_dataset(
                            "powers", data=table_data["powers"]
                        )

                        # Save fit parameters again for easy access
                        for key, value in table_data["fit_params"].items():
                            table_subgroup.attrs[key] = value

                # Save rotator information and metadata
                info_group = f.create_group("rotator_info")
                for rotator_name, info in self.rotators.items():
                    rotator_info_group = info_group.create_group(rotator_name)
                    for key, value in info.items():
                        rotator_info_group.attrs[key] = value

                # Save experiment metadata
                f.attrs["experiment_name"] = self.experiment_name
                f.attrs["experiment_type"] = self.experiment_type
                f.attrs["creation_time"] = datetime.now().isoformat()
                f.attrs["calibration_version"] = "1.0"

                # Save reference positions
                if self.reference_positions:
                    ref_group = f.create_group("reference_positions")
                    for rotator_name, position in self.reference_positions.items():
                        ref_group.attrs[rotator_name] = position

            logger.info(f"Elliptec calibration results saved to {self.data_filepath}")
            self.log_status(f"Calibration data saved to {self.data_filepath}")

        except Exception as e:
            logger.error(f"Failed to save calibration results: {e}")
            raise ExperimentError(f"Failed to save calibration results: {e}")

    def _check_stop_requested(self):
        """Check if experiment stop was requested."""
        if hasattr(self, "experiment_thread") and self.experiment_thread:
            return self.experiment_thread._stop_requested
        return False

    def get_calibrated_angle_for_power(self, rotator_name, target_power):
        """
        Get calibrated rotator angle for specified target power.

        Args:
            rotator_name (str): Name of rotator ('H800', 'H400', 'Q800')
            target_power (float): Target power transmission

        Returns:
            float: Rotator angle in degrees
        """
        if (
            not hasattr(self, "calibration_tables")
            or rotator_name not in self.calibration_tables
        ):
            raise ExperimentError(f"No calibration available for {rotator_name}")

        try:
            power_to_angle_func = self.calibration_tables[rotator_name][
                "power_to_angle_func"
            ]
            angle = power_to_angle_func(target_power)
            return float(angle)
        except Exception as e:
            raise ExperimentError(f"Failed to calculate angle for {rotator_name}: {e}")

    def get_calibrated_power_for_angle(self, rotator_name, angle):
        """
        Get calibrated power transmission for specified rotator angle.

        Args:
            rotator_name (str): Name of rotator ('H800', 'H400', 'Q800')
            angle (float): Rotator angle in degrees

        Returns:
            float: Expected power transmission
        """
        if (
            not hasattr(self, "calibration_tables")
            or rotator_name not in self.calibration_tables
        ):
            raise ExperimentError(f"No calibration available for {rotator_name}")

        try:
            fit_params = self.calibration_tables[rotator_name]["fit_params"]
            power = malus_law(
                angle,
                fit_params["amplitude"],
                fit_params["phase"],
                fit_params["offset"],
            )
            return float(power)
        except Exception as e:
            raise ExperimentError(f"Failed to calculate power for {rotator_name}: {e}")
