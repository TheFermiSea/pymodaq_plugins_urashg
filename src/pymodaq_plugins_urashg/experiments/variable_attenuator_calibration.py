"""
Variable Attenuator Calibration Experiment for μRASHG System

This module implements calibration procedures for the variable attenuator system
used in μRASHG experiments for precise optical power control. The experiment performs:

1. Malus law calibration for HWP-based power attenuation
2. Wavelength-dependent attenuation characterization
3. Power range mapping and lookup table generation
4. Attenuation accuracy validation and verification

The variable attenuator system typically consists of a half-wave plate followed
by a polarizing beam splitter, creating a cos²(θ) power transmission profile
that enables continuous power control over multiple orders of magnitude.

Key calibration outputs:
- Malus law parameters: A·cos²(θ - φ) + C
- Wavelength-dependent correction factors
- Power attenuation lookup tables
- Dynamic range characterization
- Accuracy and repeatability metrics

This calibration is essential for experiments requiring precise power control
across wide dynamic ranges, particularly power-dependent studies.
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
from scipy.interpolate import interp1d, interp2d
from scipy.optimize import curve_fit

from .base_experiment import ExperimentError, ExperimentState, URASHGBaseExperiment

logger = logging.getLogger(__name__)


def attenuator_malus_law(angle, amplitude, phase, offset, extinction_ratio=1e-4):
    """
    Enhanced Malus law for variable attenuator with extinction ratio.

    Args:
        angle (array): HWP rotation angles in degrees
        amplitude (float): Maximum transmission amplitude
        phase (float): Phase offset (optical axis alignment) in degrees
        offset (float): Baseline transmission offset
        extinction_ratio (float): Minimum transmission ratio (polarizer extinction)

    Returns:
        array: Transmitted power with extinction ratio consideration
    """
    angle_rad = np.radians(angle - phase)
    cos_squared = np.cos(angle_rad) ** 2

    # Include extinction ratio for more realistic model
    transmission = amplitude * cos_squared + offset
    transmission = np.maximum(transmission, amplitude * extinction_ratio + offset)

    return transmission


def calculate_attenuation_db(input_power, output_power):
    """
    Calculate attenuation in dB.

    Args:
        input_power (float): Input power
        output_power (float): Output power

    Returns:
        float: Attenuation in dB
    """
    if output_power <= 0 or input_power <= 0:
        return np.inf
    return -10 * np.log10(output_power / input_power)


class VariableAttenuatorCalibrationExperiment(URASHGBaseExperiment):
    """
    Variable Attenuator Calibration Experiment for precise power control.

    This experiment calibrates the variable attenuator system to enable precise
    optical power control across multiple orders of magnitude. The calibration:

    1. Characterizes the Malus law response of the HWP attenuator
    2. Maps angle-to-attenuation relationships across full dynamic range
    3. Measures wavelength-dependent attenuation characteristics
    4. Generates lookup tables for runtime power control
    5. Validates calibration accuracy and repeatability

    The variable attenuator enables:
    - Continuous power control from maximum to <0.01% transmission
    - Wavelength-independent operation (with calibration corrections)
    - High-resolution power adjustment for sensitive measurements
    - Wide dynamic range coverage for power-dependent studies

    Required Hardware:
    - Variable attenuator (typically HWP + polarizer)
    - MaiTai laser for wavelength control
    - Newport power meter for accurate power measurement
    - Rotator control for HWP positioning

    Output Products:
    - Angle-to-attenuation lookup tables
    - Wavelength correction factors
    - Dynamic range characterization
    - Calibration validation metrics
    """

    experiment_name = "Variable Attenuator Calibration"
    experiment_type = "variable_attenuator_calibration"
    required_modules = [
        "MaiTai",
        "Newport1830C",
    ]  # Attenuator module TBD based on hardware
    optional_modules = ["H800"]  # If HWP is part of existing rotator system

    def __init__(self, dashboard=None):
        super().__init__(dashboard)

        # Attenuator configuration
        self.attenuator_config = {
            "type": "hwp_polarizer",
            "max_attenuation_db": 40,  # Typical range
            "min_attenuation_db": 0.1,
            "extinction_ratio": 1e-4,
        }

        # Calibration results storage
        self.angle_sweep_data = {}
        self.wavelength_dependent_data = {}
        self.attenuation_lookup_tables = {}

        # Reference measurements
        self.reference_power = None
        self.reference_wavelength = None

        # Add attenuator-specific parameters
        self.add_attenuator_parameters()

    def add_attenuator_parameters(self):
        """Add variable attenuator calibration specific parameters."""
        attenuator_params = {
            "name": "attenuator_calibration",
            "type": "group",
            "children": [
                {
                    "name": "hardware_settings",
                    "type": "group",
                    "children": [
                        {
                            "name": "attenuator_type",
                            "type": "list",
                            "limits": [
                                "hwp_polarizer",
                                "motorized_nd",
                                "liquid_crystal",
                            ],
                            "value": "hwp_polarizer",
                        },
                        {
                            "name": "rotation_module",
                            "type": "str",
                            "value": "H800",
                            "tip": "PyMoDAQ module controlling attenuator rotation",
                        },
                        {
                            "name": "full_rotation_range",
                            "type": "bool",
                            "value": True,
                            "tip": "Use full 360° rotation for calibration",
                        },
                        {
                            "name": "settling_time",
                            "type": "float",
                            "value": 0.5,
                            "limits": [0.1, 5.0],
                            "suffix": "s",
                        },
                    ],
                },
                {
                    "name": "angle_sweep",
                    "type": "group",
                    "children": [
                        {
                            "name": "start_angle",
                            "type": "float",
                            "value": 0.0,
                            "limits": [0, 360],
                            "suffix": "°",
                        },
                        {
                            "name": "stop_angle",
                            "type": "float",
                            "value": 360.0,
                            "limits": [90, 720],
                            "suffix": "°",
                        },
                        {
                            "name": "angle_step",
                            "type": "float",
                            "value": 2.0,
                            "limits": [0.1, 45],
                            "suffix": "°",
                        },
                        {
                            "name": "high_resolution_regions",
                            "type": "str",
                            "value": "85-95, 175-185, 265-275",
                            "tip": "High-resolution angle ranges around minima",
                        },
                        {
                            "name": "hr_angle_step",
                            "type": "float",
                            "value": 0.2,
                            "limits": [0.01, 2.0],
                            "suffix": "°",
                        },
                    ],
                },
                {
                    "name": "power_measurement",
                    "type": "group",
                    "children": [
                        {
                            "name": "averaging_samples",
                            "type": "int",
                            "value": 20,
                            "limits": [5, 200],
                        },
                        {
                            "name": "measurement_timeout",
                            "type": "float",
                            "value": 1.0,
                            "limits": [0.1, 10.0],
                            "suffix": "s",
                        },
                        {
                            "name": "min_detectable_power",
                            "type": "float",
                            "value": 1e-9,
                            "limits": [1e-12, 1e-6],
                            "suffix": "W",
                        },
                        {
                            "name": "power_stability_check",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "name": "stability_tolerance",
                            "type": "float",
                            "value": 1.0,
                            "limits": [0.1, 10.0],
                            "suffix": "%",
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
                                    "value": 20.0,
                                    "limits": [5, 100],
                                    "suffix": "nm",
                                },
                            ],
                        },
                        {
                            "name": "reference_angles",
                            "type": "str",
                            "value": "0, 30, 45, 60, 90",
                            "tip": "Reference angles for wavelength characterization",
                        },
                    ],
                },
                {
                    "name": "attenuation_mapping",
                    "type": "group",
                    "children": [
                        {
                            "name": "target_attenuations_db",
                            "type": "str",
                            "value": "0.1, 0.5, 1, 2, 5, 10, 15, 20, 25, 30, 35",
                            "tip": "Target attenuation levels for lookup table",
                        },
                        {
                            "name": "attenuation_tolerance_db",
                            "type": "float",
                            "value": 0.1,
                            "limits": [0.01, 1.0],
                            "suffix": "dB",
                        },
                        {
                            "name": "max_iterations",
                            "type": "int",
                            "value": 10,
                            "limits": [3, 50],
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
                            "limits": ["malus_law", "enhanced_malus", "polynomial"],
                            "value": "enhanced_malus",
                        },
                        {
                            "name": "include_extinction_ratio",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "name": "initial_extinction_ratio",
                            "type": "float",
                            "value": 1e-4,
                            "limits": [1e-6, 1e-2],
                        },
                        {
                            "name": "fit_tolerance",
                            "type": "float",
                            "value": 1e-8,
                            "limits": [1e-12, 1e-4],
                        },
                        {
                            "name": "max_fit_iterations",
                            "type": "int",
                            "value": 2000,
                            "limits": [100, 10000],
                        },
                    ],
                },
                {
                    "name": "validation",
                    "type": "group",
                    "children": [
                        {"name": "validate_calibration", "type": "bool", "value": True},
                        {
                            "name": "validation_attenuations_db",
                            "type": "str",
                            "value": "0.7, 3, 7, 12, 18, 25",
                            "tip": "Attenuation levels for validation",
                        },
                        {
                            "name": "repeatability_tests",
                            "type": "int",
                            "value": 5,
                            "limits": [2, 20],
                        },
                        {
                            "name": "max_error_db",
                            "type": "float",
                            "value": 0.2,
                            "limits": [0.05, 2.0],
                            "suffix": "dB",
                        },
                        {"name": "hysteresis_test", "type": "bool", "value": True},
                    ],
                },
            ],
        }

        # Add to existing parameters
        self.settings.addChild(attenuator_params)

    def initialize_specific_hardware(self):
        """Initialize variable attenuator calibration specific hardware."""
        logger.info("Initializing variable attenuator calibration hardware")

        # Verify required modules
        if "MaiTai" not in self.modules:
            raise ExperimentError("MaiTai laser not available")
        if "Newport1830C" not in self.modules:
            raise ExperimentError("Newport power meter not available")

        # Get attenuator rotation module
        rotation_module = self.settings.child(
            "attenuator_calibration", "hardware_settings", "rotation_module"
        ).value()
        if rotation_module not in self.modules:
            raise ExperimentError(
                f"Attenuator rotation module {rotation_module} not available"
            )

        # Test hardware communication
        try:
            maitai = self.modules["MaiTai"]
            current_wl = maitai.get_actuator_value()
            logger.info(f"MaiTai wavelength: {current_wl} nm")

            power_meter = self.modules["Newport1830C"]
            current_power = power_meter.get_actuator_value()
            logger.info(f"Power meter reading: {current_power} W")

            attenuator = self.modules[rotation_module]
            current_angle = attenuator.get_actuator_value()
            logger.info(f"Attenuator angle: {current_angle}°")

        except Exception as e:
            raise ExperimentError(f"Hardware communication test failed: {e}")

        # Set up reference measurements
        self.reference_wavelength = 800.0  # nm
        self.reference_power = None  # Will be measured

        logger.info("Variable attenuator calibration hardware initialized successfully")

    def validate_parameters(self):
        """Validate variable attenuator calibration parameters."""
        # Check angle parameters
        start_angle = self.settings.child(
            "attenuator_calibration", "angle_sweep", "start_angle"
        ).value()
        stop_angle = self.settings.child(
            "attenuator_calibration", "angle_sweep", "stop_angle"
        ).value()
        angle_step = self.settings.child(
            "attenuator_calibration", "angle_sweep", "angle_step"
        ).value()

        if start_angle >= stop_angle:
            raise ExperimentError("Start angle must be less than stop angle")
        if angle_step <= 0:
            raise ExperimentError("Angle step must be positive")
        if (stop_angle - start_angle) / angle_step > 1000:
            logger.warning(
                "Very large number of angle points - this may take a long time"
            )

        # Check wavelength parameters if enabled
        if self.settings.child(
            "attenuator_calibration", "wavelength_calibration", "enable_wavelength_cal"
        ).value():
            wl_start = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "start_nm",
            ).value()
            wl_stop = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "stop_nm",
            ).value()
            wl_step = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "step_nm",
            ).value()

            if wl_start >= wl_stop:
                raise ExperimentError("Wavelength start must be less than stop")
            if wl_step <= 0:
                raise ExperimentError("Wavelength step must be positive")

        # Validate target attenuations
        try:
            target_att_str = self.settings.child(
                "attenuator_calibration",
                "attenuation_mapping",
                "target_attenuations_db",
            ).value()
            target_attenuations = [float(x.strip()) for x in target_att_str.split(",")]
            if not all(att >= 0 for att in target_attenuations):
                raise ExperimentError("All target attenuations must be non-negative")
        except ValueError:
            raise ExperimentError("Invalid target attenuations format")

        logger.info("Variable attenuator calibration parameters validated successfully")

    def create_data_structures(self):
        """Create data structures for variable attenuator calibration results."""
        # Get angle sweep parameters
        start_angle = self.settings.child(
            "attenuator_calibration", "angle_sweep", "start_angle"
        ).value()
        stop_angle = self.settings.child(
            "attenuator_calibration", "angle_sweep", "stop_angle"
        ).value()
        angle_step = self.settings.child(
            "attenuator_calibration", "angle_sweep", "angle_step"
        ).value()

        # Create angle arrays
        regular_angles = np.arange(start_angle, stop_angle + angle_step, angle_step)

        # Add high-resolution regions
        hr_regions_str = self.settings.child(
            "attenuator_calibration", "angle_sweep", "high_resolution_regions"
        ).value()
        hr_step = self.settings.child(
            "attenuator_calibration", "angle_sweep", "hr_angle_step"
        ).value()

        all_angles = list(regular_angles)

        try:
            for region_str in hr_regions_str.split(","):
                if "-" in region_str:
                    start_hr, stop_hr = map(float, region_str.strip().split("-"))
                    hr_angles = np.arange(start_hr, stop_hr + hr_step, hr_step)
                    all_angles.extend(hr_angles)
        except ValueError:
            logger.warning(
                "Invalid high-resolution regions format, using regular step only"
            )

        # Remove duplicates and sort
        all_angles = sorted(set(all_angles))
        self.measurement_angles = np.array(all_angles)

        # Initialize angle sweep data structure
        self.angle_sweep_data = {
            "angles": self.measurement_angles,
            "powers": np.zeros_like(self.measurement_angles),
            "attenuations_db": np.zeros_like(self.measurement_angles),
            "timestamps": np.zeros_like(self.measurement_angles),
            "power_std": np.zeros_like(self.measurement_angles),
            "reference_power": None,
        }

        # Calculate total steps for progress tracking
        angle_steps = len(self.measurement_angles)

        # Add wavelength calibration steps
        wavelength_steps = 0
        if self.settings.child(
            "attenuator_calibration", "wavelength_calibration", "enable_wavelength_cal"
        ).value():
            wl_start = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "start_nm",
            ).value()
            wl_stop = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "stop_nm",
            ).value()
            wl_step = self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "wavelength_range",
                "step_nm",
            ).value()
            wavelengths = np.arange(wl_start, wl_stop + wl_step, wl_step)

            ref_angles_str = self.settings.child(
                "attenuator_calibration", "wavelength_calibration", "reference_angles"
            ).value()
            ref_angles = [float(x.strip()) for x in ref_angles_str.split(",")]

            wavelength_steps = len(wavelengths) * len(ref_angles)

        # Add validation steps
        validation_steps = 0
        if self.settings.child(
            "attenuator_calibration", "validation", "validate_calibration"
        ).value():
            val_att_str = self.settings.child(
                "attenuator_calibration", "validation", "validation_attenuations_db"
            ).value()
            val_attenuations = [float(x.strip()) for x in val_att_str.split(",")]
            repeatability = self.settings.child(
                "attenuator_calibration", "validation", "repeatability_tests"
            ).value()
            validation_steps = len(val_attenuations) * repeatability

            if self.settings.child(
                "attenuator_calibration", "validation", "hysteresis_test"
            ).value():
                validation_steps *= 2  # Forward and reverse sweeps

        # Add attenuation mapping steps
        target_att_str = self.settings.child(
            "attenuator_calibration", "attenuation_mapping", "target_attenuations_db"
        ).value()
        target_attenuations = [float(x.strip()) for x in target_att_str.split(",")]
        mapping_steps = len(target_attenuations)

        self.total_steps = (
            angle_steps + wavelength_steps + validation_steps + mapping_steps + 10
        )  # Extra for setup

        logger.info(
            f"Created data structures: {len(self.measurement_angles)} angle points"
        )
        logger.info(f"Total experiment steps: {self.total_steps}")

    def run_experiment(self):
        """Execute the variable attenuator calibration experiment."""
        try:
            self.log_status("Starting variable attenuator calibration")
            current_step = 0

            # Phase 1: Setup and reference measurement
            self.log_status("Phase 1: Setup and reference power measurement")
            current_step = self.measure_reference_power(current_step)

            # Phase 2: Angle sweep calibration
            self.log_status("Phase 2: Angle sweep calibration")
            current_step = self.perform_angle_sweep(current_step)

            # Phase 3: Fit attenuation model
            self.log_status("Phase 3: Fitting attenuation model")
            self.fit_attenuation_model()
            current_step += 5  # Fitting steps
            self.update_progress((current_step / self.total_steps) * 100)

            # Phase 4: Generate attenuation lookup tables
            self.log_status("Phase 4: Generating attenuation lookup tables")
            current_step = self.generate_attenuation_lookup_tables(current_step)

            # Phase 5: Wavelength calibration (if enabled)
            if self.settings.child(
                "attenuator_calibration",
                "wavelength_calibration",
                "enable_wavelength_cal",
            ).value():
                self.log_status("Phase 5: Wavelength-dependent calibration")
                current_step = self.calibrate_wavelength_dependence(current_step)

            # Phase 6: Validation (if enabled)
            if self.settings.child(
                "attenuator_calibration", "validation", "validate_calibration"
            ).value():
                self.log_status("Phase 6: Calibration validation")
                current_step = self.validate_calibration_accuracy(current_step)

            # Phase 7: Save results
            self.log_status("Phase 7: Saving calibration results")
            self.save_calibration_results()

            self.log_status("Variable attenuator calibration completed successfully")

        except Exception as e:
            logger.error(f"Variable attenuator calibration failed: {e}")
            raise ExperimentError(f"Variable attenuator calibration failed: {e}")

    def measure_reference_power(self, current_step):
        """Measure reference power with attenuator at minimum attenuation."""
        self.log_status("Measuring reference power")

        # Set laser to reference wavelength
        maitai = self.modules["MaiTai"]
        target_wl = DataActuator(data=[self.reference_wavelength])
        maitai.move_abs(target_wl)

        # Wait for wavelength stabilization
        stabilization_time = self.settings.child(
            "hardware_settings", "stabilization_time"
        ).value()
        time.sleep(stabilization_time)

        # Set attenuator to minimum attenuation position (typically 0° or 45°)
        rotation_module = self.settings.child(
            "attenuator_calibration", "hardware_settings", "rotation_module"
        ).value()
        attenuator = self.modules[rotation_module]

        # Find minimum attenuation angle (maximum transmission)
        min_att_angle = 0.0  # This should be determined from the attenuator type
        target_angle = DataActuator(data=[min_att_angle])
        attenuator.move_abs(target_angle)

        settling_time = self.settings.child(
            "attenuator_calibration", "hardware_settings", "settling_time"
        ).value()
        time.sleep(settling_time)

        # Measure reference power with averaging
        power_meter = self.modules["Newport1830C"]
        averaging_samples = self.settings.child(
            "attenuator_calibration", "power_measurement", "averaging_samples"
        ).value()

        power_readings = []
        for _ in range(averaging_samples):
            power = power_meter.get_actuator_value()
            if isinstance(power, DataActuator):
                power_value = power.value()
            else:
                power_value = float(power)
            power_readings.append(power_value)
            time.sleep(0.05)

        self.reference_power = np.mean(power_readings)
        reference_std = np.std(power_readings)

        # Store reference power in data structure
        self.angle_sweep_data["reference_power"] = self.reference_power

        logger.info(
            f"Reference power: {self.reference_power:.6f} ± {reference_std:.6f} W"
        )
        self.log_status(f"Reference power measured: {self.reference_power:.6f} W")

        # Check power stability
        stability_tolerance = self.settings.child(
            "attenuator_calibration", "power_measurement", "stability_tolerance"
        ).value()
        stability_percent = (reference_std / self.reference_power) * 100

        if stability_percent > stability_tolerance:
            logger.warning(
                f"Power stability {stability_percent:.2f}% exceeds tolerance {stability_tolerance}%"
            )

        current_step += 5
        self.update_progress((current_step / self.total_steps) * 100)
        return current_step

    def perform_angle_sweep(self, current_step):
        """Perform angle sweep to characterize attenuation vs angle."""
        rotation_module = self.settings.child(
            "attenuator_calibration", "hardware_settings", "rotation_module"
        ).value()
        attenuator = self.modules[rotation_module]
        power_meter = self.modules["Newport1830C"]

        settling_time = self.settings.child(
            "attenuator_calibration", "hardware_settings", "settling_time"
        ).value()
        averaging_samples = self.settings.child(
            "attenuator_calibration", "power_measurement", "averaging_samples"
        ).value()
        min_detectable_power = self.settings.child(
            "attenuator_calibration", "power_measurement", "min_detectable_power"
        ).value()

        for i, angle in enumerate(self.measurement_angles):
            if self._check_stop_requested():
                return current_step

            self.log_status(
                f"Angle sweep: {angle:.1f}° ({i+1}/{len(self.measurement_angles)})"
            )

            # Move attenuator to target angle
            target_angle = DataActuator(data=[angle])
            attenuator.move_abs(target_angle)
            time.sleep(settling_time)

            # Measure transmitted power with averaging
            power_readings = []
            for _ in range(averaging_samples):
                power = power_meter.get_actuator_value()
                if isinstance(power, DataActuator):
                    power_value = power.value()
                else:
                    power_value = float(power)

                # Handle very low power readings
                if power_value < min_detectable_power:
                    power_value = min_detectable_power

                power_readings.append(power_value)
                time.sleep(0.02)

            avg_power = np.mean(power_readings)
            power_std = np.std(power_readings)

            # Calculate attenuation in dB
            if self.reference_power > 0 and avg_power > 0:
                attenuation_db = calculate_attenuation_db(
                    self.reference_power, avg_power
                )
            else:
                attenuation_db = np.inf

            # Store results
            self.angle_sweep_data["powers"][i] = avg_power
            self.angle_sweep_data["attenuations_db"][i] = attenuation_db
            self.angle_sweep_data["timestamps"][i] = time.time()
            self.angle_sweep_data["power_std"][i] = power_std

            logger.debug(
                f"Angle {angle:.1f}° -> Power {avg_power:.6f}W, Attenuation {attenuation_db:.2f}dB"
            )

            # Update progress
            current_step += 1
            progress = (current_step / self.total_steps) * 100
            self.update_progress(progress)

        logger.info("Angle sweep completed")
        return current_step

    def fit_attenuation_model(self):
        """Fit Malus law model to attenuation data."""
        angles = self.angle_sweep_data["angles"]
        powers = self.angle_sweep_data["powers"]

        # Remove infinite attenuation points for fitting
        valid_mask = np.isfinite(powers) & (powers > 0)
        fit_angles = angles[valid_mask]
        fit_powers = powers[valid_mask]

        if len(fit_powers) < 10:
            raise ExperimentError("Insufficient valid data points for fitting")

        # Initial parameter estimation
        power_max = np.max(fit_powers)
        power_min = np.min(fit_powers)
        amplitude_guess = power_max - power_min
        offset_guess = power_min

        # Find phase by locating maximum
        max_idx = np.argmax(fit_powers)
        phase_guess = fit_angles[max_idx]

        # Choose fitting function
        fit_function_name = self.settings.child(
            "attenuator_calibration", "fitting_settings", "fit_function"
        ).value()
        include_extinction = self.settings.child(
            "attenuator_calibration", "fitting_settings", "include_extinction_ratio"
        ).value()

        if fit_function_name == "enhanced_malus" and include_extinction:
            extinction_ratio = self.settings.child(
                "attenuator_calibration", "fitting_settings", "initial_extinction_ratio"
            ).value()
            initial_guess = [
                amplitude_guess,
                phase_guess,
                offset_guess,
                extinction_ratio,
            ]
            fit_function = attenuator_malus_law
        else:
            initial_guess = [amplitude_guess, phase_guess, offset_guess]
            fit_function = lambda angle, amp, phase, offset: attenuator_malus_law(
                angle, amp, phase, offset, 1e-4
            )

        try:
            # Perform curve fitting
            max_iterations = self.settings.child(
                "attenuator_calibration", "fitting_settings", "max_fit_iterations"
            ).value()
            tolerance = self.settings.child(
                "attenuator_calibration", "fitting_settings", "fit_tolerance"
            ).value()

            popt, pcov = curve_fit(
                fit_function,
                fit_angles,
                fit_powers,
                p0=initial_guess,
                maxfev=max_iterations,
                ftol=tolerance,
                xtol=tolerance,
            )

            # Calculate fit quality metrics
            fitted_powers = fit_function(angles, *popt)
            residuals = powers - fitted_powers

            # Only calculate metrics for valid points
            valid_residuals = residuals[valid_mask]
            rms_residual = np.sqrt(np.mean(valid_residuals**2))
            r_squared = 1 - np.sum(valid_residuals**2) / np.sum(
                (fit_powers - np.mean(fit_powers)) ** 2
            )

            # Store fit results
            if len(popt) == 4:
                amplitude, phase, offset, extinction_ratio = popt
                amplitude_err, phase_err, offset_err, extinction_err = np.sqrt(
                    np.diag(pcov)
                )

                self.fit_results = {
                    "amplitude": amplitude,
                    "phase": phase,
                    "offset": offset,
                    "extinction_ratio": extinction_ratio,
                    "amplitude_error": amplitude_err,
                    "phase_error": phase_err,
                    "offset_error": offset_err,
                    "extinction_error": extinction_err,
                    "fit_function": "enhanced_malus",
                }
            else:
                amplitude, phase, offset = popt
                amplitude_err, phase_err, offset_err = np.sqrt(np.diag(pcov))

                self.fit_results = {
                    "amplitude": amplitude,
                    "phase": phase,
                    "offset": offset,
                    "extinction_ratio": 1e-4,  # Fixed value
                    "amplitude_error": amplitude_err,
                    "phase_error": phase_err,
                    "offset_error": offset_err,
                    "extinction_error": 0.0,
                    "fit_function": "standard_malus",
                }

            # Add fit quality metrics
            self.fit_results.update(
                {
                    "rms_residual": rms_residual,
                    "r_squared": r_squared,
                    "fitted_powers": fitted_powers,
                    "residuals": residuals,
                    "fit_success": True,
                }
            )

            # Calculate dynamic range
            max_attenuation_db = np.max(
                self.angle_sweep_data["attenuations_db"][
                    np.isfinite(self.angle_sweep_data["attenuations_db"])
                ]
            )
            min_attenuation_db = np.min(
                self.angle_sweep_data["attenuations_db"][
                    np.isfinite(self.angle_sweep_data["attenuations_db"])
                ]
            )

            self.fit_results["dynamic_range_db"] = (
                max_attenuation_db - min_attenuation_db
            )
            self.fit_results["max_attenuation_db"] = max_attenuation_db
            self.fit_results["min_attenuation_db"] = min_attenuation_db

            logger.info(f"Attenuation model fit successful:")
            logger.info(f"  Amplitude: {amplitude:.6f} ± {amplitude_err:.6f}")
            logger.info(f"  Phase: {phase:.2f} ± {phase_err:.2f}°")
            logger.info(f"  Offset: {offset:.6f} ± {offset_err:.6f}")
            if "extinction_ratio" in self.fit_results:
                logger.info(
                    f"  Extinction ratio: {self.fit_results['extinction_ratio']:.2e}"
                )
            logger.info(f"  R²: {r_squared:.6f}")
            logger.info(
                f"  Dynamic range: {self.fit_results['dynamic_range_db']:.1f} dB"
            )

        except Exception as e:
            logger.error(f"Attenuation model fitting failed: {e}")
            self.fit_results = {"fit_success": False, "error": str(e)}

    def generate_attenuation_lookup_tables(self, current_step):
        """Generate lookup tables for target attenuation levels."""
        if not hasattr(self, "fit_results") or not self.fit_results.get(
            "fit_success", False
        ):
            raise ExperimentError(
                "Cannot generate lookup tables - model fitting failed"
            )

        target_att_str = self.settings.child(
            "attenuator_calibration", "attenuation_mapping", "target_attenuations_db"
        ).value()
        target_attenuations = [float(x.strip()) for x in target_att_str.split(",")]
        tolerance_db = self.settings.child(
            "attenuator_calibration", "attenuation_mapping", "attenuation_tolerance_db"
        ).value()
        max_iterations = self.settings.child(
            "attenuator_calibration", "attenuation_mapping", "max_iterations"
        ).value()

        self.attenuation_lookup_tables = {
            "target_attenuations_db": target_attenuations,
            "angles": [],
            "achieved_attenuations_db": [],
            "powers": [],
            "errors_db": [],
        }

        # Create inverse lookup function
        angles_hr = np.linspace(0, 360, 3601)  # High resolution

        # Calculate powers for high-resolution angles using fit
        if self.fit_results["fit_function"] == "enhanced_malus":
            powers_hr = attenuator_malus_law(
                angles_hr,
                self.fit_results["amplitude"],
                self.fit_results["phase"],
                self.fit_results["offset"],
                self.fit_results["extinction_ratio"],
            )
        else:
            powers_hr = attenuator_malus_law(
                angles_hr,
                self.fit_results["amplitude"],
                self.fit_results["phase"],
                self.fit_results["offset"],
                1e-4,
            )

        # Calculate attenuations
        attenuations_hr = np.array(
            [calculate_attenuation_db(self.reference_power, p) for p in powers_hr]
        )

        # Find angles for target attenuations
        for target_att in target_attenuations:
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Finding angle for {target_att:.1f} dB attenuation")

            # Check if target is within achievable range
            if target_att > self.fit_results["max_attenuation_db"]:
                logger.warning(
                    f"Target attenuation {target_att:.1f} dB exceeds maximum achievable {self.fit_results['max_attenuation_db']:.1f} dB"
                )
                # Use angle that gives maximum attenuation
                best_angle = angles_hr[np.argmax(attenuations_hr)]
                achieved_att = self.fit_results["max_attenuation_db"]

            elif target_att < self.fit_results["min_attenuation_db"]:
                logger.warning(
                    f"Target attenuation {target_att:.1f} dB below minimum achievable {self.fit_results['min_attenuation_db']:.1f} dB"
                )
                # Use angle that gives minimum attenuation
                best_angle = angles_hr[np.argmin(attenuations_hr)]
                achieved_att = self.fit_results["min_attenuation_db"]

            else:
                # Find closest angle
                diff = np.abs(attenuations_hr - target_att)
                best_idx = np.argmin(diff)
                best_angle = angles_hr[best_idx]
                achieved_att = attenuations_hr[best_idx]

            # Calculate corresponding power
            if self.fit_results["fit_function"] == "enhanced_malus":
                achieved_power = attenuator_malus_law(
                    best_angle,
                    self.fit_results["amplitude"],
                    self.fit_results["phase"],
                    self.fit_results["offset"],
                    self.fit_results["extinction_ratio"],
                )
            else:
                achieved_power = attenuator_malus_law(
                    best_angle,
                    self.fit_results["amplitude"],
                    self.fit_results["phase"],
                    self.fit_results["offset"],
                    1e-4,
                )

            error_db = abs(achieved_att - target_att)

            # Store results
            self.attenuation_lookup_tables["angles"].append(best_angle)
            self.attenuation_lookup_tables["achieved_attenuations_db"].append(
                achieved_att
            )
            self.attenuation_lookup_tables["powers"].append(achieved_power)
            self.attenuation_lookup_tables["errors_db"].append(error_db)

            logger.info(
                f"Target {target_att:.1f} dB -> Angle {best_angle:.2f}°, "
                f"Achieved {achieved_att:.2f} dB (Error: {error_db:.3f} dB)"
            )

            current_step += 1
            self.update_progress((current_step / self.total_steps) * 100)

        # Convert lists to arrays
        for key in ["angles", "achieved_attenuations_db", "powers", "errors_db"]:
            self.attenuation_lookup_tables[key] = np.array(
                self.attenuation_lookup_tables[key]
            )

        # Create interpolation function for runtime use
        try:
            self.angle_for_attenuation = interp1d(
                self.attenuation_lookup_tables["achieved_attenuations_db"],
                self.attenuation_lookup_tables["angles"],
                kind="linear",
                bounds_error=False,
                fill_value="extrapolate",
            )
        except Exception as e:
            logger.warning(f"Failed to create attenuation interpolation function: {e}")

        logger.info("Attenuation lookup tables generated successfully")
        return current_step

    def calibrate_wavelength_dependence(self, current_step):
        """Calibrate wavelength-dependent attenuation characteristics."""
        wl_start = self.settings.child(
            "attenuator_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "start_nm",
        ).value()
        wl_stop = self.settings.child(
            "attenuator_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "stop_nm",
        ).value()
        wl_step = self.settings.child(
            "attenuator_calibration",
            "wavelength_calibration",
            "wavelength_range",
            "step_nm",
        ).value()

        ref_angles_str = self.settings.child(
            "attenuator_calibration", "wavelength_calibration", "reference_angles"
        ).value()
        ref_angles = [float(x.strip()) for x in ref_angles_str.split(",")]

        wavelengths = np.arange(wl_start, wl_stop + wl_step, wl_step)

        self.log_status("Measuring wavelength-dependent attenuation")

        # Initialize wavelength calibration data
        self.wavelength_dependent_data = {
            "wavelengths": wavelengths,
            "reference_angles": ref_angles,
            "attenuations": np.zeros((len(wavelengths), len(ref_angles))),
            "powers": np.zeros((len(wavelengths), len(ref_angles))),
            "reference_powers": np.zeros(len(wavelengths)),
        }

        maitai = self.modules["MaiTai"]
        power_meter = self.modules["Newport1830C"]
        rotation_module = self.settings.child(
            "attenuator_calibration", "hardware_settings", "rotation_module"
        ).value()
        attenuator = self.modules[rotation_module]

        stabilization_time = self.settings.child(
            "hardware_settings", "stabilization_time"
        ).value()
        settling_time = self.settings.child(
            "attenuator_calibration", "hardware_settings", "settling_time"
        ).value()
        averaging_samples = self.settings.child(
            "attenuator_calibration", "power_measurement", "averaging_samples"
        ).value()

        for wl_idx, wavelength in enumerate(wavelengths):
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Wavelength calibration at {wavelength} nm")

            # Set wavelength and wait for stabilization
            target_wl = DataActuator(data=[wavelength])
            maitai.move_abs(target_wl)
            time.sleep(stabilization_time)

            # Measure reference power at minimum attenuation
            target_angle = DataActuator(data=[0.0])  # Minimum attenuation angle
            attenuator.move_abs(target_angle)
            time.sleep(settling_time)

            # Measure reference power
            ref_power_readings = []
            for _ in range(averaging_samples):
                power = power_meter.get_actuator_value()
                if isinstance(power, DataActuator):
                    power_value = power.value()
                else:
                    power_value = float(power)
                ref_power_readings.append(power_value)
                time.sleep(0.02)

            ref_power = np.mean(ref_power_readings)
            self.wavelength_dependent_data["reference_powers"][wl_idx] = ref_power

            # Measure at reference angles
            for angle_idx, angle in enumerate(ref_angles):
                if self._check_stop_requested():
                    return current_step

                # Set attenuator angle
                target_angle = DataActuator(data=[angle])
                attenuator.move_abs(target_angle)
                time.sleep(settling_time)

                # Measure power
                power_readings = []
                for _ in range(averaging_samples):
                    power = power_meter.get_actuator_value()
                    if isinstance(power, DataActuator):
                        power_value = power.value()
                    else:
                        power_value = float(power)
                    power_readings.append(power_value)
                    time.sleep(0.02)

                avg_power = np.mean(power_readings)
                attenuation_db = calculate_attenuation_db(ref_power, avg_power)

                # Store results
                self.wavelength_dependent_data["powers"][wl_idx, angle_idx] = avg_power
                self.wavelength_dependent_data["attenuations"][
                    wl_idx, angle_idx
                ] = attenuation_db

                logger.debug(f"λ={wavelength}nm, θ={angle}° -> {attenuation_db:.2f}dB")

                # Update progress
                current_step += 1
                progress = (current_step / self.total_steps) * 100
                self.update_progress(progress)

        logger.info("Wavelength-dependent calibration completed")
        return current_step

    def validate_calibration_accuracy(self, current_step):
        """Validate calibration accuracy using independent test points."""
        val_att_str = self.settings.child(
            "attenuator_calibration", "validation", "validation_attenuations_db"
        ).value()
        validation_attenuations = [float(x.strip()) for x in val_att_str.split(",")]
        repeatability_tests = self.settings.child(
            "attenuator_calibration", "validation", "repeatability_tests"
        ).value()
        max_error_db = self.settings.child(
            "attenuator_calibration", "validation", "max_error_db"
        ).value()
        hysteresis_test = self.settings.child(
            "attenuator_calibration", "validation", "hysteresis_test"
        ).value()

        self.log_status("Validating calibration accuracy")

        rotation_module = self.settings.child(
            "attenuator_calibration", "hardware_settings", "rotation_module"
        ).value()
        attenuator = self.modules[rotation_module]
        power_meter = self.modules["Newport1830C"]
        settling_time = self.settings.child(
            "attenuator_calibration", "hardware_settings", "settling_time"
        ).value()

        validation_results = []

        for target_att in validation_attenuations:
            if self._check_stop_requested():
                return current_step

            self.log_status(f"Validating {target_att:.1f} dB attenuation")

            # Get predicted angle from lookup table
            if hasattr(self, "angle_for_attenuation"):
                predicted_angle = float(self.angle_for_attenuation(target_att))
            else:
                # Fallback to direct table lookup
                idx = np.argmin(
                    np.abs(
                        self.attenuation_lookup_tables["achieved_attenuations_db"]
                        - target_att
                    )
                )
                predicted_angle = self.attenuation_lookup_tables["angles"][idx]

            # Perform repeatability tests
            measured_attenuations = []
            measured_powers = []

            for rep in range(repeatability_tests):
                # Move to predicted angle
                target_angle = DataActuator(data=[predicted_angle])
                attenuator.move_abs(target_angle)
                time.sleep(settling_time)

                # Measure power
                power = power_meter.get_actuator_value()
                if isinstance(power, DataActuator):
                    power_value = power.value()
                else:
                    power_value = float(power)

                measured_powers.append(power_value)

                # Calculate attenuation
                measured_att = calculate_attenuation_db(
                    self.reference_power, power_value
                )
                measured_attenuations.append(measured_att)

                # Update progress
                current_step += 1
                progress = (current_step / self.total_steps) * 100
                self.update_progress(progress)

            # Calculate validation metrics
            mean_att = np.mean(measured_attenuations)
            std_att = np.std(measured_attenuations)
            error_db = abs(mean_att - target_att)
            repeatability_db = std_att

            validation_result = {
                "target_attenuation_db": target_att,
                "predicted_angle": predicted_angle,
                "measured_attenuations_db": measured_attenuations,
                "measured_powers": measured_powers,
                "mean_attenuation_db": mean_att,
                "std_attenuation_db": std_att,
                "error_db": error_db,
                "repeatability_db": repeatability_db,
                "passed": error_db < max_error_db,
            }

            validation_results.append(validation_result)

            logger.info(
                f"Validation: Target {target_att:.1f}dB -> "
                f"Achieved {mean_att:.2f}±{std_att:.3f}dB "
                f"(Error: {error_db:.3f}dB)"
            )

        # Store validation results
        self.validation_results = {
            "validation_points": validation_results,
            "summary": {
                "total_points": len(validation_results),
                "passed_points": sum(1 for r in validation_results if r["passed"]),
                "pass_rate": sum(1 for r in validation_results if r["passed"])
                / len(validation_results)
                * 100,
                "mean_error_db": np.mean([r["error_db"] for r in validation_results]),
                "max_error_db": np.max([r["error_db"] for r in validation_results]),
                "mean_repeatability_db": np.mean(
                    [r["repeatability_db"] for r in validation_results]
                ),
            },
        }

        summary = self.validation_results["summary"]
        logger.info(
            f"Validation summary: {summary['passed_points']}/{summary['total_points']} points passed"
        )
        logger.info(
            f"Mean error: {summary['mean_error_db']:.3f} dB, Max error: {summary['max_error_db']:.3f} dB"
        )
        logger.info(f"Mean repeatability: {summary['mean_repeatability_db']:.3f} dB")

        return current_step

    def save_calibration_results(self):
        """Save all calibration results to HDF5 file."""
        try:
            with h5py.File(self.data_filepath, "w") as f:
                # Save angle sweep data
                sweep_group = f.create_group("angle_sweep")
                for key, value in self.angle_sweep_data.items():
                    if isinstance(value, np.ndarray):
                        sweep_group.create_dataset(key, data=value)
                    else:
                        sweep_group.attrs[key] = value

                # Save fit results
                if hasattr(self, "fit_results"):
                    fit_group = f.create_group("fit_results")
                    for key, value in self.fit_results.items():
                        if isinstance(value, np.ndarray):
                            fit_group.create_dataset(key, data=value)
                        else:
                            fit_group.attrs[key] = value

                # Save attenuation lookup tables
                if hasattr(self, "attenuation_lookup_tables"):
                    lookup_group = f.create_group("attenuation_lookup_tables")
                    for key, value in self.attenuation_lookup_tables.items():
                        if isinstance(value, np.ndarray):
                            lookup_group.create_dataset(key, data=value)
                        else:
                            lookup_group.attrs[key] = value

                # Save wavelength-dependent data
                if hasattr(self, "wavelength_dependent_data"):
                    wl_group = f.create_group("wavelength_dependent_data")
                    for key, value in self.wavelength_dependent_data.items():
                        wl_group.create_dataset(key, data=value)

                # Save validation results
                if hasattr(self, "validation_results"):
                    val_group = f.create_group("validation_results")

                    # Save individual validation points
                    for i, result in enumerate(
                        self.validation_results["validation_points"]
                    ):
                        point_group = val_group.create_group(f"point_{i}")
                        for key, value in result.items():
                            if isinstance(value, (list, np.ndarray)):
                                point_group.create_dataset(key, data=value)
                            else:
                                point_group.attrs[key] = value

                    # Save validation summary
                    summary_group = val_group.create_group("summary")
                    for key, value in self.validation_results["summary"].items():
                        summary_group.attrs[key] = value

                # Save hardware configuration
                config_group = f.create_group("hardware_configuration")
                config_group.attrs["attenuator_type"] = self.attenuator_config["type"]
                config_group.attrs["reference_wavelength"] = self.reference_wavelength
                config_group.attrs["rotation_module"] = self.settings.child(
                    "attenuator_calibration", "hardware_settings", "rotation_module"
                ).value()

                # Save experiment metadata
                f.attrs["experiment_name"] = self.experiment_name
                f.attrs["experiment_type"] = self.experiment_type
                f.attrs["creation_time"] = datetime.now().isoformat()
                f.attrs["calibration_version"] = "1.0"

            logger.info(
                f"Variable attenuator calibration results saved to {self.data_filepath}"
            )
            self.log_status(f"Calibration data saved to {self.data_filepath}")

        except Exception as e:
            logger.error(f"Failed to save calibration results: {e}")
            raise ExperimentError(f"Failed to save calibration results: {e}")

    def _check_stop_requested(self):
        """Check if experiment stop was requested."""
        if hasattr(self, "experiment_thread") and self.experiment_thread:
            return self.experiment_thread._stop_requested
        return False

    def get_angle_for_attenuation(self, target_attenuation_db):
        """
        Get attenuator angle for specified target attenuation.

        Args:
            target_attenuation_db (float): Target attenuation in dB

        Returns:
            float: Attenuator angle in degrees
        """
        if not hasattr(self, "angle_for_attenuation"):
            raise ExperimentError("Attenuation calibration not available")

        try:
            angle = float(self.angle_for_attenuation(target_attenuation_db))
            return angle
        except Exception as e:
            raise ExperimentError(f"Failed to calculate angle for attenuation: {e}")

    def get_attenuation_for_angle(self, angle):
        """
        Get attenuation for specified attenuator angle.

        Args:
            angle (float): Attenuator angle in degrees

        Returns:
            float: Expected attenuation in dB
        """
        if not hasattr(self, "fit_results") or not self.fit_results.get(
            "fit_success", False
        ):
            raise ExperimentError("Attenuation calibration not available")

        try:
            # Calculate power using fit
            if self.fit_results["fit_function"] == "enhanced_malus":
                power = attenuator_malus_law(
                    angle,
                    self.fit_results["amplitude"],
                    self.fit_results["phase"],
                    self.fit_results["offset"],
                    self.fit_results["extinction_ratio"],
                )
            else:
                power = attenuator_malus_law(
                    angle,
                    self.fit_results["amplitude"],
                    self.fit_results["phase"],
                    self.fit_results["offset"],
                    1e-4,
                )

            # Calculate attenuation
            attenuation_db = calculate_attenuation_db(self.reference_power, power)
            return float(attenuation_db)

        except Exception as e:
            raise ExperimentError(f"Failed to calculate attenuation for angle: {e}")
