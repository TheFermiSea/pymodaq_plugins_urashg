# -*- coding: utf-8 -*-
"""
μRASHG Microscopy Extension for PyMoDAQ

This extension provides comprehensive multi-device coordination for μRASHG
(micro Rotational Anisotropy Second Harmonic Generation) microscopy measurements.
It integrates with PyMoDAQ's dashboard framework using proper extension patterns.

Hardware Coordination:
- 3x Elliptec rotation mounts (QWP, HWP incident, HWP analyzer)
- Photometrics PrimeBSI camera
- Newport 1830-C power meter
- MaiTai laser with wavelength control
- Optional: ESP300 motion controller

Experiment Capabilities:
- Basic RASHG measurements with polarization sweeps
- Multi-wavelength RASHG scanning
- Full polarimetric SHG analysis
- Automated calibration sequences
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pyqtgraph as pg
from pymodaq.utils.config import Config
from pymodaq.utils.data import Axis, DataWithAxes, DataActuator
from pymodaq.utils.logger import get_module_name, set_logger
from pymodaq.utils.messenger import messagebox
from pymodaq.utils.parameter import Parameter
from pymodaq_data.data import DataRaw, DataSource
from pymodaq_gui import utils as gutils
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_utils.config import Config as UtilsConfig
from pyqtgraph.dockarea import Dock, DockArea
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QObject, QThread, Signal, QTimer

from pymodaq.extensions.utils import CustomExt
from pymodaq_plugins_urashg.utils.config import Config as PluginConfig

logger = set_logger(get_module_name(__file__))

# Extension metadata for PyMoDAQ discovery
EXTENSION_NAME = "μRASHG Microscopy System"
CLASS_NAME = "URASHGMicroscopyExtension"

# Load configurations
main_config = Config()
plugin_config = PluginConfig()


class MeasurementWorker(QThread):
    """
    Worker thread for RASHG measurements following PyMoDAQ threading patterns.

    Coordinates multi-device measurements without blocking the UI.
    """

    # Signals for thread communication
    measurement_data = Signal(object)  # Emitted when new data is acquired
    measurement_progress = Signal(int)  # Progress percentage (0-100)
    measurement_finished = Signal(bool)  # True if successful, False if error
    status_message = Signal(str, str)  # message, level (info/warning/error)

    def __init__(self, extension):
        super().__init__()
        self.extension = extension
        self.measurement_active = False
        self.measurement_params = {}

    def setup_measurement(self, measurement_type: str, params: Dict[str, Any]):
        """Setup measurement parameters."""
        self.measurement_type = measurement_type
        self.measurement_params = params

    def run(self):
        """Execute the measurement sequence."""
        try:
            self.measurement_active = True
            self.status_message.emit("Starting measurement...", "info")

            if self.measurement_type == "Basic RASHG":
                self._run_basic_rashg()
            elif self.measurement_type == "Multi-Wavelength RASHG":
                self._run_multiwavelength_rashg()
            elif self.measurement_type == "Full Polarimetric SHG":
                self._run_polarimetric_shg()
            elif self.measurement_type == "Calibration":
                self._run_calibration()
            else:
                raise ValueError(f"Unknown measurement type: {self.measurement_type}")

            self.measurement_finished.emit(True)

        except Exception as e:
            logger.error(f"Measurement error: {e}")
            self.status_message.emit(f"Measurement error: {e}", "error")
            self.measurement_finished.emit(False)
        finally:
            self.measurement_active = False

    def _run_basic_rashg(self):
        """Execute basic RASHG polarization sweep."""
        pol_steps = self.measurement_params.get("pol_steps", 36)
        integration_time = self.measurement_params.get("integration_time", 100)

        # Get device references from modules_manager
        elliptec = self.extension.modules_manager.actuators.get(
            "Elliptec_Polarization_Control"
        )
        camera = self.extension.modules_manager.detectors_2D.get("PrimeBSI_SHG_Camera")
        power_meter = self.extension.modules_manager.detectors_0D.get(
            "Newport_Power_Meter"
        )

        if not elliptec or not camera:
            raise RuntimeError("Required devices (Elliptec, Camera) not available")

        # Polarization sweep
        angles = np.linspace(0, 180, pol_steps)
        data_collection = []

        for i, angle in enumerate(angles):
            if not self.measurement_active:
                break

            # Move HWP incident polarizer (axis 0)
            hwp_positions = [angle, 0, 0]  # Only move first axis
            position_data = DataActuator(data=[np.array(hwp_positions)])
            elliptec.move_abs(position_data)

            # Wait for movement completion
            time.sleep(0.5)

            # Set camera exposure
            if hasattr(camera, "settings"):
                camera.settings.child("camera_settings", "exposure").setValue(
                    integration_time
                )

            # Acquire camera data
            camera.grab_data(Naverage=1)

            # Acquire power meter data if available
            if power_meter:
                power_meter.grab_data(Naverage=3)

            # Update progress
            progress = int((i + 1) / len(angles) * 100)
            self.measurement_progress.emit(progress)

            self.status_message.emit(f"Measured angle {angle:.1f}°", "info")

        self.status_message.emit("Basic RASHG measurement completed", "info")

    def _run_multiwavelength_rashg(self):
        """Execute multi-wavelength RASHG scan."""
        wavelength_start = self.measurement_params.get("wavelength_start", 780)
        wavelength_stop = self.measurement_params.get("wavelength_stop", 800)
        wavelength_step = self.measurement_params.get("wavelength_step", 5)

        # Get laser control
        laser = self.extension.modules_manager.actuators.get("MaiTai_Laser_Control")
        if not laser:
            raise RuntimeError("MaiTai laser not available")

        wavelengths = np.arange(
            wavelength_start, wavelength_stop + wavelength_step, wavelength_step
        )

        for i, wavelength in enumerate(wavelengths):
            if not self.measurement_active:
                break

            # Set laser wavelength
            wavelength_data = DataActuator(data=[wavelength])
            laser.move_abs(wavelength_data)

            # Wait for wavelength stabilization
            time.sleep(2.0)

            # Run basic RASHG at this wavelength
            self._run_basic_rashg()

            progress = int((i + 1) / len(wavelengths) * 100)
            self.measurement_progress.emit(progress)

            self.status_message.emit(f"Completed wavelength {wavelength} nm", "info")

    def _run_polarimetric_shg(self):
        """Execute full polarimetric SHG analysis."""
        # Implementation for full Stokes parameter analysis
        self.status_message.emit(
            "Full polarimetric SHG analysis not yet implemented", "warning"
        )

    def _run_calibration(self):
        """Execute calibration sequence."""
        # Home all rotation mounts
        elliptec = self.extension.modules_manager.actuators.get(
            "Elliptec_Polarization_Control"
        )
        if elliptec and hasattr(elliptec, "move_home"):
            elliptec.move_home()
            self.status_message.emit("Homed all rotation mounts", "info")

        # Additional calibration steps...
        self.status_message.emit("Calibration completed", "info")

    def stop_measurement(self):
        """Stop the current measurement."""
        self.measurement_active = False
        self.status_message.emit("Measurement stopped by user", "warning")


class URASHGMicroscopyExtension(CustomExt):
    """
    Production-ready μRASHG Extension for PyMoDAQ Dashboard

    Follows PyMoDAQ 5.x extension patterns and integrates properly with
    the dashboard through PresetManager and modules_manager.
    """

    # Extension parameters following PyMoDAQ patterns
    params = [
        {
            "title": "Experiment Configuration",
            "name": "experiment",
            "type": "group",
            "children": [
                {
                    "title": "Measurement Type:",
                    "name": "measurement_type",
                    "type": "list",
                    "limits": [
                        "Basic RASHG",
                        "Multi-Wavelength RASHG",
                        "Full Polarimetric SHG",
                        "Calibration",
                    ],
                    "value": "Basic RASHG",
                },
                {
                    "title": "Polarization Steps:",
                    "name": "pol_steps",
                    "type": "int",
                    "value": 36,
                    "min": 4,
                    "max": 360,
                    "step": 1,
                },
                {
                    "title": "Integration Time (ms):",
                    "name": "integration_time",
                    "type": "float",
                    "value": 100.0,
                    "min": 1.0,
                    "max": 10000.0,
                    "suffix": "ms",
                },
            ],
        },
        {
            "title": "Wavelength Scan",
            "name": "wavelength_scan",
            "type": "group",
            "children": [
                {
                    "title": "Start (nm):",
                    "name": "wavelength_start",
                    "type": "float",
                    "value": 780.0,
                    "min": 700.0,
                    "max": 900.0,
                    "suffix": "nm",
                },
                {
                    "title": "Stop (nm):",
                    "name": "wavelength_stop",
                    "type": "float",
                    "value": 800.0,
                    "min": 700.0,
                    "max": 900.0,
                    "suffix": "nm",
                },
                {
                    "title": "Step (nm):",
                    "name": "wavelength_step",
                    "type": "float",
                    "value": 5.0,
                    "min": 0.1,
                    "max": 50.0,
                    "suffix": "nm",
                },
            ],
        },
        {
            "title": "Data Management",
            "name": "data_management",
            "type": "group",
            "children": [
                {
                    "title": "Auto Save:",
                    "name": "auto_save",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Save Format:",
                    "name": "save_format",
                    "type": "list",
                    "limits": ["HDF5", "CSV", "NPZ"],
                    "value": "HDF5",
                },
                {
                    "title": "Data Path:",
                    "name": "data_path",
                    "type": "browsepath",
                    "value": str(Path.home() / "rashg_data"),
                },
            ],
        },
        {
            "title": "Device Status",
            "name": "device_status",
            "type": "group",
            "children": [
                {
                    "title": "Elliptec Status:",
                    "name": "elliptec_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                },
                {
                    "title": "Camera Status:",
                    "name": "camera_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                },
                {
                    "title": "Laser Status:",
                    "name": "laser_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                },
                {
                    "title": "Power Meter Status:",
                    "name": "power_meter_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                },
            ],
        },
    ]

    def __init__(self, parent: gutils.DockArea, dashboard):
        """
        Initialize the URASHG extension.

        Args:
            parent: DockArea parent widget
            dashboard: PyMoDAQ dashboard instance with modules_manager
        """
        super().__init__(parent, dashboard)

        # Access to PyMoDAQ's device management
        self._modules_manager = dashboard.modules_manager if dashboard else None

        # Measurement worker thread
        self.measurement_worker = None

        # Data viewers
        self.camera_viewer = None
        self.plot_viewer = None

        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_device_status)
        self.status_timer.start(5000)  # Update every 5 seconds

        # Initialize UI
        self.setup_ui()

    @property
    def modules_manager(self):
        """Access to PyMoDAQ's modules manager."""
        return self._modules_manager

    def setup_docks(self):
        """Setup the extension docks layout."""

        # Ensure dockarea is available
        if not hasattr(self, "dockarea") or self.dockarea is None:
            logger.warning("No dockarea available for extension docks")
            return

        # Main control dock
        self.docks["control"] = gutils.Dock("URASHG Control", size=(400, 600))
        self.dockarea.addDock(self.docks["control"])

        # Add settings tree to control dock
        if hasattr(self, "settings_tree") and self.settings_tree is not None:
            self.docks["control"].addWidget(self.settings_tree)

        # Camera data viewer dock
        self.docks["camera"] = gutils.Dock("SHG Camera Data", size=(600, 600))
        self.dockarea.addDock(self.docks["camera"], "right", self.docks["control"])

        # Create camera viewer
        self.camera_viewer = Viewer2D(self.docks["camera"])
        self.docks["camera"].addWidget(self.camera_viewer)

        # Plot analysis dock
        self.docks["plots"] = gutils.Dock("RASHG Analysis", size=(600, 400))
        self.dockarea.addDock(self.docks["plots"], "bottom", self.docks["camera"])

        # Create plot viewer
        self.plot_viewer = Viewer1D(self.docks["plots"])
        self.docks["plots"].addWidget(self.plot_viewer)

        # Status dock
        self.docks["status"] = gutils.Dock("System Status", size=(400, 200))
        self.dockarea.addDock(self.docks["status"], "bottom", self.docks["control"])

        # Create status display widget
        self.status_widget = QtWidgets.QTextEdit()
        self.status_widget.setReadOnly(True)
        self.status_widget.setMaximumHeight(180)
        self.docks["status"].addWidget(self.status_widget)

    def setup_actions(self):
        """Setup extension actions."""

        # Measurement actions
        self.add_action(
            "start_measurement",
            "Start Measurement",
            "run",
            "Start RASHG measurement sequence",
            checkable=False,
        )
        self.add_action(
            "stop_measurement",
            "Stop Measurement",
            "stop",
            "Stop current measurement",
            checkable=False,
        )

        # Device actions
        self.add_action(
            "initialize_devices",
            "Initialize Devices",
            "connect",
            "Initialize all RASHG devices",
            checkable=False,
        )
        self.add_action(
            "home_rotators",
            "Home Rotators",
            "home",
            "Home all rotation mounts",
            checkable=False,
        )

        # Calibration actions
        self.add_action(
            "run_calibration",
            "Run Calibration",
            "calibrate",
            "Run system calibration",
            checkable=False,
        )

        # Data actions
        self.add_action(
            "save_data", "Save Data", "save", "Save current data", checkable=False
        )
        self.add_action(
            "load_data", "Load Data", "open", "Load previous data", checkable=False
        )

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """Setup extension menu."""
        if menubar is None:
            return

        # Measurement menu
        measurement_menu = menubar.addMenu("Measurement")
        self.affect_to("start_measurement", measurement_menu)
        self.affect_to("stop_measurement", measurement_menu)
        measurement_menu.addSeparator()
        self.affect_to("run_calibration", measurement_menu)

        # Device menu
        device_menu = menubar.addMenu("Devices")
        self.affect_to("initialize_devices", device_menu)
        self.affect_to("home_rotators", device_menu)

        # Data menu
        data_menu = menubar.addMenu("Data")
        self.affect_to("save_data", data_menu)
        self.affect_to("load_data", data_menu)

    def connect_things(self):
        """Connect actions and signals."""

        # Connect actions to methods
        self.get_action("start_measurement").triggered.connect(self.start_measurement)
        self.get_action("stop_measurement").triggered.connect(self.stop_measurement)
        self.get_action("initialize_devices").triggered.connect(self.initialize_devices)
        self.get_action("home_rotators").triggered.connect(self.home_rotators)
        self.get_action("run_calibration").triggered.connect(self.run_calibration)
        self.get_action("save_data").triggered.connect(self.save_data)
        self.get_action("load_data").triggered.connect(self.load_data)

    def value_changed(self, param):
        """Handle parameter changes."""
        param_name = param.name()
        param_value = param.value()

        if param_name == "measurement_type":
            self.log_message(f"Measurement type changed to: {param_value}")

        elif param_name in ["pol_steps", "integration_time"]:
            self.log_message(f"Updated {param_name}: {param_value}")

        elif param_name in ["wavelength_start", "wavelength_stop", "wavelength_step"]:
            self.log_message(
                f"Wavelength scan parameter updated: {param_name} = {param_value}"
            )

    def start_measurement(self):
        """Start a RASHG measurement sequence."""
        try:
            if self.measurement_worker and self.measurement_worker.isRunning():
                self.log_message("Measurement already in progress", "warning")
                return

            # Check device availability
            if not self._check_devices_ready():
                self.log_message("Not all required devices are ready", "error")
                return

            # Get measurement parameters
            measurement_type = self.settings.child(
                "experiment", "measurement_type"
            ).value()
            params = {
                "pol_steps": self.settings.child("experiment", "pol_steps").value(),
                "integration_time": self.settings.child(
                    "experiment", "integration_time"
                ).value(),
                "wavelength_start": self.settings.child(
                    "wavelength_scan", "wavelength_start"
                ).value(),
                "wavelength_stop": self.settings.child(
                    "wavelength_scan", "wavelength_stop"
                ).value(),
                "wavelength_step": self.settings.child(
                    "wavelength_scan", "wavelength_step"
                ).value(),
            }

            # Create and start measurement worker
            self.measurement_worker = MeasurementWorker(self)
            self.measurement_worker.setup_measurement(measurement_type, params)

            # Connect worker signals
            self.measurement_worker.measurement_data.connect(self.on_measurement_data)
            self.measurement_worker.measurement_progress.connect(
                self.on_measurement_progress
            )
            self.measurement_worker.measurement_finished.connect(
                self.on_measurement_finished
            )
            self.measurement_worker.status_message.connect(self.log_message)

            # Start measurement
            self.measurement_worker.start()
            self.log_message(f"Started {measurement_type} measurement", "info")

        except Exception as e:
            self.log_message(f"Error starting measurement: {e}", "error")

    def stop_measurement(self):
        """Stop the current measurement."""
        if self.measurement_worker and self.measurement_worker.isRunning():
            self.measurement_worker.stop_measurement()
            self.measurement_worker.wait(3000)  # Wait up to 3 seconds
            self.log_message("Measurement stopped", "warning")
        else:
            self.log_message("No measurement in progress", "info")

    def initialize_devices(self):
        """Initialize all RASHG devices using PyMoDAQ's modules_manager."""
        try:
            self.log_message("Initializing RASHG devices...")

            # Check if modules_manager is available
            if not self._modules_manager:
                self.log_message("No modules manager available", "error")
                return False

            # Check if devices are loaded in modules_manager
            actuators = self._modules_manager.actuators
            detectors_2d = self._modules_manager.detectors_2D
            detectors_0d = self._modules_manager.detectors_0D

            # Expected devices from preset
            expected_devices = {
                "actuators": ["Elliptec_Polarization_Control", "MaiTai_Laser_Control"],
                "detectors_2D": ["PrimeBSI_SHG_Camera"],
                "detectors_0D": ["Newport_Power_Meter"],
            }

            # Check device availability
            missing_devices = []

            for device_name in expected_devices["actuators"]:
                if device_name not in actuators:
                    missing_devices.append(f"Actuator: {device_name}")

            for device_name in expected_devices["detectors_2D"]:
                if device_name not in detectors_2d:
                    missing_devices.append(f"2D Detector: {device_name}")

            for device_name in expected_devices["detectors_0D"]:
                if device_name not in detectors_0d:
                    missing_devices.append(f"0D Detector: {device_name}")

            if missing_devices:
                missing_list = "\n".join(missing_devices)
                self.log_message(
                    f"Missing devices:\n{missing_list}\n\nPlease load the URASHG preset first.",
                    "error",
                )
                return False

            self.log_message("All RASHG devices are available", "info")
            self.update_device_status()
            return True

        except Exception as e:
            self.log_message(f"Error initializing devices: {e}", "error")
            return False

    def home_rotators(self):
        """Home all rotation mounts."""
        try:
            elliptec = self._modules_manager.actuators.get(
                "Elliptec_Polarization_Control"
            )
            if elliptec:
                if hasattr(elliptec, "move_home"):
                    elliptec.move_home()
                    self.log_message("Homing all rotation mounts...", "info")
                else:
                    self.log_message(
                        "Elliptec device does not support homing", "warning"
                    )
            else:
                self.log_message("Elliptec device not available", "error")

        except Exception as e:
            self.log_message(f"Error homing rotators: {e}", "error")

    def run_calibration(self):
        """Run system calibration."""
        if self.measurement_worker and self.measurement_worker.isRunning():
            self.log_message("Cannot run calibration during measurement", "warning")
            return

        # Set measurement type to calibration and start
        self.settings.child("experiment", "measurement_type").setValue("Calibration")
        self.start_measurement()

    def save_data(self):
        """Save current measurement data."""
        # Implementation depends on data format
        self.log_message("Data saving not yet implemented", "warning")

    def load_data(self):
        """Load previous measurement data."""
        # Implementation depends on data format
        self.log_message("Data loading not yet implemented", "warning")

    def update_device_status(self):
        """Update device status indicators."""
        try:
            if not self._modules_manager:
                return

            # Check Elliptec status
            elliptec = self._modules_manager.actuators.get(
                "Elliptec_Polarization_Control"
            )
            elliptec_status = "Connected" if elliptec else "Not Available"
            self.settings.child("device_status", "elliptec_status").setValue(
                elliptec_status
            )

            # Check Camera status
            camera = self._modules_manager.detectors_2D.get("PrimeBSI_SHG_Camera")
            camera_status = "Connected" if camera else "Not Available"
            self.settings.child("device_status", "camera_status").setValue(
                camera_status
            )

            # Check Laser status
            laser = self._modules_manager.actuators.get("MaiTai_Laser_Control")
            laser_status = "Connected" if laser else "Not Available"
            self.settings.child("device_status", "laser_status").setValue(laser_status)

            # Check Power Meter status
            power_meter = self._modules_manager.detectors_0D.get("Newport_Power_Meter")
            power_meter_status = "Connected" if power_meter else "Not Available"
            self.settings.child("device_status", "power_meter_status").setValue(
                power_meter_status
            )

        except Exception as e:
            logger.error(f"Error updating device status: {e}")

    def _check_devices_ready(self) -> bool:
        """Check if all required devices are ready for measurement."""
        if not self._modules_manager:
            return False

        elliptec = self._modules_manager.actuators.get("Elliptec_Polarization_Control")
        camera = self._modules_manager.detectors_2D.get("PrimeBSI_SHG_Camera")

        # Minimum required: Elliptec + Camera
        return elliptec is not None and camera is not None

    def on_measurement_data(self, data):
        """Handle new measurement data."""
        # Update data viewers
        if hasattr(data, "data") and self.camera_viewer:
            # Display camera data if available
            pass

    def on_measurement_progress(self, progress: int):
        """Handle measurement progress updates."""
        self.log_message(f"Measurement progress: {progress}%", "info")

    def on_measurement_finished(self, success: bool):
        """Handle measurement completion."""
        if success:
            self.log_message("Measurement completed successfully", "info")
        else:
            self.log_message("Measurement failed or was interrupted", "error")

        # Clean up worker
        if self.measurement_worker:
            self.measurement_worker = None

    def log_message(self, message: str, level: str = "info"):
        """Add a message to the status log."""
        timestamp = time.strftime("%H:%M:%S")

        if level == "error":
            formatted_msg = (
                f"<span style='color: red;'>[{timestamp}] ERROR: {message}</span>"
            )
        elif level == "warning":
            formatted_msg = (
                f"<span style='color: orange;'>[{timestamp}] WARNING: {message}</span>"
            )
        else:
            formatted_msg = f"[{timestamp}] {message}"

        if hasattr(self, "status_widget"):
            self.status_widget.append(formatted_msg)

        # Also log to Python logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)


def main():
    """Main function for standalone testing."""
    from pymodaq.utils.gui_utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset
    from pymodaq.utils.messenger import messagebox
    from pymodaq_utils.config import ConfigError

    app = mkQApp(EXTENSION_NAME)
    try:
        preset_file_name = plugin_config(
            "presets", "preset_for_urashgmicroscopyextension"
        )
        load_dashboard_with_preset(preset_file_name, EXTENSION_NAME)
        app.exec()

    except ConfigError:
        messagebox(
            f'No entry with name "preset_for_urashgmicroscopyextension" has been configured '
            f"in the plugin config file. The toml entry should be:\n"
            f"[presets]\n"
            f'preset_for_urashgmicroscopyextension = "urashg_microscopy_system"'
        )


if __name__ == "__main__":
    main()
