"""
Automated μRASHG Measurement Example Script

This script demonstrates how to perform automated polarization-resolved SHG measurements
using the URASHG PyMoDAQ plugin package. It includes setup, configuration, data acquisition,
and basic analysis for a complete μRASHG experiment.

This example shows the integration of all hardware components:
- Red Pitaya PID laser stabilization
- Thorlabs ELL14 polarization control
- Photometrics Prime BSI camera detection
- Automated data collection and export

Usage:
    python automated_rashg_scan.py --config rashg_config.yaml --output ./data/
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# PyMoDAQ imports
from pymodaq.dashboard import DashBoard
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport

from pymodaq_plugins_urashg.analysis import rashg_analysis

# URASHG plugin imports
from pymodaq_plugins_urashg.hardware.urashg import URASHGSystem
from pymodaq_plugins_urashg.utils import configuration_manager


class AutomatedμRASHGScanner:
    """
    Automated μRASHG measurement system for polarization-resolved SHG experiments.

    This class provides high-level automation for μRASHG measurements, including:
    - System initialization and hardware coordination
    - Automated polarization scans with precise angle control
    - Real-time data acquisition and processing
    - Background subtraction and signal optimization
    - Data export in multiple formats (HDF5, CSV, images)

    The scanner integrates all hardware components and provides a simple interface
    for complex measurement sequences.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the automated μRASHG scanner.

        Args:
            config_file: Path to YAML configuration file with hardware settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_configuration(config_file)

        # Initialize PyMoDAQ dashboard
        self.dashboard = None
        self.hardware_system = None

        # Plugin references
        self.redpitaya_plugin = None
        self.elliptec_plugin = None
        self.camera_plugin = None

        # Measurement state
        self.is_initialized = False
        self.measurement_active = False
        self.background_image = None

        # Data storage
        self.scan_data = []
        self.metadata = {}

    def _load_configuration(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        if config_file and Path(config_file).exists():
            return configuration_manager.load_config(config_file)
        else:
            self.logger.warning("No config file provided, using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration for μRASHG measurements."""
        return {
            "hardware": {
                "redpitaya": {
                    "ip_address": "192.168.1.100",
                    "pid_parameters": {
                        "kp": 0.1,
                        "ki": 0.01,
                        "kd": 0.001,
                        "setpoint_mw": 100.0,
                    },
                },
                "elliptec": {
                    "ports": {
                        "QWP": "COM3",
                        "HWP_incident": "COM4",
                        "HWP_analyzer": "COM5",
                    },
                    "home_on_startup": True,
                },
                "camera": {
                    "exposure_ms": 100.0,
                    "gain": 1,
                    "roi": {
                        "enabled": True,
                        "x": 500,
                        "y": 500,
                        "width": 100,
                        "height": 100,
                    },
                },
            },
            "measurement": {
                "polarization_scan": {
                    "start_angle": 0.0,
                    "end_angle": 180.0,
                    "step_size": 5.0,
                    "averaging_frames": 3,
                },
                "background_subtraction": True,
                "save_full_images": True,
            },
        }

    def initialize_system(self) -> bool:
        """
        Initialize the complete μRASHG measurement system.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing μRASHG measurement system...")

            # Initialize PyMoDAQ dashboard
            self.dashboard = DashBoard()

            # Load μRASHG preset configuration
            preset_file = Path(__file__).parent / "presets" / "RASHG_System.xml"
            if preset_file.exists():
                self.dashboard.load_preset(str(preset_file))
            else:
                self.logger.warning(
                    "No preset file found, manual plugin setup required"
                )
                self._setup_plugins_manually()

            # Get plugin references
            self._get_plugin_references()

            # Initialize hardware system
            self.hardware_system = URASHGSystem()
            self.hardware_system.initialize_all_hardware()

            # Configure hardware with loaded settings
            self._configure_hardware()

            # Run system diagnostics
            if not self._run_system_diagnostics():
                raise RuntimeError("System diagnostics failed")

            self.is_initialized = True
            self.logger.info("μRASHG system initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"System initialization failed: {str(e)}")
            return False

    def _setup_plugins_manually(self):
        """Setup plugins manually if no preset file is available."""
        # This would typically be done through the Dashboard GUI
        # For automation, we assume plugins are pre-configured
        self.logger.info("Manual plugin setup - please configure plugins in Dashboard")

    def _get_plugin_references(self):
        """Get references to initialized plugins from the dashboard."""
        try:
            # Get move plugins
            self.redpitaya_plugin = self.dashboard.get_move_by_title("RedPitaya_PID")
            self.elliptec_plugin = self.dashboard.get_move_by_title(
                "Elliptec_Polarization"
            )

            # Get viewer plugins
            self.camera_plugin = self.dashboard.get_viewer_by_title("PrimeBSI_Camera")

            self.logger.info("Plugin references acquired successfully")

        except Exception as e:
            self.logger.error(f"Failed to get plugin references: {str(e)}")
            raise

    def _configure_hardware(self):
        """Configure all hardware components with loaded settings."""
        # Configure Red Pitaya PID
        pid_config = self.config["hardware"]["redpitaya"]["pid_parameters"]
        self.hardware_system.redpitaya.set_pid_parameters(
            kp=pid_config["kp"], ki=pid_config["ki"], kd=pid_config["kd"]
        )
        self.hardware_system.redpitaya.set_power_setpoint(pid_config["setpoint_mw"])

        # Configure camera
        camera_config = self.config["hardware"]["camera"]
        self.hardware_system.camera.set_exposure_time(camera_config["exposure_ms"])
        self.hardware_system.camera.set_gain(camera_config["gain"])

        if camera_config["roi"]["enabled"]:
            roi = camera_config["roi"]
            self.hardware_system.camera.set_roi(
                x=roi["x"], y=roi["y"], width=roi["width"], height=roi["height"]
            )

        self.logger.info("Hardware configuration complete")

    def _run_system_diagnostics(self) -> bool:
        """Run comprehensive system diagnostics."""
        try:
            self.logger.info("Running system diagnostics...")

            # Test Red Pitaya communication
            if not self.hardware_system.redpitaya.test_communication():
                self.logger.error("Red Pitaya communication test failed")
                return False

            # Test Elliptec controllers
            if not self.hardware_system.elliptec.test_all_controllers():
                self.logger.error("Elliptec controller test failed")
                return False

            # Test camera
            if not self.hardware_system.camera.test_acquisition():
                self.logger.error("Camera acquisition test failed")
                return False

            self.logger.info("All system diagnostics passed")
            return True

        except Exception as e:
            self.logger.error(f"System diagnostics failed: {str(e)}")
            return False

    def acquire_background(self, num_frames: int = 10) -> np.ndarray:
        """
        Acquire background image with laser blocked.

        Args:
            num_frames: Number of frames to average for background

        Returns:
            np.ndarray: Background image
        """
        self.logger.info(f"Acquiring background image ({num_frames} frames)")

        input("Please block the laser and press Enter to continue...")

        background_frames = []
        for i in range(num_frames):
            frame = self.hardware_system.camera.acquire_frame()
            background_frames.append(frame)
            self.logger.info(f"Background frame {i+1}/{num_frames} acquired")

        self.background_image = np.mean(background_frames, axis=0)
        self.logger.info("Background acquisition complete")

        input("Please unblock the laser and press Enter to continue...")

        return self.background_image

    def run_polarization_scan(
        self,
        angles: Optional[List[float]] = None,
        save_path: Optional[str] = None,
    ) -> Dict:
        """
        Run automated polarization-resolved SHG measurement.

        Args:
            angles: List of HWP angles to scan (degrees)
            save_path: Path for saving measurement data

        Returns:
            Dict: Measurement results and metadata
        """
        if not self.is_initialized:
            raise RuntimeError(
                "System not initialized. Call initialize_system() first."
            )

        # Use config angles if none provided
        if angles is None:
            scan_config = self.config["measurement"]["polarization_scan"]
            angles = np.arange(
                scan_config["start_angle"],
                scan_config["end_angle"] + scan_config["step_size"],
                scan_config["step_size"],
            )

        self.logger.info(f"Starting polarization scan: {len(angles)} angles")
        self.measurement_active = True

        try:
            # Acquire background if enabled and not already done
            if (
                self.config["measurement"]["background_subtraction"]
                and self.background_image is None
            ):
                self.acquire_background()

            # Initialize data storage
            self.scan_data = []
            polarization_angles = []
            shg_intensities = []
            full_images = []

            # Scan loop
            for i, angle in enumerate(angles):
                if not self.measurement_active:
                    self.logger.info("Measurement cancelled by user")
                    break

                self.logger.info(f"Measuring angle {angle}° ({i+1}/{len(angles)})")

                # Set polarization angle
                self.hardware_system.elliptec.set_hwp_incident_angle(angle)

                # Wait for movement to complete
                time.sleep(0.5)  # Allow for mechanical settling

                # Acquire frames with averaging
                frame_data = self._acquire_averaged_frames(
                    self.config["measurement"]["polarization_scan"]["averaging_frames"]
                )

                # Process frame data
                processed_frame, intensity = self._process_frame(frame_data)

                # Store data
                polarization_angles.append(angle)
                shg_intensities.append(intensity)

                if self.config["measurement"]["save_full_images"]:
                    full_images.append(processed_frame)

                # Log progress
                self.logger.info(f"Angle {angle}°: SHG intensity = {intensity:.2f}")

            # Compile results
            results = {
                "polarization_angles": np.array(polarization_angles),
                "shg_intensities": np.array(shg_intensities),
                "full_images": np.array(full_images) if full_images else None,
                "background_image": self.background_image,
                "metadata": self._generate_metadata(),
            }

            # Save data if path provided
            if save_path:
                self._save_results(results, save_path)

            self.logger.info("Polarization scan completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"Polarization scan failed: {str(e)}")
            raise
        finally:
            self.measurement_active = False

    def _acquire_averaged_frames(self, num_frames: int) -> np.ndarray:
        """Acquire and average multiple frames."""
        frames = []
        for i in range(num_frames):
            frame = self.hardware_system.camera.acquire_frame()
            frames.append(frame)

        return np.mean(frames, axis=0)

    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Process acquired frame with background subtraction and ROI integration.

        Args:
            frame: Raw camera frame

        Returns:
            Tuple[np.ndarray, float]: (processed_frame, integrated_intensity)
        """
        # Background subtraction if enabled
        if (
            self.config["measurement"]["background_subtraction"]
            and self.background_image is not None
        ):
            processed_frame = frame - self.background_image
            # Clip negative values
            processed_frame = np.clip(processed_frame, 0, None)
        else:
            processed_frame = frame.copy()

        # ROI integration
        roi_config = self.config["hardware"]["camera"]["roi"]
        if roi_config["enabled"]:
            x, y = roi_config["x"], roi_config["y"]
            w, h = roi_config["width"], roi_config["height"]
            roi_intensity = np.sum(processed_frame[y : y + h, x : x + w])
        else:
            roi_intensity = np.sum(processed_frame)

        return processed_frame, float(roi_intensity)

    def _generate_metadata(self) -> Dict:
        """Generate comprehensive metadata for the measurement."""
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "configuration": self.config,
            "hardware_status": self.hardware_system.get_system_status(),
            "software_version": "0.1.0",
            "measurement_type": "polarization_resolved_shg",
        }

    def _save_results(self, results: Dict, save_path: str):
        """Save measurement results in multiple formats."""
        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"rashg_scan_{timestamp}"

        # Save HDF5 file with complete data
        h5_file = save_dir / f"{base_name}.h5"
        rashg_analysis.save_rashg_data(results, str(h5_file))

        # Save CSV file with extracted data
        csv_file = save_dir / f"{base_name}.csv"
        self._save_csv_data(results, str(csv_file))

        # Save analysis plots
        plot_file = save_dir / f"{base_name}_analysis.png"
        self._create_analysis_plots(results, str(plot_file))

        self.logger.info(f"Results saved to {save_dir}")

    def _save_csv_data(self, results: Dict, csv_path: str):
        """Save angle vs intensity data as CSV."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "polarization_angle_deg": results["polarization_angles"],
                "shg_intensity": results["shg_intensities"],
            }
        )
        df.to_csv(csv_path, index=False)

    def _create_analysis_plots(self, results: Dict, plot_path: str):
        """Create and save analysis plots."""
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Linear plot
        ax1.plot(results["polarization_angles"], results["shg_intensities"], "bo-")
        ax1.set_xlabel("HWP Angle (degrees)")
        ax1.set_ylabel("SHG Intensity (counts)")
        ax1.set_title("Polarization-Resolved SHG")
        ax1.grid(True)

        # Polar plot
        angles_rad = np.deg2rad(
            2 * results["polarization_angles"]
        )  # Factor of 2 for SHG
        ax2 = plt.subplot(122, projection="polar")
        ax2.plot(angles_rad, results["shg_intensities"], "ro-")
        ax2.set_title("SHG Polar Response")

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

    def stop_measurement(self):
        """Stop the current measurement."""
        self.measurement_active = False
        self.logger.info("Measurement stop requested")

    def shutdown_system(self):
        """Safely shutdown the measurement system."""
        try:
            self.logger.info("Shutting down μRASHG system...")

            if self.measurement_active:
                self.stop_measurement()
                time.sleep(1)  # Allow measurement to stop

            if self.hardware_system:
                self.hardware_system.shutdown_all_hardware()

            if self.dashboard:
                self.dashboard.quit_fun()

            self.logger.info("System shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")


def main():
    """Main function for standalone script execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Automated μRASHG Measurement")
    parser.add_argument("--config", type=str, help="Configuration file path")
    parser.add_argument(
        "--output",
        type=str,
        default="./data/",
        help="Output directory for results",
    )
    parser.add_argument("--angles", type=str, help="Comma-separated list of angles")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse angles if provided
    angles = None
    if args.angles:
        angles = [float(x.strip()) for x in args.angles.split(",")]

    # Initialize scanner
    scanner = AutomatedμRASHGScanner(config_file=args.config)

    try:
        # Initialize system
        if not scanner.initialize_system():
            print("System initialization failed. Please check hardware connections.")
            return 1

        # Run measurement
        results = scanner.run_polarization_scan(angles=angles, save_path=args.output)

        print(f"Measurement completed successfully!")
        print(f"Measured {len(results['polarization_angles'])} angles")
        print(f"Results saved to {args.output}")

        return 0

    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user")
        scanner.stop_measurement()
        return 0

    except Exception as e:
        print(f"Measurement failed: {str(e)}")
        return 1

    finally:
        scanner.shutdown_system()


if __name__ == "__main__":
    sys.exit(main())
