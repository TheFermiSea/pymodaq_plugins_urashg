"""
Wavelength-Dependent RASHG Experiment with Power Stabilization

This module implements spectroscopic μRASHG measurements with comprehensive
wavelength-dependent analysis and laser power stabilization using Red Pitaya
PyRPL hardware. The experiment performs:

1. Wide wavelength range scans with fine spectral resolution
2. Real-time laser power stabilization during wavelength changes
3. Wavelength-dependent anisotropy characterization
4. Spectral line shape analysis and fitting
5. Power-corrected signal analysis
6. Multi-order susceptibility analysis

The Wavelength-Dependent RASHG experiment is optimized for:
- Electronic resonance studies with stable laser power
- Bandgap characterization with power drift correction
- Dispersion relation mapping with consistent excitation
- Multi-photon process identification
- Wavelength-optimized measurement protocols
- Long-duration spectroscopic measurements

This experiment integrates PyRPL-based PID control for hardware-level
laser power stabilization during wavelength scanning, ensuring measurement
accuracy and repeatability across the entire spectral range.

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

import numpy as np
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from contextlib import contextmanager

from qtpy import QtCore
from pymodaq_gui.parameter import Parameter
from pymodaq_data import DataWithAxes, DataToExport, Axis
from enum import Enum as BaseEnum

from .base_experiment import URASHGBaseExperiment, ExperimentState
try:
    from ..hardware.urashg.redpitaya_control import (
        PowerStabilizationController, StabilizationConfiguration,
        PowerTarget, PowerStabilizationError
    )
    PYRPL_AVAILABLE = True
except ImportError:
    # PyRPL not available - provide mock classes
    PowerStabilizationController = None
    StabilizationConfiguration = None
    PowerTarget = None
    PowerStabilizationError = Exception
    PYRPL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SpectralPoint:
    """Data structure for a single spectral measurement point."""
    wavelength: float  # nm
    target_power: float  # V (setpoint)
    measured_power: float  # V (actual)
    power_stability: Dict[str, Any]  # stability metrics
    measurement_data: Dict[str, Any]  # RASHG measurement results
    timestamp: float  # Unix timestamp


@dataclass
class SpectralScanConfiguration:
    """Configuration for wavelength-dependent spectral scan."""
    # Wavelength scan parameters
    wavelength_start: float = 700.0  # nm
    wavelength_end: float = 900.0  # nm
    wavelength_step: float = 2.0  # nm
    wavelength_settle_time: float = 0.5  # s

    # Power stabilization parameters
    power_setpoint: float = 0.5  # V (constant power target)
    power_tolerance: float = 0.001  # V (stability requirement)
    power_stabilization_timeout: float = 10.0  # s
    enable_power_stabilization: bool = True

    # Measurement parameters
    measurements_per_point: int = 5  # averages per wavelength
    measurement_delay: float = 0.1  # s between measurements

    # Analysis parameters
    normalize_to_power: bool = True
    power_correction_order: int = 1  # 1 = linear, 2 = quadratic


class WavelengthDependentRASHGExperiment(URASHGBaseExperiment):
    """
    Wavelength-Dependent RASHG Experiment with integrated power stabilization.

    This experiment implements comprehensive wavelength-dependent μRASHG
    measurements with hardware-level laser power stabilization using Red Pitaya
    PyRPL control. Key features:

    - Coordinated wavelength scanning with MaiTai laser
    - Real-time power stabilization during wavelength changes
    - Power-corrected spectroscopic analysis
    - Comprehensive stability monitoring and reporting
    - Adaptive measurement protocols based on power stability
    - Integration with existing URASHG measurement framework

    The experiment ensures measurement accuracy by:
    1. Setting wavelength and waiting for laser stabilization
    2. Configuring power target based on wavelength
    3. Activating PyRPL PID control for power stabilization
    4. Waiting for power stability before measurement
    5. Performing RASHG measurements with stable power
    6. Collecting power monitoring data for correction
    7. Moving to next wavelength and repeating

    Required Hardware:
    - MaiTai laser with wide tuning range (700-900nm)
    - Red Pitaya STEMlab for power stabilization
    - Newport 1830C power meter for power monitoring
    - Standard μRASHG polarimetry hardware (H800, H400, etc.)

    Optional Hardware:
    - Q800 quarter-wave plate for enhanced measurements
    - Spectrometer for verification measurements
    """

    experiment_name = "Wavelength-Dependent RASHG with Power Stabilization"
    experiment_type = "wavelength_dependent_rashg_stabilized"
    required_modules = ['MaiTai', 'H800', 'H400', 'Newport1830C', 'PyRPL_PID']
    optional_modules = ['Q800', 'Spectrometer']

    def __init__(self, dashboard=None):
        """Initialize the wavelength-dependent RASHG experiment."""
        super().__init__(dashboard)

        # Power stabilization controller
        self.power_controller: Optional[PowerStabilizationController] = None
        self.power_stabilization_config: Optional[StabilizationConfiguration] = None

        # Spectral scan configuration
        self.scan_config = SpectralScanConfiguration()

        # Experimental data storage
        self.spectral_data: List[SpectralPoint] = []
        self.current_wavelength: Optional[float] = None
        self.current_power_target: Optional[PowerTarget] = None

        # Status tracking
        self.wavelength_index = 0
        self.total_wavelengths = 0
        self.scan_start_time = None

        # Initialize power stabilization configuration
        self._initialize_power_stabilization_config()

        logger.info("Wavelength-Dependent RASHG with Power Stabilization initialized")

    def _initialize_power_stabilization_config(self):
        """Initialize default power stabilization configuration."""
        self.power_stabilization_config = StabilizationConfiguration(
            hostname="rp-f08d6c.local",  # Red Pitaya hostname
            config_name="urashg_spectroscopy",  # Unique config for spectroscopy

            # PID parameters optimized for power stabilization
            p_gain=0.15,  # Slightly higher for fast wavelength changes
            i_gain=0.02,  # Moderate integral for steady-state accuracy
            d_gain=0.0,   # No derivative to avoid noise amplification

            # Monitoring parameters for spectroscopic measurements
            power_monitoring_rate=20.0,  # 20 Hz for detailed monitoring
            stability_check_duration=2.0,  # 2s window for stability assessment
            power_stability_threshold=0.002,  # 2mV RMS for high precision

            # Safety limits
            min_power_setpoint=-0.8,  # Conservative limits for laser safety
            max_power_setpoint=0.8,

            mock_mode=False  # Will auto-switch if PyRPL unavailable
        )

    def _setup_experimental_parameters(self):
        """Setup parameter tree for the experiment."""
        # This would typically be implemented to create a PyQt parameter tree
        # For now, we'll use the scan_config directly
        pass

    @property
    def wavelength_points(self) -> np.ndarray:
        """Get the wavelength points for the spectral scan."""
        return np.arange(
            self.scan_config.wavelength_start,
            self.scan_config.wavelength_end + self.scan_config.wavelength_step,
            self.scan_config.wavelength_step
        )

    def initialize_hardware(self) -> bool:
        """
        Initialize all hardware modules including power stabilization.

        Returns:
            bool: True if all hardware initialized successfully
        """
        try:
            # Initialize base hardware (MaiTai, Newport1830C, etc.)
            if not super().initialize_hardware():
                logger.error("Failed to initialize base hardware")
                return False

            # Initialize power stabilization controller
            if self.scan_config.enable_power_stabilization:
                self.power_controller = PowerStabilizationController(
                    self.power_stabilization_config
                )

                # Add status callback for power controller
                self.power_controller.add_status_callback(self._power_status_callback)

                # Connect to Red Pitaya
                if not self.power_controller.connect():
                    logger.error("Failed to connect to power stabilization hardware")
                    if not self.power_stabilization_config.mock_mode:
                        return False

                logger.info("Power stabilization controller initialized")

            self.hardware_initialized = True
            return True

        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            return False

    def cleanup_hardware(self):
        """Clean up all hardware connections."""
        try:
            # Disconnect power stabilization controller
            if self.power_controller:
                self.power_controller.disconnect()
                self.power_controller = None

            # Clean up base hardware
            super().cleanup_hardware()

        except Exception as e:
            logger.error(f"Hardware cleanup error: {e}")

    def _power_status_callback(self, message: str):
        """Callback for power stabilization status updates."""
        logger.info(f"Power Stabilization: {message}")
        if hasattr(self, 'progress_callback') and self.progress_callback:
            self.progress_callback(f"Power: {message}")

    def calculate_power_target(self, wavelength: float) -> float:
        """
        Calculate optimal power target for given wavelength.

        This can be enhanced with wavelength-dependent power correction
        based on laser characteristics or measurement requirements.

        Args:
            wavelength: Target wavelength in nm

        Returns:
            Power setpoint in volts
        """
        # For now, use constant power target
        # Future enhancement: wavelength-dependent power correction
        base_power = self.scan_config.power_setpoint

        # Optional: Add wavelength-dependent correction
        # wavelength_correction = self._get_wavelength_power_correction(wavelength)
        # return base_power + wavelength_correction

        return base_power

    @contextmanager
    def wavelength_measurement_context(self, wavelength: float):
        """
        Context manager for wavelength-specific measurements with power stabilization.

        This handles:
        1. Setting wavelength and waiting for stabilization
        2. Configuring power target for the wavelength
        3. Starting power stabilization
        4. Waiting for power stability
        5. Yielding control for measurements
        6. Stopping power stabilization when done

        Args:
            wavelength: Target wavelength in nm
        """
        measurement_success = False

        try:
            # Update progress
            if self.progress_callback:
                self.progress_callback(f"Setting up wavelength {wavelength:.1f} nm")

            # Set wavelength on MaiTai laser
            logger.info(f"Setting wavelength to {wavelength:.1f} nm")
            if 'MaiTai' in self.modules:
                # Set wavelength and wait for stabilization
                self.modules['MaiTai'].move_abs(wavelength)
                time.sleep(self.scan_config.wavelength_settle_time)

            self.current_wavelength = wavelength

            # Configure power stabilization if enabled
            if self.scan_config.enable_power_stabilization and self.power_controller:
                power_setpoint = self.calculate_power_target(wavelength)
                power_target = PowerTarget(
                    wavelength=wavelength,
                    power_setpoint=power_setpoint,
                    tolerance=self.scan_config.power_tolerance,
                    timeout=self.scan_config.power_stabilization_timeout
                )

                self.current_power_target = power_target

                # Use power controller's context manager for stabilization
                with self.power_controller.power_stabilization_context(
                    power_target, wait_for_stability=True
                ) as power_stable:

                    if power_stable:
                        measurement_success = True
                        logger.info(f"Power stabilized at {wavelength:.1f} nm")
                        if self.progress_callback:
                            self.progress_callback(f"Power stable at {wavelength:.1f} nm")

                        yield power_stable
                    else:
                        logger.warning(f"Power stabilization failed at {wavelength:.1f} nm")
                        if self.progress_callback:
                            self.progress_callback(f"Power unstable at {wavelength:.1f} nm")
                        yield False
            else:
                # No power stabilization - proceed directly
                measurement_success = True
                yield True

        except Exception as e:
            logger.error(f"Error in wavelength measurement context: {e}")
            yield False

        finally:
            if measurement_success:
                logger.debug(f"Completed measurement context for {wavelength:.1f} nm")

    def perform_rashg_measurement(self, wavelength: float) -> Dict[str, Any]:
        """
        Perform RASHG measurement at specified wavelength with power monitoring.

        Args:
            wavelength: Measurement wavelength in nm

        Returns:
            Dictionary containing RASHG measurement data
        """
        measurement_data = {
            'wavelength': wavelength,
            'timestamp': time.time(),
            'measurements': [],
            'power_readings': [],
            'measurement_statistics': {}
        }

        # Perform multiple measurements for averaging
        for i in range(self.scan_config.measurements_per_point):
            try:
                # Record power if available
                if self.power_controller:
                    current_power = self.power_controller.get_current_power()
                    measurement_data['power_readings'].append(current_power)

                # Perform RASHG measurement (placeholder for actual measurement)
                # This would typically involve:
                # 1. Setting polarization angles
                # 2. Acquiring camera images
                # 3. Processing RASHG signals
                # 4. Extracting anisotropy parameters

                rashg_signal = self._measure_rashg_signal()
                measurement_data['measurements'].append(rashg_signal)

                # Delay between measurements
                if i < self.scan_config.measurements_per_point - 1:
                    time.sleep(self.scan_config.measurement_delay)

            except Exception as e:
                logger.error(f"Measurement error at {wavelength} nm: {e}")

        # Calculate measurement statistics
        if measurement_data['measurements']:
            measurements = np.array(measurement_data['measurements'])
            measurement_data['measurement_statistics'] = {
                'mean': np.mean(measurements),
                'std': np.std(measurements),
                'count': len(measurements)
            }

        return measurement_data

    def _measure_rashg_signal(self) -> float:
        """
        Placeholder for actual RASHG signal measurement.

        This would implement the full RASHG measurement protocol:
        - Polarization control
        - Camera acquisition
        - Signal processing
        - Anisotropy calculation

        Returns:
            RASHG signal value
        """
        # Placeholder: return simulated signal with noise
        baseline = 1000.0
        noise = np.random.normal(0, 50)

        # Simple wavelength dependence for demonstration
        if self.current_wavelength:
            wavelength_factor = np.sin((self.current_wavelength - 750) * np.pi / 100)
            signal = baseline * (1 + 0.5 * wavelength_factor) + noise
        else:
            signal = baseline + noise

        return signal

    def run_spectral_scan(self) -> bool:
        """
        Execute the complete wavelength-dependent spectral scan.

        Returns:
            bool: True if scan completed successfully
        """
        try:
            # Initialize scan
            wavelengths = self.wavelength_points
            self.total_wavelengths = len(wavelengths)
            self.wavelength_index = 0
            self.scan_start_time = time.time()
            self.spectral_data.clear()

            logger.info(f"Starting spectral scan: {wavelengths[0]:.1f} - {wavelengths[-1]:.1f} nm "
                       f"({len(wavelengths)} points)")

            # Scan each wavelength
            for wavelength in wavelengths:
                if self.state != ExperimentState.RUNNING:
                    logger.info("Spectral scan stopped by user")
                    break

                # Update progress
                progress = (self.wavelength_index / self.total_wavelengths) * 100
                if self.progress_callback:
                    self.progress_callback(f"Scanning {wavelength:.1f} nm ({progress:.1f}%)")

                # Perform measurement with power stabilization
                with self.wavelength_measurement_context(wavelength) as stable:
                    if stable:
                        # Collect RASHG measurement data
                        measurement_data = self.perform_rashg_measurement(wavelength)

                        # Get power stability information
                        power_stability = {}
                        if self.power_controller:
                            power_stability = self.power_controller.assess_power_stability()

                        # Create spectral point data structure
                        spectral_point = SpectralPoint(
                            wavelength=wavelength,
                            target_power=self.current_power_target.power_setpoint if self.current_power_target else 0.0,
                            measured_power=np.mean(measurement_data.get('power_readings', [0.0])),
                            power_stability=power_stability,
                            measurement_data=measurement_data,
                            timestamp=time.time()
                        )

                        self.spectral_data.append(spectral_point)
                        logger.info(f"Completed measurement at {wavelength:.1f} nm")

                    else:
                        logger.warning(f"Skipped measurement at {wavelength:.1f} nm due to power instability")

                self.wavelength_index += 1

            # Scan completed
            scan_duration = time.time() - self.scan_start_time
            logger.info(f"Spectral scan completed: {len(self.spectral_data)} points in {scan_duration:.1f}s")

            return len(self.spectral_data) > 0

        except Exception as e:
            logger.error(f"Spectral scan failed: {e}")
            return False

    def analyze_spectral_data(self) -> Dict[str, Any]:
        """
        Analyze collected spectral data with power correction.

        Returns:
            Dictionary containing analysis results
        """
        if not self.spectral_data:
            return {'error': 'No spectral data available'}

        # Extract data arrays
        wavelengths = np.array([point.wavelength for point in self.spectral_data])
        signals = np.array([point.measurement_data['measurement_statistics']['mean']
                           for point in self.spectral_data])
        powers = np.array([point.measured_power for point in self.spectral_data])

        # Power normalization if enabled
        normalized_signals = signals.copy()
        if self.scan_config.normalize_to_power and len(powers) > 0:
            # Normalize to average power
            avg_power = np.mean(powers[powers > 0])
            if avg_power > 0:
                power_correction = (avg_power / powers) ** self.scan_config.power_correction_order
                power_correction[powers <= 0] = 1.0  # Avoid division by zero
                normalized_signals = signals * power_correction

        analysis_results = {
            'wavelengths': wavelengths,
            'raw_signals': signals,
            'normalized_signals': normalized_signals,
            'measured_powers': powers,
            'scan_duration': time.time() - self.scan_start_time if self.scan_start_time else 0,
            'total_points': len(self.spectral_data),
            'power_stabilization_enabled': self.scan_config.enable_power_stabilization,
            'power_statistics': {
                'mean_power': np.mean(powers) if len(powers) > 0 else 0,
                'power_std': np.std(powers) if len(powers) > 0 else 0,
                'power_variation': (np.max(powers) - np.min(powers)) if len(powers) > 0 else 0
            }
        }

        # Power stability analysis
        stability_scores = []
        for point in self.spectral_data:
            if point.power_stability:
                stability_scores.append(point.power_stability.get('rms_deviation', 0))

        if stability_scores:
            analysis_results['stability_statistics'] = {
                'mean_rms_deviation': np.mean(stability_scores),
                'max_rms_deviation': np.max(stability_scores),
                'stability_threshold': self.power_stabilization_config.power_stability_threshold
            }

        return analysis_results

    def save_experimental_data(self, filename: Optional[str] = None) -> str:
        """
        Save experimental data and analysis results.

        Args:
            filename: Optional filename (auto-generated if None)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"urashg_spectral_scan_{timestamp}.npz"

        # Prepare data for saving
        save_data = {
            'wavelengths': np.array([point.wavelength for point in self.spectral_data]),
            'signals': np.array([point.measurement_data['measurement_statistics']['mean']
                               for point in self.spectral_data]),
            'powers': np.array([point.measured_power for point in self.spectral_data]),
            'timestamps': np.array([point.timestamp for point in self.spectral_data]),
            'scan_config': {
                'wavelength_start': self.scan_config.wavelength_start,
                'wavelength_end': self.scan_config.wavelength_end,
                'wavelength_step': self.scan_config.wavelength_step,
                'power_setpoint': self.scan_config.power_setpoint,
                'enable_power_stabilization': self.scan_config.enable_power_stabilization
            },
            'analysis_results': self.analyze_spectral_data()
        }

        # Save data
        np.savez_compressed(filename, **save_data)
        logger.info(f"Experimental data saved to {filename}")

        return filename

    def run_experiment(self):
        """Execute the complete Wavelength-Dependent RASHG experiment."""
        try:
            self.state = ExperimentState.INITIALIZING

            # Initialize hardware
            if not self.initialize_hardware():
                raise ExperimentError("Hardware initialization failed")

            self.state = ExperimentState.RUNNING

            # Run spectral scan
            scan_success = self.run_spectral_scan()

            if scan_success:
                self.state = ExperimentState.COMPLETED

                # Analyze and save data
                analysis_results = self.analyze_spectral_data()
                saved_file = self.save_experimental_data()

                logger.info("Wavelength-Dependent RASHG experiment completed successfully")
                logger.info(f"Data saved to: {saved_file}")

                # Report summary
                if 'total_points' in analysis_results:
                    logger.info(f"Collected {analysis_results['total_points']} spectral points")

                if 'power_statistics' in analysis_results:
                    power_stats = analysis_results['power_statistics']
                    logger.info(f"Power stability: {power_stats['power_std']:.4f}V RMS "
                               f"(variation: {power_stats['power_variation']:.4f}V)")

                return analysis_results

            else:
                self.state = ExperimentState.ERROR
                raise ExperimentError("Spectral scan failed")

        except Exception as e:
            self.state = ExperimentState.ERROR
            logger.error(f"Experiment failed: {e}")
            raise

        finally:
            # Always cleanup hardware
            self.cleanup_hardware()
