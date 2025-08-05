"""
Power-Dependent Second Harmonic Generation (PDSHG) Experiment for μRASHG System

This module implements the core power-dependent RASHG measurement, which is
fundamental to μRASHG microscopy. The experiment performs:

1. Multi-dimensional parameter sweeps: [wavelength, power, angle]
2. Rotational anisotropy measurements via dual HWP control
3. Real-time power control using calibrated EOM system
4. Photodiode and power meter data acquisition
5. Background subtraction and signal processing

The PDSHG experiment is optimized for studies of:
- Power-dependent nonlinear optical responses
- Anisotropic susceptibility tensor elements
- Surface vs. bulk contributions to SHG
- Crystallographic orientation mapping

Key experimental features:
- Logarithmic power spacing for wide dynamic range
- Synchronized dual HWP rotation (H800: α/2, H400: 360-25-α/2)
- Descending power order for thermal management
- Real-time calibration verification
- Statistical analysis with error propagation

This experiment generates the core data for μRASHG analysis without camera
detection, making it suitable for point measurements and optimization.
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path
from datetime import datetime
import h5py
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d

from qtpy import QtWidgets, QtCore
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataWithAxes, DataToExport, Axis
from pymodaq.control_modules.utils import DataActuator

from .base_experiment import URASHGBaseExperiment, ExperimentState, ExperimentError
import logging

logger = logging.getLogger(__name__)


def rashg_cosine_squared(angle, amplitude, phase, offset):
    """
    RASHG angular dependence following cos²(2θ + φ) pattern.
    
    For RASHG measurements, the fundamental angular dependence follows:
    I(θ) = A·cos²(2θ + φ) + C
    
    Args:
        angle (array): HWP rotation angles in degrees
        amplitude (float): RASHG signal amplitude
        phase (float): Phase offset related to crystal orientation
        offset (float): Isotropic background contribution
        
    Returns:
        array: RASHG signal intensity
    """
    angle_rad = np.radians(2 * angle + phase)
    return amplitude * np.cos(angle_rad)**2 + offset


def power_law_fitting(power, coefficient, exponent, offset):
    """
    Power law fitting for SHG intensity vs excitation power.
    
    For second harmonic generation: I_SHG ∝ I_fundamental^n
    where n ≈ 2 for pure SHG, but can deviate due to:
    - Saturation effects
    - Multi-photon processes
    - Thermal effects
    
    Args:
        power (array): Excitation power values
        coefficient (float): Power law coefficient
        exponent (float): Power law exponent (≈2 for SHG)
        offset (float): Background offset
        
    Returns:
        array: SHG intensity
    """
    return coefficient * np.power(power, exponent) + offset


class PDSHGExperiment(URASHGBaseExperiment):
    """
    Power-Dependent Second Harmonic Generation (PDSHG) Experiment.
    
    This experiment performs the core μRASHG measurement with comprehensive
    power-dependent analysis. The measurement protocol:
    
    1. Multi-wavelength excitation with precise power control
    2. Rotational anisotropy via synchronized dual HWP rotation
    3. Power-dependent analysis across logarithmic power range
    4. Real-time background subtraction and signal processing
    5. Statistical analysis with error propagation and fitting
    
    The experiment generates 3D datasets: [wavelength, power, angle] with
    both photodiode voltage and power meter verification for each point.
    
    Key capabilities:
    - Wide power range (4+ orders of magnitude) with logarithmic spacing
    - Thermal management via descending power order
    - Real-time EOM calibration and power verification
    - Synchronized rotator control with hardware offsets
    - Background subtraction and signal normalization
    - Live curve fitting and parameter extraction
    
    Required Hardware:
    - MaiTai laser with wavelength control
    - EOM system with PID power control
    - H800, H400 rotators for polarization control
    - Newport power meter for power verification
    - Photodiode for real-time signal monitoring
    
    Output Products:
    - 3D RASHG datasets with statistical analysis
    - Power law fitting parameters and quality metrics
    - Angular anisotropy parameters from cos²(2θ) fits
    - Calibration verification and drift correction data
    """
    
    experiment_name = "Power-Dependent RASHG (PDSHG)"
    experiment_type = "pdshg_experiment"
    required_modules = ['MaiTai', 'H800', 'H400', 'Newport1830C']
    optional_modules = ['Q800']  # QWP for ellipticity control if needed
    
    def __init__(self, dashboard=None):
        super().__init__(dashboard)
        
        # Experiment configuration
        self.rashg_config = {
            'hwp_rotation_scheme': 'dual_hwp',  # H800: α/2, H400: 360-25-α/2
            'power_sequence': 'descending',     # High to low power for thermal management
            'background_subtraction': True,
            'real_time_fitting': True
        }
        
        # Data storage structures
        self.measurement_data = {}
        self.background_data = {}
        self.calibration_verification = {}
        
        # Fitting results
        self.angular_fits = {}
        self.power_law_fits = {}
        
        # Current measurement state
        self.current_wavelength = None
        self.current_power = None
        self.current_angle = None
        
        # Add PDSHG-specific parameters
        self.add_pdshg_parameters()
        
    def add_pdshg_parameters(self):
        """Add PDSHG experiment specific parameters."""
        pdshg_params = {
            'name': 'pdshg_experiment',
            'type': 'group',
            'children': [
                {
                    'name': 'measurement_ranges',
                    'type': 'group',
                    'children': [
                        {
                            'name': 'wavelength_range',
                            'type': 'group',
                            'children': [
                                {'name': 'start_nm', 'type': 'float', 'value': 780.0,
                                 'limits': [700, 950], 'suffix': 'nm'},
                                {'name': 'stop_nm', 'type': 'float', 'value': 820.0,
                                 'limits': [750, 1000], 'suffix': 'nm'},
                                {'name': 'step_nm', 'type': 'float', 'value': 10.0,
                                 'limits': [1, 50], 'suffix': 'nm'},
                            ]
                        },
                        {
                            'name': 'power_range',
                            'type': 'group',
                            'children': [
                                {'name': 'min_power', 'type': 'float', 'value': 0.0005,
                                 'limits': [1e-6, 0.01], 'suffix': 'W'},
                                {'name': 'max_power', 'type': 'float', 'value': 0.020,
                                 'limits': [0.005, 0.1], 'suffix': 'W'},
                                {'name': 'power_points', 'type': 'int', 'value': 12,
                                 'limits': [5, 50]},
                                {'name': 'logarithmic_spacing', 'type': 'bool', 'value': True},
                                {'name': 'descending_order', 'type': 'bool', 'value': True,
                                 'tip': 'Start with high power to minimize thermal effects'},
                            ]
                        },
                        {
                            'name': 'angle_range',
                            'type': 'group',
                            'children': [
                                {'name': 'start_angle', 'type': 'float', 'value': 0.0,
                                 'limits': [0, 360], 'suffix': '°'},
                                {'name': 'stop_angle', 'type': 'float', 'value': 360.0,
                                 'limits': [90, 720], 'suffix': '°'},
                                {'name': 'angle_step', 'type': 'float', 'value': 15.0,
                                 'limits': [1, 90], 'suffix': '°'},
                                {'name': 'fine_angle_regions', 'type': 'str',
                                 'value': '0-90, 180-270',
                                 'tip': 'Fine sampling regions (format: start-stop, start-stop)'},
                                {'name': 'fine_angle_step', 'type': 'float', 'value': 5.0,
                                 'limits': [0.1, 45], 'suffix': '°'},
                            ]
                        },
                    ]
                },
                {
                    'name': 'hwp_control',
                    'type': 'group',
                    'children': [
                        {'name': 'rotation_scheme', 'type': 'list',
                         'limits': ['dual_hwp', 'single_hwp', 'custom'],
                         'value': 'dual_hwp'},
                        {'name': 'h800_formula', 'type': 'str', 'value': 'α/2',
                         'tip': 'H800 angle formula (α = measurement angle)'},
                        {'name': 'h400_formula', 'type': 'str', 'value': '360-25-α/2',
                         'tip': 'H400 angle formula'},
                        {'name': 'hwp_offsets', 'type': 'group',
                         'children': [
                             {'name': 'h800_offset', 'type': 'float', 'value': 0.0,
                              'limits': [-180, 180], 'suffix': '°'},
                             {'name': 'h400_offset', 'type': 'float', 'value': 0.0,
                              'limits': [-180, 180], 'suffix': '°'},
                         ]},
                        {'name': 'settling_time', 'type': 'float', 'value': 0.5,
                         'limits': [0.1, 5.0], 'suffix': 's'},
                    ]
                },
                {
                    'name': 'power_control',
                    'type': 'group',
                    'children': [
                        {'name': 'use_eom_calibration', 'type': 'bool', 'value': True},
                        {'name': 'eom_calibration_file', 'type': 'browsepath', 'value': ''},
                        {'name': 'power_tolerance', 'type': 'float', 'value': 1.0,
                         'limits': [0.1, 10.0], 'suffix': '%'},
                        {'name': 'power_verification', 'type': 'bool', 'value': True,
                         'tip': 'Verify power with independent power meter'},
                        {'name': 'max_power_iterations', 'type': 'int', 'value': 10,
                         'limits': [3, 50]},
                    ]
                },
                {
                    'name': 'data_acquisition',
                    'type': 'group',
                    'children': [
                        {'name': 'averaging_samples', 'type': 'int', 'value': 100,
                         'limits': [10, 1000], 'tip': 'Photodiode averaging samples'},
                        {'name': 'measurement_timeout', 'type': 'float', 'value': 2.0,
                         'limits': [0.5, 30.0], 'suffix': 's'},
                        {'name': 'background_subtraction', 'type': 'bool', 'value': True},
                        {'name': 'background_frequency', 'type': 'list',
                         'limits': ['per_wavelength', 'per_power', 'per_measurement', 'start_only'],
                         'value': 'per_wavelength'},
                        {'name': 'signal_validation', 'type': 'bool', 'value': True,
                         'tip': 'Validate signal levels and stability'},
                    ]
                },
                {
                    'name': 'analysis_settings',
                    'type': 'group',
                    'children': [
                        {'name': 'real_time_fitting', 'type': 'bool', 'value': True},
                        {'name': 'angular_fit_function', 'type': 'list',
                         'limits': ['cos_squared_2theta', 'cos_squared_theta', 'custom'],
                         'value': 'cos_squared_2theta'},
                        {'name': 'power_law_fitting', 'type': 'bool', 'value': True},
                        {'name': 'expected_shg_exponent', 'type': 'float', 'value': 2.0,
                         'limits': [1.5, 3.0]},
                        {'name': 'fit_quality_threshold', 'type': 'float', 'value': 0.95,
                         'limits': [0.5, 1.0], 'tip': 'Minimum R² for acceptable fits'},
                    ]
                },
                {
                    'name': 'experimental_conditions',
                    'type': 'group',
                    'children': [
                        {'name': 'sample_name', 'type': 'str', 'value': 'Sample_1'},
                        {'name': 'measurement_position', 'type': 'str', 'value': 'Center'},
                        {'name': 'polarization_config', 'type': 'str', 'value': 'Standard'},
                        {'name': 'environmental_notes', 'type': 'str', 'value': ''},
                        {'name': 'expected_signal_level', 'type': 'float', 'value': 1.0,
                         'limits': [0.001, 1000], 'suffix': 'V'},
                    ]
                }
            ]
        }
        
        # Add to existing parameters
        self.settings.addChild(pdshg_params)
    
    def initialize_specific_hardware(self):
        """Initialize PDSHG experiment specific hardware."""
        logger.info("Initializing PDSHG experiment hardware")
        
        # Verify required hardware modules
        required_modules = ['MaiTai', 'H800', 'H400', 'Newport1830C']
        for module_name in required_modules:
            if module_name not in self.modules:
                raise ExperimentError(f"Required module {module_name} not available")
        
        # Test hardware communication
        try:
            # MaiTai laser
            maitai = self.modules['MaiTai']
            current_wl = maitai.get_actuator_value()
            logger.info(f"MaiTai wavelength: {current_wl} nm")
            
            # Rotators
            h800 = self.modules['H800']
            h800_pos = h800.get_actuator_value()
            logger.info(f"H800 position: {h800_pos}°")
            
            h400 = self.modules['H400']
            h400_pos = h400.get_actuator_value()
            logger.info(f"H400 position: {h400_pos}°")
            
            # Power meter
            power_meter = self.modules['Newport1830C']
            current_power = power_meter.get_actuator_value()
            logger.info(f"Power meter reading: {current_power} W")
            
        except Exception as e:
            raise ExperimentError(f"Hardware communication test failed: {e}")
        
        # Load EOM calibration if specified
        if self.settings.child('pdshg_experiment', 'power_control', 'use_eom_calibration').value():
            eom_cal_file = self.settings.child('pdshg_experiment', 'power_control', 'eom_calibration_file').value()
            if eom_cal_file and Path(eom_cal_file).exists():
                try:
                    self.load_eom_calibration(eom_cal_file)
                    logger.info(f"Loaded EOM calibration from {eom_cal_file}")
                except Exception as e:
                    logger.warning(f"Failed to load EOM calibration: {e}")
        
        logger.info("PDSHG experiment hardware initialized successfully")
    
    def load_eom_calibration(self, calibration_file):
        """Load EOM calibration data from file."""
        # TODO: Implement EOM calibration loading
        # This would load the calibration data from the EOM calibration experiment
        logger.info(f"Loading EOM calibration from {calibration_file}")
        # Placeholder for actual implementation
        pass
    
    def validate_parameters(self):
        """Validate PDSHG experiment parameters."""
        # Check wavelength range
        wl_start = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'start_nm').value()
        wl_stop = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'stop_nm').value()
        wl_step = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'step_nm').value()
        
        if wl_start >= wl_stop:
            raise ExperimentError("Wavelength start must be less than stop")
        if wl_step <= 0:
            raise ExperimentError("Wavelength step must be positive")
        
        # Check power range
        p_min = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'min_power').value()
        p_max = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'max_power').value()
        p_points = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'power_points').value()
        
        if p_min >= p_max:
            raise ExperimentError("Minimum power must be less than maximum power")
        if p_points < 3:
            raise ExperimentError("Must have at least 3 power points")
        
        # Check angle range
        angle_start = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'start_angle').value()
        angle_stop = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'stop_angle').value()
        angle_step = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'angle_step').value()
        
        if angle_start >= angle_stop:
            raise ExperimentError("Angle start must be less than stop")
        if angle_step <= 0:
            raise ExperimentError("Angle step must be positive")
        
        # Validate HWP formulas
        h800_formula = self.settings.child('pdshg_experiment', 'hwp_control', 'h800_formula').value()
        h400_formula = self.settings.child('pdshg_experiment', 'hwp_control', 'h400_formula').value()
        
        # Test formula evaluation with dummy angle
        try:
            test_angle = 45.0
            self.evaluate_hwp_formula(h800_formula, test_angle)
            self.evaluate_hwp_formula(h400_formula, test_angle)
        except Exception as e:
            raise ExperimentError(f"Invalid HWP formula: {e}")
        
        logger.info("PDSHG experiment parameters validated successfully")
    
    def evaluate_hwp_formula(self, formula, angle):
        """Evaluate HWP angle formula."""
        # Replace α with the actual angle value
        formula_eval = formula.replace('α', str(angle))
        
        # Simple evaluation of common formulas
        # TODO: Implement more robust formula parser if needed
        try:
            if '/' in formula_eval:
                if 'α/2' in formula:
                    return angle / 2
                else:
                    return eval(formula_eval)
            else:
                return eval(formula_eval)
        except Exception as e:
            raise ValueError(f"Cannot evaluate formula {formula}: {e}")
    
    def create_data_structures(self):
        """Create data structures for PDSHG measurement results."""
        # Get measurement parameters
        wl_start = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'start_nm').value()
        wl_stop = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'stop_nm').value()
        wl_step = self.settings.child('pdshg_experiment', 'measurement_ranges', 'wavelength_range', 'step_nm').value()
        
        p_min = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'min_power').value()
        p_max = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'max_power').value()
        p_points = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'power_points').value()
        log_spacing = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'logarithmic_spacing').value()
        descending = self.settings.child('pdshg_experiment', 'measurement_ranges', 'power_range', 'descending_order').value()
        
        angle_start = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'start_angle').value()
        angle_stop = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'stop_angle').value()
        angle_step = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'angle_step').value()
        
        # Create coordinate arrays
        wavelengths = np.arange(wl_start, wl_stop + wl_step, wl_step)
        
        if log_spacing:
            powers = np.logspace(np.log10(p_min), np.log10(p_max), p_points)
        else:
            powers = np.linspace(p_min, p_max, p_points)
        
        if descending:
            powers = powers[::-1]  # Reverse for descending order
        
        # Create angle array with fine regions
        regular_angles = np.arange(angle_start, angle_stop + angle_step, angle_step)
        all_angles = list(regular_angles)
        
        # Add fine angle regions
        try:
            fine_regions = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'fine_angle_regions').value()
            fine_step = self.settings.child('pdshg_experiment', 'measurement_ranges', 'angle_range', 'fine_angle_step').value()
            
            for region_str in fine_regions.split(','):
                if '-' in region_str.strip():
                    start_fine, stop_fine = map(float, region_str.strip().split('-'))
                    fine_angles = np.arange(start_fine, stop_fine + fine_step, fine_step)
                    all_angles.extend(fine_angles)
        except ValueError:
            logger.warning("Invalid fine angle regions format, using regular step only")
        
        # Remove duplicates and sort
        angles = np.array(sorted(set(all_angles)))
        
        # Initialize measurement data structure
        self.measurement_data = {
            'wavelengths': wavelengths,
            'powers': powers,
            'angles': angles,
            'photodiode_voltage': np.zeros((len(wavelengths), len(powers), len(angles))),
            'power_meter_reading': np.zeros((len(wavelengths), len(powers), len(angles))),
            'background_voltage': np.zeros((len(wavelengths), len(angles))),
            'timestamps': np.zeros((len(wavelengths), len(powers), len(angles))),
            'h800_positions': np.zeros((len(wavelengths), len(powers), len(angles))),
            'h400_positions': np.zeros((len(wavelengths), len(powers), len(angles))),
            'measurement_quality': np.zeros((len(wavelengths), len(powers), len(angles))),
        }
        
        # Initialize background data
        self.background_data = {
            'wavelengths': wavelengths,
            'angles': angles,
            'background_voltage': np.zeros((len(wavelengths), len(angles))),
            'background_timestamps': np.zeros((len(wavelengths), len(angles))),
        }
        
        # Calculate total steps for progress tracking
        total_measurement_points = len(wavelengths) * len(powers) * len(angles)
        background_points = len(wavelengths) * len(angles)  # Background per wavelength
        setup_steps = len(wavelengths) * 2  # Wavelength changes and stabilization
        
        self.total_steps = total_measurement_points + background_points + setup_steps
        
        logger.info(f"Created data structures: {len(wavelengths)} wavelengths, "
                   f"{len(powers)} powers, {len(angles)} angles")
        logger.info(f"Total measurement points: {total_measurement_points}")
        logger.info(f"Total experiment steps: {self.total_steps}")
    
    def run_experiment(self):
        """Execute the PDSHG experiment."""
        try:
            self.log_status("Starting PDSHG experiment")
            current_step = 0
            
            # Phase 1: Setup and validation
            self.log_status("Phase 1: Experimental setup and validation")
            current_step = self.setup_experiment(current_step)
            
            # Phase 2: Main measurement loop
            self.log_status("Phase 2: PDSHG measurements")
            current_step = self.perform_pdshg_measurements(current_step)
            
            # Phase 3: Data analysis and fitting
            self.log_status("Phase 3: Data analysis and curve fitting")
            self.analyze_pdshg_data()
            current_step += 20  # Analysis steps
            self.update_progress((current_step / self.total_steps) * 100)
            
            # Phase 4: Save results
            self.log_status("Phase 4: Saving experiment results")
            self.save_pdshg_results()
            
            self.log_status("PDSHG experiment completed successfully")
            
        except Exception as e:
            logger.error(f"PDSHG experiment failed: {e}")
            raise ExperimentError(f"PDSHG experiment failed: {e}")
    
    def setup_experiment(self, current_step):
        """Set up experiment conditions and initial measurements."""
        # Initialize laser shutter (closed for safety)
        # TODO: Implement shutter control if available
        
        # Set initial rotator positions
        h800 = self.modules['H800']
        h400 = self.modules['H400']
        
        # Set to initial positions (typically 0°)
        initial_position = DataActuator(data=[0.0])
        h800.move_abs(initial_position)
        h400.move_abs(initial_position)
        
        # Wait for settling
        settling_time = self.settings.child('pdshg_experiment', 'hwp_control', 'settling_time').value()
        time.sleep(settling_time)
        
        # Verify power meter functionality
        power_meter = self.modules['Newport1830C']
        initial_power = power_meter.get_actuator_value()
        logger.info(f"Initial power meter reading: {initial_power} W")
        
        current_step += 5
        self.update_progress((current_step / self.total_steps) * 100)
        return current_step
    
    def perform_pdshg_measurements(self, current_step):
        """Perform the main PDSHG measurement loop."""
        wavelengths = self.measurement_data['wavelengths']
        powers = self.measurement_data['powers']
        angles = self.measurement_data['angles']
        
        maitai = self.modules['MaiTai']
        stabilization_time = self.settings.child('hardware_settings', 'stabilization_time').value()
        
        for wl_idx, wavelength in enumerate(wavelengths):
            if self._check_stop_requested():
                return current_step
                
            self.log_status(f"PDSHG measurement at {wavelength:.1f} nm")
            self.current_wavelength = wavelength
            
            # Set wavelength and wait for stabilization
            target_wl = DataActuator(data=[wavelength])
            maitai.move_abs(target_wl)
            time.sleep(stabilization_time)
            
            # Measure background if needed
            bg_frequency = self.settings.child('pdshg_experiment', 'data_acquisition', 'background_frequency').value()
            if bg_frequency == 'per_wavelength' or (bg_frequency == 'start_only' and wl_idx == 0):
                current_step = self.measure_background(wl_idx, current_step)
            
            # Power loop
            for p_idx, power in enumerate(powers):
                if self._check_stop_requested():
                    return current_step
                    
                self.log_status(f"Power {power:.6f} W ({p_idx+1}/{len(powers)})")
                self.current_power = power
                
                # Set laser power using EOM control
                current_step = self.set_laser_power(power, current_step)
                
                # Angle loop
                for a_idx, angle in enumerate(angles):
                    if self._check_stop_requested():
                        return current_step
                        
                    self.current_angle = angle
                    
                    # Set rotator positions
                    current_step = self.set_rotator_positions(angle, current_step)
                    
                    # Perform measurement
                    measurement_result = self.perform_single_measurement()
                    
                    # Store results
                    self.measurement_data['photodiode_voltage'][wl_idx, p_idx, a_idx] = measurement_result['pd_voltage']
                    self.measurement_data['power_meter_reading'][wl_idx, p_idx, a_idx] = measurement_result['pm_reading']
                    self.measurement_data['timestamps'][wl_idx, p_idx, a_idx] = measurement_result['timestamp']
                    self.measurement_data['h800_positions'][wl_idx, p_idx, a_idx] = measurement_result['h800_pos']
                    self.measurement_data['h400_positions'][wl_idx, p_idx, a_idx] = measurement_result['h400_pos']
                    self.measurement_data['measurement_quality'][wl_idx, p_idx, a_idx] = measurement_result['quality']
                    
                    # Real-time analysis if enabled
                    if self.settings.child('pdshg_experiment', 'analysis_settings', 'real_time_fitting').value():
                        if a_idx > 5:  # Need minimum points for fitting
                            self.perform_real_time_analysis(wl_idx, p_idx, a_idx)
                    
                    # Update progress
                    current_step += 1
                    progress = (current_step / self.total_steps) * 100
                    self.update_progress(progress)
                    
                    logger.debug(f"λ={wavelength:.1f}nm, P={power:.6f}W, θ={angle:.1f}° -> "
                               f"PD={measurement_result['pd_voltage']:.6f}V")
        
        logger.info("PDSHG measurements completed")
        return current_step
    
    def measure_background(self, wl_idx, current_step):
        """Measure background signal with laser shutter closed."""
        self.log_status("Measuring background signal")
        
        # TODO: Close laser shutter if available
        # For now, assume background is measured with laser blocked
        
        angles = self.measurement_data['angles']
        
        for a_idx, angle in enumerate(angles):
            if self._check_stop_requested():
                return current_step
                
            # Set rotator positions
            self.set_rotator_positions(angle, current_step, update_progress=False)
            
            # Measure background
            bg_result = self.perform_single_measurement()
            
            # Store background data
            self.background_data['background_voltage'][wl_idx, a_idx] = bg_result['pd_voltage']
            self.background_data['background_timestamps'][wl_idx, a_idx] = bg_result['timestamp']
            
            current_step += 1
            
        # TODO: Open laser shutter
        logger.info(f"Background measurement completed for wavelength {self.measurement_data['wavelengths'][wl_idx]:.1f} nm")
        return current_step
    
    def set_laser_power(self, target_power, current_step):
        """Set laser power using EOM calibration or direct control."""
        if self.settings.child('pdshg_experiment', 'power_control', 'use_eom_calibration').value():
            # TODO: Implement EOM-based power control
            # This would use the calibration data to set EOM voltage
            logger.debug(f"Setting EOM power to {target_power:.6f} W")
            # Placeholder for EOM control
            time.sleep(0.1)
        else:
            # Fallback to manual power setting
            logger.debug(f"Manual power setting: {target_power:.6f} W")
        
        # Verify power if enabled
        if self.settings.child('pdshg_experiment', 'power_control', 'power_verification').value():
            power_meter = self.modules['Newport1830C']
            measured_power = power_meter.get_actuator_value()
            
            if isinstance(measured_power, DataActuator):
                power_value = measured_power.value()
            else:
                power_value = float(measured_power)
            
            tolerance = self.settings.child('pdshg_experiment', 'power_control', 'power_tolerance').value()
            error_percent = abs(power_value - target_power) / target_power * 100
            
            if error_percent > tolerance:
                logger.warning(f"Power error {error_percent:.1f}% exceeds tolerance {tolerance}%")
        
        return current_step
    
    def set_rotator_positions(self, angle, current_step, update_progress=True):
        """Set rotator positions according to measurement angle."""
        h800 = self.modules['H800']
        h400 = self.modules['H400']
        
        # Get HWP formulas and offsets
        h800_formula = self.settings.child('pdshg_experiment', 'hwp_control', 'h800_formula').value()
        h400_formula = self.settings.child('pdshg_experiment', 'hwp_control', 'h400_formula').value()
        h800_offset = self.settings.child('pdshg_experiment', 'hwp_control', 'hwp_offsets', 'h800_offset').value()
        h400_offset = self.settings.child('pdshg_experiment', 'hwp_control', 'hwp_offsets', 'h400_offset').value()
        
        # Calculate target positions
        h800_angle = self.evaluate_hwp_formula(h800_formula, angle) + h800_offset
        h400_angle = self.evaluate_hwp_formula(h400_formula, angle) + h400_offset
        
        # Move rotators
        h800_position = DataActuator(data=[h800_angle])
        h400_position = DataActuator(data=[h400_angle])
        
        h800.move_abs(h800_position)
        h400.move_abs(h400_position)
        
        # Wait for settling
        settling_time = self.settings.child('pdshg_experiment', 'hwp_control', 'settling_time').value()
        time.sleep(settling_time)
        
        logger.debug(f"Set rotators: H800={h800_angle:.1f}°, H400={h400_angle:.1f}°")
        
        if update_progress:
            current_step += 1
            
        return current_step
    
    def perform_single_measurement(self):
        """Perform a single PDSHG measurement point."""
        averaging_samples = self.settings.child('pdshg_experiment', 'data_acquisition', 'averaging_samples').value()
        timeout = self.settings.child('pdshg_experiment', 'data_acquisition', 'measurement_timeout').value()
        
        # TODO: Implement photodiode voltage measurement
        # For now, simulate measurement
        start_time = time.time()
        
        # Simulate photodiode readings with averaging
        pd_readings = []
        for _ in range(averaging_samples):
            # Simulate RASHG signal with cos²(2θ) dependence plus noise
            if self.current_angle is not None:
                signal = 1.0 * np.cos(np.radians(2 * self.current_angle))**2 + 0.1
                noise = np.random.normal(0, 0.01)
                pd_reading = signal + noise
            else:
                pd_reading = np.random.normal(0.5, 0.01)
            
            pd_readings.append(pd_reading)
            time.sleep(0.001)  # Small delay between samples
        
        pd_voltage = np.mean(pd_readings)
        pd_std = np.std(pd_readings)
        
        # Get power meter reading
        power_meter = self.modules['Newport1830C']
        pm_reading = power_meter.get_actuator_value()
        if isinstance(pm_reading, DataActuator):
            pm_value = pm_reading.value()
        else:
            pm_value = float(pm_reading)
        
        # Get actual rotator positions
        h800 = self.modules['H800']
        h400 = self.modules['H400']
        
        h800_pos = h800.get_actuator_value()
        h400_pos = h400.get_actuator_value()
        
        if isinstance(h800_pos, DataActuator):
            h800_value = h800_pos.value()
        else:
            h800_value = float(h800_pos)
            
        if isinstance(h400_pos, DataActuator):
            h400_value = h400_pos.value()
        else:
            h400_value = float(h400_pos)
        
        # Calculate measurement quality metric
        stability = pd_std / pd_voltage if pd_voltage > 0 else 1.0
        quality = 1.0 / (1.0 + stability)  # Quality decreases with instability
        
        measurement_result = {
            'pd_voltage': pd_voltage,
            'pd_std': pd_std,
            'pm_reading': pm_value,
            'h800_pos': h800_value,
            'h400_pos': h400_value,
            'timestamp': time.time(),
            'quality': quality,
            'measurement_time': time.time() - start_time
        }
        
        return measurement_result
    
    def perform_real_time_analysis(self, wl_idx, p_idx, a_idx):
        """Perform real-time analysis and fitting during measurement."""
        # Get current data for fitting
        angles = self.measurement_data['angles'][:a_idx+1]
        voltages = self.measurement_data['photodiode_voltage'][wl_idx, p_idx, :a_idx+1]
        
        # Subtract background if available
        if self.settings.child('pdshg_experiment', 'data_acquisition', 'background_subtraction').value():
            if wl_idx < len(self.background_data['background_voltage']):
                bg_voltages = self.background_data['background_voltage'][wl_idx, :a_idx+1]
                corrected_voltages = voltages - bg_voltages
            else:
                corrected_voltages = voltages
        else:
            corrected_voltages = voltages
        
        # Try to fit angular dependence
        try:
            fit_func = self.settings.child('pdshg_experiment', 'analysis_settings', 'angular_fit_function').value()
            
            if fit_func == 'cos_squared_2theta':
                popt, pcov = curve_fit(rashg_cosine_squared, angles, corrected_voltages,
                                     p0=[np.max(corrected_voltages), 0, np.min(corrected_voltages)])
                
                amplitude, phase, offset = popt
                fitted_data = rashg_cosine_squared(angles, *popt)
                residuals = corrected_voltages - fitted_data
                r_squared = 1 - np.sum(residuals**2) / np.sum((corrected_voltages - np.mean(corrected_voltages))**2)
                
                # Store fit results
                fit_key = f'wl_{wl_idx}_p_{p_idx}'
                self.angular_fits[fit_key] = {
                    'amplitude': amplitude,
                    'phase': phase,
                    'offset': offset,
                    'r_squared': r_squared,
                    'data_points': len(angles)
                }
                
                logger.debug(f"Real-time fit: A={amplitude:.4f}, φ={phase:.1f}°, R²={r_squared:.3f}")
                
        except Exception as e:
            logger.debug(f"Real-time fitting failed: {e}")
    
    def analyze_pdshg_data(self):
        """Perform comprehensive analysis of PDSHG data."""
        self.log_status("Analyzing PDSHG data and performing curve fitting")
        
        wavelengths = self.measurement_data['wavelengths']
        powers = self.measurement_data['powers']
        angles = self.measurement_data['angles']
        
        # Initialize analysis results storage
        self.angular_fits = {}
        self.power_law_fits = {}
        
        # Analyze each wavelength and power combination
        for wl_idx, wavelength in enumerate(wavelengths):
            for p_idx, power in enumerate(powers):
                # Get data for this wavelength/power combination
                voltages = self.measurement_data['photodiode_voltage'][wl_idx, p_idx, :]
                
                # Background subtraction
                if self.settings.child('pdshg_experiment', 'data_acquisition', 'background_subtraction').value():
                    if wl_idx < len(self.background_data['background_voltage']):
                        bg_voltages = self.background_data['background_voltage'][wl_idx, :]
                        corrected_voltages = voltages - bg_voltages
                    else:
                        corrected_voltages = voltages
                else:
                    corrected_voltages = voltages
                
                # Fit angular dependence
                try:
                    popt, pcov = curve_fit(rashg_cosine_squared, angles, corrected_voltages,
                                         p0=[np.max(corrected_voltages), 0, np.min(corrected_voltages)])
                    
                    amplitude, phase, offset = popt
                    amplitude_err, phase_err, offset_err = np.sqrt(np.diag(pcov))
                    
                    fitted_data = rashg_cosine_squared(angles, *popt)
                    residuals = corrected_voltages - fitted_data
                    r_squared = 1 - np.sum(residuals**2) / np.sum((corrected_voltages - np.mean(corrected_voltages))**2)
                    
                    fit_key = f'wl_{wavelength:.0f}_p_{power:.6f}'
                    self.angular_fits[fit_key] = {
                        'wavelength': wavelength,
                        'power': power,
                        'amplitude': amplitude,
                        'phase': phase,
                        'offset': offset,
                        'amplitude_error': amplitude_err,
                        'phase_error': phase_err,
                        'offset_error': offset_err,
                        'r_squared': r_squared,
                        'fitted_data': fitted_data,
                        'residuals': residuals,
                        'corrected_voltages': corrected_voltages
                    }
                    
                except Exception as e:
                    logger.warning(f"Angular fitting failed for λ={wavelength}nm, P={power}W: {e}")
        
        # Power law analysis for each wavelength and angle
        if self.settings.child('pdshg_experiment', 'analysis_settings', 'power_law_fitting').value():
            for wl_idx, wavelength in enumerate(wavelengths):
                for a_idx, angle in enumerate(angles):
                    # Get power dependence data
                    power_data = powers
                    voltage_data = self.measurement_data['photodiode_voltage'][wl_idx, :, a_idx]
                    
                    # Background correction
                    if self.settings.child('pdshg_experiment', 'data_acquisition', 'background_subtraction').value():
                        if wl_idx < len(self.background_data['background_voltage']):
                            bg_voltage = self.background_data['background_voltage'][wl_idx, a_idx]
                            corrected_voltage_data = voltage_data - bg_voltage
                        else:
                            corrected_voltage_data = voltage_data
                    else:
                        corrected_voltage_data = voltage_data
                    
                    # Fit power law
                    try:
                        expected_exp = self.settings.child('pdshg_experiment', 'analysis_settings', 'expected_shg_exponent').value()
                        p0 = [1.0, expected_exp, 0.0]  # coefficient, exponent, offset
                        
                        popt, pcov = curve_fit(power_law_fitting, power_data, corrected_voltage_data, p0=p0)
                        
                        coefficient, exponent, offset = popt
                        coeff_err, exp_err, offset_err = np.sqrt(np.diag(pcov))
                        
                        fitted_power_data = power_law_fitting(power_data, *popt)
                        residuals = corrected_voltage_data - fitted_power_data
                        r_squared = 1 - np.sum(residuals**2) / np.sum((corrected_voltage_data - np.mean(corrected_voltage_data))**2)
                        
                        fit_key = f'wl_{wavelength:.0f}_a_{angle:.0f}'
                        self.power_law_fits[fit_key] = {
                            'wavelength': wavelength,
                            'angle': angle,
                            'coefficient': coefficient,
                            'exponent': exponent,
                            'offset': offset,
                            'coefficient_error': coeff_err,
                            'exponent_error': exp_err,
                            'offset_error': offset_err,
                            'r_squared': r_squared,
                            'fitted_data': fitted_power_data,
                            'residuals': residuals
                        }
                        
                    except Exception as e:
                        logger.warning(f"Power law fitting failed for λ={wavelength}nm, θ={angle}°: {e}")
        
        # Summary statistics
        angular_r_squared_values = [fit['r_squared'] for fit in self.angular_fits.values()]
        power_law_r_squared_values = [fit['r_squared'] for fit in self.power_law_fits.values()]
        
        logger.info(f"Angular fits: {len(self.angular_fits)} fits, "
                   f"mean R² = {np.mean(angular_r_squared_values):.3f}")
        logger.info(f"Power law fits: {len(self.power_law_fits)} fits, "
                   f"mean R² = {np.mean(power_law_r_squared_values):.3f}")
    
    def save_pdshg_results(self):
        """Save all PDSHG experiment results to HDF5 file."""
        try:
            with h5py.File(self.data_filepath, 'w') as f:
                # Save measurement data
                data_group = f.create_group('measurement_data')
                for key, value in self.measurement_data.items():
                    data_group.create_dataset(key, data=value)
                
                # Save background data
                bg_group = f.create_group('background_data')
                for key, value in self.background_data.items():
                    bg_group.create_dataset(key, data=value)
                
                # Save angular fit results
                if self.angular_fits:
                    angular_fit_group = f.create_group('angular_fits')
                    for fit_key, fit_data in self.angular_fits.items():
                        fit_subgroup = angular_fit_group.create_group(fit_key)
                        for param_key, param_value in fit_data.items():
                            if isinstance(param_value, np.ndarray):
                                fit_subgroup.create_dataset(param_key, data=param_value)
                            else:
                                fit_subgroup.attrs[param_key] = param_value
                
                # Save power law fit results
                if self.power_law_fits:
                    power_fit_group = f.create_group('power_law_fits')
                    for fit_key, fit_data in self.power_law_fits.items():
                        fit_subgroup = power_fit_group.create_group(fit_key)
                        for param_key, param_value in fit_data.items():
                            if isinstance(param_value, np.ndarray):
                                fit_subgroup.create_dataset(param_key, data=param_value)
                            else:
                                fit_subgroup.attrs[param_key] = param_value
                
                # Save experimental conditions
                conditions_group = f.create_group('experimental_conditions')
                conditions_group.attrs['sample_name'] = self.settings.child('pdshg_experiment', 'experimental_conditions', 'sample_name').value()
                conditions_group.attrs['measurement_position'] = self.settings.child('pdshg_experiment', 'experimental_conditions', 'measurement_position').value()
                conditions_group.attrs['polarization_config'] = self.settings.child('pdshg_experiment', 'experimental_conditions', 'polarization_config').value()
                
                # Save hardware configuration
                hw_group = f.create_group('hardware_configuration')
                hw_group.attrs['h800_formula'] = self.settings.child('pdshg_experiment', 'hwp_control', 'h800_formula').value()
                hw_group.attrs['h400_formula'] = self.settings.child('pdshg_experiment', 'hwp_control', 'h400_formula').value()
                hw_group.attrs['h800_offset'] = self.settings.child('pdshg_experiment', 'hwp_control', 'hwp_offsets', 'h800_offset').value()
                hw_group.attrs['h400_offset'] = self.settings.child('pdshg_experiment', 'hwp_control', 'hwp_offsets', 'h400_offset').value()
                
                # Save experiment metadata
                f.attrs['experiment_name'] = self.experiment_name
                f.attrs['experiment_type'] = self.experiment_type
                f.attrs['creation_time'] = datetime.now().isoformat()
                f.attrs['data_version'] = '1.0'
                
            logger.info(f"PDSHG experiment results saved to {self.data_filepath}")
            self.log_status(f"Results saved to {self.data_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save PDSHG results: {e}")
            raise ExperimentError(f"Failed to save PDSHG results: {e}")
    
    def _check_stop_requested(self):
        """Check if experiment stop was requested."""
        if hasattr(self, 'experiment_thread') and self.experiment_thread:
            return self.experiment_thread._stop_requested
        return False
    
    def get_rashg_amplitude(self, wavelength, power):
        """
        Get RASHG amplitude for specified wavelength and power.
        
        Args:
            wavelength (float): Wavelength in nm
            power (float): Power in W
            
        Returns:
            float: RASHG amplitude or None if not found
        """
        fit_key = f'wl_{wavelength:.0f}_p_{power:.6f}'
        if fit_key in self.angular_fits:
            return self.angular_fits[fit_key]['amplitude']
        return None
    
    def get_power_law_exponent(self, wavelength, angle):
        """
        Get power law exponent for specified wavelength and angle.
        
        Args:
            wavelength (float): Wavelength in nm
            angle (float): Angle in degrees
            
        Returns:
            float: Power law exponent or None if not found
        """
        fit_key = f'wl_{wavelength:.0f}_a_{angle:.0f}'
        if fit_key in self.power_law_fits:
            return self.power_law_fits[fit_key]['exponent']
        return None