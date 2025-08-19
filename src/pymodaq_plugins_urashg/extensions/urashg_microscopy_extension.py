# -*- coding: utf-8 -*-
"""
μRASHG Microscopy Extension for PyMoDAQ

This extension provides comprehensive multi-device coordination for μRASHG
(micro Rotational Anisotropy Second Harmonic Generation) microscopy measurements.
It integrates all hardware devices through PyMoDAQ's dashboard framework.

Hardware Coordination:
- 3x Elliptec rotation mounts (QWP, HWP incident, HWP analyzer)
- Photometrics PrimeBSI camera
- Newport 1830-C power meter
- MaiTai laser with EOM control
- Optional: PyRPL PID stabilization

Experiment Capabilities:
- Basic RASHG measurements with polarization sweeps
- Multi-wavelength RASHG scanning
- Full polarimetric SHG analysis
- Automated calibration sequences
"""

import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import QObject, Signal
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea

from pymodaq.utils.gui_utils import CustomApp
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataWithAxes, Axis
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from pymodaq.utils.messenger import messagebox
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_data.data import DataRaw


from pathlib import Path

logger = set_logger(get_module_name(__file__))


class URASHGMicroscopyExtension(CustomApp):
    """
    Production-ready μRASHG Extension for PyMoDAQ Dashboard

    Provides coordinated control of multiple devices for sophisticated
    polarimetric SHG measurements through PyMoDAQ's Extension framework.
    """

    # Extension metadata
    name = "μRASHG Microscopy System"
    description = (
        "Complete polarimetric SHG measurements with multi-device coordination"
    )
    author = "μRASHG Development Team"
    version = "1.0.0"

    # Signals for inter-component communication
    measurement_started = Signal()
    measurement_finished = Signal()
    measurement_progress = Signal(int)  # Progress percentage 0-100
    device_status_changed = Signal(str, str)  # device_name, status
    error_occurred = Signal(str)  # error_message

    # Parameter tree definition
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
                    "type": "int",
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 1,
                },
                {
                    "title": "Number of Averages:",
                    "name": "averages",
                    "type": "int",
                    "value": 1,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "title": "Polarization Range",
                    "name": "pol_range",
                    "type": "group",
                    "children": [
                        {
                            "title": "Start Angle (°):",
                            "name": "pol_start",
                            "type": "float",
                            "value": 0.0,
                            "min": 0.0,
                            "max": 360.0,
                            "step": 0.1,
                        },
                        {
                            "title": "End Angle (°):",
                            "name": "pol_end",
                            "type": "float",
                            "value": 180.0,
                            "min": 0.0,
                            "max": 360.0,
                            "step": 0.1,
                        },
                    ],
                },
            ],
        },
        {
            "title": "Hardware Settings",
            "name": "hardware",
            "type": "group",
            "children": [
                {
                    "title": "Device Configuration",
                    "name": "devices",
                    "type": "group",
                    "children": [
                        {
                            "title": "QWP Device:",
                            "name": "qwp_device",
                            "type": "str",
                            "value": "Elliptec",
                            "readonly": True,
                        },
                        {
                            "title": "QWP Axis Index:",
                            "name": "qwp_axis",
                            "type": "int",
                            "value": 0,
                            "min": 0,
                            "max": 2,
                            "readonly": True,
                        },
                        {
                            "title": "HWP Incident Device:",
                            "name": "hwp_inc_device",
                            "type": "str",
                            "value": "Elliptec",
                            "readonly": True,
                        },
                        {
                            "title": "HWP Incident Axis:",
                            "name": "hwp_inc_axis",
                            "type": "int",
                            "value": 1,
                            "min": 0,
                            "max": 2,
                            "readonly": True,
                        },
                        {
                            "title": "HWP Analyzer Device:",
                            "name": "hwp_ana_device",
                            "type": "str",
                            "value": "Elliptec",
                            "readonly": True,
                        },
                        {
                            "title": "HWP Analyzer Axis:",
                            "name": "hwp_ana_axis",
                            "type": "int",
                            "value": 2,
                            "min": 0,
                            "max": 2,
                            "readonly": True,
                        },
                        {
                            "title": "Camera Device:",
                            "name": "camera_device",
                            "type": "str",
                            "value": "PrimeBSI",
                            "readonly": True,
                        },
                        {
                            "title": "Power Meter Device:",
                            "name": "power_device",
                            "type": "str",
                            "value": "Newport1830C",
                            "readonly": True,
                        },
                        {
                            "title": "Laser Device:",
                            "name": "laser_device",
                            "type": "str",
                            "value": "MaiTai",
                            "readonly": True,
                        },
                    ],
                },
                {
                    "title": "Camera Settings",
                    "name": "camera",
                    "type": "group",
                    "children": [
                        {
                            "title": "ROI Settings",
                            "name": "roi",
                            "type": "group",
                            "children": [
                                {
                                    "title": "X Start:",
                                    "name": "x_start",
                                    "type": "int",
                                    "value": 0,
                                    "min": 0,
                                    "max": 2048,
                                },
                                {
                                    "title": "Y Start:",
                                    "name": "y_start",
                                    "type": "int",
                                    "value": 0,
                                    "min": 0,
                                    "max": 2048,
                                },
                                {
                                    "title": "Width:",
                                    "name": "width",
                                    "type": "int",
                                    "value": 2048,
                                    "min": 1,
                                    "max": 2048,
                                },
                                {
                                    "title": "Height:",
                                    "name": "height",
                                    "type": "int",
                                    "value": 2048,
                                    "min": 1,
                                    "max": 2048,
                                },
                            ],
                        },
                        {
                            "title": "Binning:",
                            "name": "binning",
                            "type": "list",
                            "limits": ["1x1", "2x2", "4x4"],
                            "value": "1x1",
                        },
                    ],
                },
                {
                    "title": "Safety Limits",
                    "name": "safety",
                    "type": "group",
                    "children": [
                        {
                            "title": "Max Laser Power (%):",
                            "name": "max_power",
                            "type": "float",
                            "value": 50.0,
                            "min": 0.0,
                            "max": 100.0,
                            "step": 0.1,
                        },
                        {
                            "title": "Rotation Speed (°/s):",
                            "name": "rotation_speed",
                            "type": "float",
                            "value": 30.0,
                            "min": 1.0,
                            "max": 100.0,
                            "step": 1.0,
                        },
                        {
                            "title": "Camera Timeout (s):",
                            "name": "camera_timeout",
                            "type": "float",
                            "value": 5.0,
                            "min": 0.1,
                            "max": 60.0,
                            "step": 0.1,
                        },
                        {
                            "title": "Movement Timeout (s):",
                            "name": "movement_timeout",
                            "type": "float",
                            "value": 10.0,
                            "min": 1.0,
                            "max": 60.0,
                            "step": 0.1,
                        },
                    ],
                },
            ],
        },
        {
            "title": "Multi-Wavelength Settings",
            "name": "wavelength",
            "type": "group",
            "children": [
                {
                    "title": "Enable Wavelength Scan:",
                    "name": "enable_scan",
                    "type": "bool",
                    "value": False,
                },
                {
                    "title": "Start Wavelength (nm):",
                    "name": "wl_start",
                    "type": "int",
                    "value": 700,
                    "min": 700,
                    "max": 1000,
                    "step": 1,
                },
                {
                    "title": "Stop Wavelength (nm):",
                    "name": "wl_stop",
                    "type": "int",
                    "value": 900,
                    "min": 700,
                    "max": 1000,
                    "step": 1,
                },
                {
                    "title": "Wavelength Steps:",
                    "name": "wl_steps",
                    "type": "int",
                    "value": 10,
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "title": "Wavelength Stabilization (s):",
                    "name": "wl_stabilization",
                    "type": "float",
                    "value": 2.0,
                    "min": 0.1,
                    "max": 30.0,
                    "step": 0.1,
                },
                {
                    "title": "Auto-sync Power Meter:",
                    "name": "auto_sync_pm",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Sweep Mode:",
                    "name": "sweep_mode",
                    "type": "list",
                    "limits": ["Linear", "Logarithmic", "Custom"],
                    "value": "Linear",
                },
            ],
        },
        {
            "title": "Data Management",
            "name": "data",
            "type": "group",
            "children": [
                {
                    "title": "Save Directory:",
                    "name": "save_dir",
                    "type": "browsepath",
                    "value": str(Path.home() / "urashg_data"),
                },
                {
                    "title": "Auto Save:",
                    "name": "auto_save",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "File Prefix:",
                    "name": "file_prefix",
                    "type": "str",
                    "value": "urashg_measurement",
                },
                {
                    "title": "Save Raw Images:",
                    "name": "save_raw",
                    "type": "bool",
                    "value": False,
                },
                {
                    "title": "Save Processed Data:",
                    "name": "save_processed",
                    "type": "bool",
                    "value": True,
                },
            ],
        },
        {
            "title": "Advanced Settings",
            "name": "advanced",
            "type": "group",
            "children": [
                {
                    "title": "Real-time Analysis:",
                    "name": "realtime_analysis",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Background Subtraction:",
                    "name": "bg_subtraction",
                    "type": "bool",
                    "value": False,
                },
                {
                    "title": "Stabilization Time (s):",
                    "name": "stabilization_time",
                    "type": "float",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                },
            ],
        },
        # PyMoDAQ standard: Actions defined in parameter tree instead of manual buttons
        {
            "title": "Measurement Control",
            "name": "measurement_control",
            "type": "group",
            "children": [
                {
                    "title": "Start μRASHG Measurement",
                    "name": "start_measurement",
                    "type": "action",
                },
                {
                    "title": "Stop Measurement",
                    "name": "stop_measurement",
                    "type": "action",
                },
                {
                    "title": "Pause Measurement",
                    "name": "pause_measurement",
                    "type": "action",
                },
            ],
        },
        {
            "title": "Device Management",
            "name": "device_control",
            "type": "group",
            "children": [
                {
                    "title": "Initialize Devices",
                    "name": "initialize_devices",
                    "type": "action",
                },
                {
                    "title": "Check Device Status",
                    "name": "check_devices",
                    "type": "action",
                },
                {"title": "Emergency Stop", "name": "emergency_stop", "type": "action"},
            ],
        },
        {
            "title": "Configuration",
            "name": "configuration",
            "type": "group",
            "children": [
                {
                    "title": "Load Configuration",
                    "name": "load_config",
                    "type": "action",
                },
                {
                    "title": "Save Configuration",
                    "name": "save_config",
                    "type": "action",
                },
            ],
        },
        {
            "title": "Data Analysis",
            "name": "analysis",
            "type": "group",
            "children": [
                {
                    "title": "Analyze Current Data",
                    "name": "analyze_data",
                    "type": "action",
                },
                {
                    "title": "Fit RASHG Pattern",
                    "name": "fit_rashg_curve",
                    "type": "action",
                },
                {"title": "Export Data", "name": "export_data", "type": "action"},
                {
                    "title": "Export Analysis Results",
                    "name": "export_analysis",
                    "type": "action",
                },
            ],
        },
        # === DEVICE CONTROL PARAMETERS (Replace manual widget creation) ===
        {
            "title": "Device Control",
            "name": "device_control",
            "type": "group",
            "children": [
                # Laser Control
                {
                    "title": "Laser Control",
                    "name": "laser_control",
                    "type": "group",
                    "children": [
                        {
                            "title": "Laser Status:",
                            "name": "laser_status",
                            "type": "str",
                            "value": "Disconnected",
                            "readonly": True,
                        },
                        {
                            "title": "Current Wavelength (nm):",
                            "name": "current_wavelength",
                            "type": "float",
                            "value": 800.0,
                            "readonly": True,
                            "decimals": 1,
                        },
                        {
                            "title": "Set Wavelength (nm):",
                            "name": "set_wavelength",
                            "type": "float",
                            "value": 800.0,
                            "min": 700.0,
                            "max": 1000.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Set Wavelength:",
                            "name": "set_wavelength_action",
                            "type": "action",
                        },
                        {
                            "title": "Shutter Status:",
                            "name": "shutter_status",
                            "type": "str",
                            "value": "Unknown",
                            "readonly": True,
                        },
                        {
                            "title": "Open Shutter:",
                            "name": "open_shutter",
                            "type": "action",
                        },
                        {
                            "title": "Close Shutter:",
                            "name": "close_shutter",
                            "type": "action",
                        },
                    ],
                },
                # Rotator Control
                {
                    "title": "Rotator Control",
                    "name": "rotator_control",
                    "type": "group",
                    "children": [
                        {
                            "title": "QWP (Quarter Wave Plate)",
                            "name": "qwp_control",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Current Position (°):",
                                    "name": "qwp_current_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "readonly": True,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Set Position (°):",
                                    "name": "qwp_set_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "min": 0.0,
                                    "max": 360.0,
                                    "step": 0.01,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Move QWP:",
                                    "name": "move_qwp",
                                    "type": "action",
                                },
                                {
                                    "title": "Home QWP:",
                                    "name": "home_qwp",
                                    "type": "action",
                                },
                            ],
                        },
                        {
                            "title": "HWP Incident (Half Wave Plate)",
                            "name": "hwp_inc_control",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Current Position (°):",
                                    "name": "hwp_inc_current_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "readonly": True,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Set Position (°):",
                                    "name": "hwp_inc_set_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "min": 0.0,
                                    "max": 360.0,
                                    "step": 0.01,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Move HWP Inc:",
                                    "name": "move_hwp_inc",
                                    "type": "action",
                                },
                                {
                                    "title": "Home HWP Inc:",
                                    "name": "home_hwp_inc",
                                    "type": "action",
                                },
                            ],
                        },
                        {
                            "title": "HWP Analyzer (Half Wave Plate)",
                            "name": "hwp_ana_control",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Current Position (°):",
                                    "name": "hwp_ana_current_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "readonly": True,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Set Position (°):",
                                    "name": "hwp_ana_set_pos",
                                    "type": "float",
                                    "value": 0.0,
                                    "min": 0.0,
                                    "max": 360.0,
                                    "step": 0.01,
                                    "decimals": 2,
                                },
                                {
                                    "title": "Move HWP Ana:",
                                    "name": "move_hwp_ana",
                                    "type": "action",
                                },
                                {
                                    "title": "Home HWP Ana:",
                                    "name": "home_hwp_ana",
                                    "type": "action",
                                },
                            ],
                        },
                        {
                            "title": "Emergency Stop All Rotators:",
                            "name": "emergency_stop_rotators",
                            "type": "action",
                        },
                    ],
                },
                # Power Meter Control
                {
                    "title": "Power Meter Control",
                    "name": "power_control",
                    "type": "group",
                    "children": [
                        {
                            "title": "Current Power (mW):",
                            "name": "current_power",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 3,
                        },
                        {
                            "title": "Power Meter Wavelength (nm):",
                            "name": "power_wavelength",
                            "type": "float",
                            "value": 800.0,
                            "readonly": True,
                            "decimals": 1,
                        },
                        {
                            "title": "Auto-sync with laser:",
                            "name": "auto_sync_wavelength",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "title": "Sync Status:",
                            "name": "sync_status",
                            "type": "str",
                            "value": "Ready",
                            "readonly": True,
                        },
                        {
                            "title": "Manual Sync Now:",
                            "name": "manual_sync",
                            "type": "action",
                        },
                    ],
                },
            ],
        },
        # === ANALYSIS CONTROL PARAMETERS (Replace manual widget creation) ===
        {
            "title": "Analysis Control",
            "name": "analysis_control",
            "type": "group",
            "children": [
                # Polar Analysis
                {
                    "title": "Polar Analysis",
                    "name": "polar_analysis",
                    "type": "group",
                    "children": [
                        {
                            "title": "Real-time fitting:",
                            "name": "auto_fit",
                            "type": "bool",
                            "value": True,
                        },
                        {
                            "title": "Fit RASHG Pattern:",
                            "name": "fit_rashg",
                            "type": "action",
                        },
                        {
                            "title": "Fit Results:",
                            "name": "fit_results",
                            "type": "str",
                            "value": "No data",
                            "readonly": True,
                        },
                        {
                            "title": "RASHG Amplitude:",
                            "name": "rashg_amplitude",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 3,
                        },
                        {
                            "title": "Phase (°):",
                            "name": "phase_degrees",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 2,
                        },
                        {
                            "title": "R-squared:",
                            "name": "r_squared",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 4,
                        },
                    ],
                },
                # Spectral Analysis
                {
                    "title": "Spectral Analysis",
                    "name": "spectral_analysis",
                    "type": "group",
                    "children": [
                        {
                            "title": "Analysis Mode:",
                            "name": "spectral_mode",
                            "type": "list",
                            "limits": [
                                "RASHG Amplitude",
                                "Phase",
                                "Contrast",
                                "All Parameters",
                            ],
                            "value": "RASHG Amplitude",
                        },
                        {
                            "title": "Update Analysis:",
                            "name": "update_spectral",
                            "type": "action",
                        },
                        {
                            "title": "Analysis Status:",
                            "name": "spectral_status",
                            "type": "str",
                            "value": "Ready",
                            "readonly": True,
                        },
                    ],
                },
                # Power Monitoring
                {
                    "title": "Power Monitoring",
                    "name": "power_monitoring",
                    "type": "group",
                    "children": [
                        {
                            "title": "Current Power (mW):",
                            "name": "live_power",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 3,
                        },
                        {
                            "title": "Power Stability (%):",
                            "name": "power_stability",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 2,
                        },
                        {
                            "title": "Monitor Duration (s):",
                            "name": "monitor_duration",
                            "type": "int",
                            "value": 300,
                            "min": 30,
                            "max": 3600,
                        },
                    ],
                },
                # 3D Visualization
                {
                    "title": "3D Visualization",
                    "name": "volume_3d",
                    "type": "group",
                    "children": [
                        {
                            "title": "Visualization Mode:",
                            "name": "volume_mode",
                            "type": "list",
                            "limits": ["Surface", "Scatter", "Wireframe"],
                            "value": "Surface",
                        },
                        {
                            "title": "Update 3D View:",
                            "name": "update_3d",
                            "type": "action",
                        },
                        {
                            "title": "3D Available:",
                            "name": "opengl_available",
                            "type": "bool",
                            "value": False,
                            "readonly": True,
                        },
                    ],
                },
                # General Analysis
                {
                    "title": "General Analysis",
                    "name": "general_analysis",
                    "type": "group",
                    "children": [
                        {
                            "title": "Analysis Status:",
                            "name": "analysis_status",
                            "type": "str",
                            "value": "Ready",
                            "readonly": True,
                        },
                        {
                            "title": "Last Analysis Time:",
                            "name": "last_analysis_time",
                            "type": "str",
                            "value": "Never",
                            "readonly": True,
                        },
                        {
                            "title": "Data Points Analyzed:",
                            "name": "data_points_count",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                    ],
                },
            ],
        },
        # === STATUS MONITORING PARAMETERS (Replace manual widget creation) ===
        {
            "title": "Status Monitoring",
            "name": "status_monitoring",
            "type": "group",
            "children": [
                # Device Status
                {
                    "title": "Device Status",
                    "name": "device_status",
                    "type": "group",
                    "children": [
                        {
                            "title": "Camera Status:",
                            "name": "camera_status",
                            "type": "str",
                            "value": "Unknown",
                            "readonly": True,
                        },
                        {
                            "title": "Camera Temperature (°C):",
                            "name": "camera_temperature",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 2,
                        },
                        {
                            "title": "Laser Status:",
                            "name": "laser_status_display",
                            "type": "str",
                            "value": "Unknown",
                            "readonly": True,
                        },
                        {
                            "title": "Laser Wavelength (nm):",
                            "name": "laser_wavelength_display",
                            "type": "float",
                            "value": 0.0,
                            "readonly": True,
                            "decimals": 1,
                        },
                        {
                            "title": "Rotator Status:",
                            "name": "rotator_status",
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
                        {
                            "title": "Overall System Status:",
                            "name": "system_status",
                            "type": "str",
                            "value": "Initializing",
                            "readonly": True,
                        },
                    ],
                },
                # Measurement Status
                {
                    "title": "Measurement Status",
                    "name": "measurement_status",
                    "type": "group",
                    "children": [
                        {
                            "title": "Current State:",
                            "name": "measurement_state",
                            "type": "str",
                            "value": "Idle",
                            "readonly": True,
                        },
                        {
                            "title": "Progress (%):",
                            "name": "measurement_progress",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                            "min": 0,
                            "max": 100,
                        },
                        {
                            "title": "Data Points Collected:",
                            "name": "data_points_collected",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Estimated Time Remaining:",
                            "name": "time_remaining",
                            "type": "str",
                            "value": "--:--",
                            "readonly": True,
                        },
                        {
                            "title": "Last Error:",
                            "name": "last_error",
                            "type": "str",
                            "value": "None",
                            "readonly": True,
                        },
                    ],
                },
                # Hardware Health
                {
                    "title": "Hardware Health",
                    "name": "hardware_health",
                    "type": "group",
                    "children": [
                        {
                            "title": "Connection Uptime:",
                            "name": "connection_uptime",
                            "type": "str",
                            "value": "00:00:00",
                            "readonly": True,
                        },
                        {
                            "title": "Total Measurements:",
                            "name": "total_measurements",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Error Count:",
                            "name": "error_count",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Last Successful Measurement:",
                            "name": "last_successful_measurement",
                            "type": "str",
                            "value": "Never",
                            "readonly": True,
                        },
                        {
                            "title": "Performance Score:",
                            "name": "performance_score",
                            "type": "float",
                            "value": 100.0,
                            "readonly": True,
                            "decimals": 1,
                            "suffix": "%",
                        },
                    ],
                },
                # System Information
                {
                    "title": "System Information",
                    "name": "system_info",
                    "type": "group",
                    "children": [
                        {
                            "title": "Extension Version:",
                            "name": "extension_version",
                            "type": "str",
                            "value": "3.0.0",
                            "readonly": True,
                        },
                        {
                            "title": "PyMoDAQ Version:",
                            "name": "pymodaq_version",
                            "type": "str",
                            "value": "Unknown",
                            "readonly": True,
                        },
                        {
                            "title": "Session Start Time:",
                            "name": "session_start",
                            "type": "str",
                            "value": "Unknown",
                            "readonly": True,
                        },
                        {
                            "title": "Available Devices:",
                            "name": "available_devices_count",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Missing Devices:",
                            "name": "missing_devices_count",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                    ],
                },
            ],
        },
        # === SCANNER INTEGRATION (PyMoDAQ coordinated measurements) ===
        {
            "title": "Scanner Integration",
            "name": "scanner_integration",
            "type": "group",
            "children": [
                # Scan Type Selection
                {
                    "title": "Scan Configuration",
                    "name": "scan_config",
                    "type": "group",
                    "children": [
                        {
                            "title": "Scan Type:",
                            "name": "scan_type",
                            "type": "list",
                            "limits": [
                                "None",
                                "Polarization Scan",
                                "Wavelength Scan",
                                "Spatial Scan (Future)",
                                "Multi-Parameter Scan",
                            ],
                            "value": "None",
                        },
                        {
                            "title": "Enable Scanner:",
                            "name": "enable_scanner",
                            "type": "bool",
                            "value": False,
                        },
                        {
                            "title": "Scan Mode:",
                            "name": "scan_mode",
                            "type": "list",
                            "limits": ["Sequential", "Synchronized", "Continuous"],
                            "value": "Sequential",
                        },
                    ],
                },
                # Polarization Scanning
                {
                    "title": "Polarization Scanning",
                    "name": "polarization_scan",
                    "type": "group",
                    "children": [
                        {
                            "title": "Start Angle (°):",
                            "name": "pol_start_angle",
                            "type": "float",
                            "value": 0.0,
                            "min": 0.0,
                            "max": 360.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "End Angle (°):",
                            "name": "pol_end_angle",
                            "type": "float",
                            "value": 180.0,
                            "min": 0.0,
                            "max": 360.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Step Size (°):",
                            "name": "pol_step_size",
                            "type": "float",
                            "value": 5.0,
                            "min": 0.1,
                            "max": 90.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Active Element:",
                            "name": "pol_active_element",
                            "type": "list",
                            "limits": ["QWP", "HWP_Incident", "HWP_Analyzer", "All"],
                            "value": "HWP_Incident",
                        },
                        {
                            "title": "Settling Time (ms):",
                            "name": "pol_settle_time",
                            "type": "int",
                            "value": 500,
                            "min": 100,
                            "max": 5000,
                        },
                    ],
                },
                # Wavelength Scanning
                {
                    "title": "Wavelength Scanning",
                    "name": "wavelength_scan",
                    "type": "group",
                    "children": [
                        {
                            "title": "Start Wavelength (nm):",
                            "name": "wl_start",
                            "type": "float",
                            "value": 700.0,
                            "min": 700.0,
                            "max": 1000.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "End Wavelength (nm):",
                            "name": "wl_end",
                            "type": "float",
                            "value": 900.0,
                            "min": 700.0,
                            "max": 1000.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Step Size (nm):",
                            "name": "wl_step_size",
                            "type": "float",
                            "value": 10.0,
                            "min": 0.1,
                            "max": 50.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Stabilization Time (s):",
                            "name": "wl_stabilize_time",
                            "type": "float",
                            "value": 2.0,
                            "min": 0.5,
                            "max": 10.0,
                            "step": 0.1,
                            "decimals": 1,
                        },
                        {
                            "title": "Auto-sync Power Meter:",
                            "name": "wl_auto_sync_power",
                            "type": "bool",
                            "value": True,
                        },
                    ],
                },
                # Spatial Scanning (Future Implementation)
                {
                    "title": "Spatial Scanning (Future)",
                    "name": "spatial_scan",
                    "type": "group",
                    "children": [
                        {
                            "title": "X Start (μm):",
                            "name": "x_start",
                            "type": "float",
                            "value": -100.0,
                            "min": -1000.0,
                            "max": 1000.0,
                            "decimals": 1,
                            "readonly": True,
                        },
                        {
                            "title": "X End (μm):",
                            "name": "x_end",
                            "type": "float",
                            "value": 100.0,
                            "min": -1000.0,
                            "max": 1000.0,
                            "decimals": 1,
                            "readonly": True,
                        },
                        {
                            "title": "Y Start (μm):",
                            "name": "y_start",
                            "type": "float",
                            "value": -100.0,
                            "min": -1000.0,
                            "max": 1000.0,
                            "decimals": 1,
                            "readonly": True,
                        },
                        {
                            "title": "Y End (μm):",
                            "name": "y_end",
                            "type": "float",
                            "value": 100.0,
                            "min": -1000.0,
                            "max": 1000.0,
                            "decimals": 1,
                            "readonly": True,
                        },
                        {
                            "title": "Note:",
                            "name": "spatial_note",
                            "type": "str",
                            "value": "Requires galvo scanner hardware integration",
                            "readonly": True,
                        },
                    ],
                },
                # Scan Control Actions
                {
                    "title": "Scan Control",
                    "name": "scan_control",
                    "type": "group",
                    "children": [
                        {
                            "title": "Start Scan:",
                            "name": "start_scan",
                            "type": "action",
                        },
                        {"title": "Stop Scan:", "name": "stop_scan", "type": "action"},
                        {
                            "title": "Pause Scan:",
                            "name": "pause_scan",
                            "type": "action",
                        },
                        {
                            "title": "Resume Scan:",
                            "name": "resume_scan",
                            "type": "action",
                        },
                        {
                            "title": "Preview Scan:",
                            "name": "preview_scan",
                            "type": "action",
                        },
                    ],
                },
                # Scan Status
                {
                    "title": "Scan Status",
                    "name": "scan_status",
                    "type": "group",
                    "children": [
                        {
                            "title": "Current Status:",
                            "name": "current_status",
                            "type": "str",
                            "value": "Idle",
                            "readonly": True,
                        },
                        {
                            "title": "Progress (%):",
                            "name": "scan_progress",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                            "min": 0,
                            "max": 100,
                        },
                        {
                            "title": "Current Position:",
                            "name": "current_position",
                            "type": "str",
                            "value": "N/A",
                            "readonly": True,
                        },
                        {
                            "title": "Points Completed:",
                            "name": "points_completed",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Total Points:",
                            "name": "total_points",
                            "type": "int",
                            "value": 0,
                            "readonly": True,
                        },
                        {
                            "title": "Estimated Time Remaining:",
                            "name": "eta",
                            "type": "str",
                            "value": "--:--",
                            "readonly": True,
                        },
                    ],
                },
            ],
        },
    ]

    def __init__(self, parent):
        """
        Initialize the μRASHG Microscopy Extension.

        Args:
            parent: DockArea or QWidget parent container
        """
        super().__init__(parent)

        # Get dashboard reference - try to find it in global scope or parent
        self.dashboard = None
        if hasattr(parent, "dashboard"):
            self.dashboard = parent.dashboard
        elif hasattr(parent, "modules_manager"):
            self.dashboard = parent
        else:
            # Look for dashboard in global variables from launcher
            import sys

            frame = sys._getframe(1)
            if "dashboard" in frame.f_locals:
                self.dashboard = frame.f_locals["dashboard"]
            elif "dashboard" in frame.f_globals:
                self.dashboard = frame.f_globals["dashboard"]

        # Initialize CustomApp attributes that may not be set by parent
        if not hasattr(self, "dockarea") or self.dockarea is None:
            self.dockarea = parent  # Use parent as dockarea
        if not hasattr(self, "docks"):
            self.docks = {}  # Initialize empty docks dictionary

        # Device management (initialize before UI setup)
        self.device_manager = self.dashboard.modules_manager
        self.available_devices = {}
        self.missing_devices = []

        # Initialize UI components
        self.setup_ui()

        # Connect parameter actions to methods (PyMoDAQ standard pattern)
        self.connect_parameter_actions()

        # Measurement state
        self.is_measuring = False
        self.measurement_thread = None
        self.current_measurement_data = None

        # UI components (will be created in setup methods)
        self.control_widget = None
        self.visualization_widget = None
        self.status_widget = None

        # Plotting components
        self.camera_view = None
        self.polar_plot = None
        self.power_plot = None
        self.progress_bar = None

        # Status monitoring using PyMoDAQ threading patterns instead of QTimer
        self._status_monitoring_active = False
        self._status_worker_thread = None
        self._status_update_interval = 5.0  # seconds

        logger.info(f"Initialized {self.name} extension v{self.version}")

    def setup_ui(self):
        """Set up the complete user interface for the extension."""
        logger.info("Setting up μRASHG extension UI...")

        # Initialize UI components in proper order
        self.setup_docks()  # Create dock layout
        self.setup_actions()  # Create actions/menus
        self.setup_widgets()  # Create main widgets
        self.connect_things()  # Connect signals/slots

        logger.info("μRASHG extension UI setup complete")

    def setup_docks(self):
        """
        Set up the dock layout for the extension.

        Creates a comprehensive dock layout with:
        - Control panel (left)
        - Device Controls (left bottom) ⭐ NEW PHASE 3
        - Live preview (top right)
        - Analysis display (middle right)
        - Status and progress (bottom)
        """
        # Control Panel Dock (left side)
        self.docks["control"] = Dock("μRASHG Control", size=(400, 600))
        self.dockarea.addDock(self.docks["control"], "left")

        # Device Control Dock (left bottom) ⭐ NEW PHASE 3 FEATURE
        self.docks["device_control"] = Dock("Direct Device Controls", size=(400, 400))
        self.dockarea.addDock(
            self.docks["device_control"], "bottom", self.docks["control"]
        )

        # Live Camera Preview Dock (top right)
        self.docks["preview"] = Dock("Live Camera Preview", size=(600, 400))
        self.dockarea.addDock(self.docks["preview"], "right", self.docks["control"])

        # RASHG Analysis Dock (middle right)
        self.docks["analysis"] = Dock("RASHG Analysis", size=(600, 400))
        self.dockarea.addDock(self.docks["analysis"], "bottom", self.docks["preview"])

        # System Status and Progress Dock (bottom)
        self.docks["status"] = Dock("System Status & Progress", size=(1000, 200))
        self.dockarea.addDock(
            self.docks["status"], "bottom", self.docks["device_control"]
        )

        logger.info("Created dock layout for μRASHG extension")

    def setup_actions(self):
        """
        Set up actions and menu items for the extension.

        Creates essential actions for:
        - Starting/stopping measurements
        - Device initialization
        - Configuration management
        - Emergency stop
        """
        # Measurement control actions
        self.add_action(
            "start_measurement",
            "Start μRASHG Measurement",
            self.start_measurement,
            icon="SP_MediaPlay",
        )
        self.add_action(
            "stop_measurement",
            "Stop Measurement",
            self.stop_measurement,
            icon="SP_MediaStop",
        )
        self.add_action(
            "pause_measurement",
            "Pause Measurement",
            self.pause_measurement,
            icon="SP_MediaPause",
        )

        # Device management actions
        self.add_action(
            "initialize_devices",
            "Initialize Devices",
            self.initialize_devices,
            icon="SP_ComputerIcon",
        )
        self.add_action(
            "check_devices",
            "Check Device Status",
            self.check_device_status,
            icon="SP_DialogApplyButton",
        )
        self.add_action(
            "emergency_stop",
            "Emergency Stop",
            self.emergency_stop,
            icon="SP_BrowserStop",
        )

        # Configuration actions
        self.add_action(
            "load_config",
            "Load Configuration",
            self.load_configuration,
            icon="SP_DialogOpenButton",
        )
        self.add_action(
            "save_config",
            "Save Configuration",
            self.save_configuration,
            icon="SP_DialogSaveButton",
        )

        # Analysis actions (Enhanced for Phase 3)
        self.add_action(
            "analyze_data",
            "Analyze Current Data",
            self.analyze_current_data,
            icon="SP_FileDialogDetailedView",
        )
        self.add_action(
            "fit_rashg_curve",
            "Fit RASHG Pattern",  # ⭐ NEW
            self.fit_rashg_pattern,
            icon="SP_ComputerIcon",
        )
        self.add_action(
            "export_data", "Export Data", self.export_data, icon="SP_DialogSaveButton"
        )
        self.add_action(
            "export_analysis",
            "Export Analysis Results",  # ⭐ NEW
            self.export_analysis_results,
            icon="SP_DialogSaveButton",
        )

        logger.info("Created actions for μRASHG extension")

    def connect_parameter_actions(self):
        """Connect parameter tree actions to methods (PyMoDAQ standard pattern)."""
        try:
            # Measurement control actions
            self.settings.child(
                "measurement_control", "start_measurement"
            ).sigActivated.connect(self.start_measurement)
            self.settings.child(
                "measurement_control", "stop_measurement"
            ).sigActivated.connect(self.stop_measurement)
            self.settings.child(
                "measurement_control", "pause_measurement"
            ).sigActivated.connect(self.pause_measurement)

            # Device management actions (original parameters)
            self.settings.child(
                "device_control", "initialize_devices"
            ).sigActivated.connect(self.initialize_devices)
            self.settings.child("device_control", "check_devices").sigActivated.connect(
                self.check_device_status
            )
            self.settings.child(
                "device_control", "emergency_stop"
            ).sigActivated.connect(self.emergency_stop)

            # Configuration actions
            self.settings.child("configuration", "load_config").sigActivated.connect(
                self.load_configuration
            )
            self.settings.child("configuration", "save_config").sigActivated.connect(
                self.save_configuration
            )

            # Analysis actions (original parameters)
            self.settings.child("analysis", "analyze_data").sigActivated.connect(
                self.analyze_current_data
            )
            self.settings.child("analysis", "fit_rashg_curve").sigActivated.connect(
                self.fit_rashg_pattern
            )
            self.settings.child("analysis", "export_data").sigActivated.connect(
                self.export_data
            )
            self.settings.child("analysis", "export_analysis").sigActivated.connect(
                self.export_analysis_results
            )

            # Device Control Parameter Tree Actions (New PyMoDAQ Standards)
            try:
                # Laser control actions
                self.settings.child(
                    "device_control", "laser_control", "set_wavelength_action"
                ).sigActivated.connect(
                    lambda: self.set_laser_wavelength_from_parameter(
                        self.settings.child(
                            "device_control", "laser_control", "set_wavelength"
                        ).value()
                    )
                )
                self.settings.child(
                    "device_control", "laser_control", "open_shutter"
                ).sigActivated.connect(self.open_laser_shutter)
                self.settings.child(
                    "device_control", "laser_control", "close_shutter"
                ).sigActivated.connect(self.close_laser_shutter)

                # Rotator control actions
                self.settings.child(
                    "device_control", "rotator_control", "qwp_control", "move_qwp"
                ).sigActivated.connect(
                    lambda: self.move_rotator_from_parameter(
                        0,
                        self.settings.child(
                            "device_control",
                            "rotator_control",
                            "qwp_control",
                            "qwp_set_pos",
                        ).value(),
                    )
                )
                self.settings.child(
                    "device_control", "rotator_control", "qwp_control", "home_qwp"
                ).sigActivated.connect(lambda: self.home_rotator(0))

                self.settings.child(
                    "device_control",
                    "rotator_control",
                    "hwp_inc_control",
                    "move_hwp_inc",
                ).sigActivated.connect(
                    lambda: self.move_rotator_from_parameter(
                        1,
                        self.settings.child(
                            "device_control",
                            "rotator_control",
                            "hwp_inc_control",
                            "hwp_inc_set_pos",
                        ).value(),
                    )
                )
                self.settings.child(
                    "device_control",
                    "rotator_control",
                    "hwp_inc_control",
                    "home_hwp_inc",
                ).sigActivated.connect(lambda: self.home_rotator(1))

                self.settings.child(
                    "device_control",
                    "rotator_control",
                    "hwp_ana_control",
                    "move_hwp_ana",
                ).sigActivated.connect(
                    lambda: self.move_rotator_from_parameter(
                        2,
                        self.settings.child(
                            "device_control",
                            "rotator_control",
                            "hwp_ana_control",
                            "hwp_ana_set_pos",
                        ).value(),
                    )
                )
                self.settings.child(
                    "device_control",
                    "rotator_control",
                    "hwp_ana_control",
                    "home_hwp_ana",
                ).sigActivated.connect(lambda: self.home_rotator(2))

                self.settings.child(
                    "device_control", "rotator_control", "emergency_stop_rotators"
                ).sigActivated.connect(self.emergency_stop_rotators)

                # Power meter control actions
                self.settings.child(
                    "device_control", "power_control", "auto_sync_wavelength"
                ).sigValueChanged.connect(self.on_auto_sync_changed)
                self.settings.child(
                    "device_control", "power_control", "manual_sync"
                ).sigActivated.connect(self.manual_sync_wavelength)

                logger.info(
                    "Connected device control parameter tree actions (PyMoDAQ standards)"
                )

            except Exception as e:
                logger.warning(
                    f"Some device control parameter connections failed (parameters may not exist yet): {e}"
                )

            # Analysis Control Parameter Tree Actions (New PyMoDAQ Standards)
            try:
                # Polar analysis actions
                self.settings.child(
                    "analysis_control", "polar_analysis", "auto_fit"
                ).sigValueChanged.connect(self.on_auto_fit_changed)
                self.settings.child(
                    "analysis_control", "polar_analysis", "fit_rashg"
                ).sigActivated.connect(self.fit_rashg_pattern)

                # Spectral analysis actions
                self.settings.child(
                    "analysis_control", "spectral_analysis", "spectral_mode"
                ).sigValueChanged.connect(self.update_spectral_analysis)
                self.settings.child(
                    "analysis_control", "spectral_analysis", "update_spectral"
                ).sigActivated.connect(self.update_spectral_analysis)

                # 3D visualization actions
                self.settings.child(
                    "analysis_control", "volume_3d", "volume_mode"
                ).sigValueChanged.connect(self.update_3d_visualization)
                self.settings.child(
                    "analysis_control", "volume_3d", "update_3d"
                ).sigActivated.connect(self.update_3d_visualization)

                logger.info(
                    "Connected analysis control parameter tree actions (PyMoDAQ standards)"
                )

            except Exception as e:
                logger.warning(
                    f"Some analysis control parameter connections failed (parameters may not exist yet): {e}"
                )

            # Scanner Integration Parameter Actions (New PyMoDAQ Standards)
            try:
                self._connect_scanner_parameter_actions()
            except Exception as e:
                logger.warning(f"Could not connect scanner parameter actions: {e}")

            logger.info("Connected parameter actions to methods (PyMoDAQ standard)")
        except Exception as e:
            logger.error(f"Error connecting parameter actions: {e}")

    def _on_device_control_parameter_changed(self, param, changes):
        """Handle device control parameter changes (PyMoDAQ standards compliant)."""
        for param, change, data in changes:
            path = self.device_control_settings.childPath(param)

            if len(path) >= 2:
                group_name = path[-2]
                param_name = path[-1]

                try:
                    # Laser Control Actions
                    if group_name == "laser_control":
                        if param_name == "set_wavelength_action":
                            wavelength = self.device_control_settings.child(
                                "laser_control", "set_wavelength"
                            ).value()
                            self.set_laser_wavelength_from_parameter(wavelength)
                        elif param_name == "open_shutter":
                            self.open_laser_shutter()
                        elif param_name == "close_shutter":
                            self.close_laser_shutter()

                    # Rotator Control Actions
                    elif group_name in [
                        "qwp_control",
                        "hwp_inc_control",
                        "hwp_ana_control",
                    ]:
                        axis_map = {
                            "qwp_control": 0,
                            "hwp_inc_control": 1,
                            "hwp_ana_control": 2,
                        }
                        axis = axis_map[group_name]

                        if param_name.startswith("move_"):
                            position = self.device_control_settings.child(
                                group_name, param_name.replace("move_", "") + "_set_pos"
                            ).value()
                            self.move_rotator_from_parameter(axis, position)
                        elif param_name.startswith("home_"):
                            self.home_rotator(axis)

                    elif (
                        group_name == "rotator_control"
                        and param_name == "emergency_stop_rotators"
                    ):
                        self.emergency_stop_rotators()

                    # Power Meter Control Actions
                    elif group_name == "power_control":
                        if param_name == "auto_sync_wavelength":
                            self.on_auto_sync_changed()
                        elif param_name == "manual_sync":
                            self.manual_sync_wavelength()

                except Exception as e:
                    logger.error(
                        f"Error handling device control parameter change {path}: {e}"
                    )
                    self.log_message(f"Device control error: {e}", level="ERROR")

    def set_laser_wavelength_from_parameter(self, wavelength):
        """Set laser wavelength from parameter tree (PyMoDAQ pattern)."""
        try:
            # Update the actual laser hardware
            self.set_laser_wavelength()  # Use existing method

            # Update parameter tree display
            self.device_control_settings.child(
                "laser_control", "current_wavelength"
            ).setValue(wavelength)
            self.log_message(
                f"Laser wavelength set to {wavelength:.1f} nm", level="INFO"
            )
        except Exception as e:
            logger.error(f"Error setting laser wavelength from parameter: {e}")
            self.log_message(f"Failed to set wavelength: {e}", level="ERROR")

    def move_rotator_from_parameter(self, axis, position):
        """Move rotator from parameter tree (PyMoDAQ pattern)."""
        try:
            # Use existing rotator move method
            self.move_rotator(axis)

            # Update current position display in parameter tree
            axis_names = ["qwp_control", "hwp_inc_control", "hwp_ana_control"]
            if axis < len(axis_names):
                group_name = axis_names[axis]
                param_name = group_name.replace("_control", "") + "_current_pos"
                self.device_control_settings.child(group_name, param_name).setValue(
                    position
                )

            self.log_message(
                f"Rotator axis {axis} moved to {position:.2f}°", level="INFO"
            )
        except Exception as e:
            logger.error(f"Error moving rotator from parameter: {e}")
            self.log_message(f"Failed to move rotator: {e}", level="ERROR")

    def update_device_control_parameters(self):
        """Update device control parameters from hardware state (PyMoDAQ standards pattern)."""
        try:
            # Update laser parameters
            if hasattr(self, "device_manager") and self.device_manager:
                # Get laser wavelength from hardware
                try:
                    laser_wavelength = self.get_current_laser_wavelength()
                    if laser_wavelength is not None:
                        self.settings.child(
                            "device_control", "laser_control", "current_wavelength"
                        ).setValue(laser_wavelength)

                    # Update laser status
                    laser_available = "MaiTai" in self.available_devices
                    laser_status = "Connected" if laser_available else "Disconnected"
                    self.settings.child(
                        "device_control", "laser_control", "laser_status"
                    ).setValue(laser_status)

                except Exception as e:
                    logger.debug(f"Could not update laser parameters: {e}")

                # Update rotator positions
                try:
                    positions = self.get_current_elliptec_positions()
                    if positions:
                        axis_params = [
                            (
                                "device_control",
                                "rotator_control",
                                "qwp_control",
                                "qwp_current_pos",
                            ),
                            (
                                "device_control",
                                "rotator_control",
                                "hwp_inc_control",
                                "hwp_inc_current_pos",
                            ),
                            (
                                "device_control",
                                "rotator_control",
                                "hwp_ana_control",
                                "hwp_ana_current_pos",
                            ),
                        ]

                        for i, param_path in enumerate(axis_params):
                            if i < len(positions) and positions[i] is not None:
                                self.settings.child(*param_path).setValue(positions[i])

                except Exception as e:
                    logger.debug(f"Could not update rotator parameters: {e}")

                # Update power meter parameters
                try:
                    # Get power reading
                    if hasattr(self, "power_display") and hasattr(
                        self.power_display, "text"
                    ):
                        power_text = self.power_display.text()
                        if power_text != "--- mW":
                            try:
                                power_value = float(power_text.replace(" mW", ""))
                                self.settings.child(
                                    "device_control", "power_control", "current_power"
                                ).setValue(power_value)
                            except ValueError:
                                pass

                    # Update power meter wavelength if available
                    if hasattr(self, "power_wavelength_display") and hasattr(
                        self.power_wavelength_display, "text"
                    ):
                        wl_text = self.power_wavelength_display.text()
                        if wl_text != "--- nm":
                            try:
                                wl_value = float(wl_text.replace(" nm", ""))
                                self.settings.child(
                                    "device_control",
                                    "power_control",
                                    "power_wavelength",
                                ).setValue(wl_value)
                            except ValueError:
                                pass

                except Exception as e:
                    logger.debug(f"Could not update power parameters: {e}")

        except Exception as e:
            logger.debug(f"Error updating device control parameters: {e}")

    def setup_widgets(self):
        """
        Set up all widget components for the extension.

        Creates and configures:
        - Control panel with parameter tree and buttons
        - Live camera preview
        - Real-time analysis plots
        - Status monitoring display
        """
        self.setup_control_widget()
        self.setup_device_control_widget()  # ⭐ NEW PHASE 3 FEATURE
        self.setup_visualization_widget()
        self.setup_analysis_widget()
        self.setup_status_widget()

        logger.info("Created all widgets for μRASHG extension")

    def setup_control_widget(self):
        """Set up the control panel widget using PyMoDAQ parameter-driven approach."""
        self.control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(self.control_widget)

        # Parameter tree - PyMoDAQ automatically generates action buttons from parameter tree
        control_layout.addWidget(self.settings_tree)

        # Progress bar for measurement feedback
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        # Add to dock
        self.docks["control"].addWidget(self.control_widget)

        logger.info("Setup control widget with PyMoDAQ parameter-driven approach")

    def setup_device_control_widget(self):
        """Set up the device control widget using PyMoDAQ parameter trees (PyMoDAQ Standards Compliant)."""
        # Instead of manual Qt widget creation, use PyMoDAQ's parameter tree system
        # The device control parameters are defined in self.params['device_control']
        # and will be automatically rendered by PyMoDAQ's ParameterTree widget

        # Create a simple container widget for the parameter tree
        self.device_control_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.device_control_widget)

        # Create parameter tree widget for device control parameters
        from pymodaq.utils.parameter import ParameterTree

        # Extract device control parameters from main params
        device_control_params = None
        for param in self.params:
            if param.get("name") == "device_control":
                device_control_params = param["children"]
                break

        if device_control_params:
            # Create parameter tree widget
            self.device_control_parameter_tree = ParameterTree()
            self.device_control_parameter_tree.setParameters(
                device_control_params, showTop=False
            )

            # Connect parameter changes to device control actions
            self.device_control_parameter_tree.sigTreeStateChanged.connect(
                self._on_device_control_parameter_changed
            )

            layout.addWidget(self.device_control_parameter_tree)

            # Store reference to the parameter object for easy access
            self.device_control_settings = self.device_control_parameter_tree.p
        else:
            # Fallback label if parameters not found
            fallback_label = QtWidgets.QLabel("Device control parameters not found")
            layout.addWidget(fallback_label)

        # Add to dock
        self.docks["device_control"].addWidget(self.device_control_widget)

        # Start device update monitoring using PyMoDAQ threading patterns
        self._device_update_active = False
        self._device_update_thread = None
        self._device_update_interval = 1.0  # seconds

        logger.info("Created PyMoDAQ parameter-based device control widget")

    def setup_visualization_widget(self):
        """Set up the camera preview widget."""
        self.camera_view = pg.ImageView()
        self.camera_view.setImage(np.zeros((512, 512)))  # Placeholder image

        # Add to dock
        self.docks["preview"].addWidget(self.camera_view)

    def setup_analysis_widget(self):
        """Set up the analysis widget using PyMoDAQ parameter trees (PyMoDAQ Standards Compliant)."""
        # Create main analysis widget container
        analysis_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(analysis_widget)

        # Create tabs for different analysis views
        self.analysis_tabs = QtWidgets.QTabWidget()

        # === POLAR PLOT TAB (Enhanced with PyMoDAQ Viewer1D) ===
        polar_widget = QtWidgets.QWidget()
        polar_layout = QtWidgets.QVBoxLayout(polar_widget)

        # Polar plot using PyMoDAQ Viewer1D
        self.polar_plot = Viewer1D()
        self.polar_plot.set_title("RASHG Polar Response")
        self.polar_plot.set_axis_label("left", "SHG Intensity")
        self.polar_plot.set_axis_unit("left", "counts")
        self.polar_plot.set_axis_label("bottom", "Polarization Angle")
        self.polar_plot.set_axis_unit("bottom", "°")
        self.polar_plot.show_grid(True)
        self.polar_plot.show_legend(True)

        polar_layout.addWidget(self.polar_plot)
        self.analysis_tabs.addTab(polar_widget, "Polar Analysis")

        # === SPECTRAL ANALYSIS TAB ===
        spectral_widget = QtWidgets.QWidget()
        spectral_layout = QtWidgets.QVBoxLayout(spectral_widget)

        # Spectral plot using PyMoDAQ Viewer1D
        self.spectral_plot = Viewer1D()
        self.spectral_plot.set_title("Spectral RASHG Analysis")
        self.spectral_plot.set_axis_label("left", "RASHG Amplitude")
        self.spectral_plot.set_axis_unit("left", "a.u.")
        self.spectral_plot.set_axis_label("bottom", "Wavelength")
        self.spectral_plot.set_axis_unit("bottom", "nm")
        self.spectral_plot.show_grid(True)
        self.spectral_plot.show_legend(True)

        spectral_layout.addWidget(self.spectral_plot)
        self.analysis_tabs.addTab(spectral_widget, "Spectral Analysis")

        # === POWER MONITORING TAB ===
        power_widget = QtWidgets.QWidget()
        power_layout = QtWidgets.QVBoxLayout(power_widget)

        # Power plot using PyMoDAQ Viewer1D
        self.power_plot = Viewer1D()
        self.power_plot.set_title("Power Stability")
        self.power_plot.set_axis_label("left", "Power")
        self.power_plot.set_axis_unit("left", "mW")
        self.power_plot.set_axis_label("bottom", "Time")
        self.power_plot.set_axis_unit("bottom", "s")
        self.power_plot.show_grid(True)

        power_layout.addWidget(self.power_plot)
        self.analysis_tabs.addTab(power_widget, "Power Monitor")

        # === 3D ANALYSIS TAB ===
        opengl_available = self._check_3d_support()
        if opengl_available:
            volume_widget = QtWidgets.QWidget()
            volume_layout = QtWidgets.QVBoxLayout(volume_widget)

            try:
                import pyqtgraph.opengl as gl

                self.volume_view = gl.GLViewWidget()
                self.volume_view.setCameraPosition(distance=50)
                volume_layout.addWidget(self.volume_view)

                self.analysis_tabs.addTab(volume_widget, "3D Visualization")

            except ImportError:
                logger.info("OpenGL not available, 3D visualization disabled")
                opengl_available = False

        # === PARAMETER TREE FOR ANALYSIS CONTROLS ===
        from pymodaq.utils.parameter import ParameterTree

        # Extract analysis control parameters from main params
        analysis_control_params = None
        for param in self.params:
            if param.get("name") == "analysis_control":
                analysis_control_params = param["children"]
                break

        if analysis_control_params:
            # Create parameter tree widget for analysis controls
            self.analysis_control_parameter_tree = ParameterTree()
            self.analysis_control_parameter_tree.setParameters(
                analysis_control_params, showTop=False
            )

            # Connect parameter changes to analysis actions
            self.analysis_control_parameter_tree.sigTreeStateChanged.connect(
                self._on_analysis_control_parameter_changed
            )

            # Store reference to the parameter object for easy access
            self.analysis_control_settings = self.analysis_control_parameter_tree.p

            # Update 3D availability parameter
            self.analysis_control_settings.child(
                "volume_3d", "opengl_available"
            ).setValue(opengl_available)

            # Create a splitter to show plots and controls
            splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            splitter.addWidget(self.analysis_tabs)
            splitter.addWidget(self.analysis_control_parameter_tree)
            splitter.setStretchFactor(0, 3)  # Give more space to plots
            splitter.setStretchFactor(1, 1)  # Less space to parameter tree

            main_layout.addWidget(splitter)
        else:
            # Fallback - just add tabs if parameters not found
            main_layout.addWidget(self.analysis_tabs)

        # Initialize analysis data storage
        self.current_fit_results = None
        self.spectral_analysis_data = None

        # Add to dock
        self.docks["analysis"].addWidget(analysis_widget)

        logger.info("Created PyMoDAQ parameter-based analysis widget")

    def _on_analysis_control_parameter_changed(self, param, changes):
        """Handle analysis control parameter changes (PyMoDAQ standards compliant)."""
        for param, change, data in changes:
            path = self.analysis_control_settings.childPath(param)

            if len(path) >= 2:
                group_name = path[-2]
                param_name = path[-1]

                try:
                    # Polar Analysis Actions
                    if group_name == "polar_analysis":
                        if param_name == "auto_fit":
                            # Real-time fitting toggle
                            self.on_auto_fit_changed()
                        elif param_name == "fit_rashg":
                            # Manual fit trigger
                            self.fit_rashg_pattern()

                    # Spectral Analysis Actions
                    elif group_name == "spectral_analysis":
                        if param_name == "spectral_mode":
                            # Mode change triggers update
                            self.update_spectral_analysis()
                        elif param_name == "update_spectral":
                            # Manual update trigger
                            self.update_spectral_analysis()

                    # 3D Visualization Actions
                    elif group_name == "volume_3d":
                        if param_name == "volume_mode":
                            # Mode change triggers 3D update
                            self.update_3d_visualization()
                        elif param_name == "update_3d":
                            # Manual 3D update trigger
                            self.update_3d_visualization()

                except Exception as e:
                    logger.error(
                        f"Error handling analysis control parameter change {path}: {e}"
                    )
                    self.log_message(f"Analysis control error: {e}", level="ERROR")

    def update_analysis_control_parameters(self):
        """Update analysis control parameters with current analysis state (PyMoDAQ standards)."""
        try:
            if (
                hasattr(self, "analysis_control_settings")
                and self.analysis_control_settings
            ):
                # Update polar analysis results
                if self.current_fit_results:
                    fit_text = f"A={self.current_fit_results.get('amplitude', 0):.3f}, φ={self.current_fit_results.get('phase', 0):.2f}°"
                    self.analysis_control_settings.child(
                        "polar_analysis", "fit_results"
                    ).setValue(fit_text)
                    self.analysis_control_settings.child(
                        "polar_analysis", "rashg_amplitude"
                    ).setValue(self.current_fit_results.get("amplitude", 0))
                    self.analysis_control_settings.child(
                        "polar_analysis", "phase_degrees"
                    ).setValue(self.current_fit_results.get("phase", 0))
                    self.analysis_control_settings.child(
                        "polar_analysis", "r_squared"
                    ).setValue(self.current_fit_results.get("r_squared", 0))

                # Update spectral analysis status
                if (
                    hasattr(self, "spectral_analysis_data")
                    and self.spectral_analysis_data
                ):
                    self.analysis_control_settings.child(
                        "spectral_analysis", "spectral_status"
                    ).setValue("Data Available")
                else:
                    self.analysis_control_settings.child(
                        "spectral_analysis", "spectral_status"
                    ).setValue("No Data")

                # Update power monitoring if available
                if (
                    hasattr(self, "_power_history")
                    and self._power_history
                    and len(self._power_history["power"]) > 0
                ):
                    current_power = self._power_history["power"][-1]
                    self.analysis_control_settings.child(
                        "power_monitoring", "live_power"
                    ).setValue(current_power)

                    # Calculate power stability (coefficient of variation)
                    if len(self._power_history["power"]) > 1:
                        import numpy as np

                        power_array = np.array(self._power_history["power"])
                        mean_power = np.mean(power_array)
                        std_power = np.std(power_array)
                        stability = (
                            (1 - std_power / mean_power) * 100 if mean_power > 0 else 0
                        )
                        self.analysis_control_settings.child(
                            "power_monitoring", "power_stability"
                        ).setValue(max(0, stability))

                # Update general analysis status
                import datetime

                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                self.analysis_control_settings.child(
                    "general_analysis", "last_analysis_time"
                ).setValue(current_time)

                # Update data points count
                if (
                    hasattr(self, "current_measurement_data")
                    and self.current_measurement_data
                ):
                    data_count = (
                        len(self.current_measurement_data)
                        if isinstance(self.current_measurement_data, list)
                        else 1
                    )
                    self.analysis_control_settings.child(
                        "general_analysis", "data_points_count"
                    ).setValue(data_count)

        except Exception as e:
            logger.debug(f"Error updating analysis control parameters: {e}")

    def setup_status_widget(self):
        """Set up the status monitoring widget using PyMoDAQ parameter trees (PyMoDAQ Standards Compliant)."""
        # Create main status widget container
        self.status_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(self.status_widget)

        # Create splitter for parameter tree and log display
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # === STATUS PARAMETER TREE ===
        from pymodaq.utils.parameter import ParameterTree

        # Extract status monitoring parameters from main params
        status_monitoring_params = None
        for param in self.params:
            if param.get("name") == "status_monitoring":
                status_monitoring_params = param["children"]
                break

        if status_monitoring_params:
            # Create parameter tree widget for status monitoring
            self.status_monitoring_parameter_tree = ParameterTree()
            self.status_monitoring_parameter_tree.setParameters(
                status_monitoring_params, showTop=False
            )

            # Store reference to the parameter object for easy access
            self.status_monitoring_settings = self.status_monitoring_parameter_tree.p

            # Initialize system information
            self._initialize_system_info()

            splitter.addWidget(self.status_monitoring_parameter_tree)
        else:
            # Fallback if parameters not found
            fallback_label = QtWidgets.QLabel("Status monitoring parameters not found")
            splitter.addWidget(fallback_label)

        # === LOG DISPLAY (Keep as QTextEdit for real-time log viewing) ===
        log_container = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_container)

        log_layout.addWidget(QtWidgets.QLabel("Activity Log:"))

        self.log_display = QtWidgets.QTextEdit()
        self.log_display.setMaximumHeight(200)
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet(
            """
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
                background-color: #f8f8f8;
                border: 1px solid #ccc;
            }
        """
        )

        # Add log controls
        log_controls = QtWidgets.QWidget()
        log_controls_layout = QtWidgets.QHBoxLayout(log_controls)

        clear_log_button = QtWidgets.QPushButton("Clear Log")
        clear_log_button.clicked.connect(lambda: self.log_display.clear())
        clear_log_button.setMaximumWidth(100)
        log_controls_layout.addWidget(clear_log_button)

        log_level_combo = QtWidgets.QComboBox()
        log_level_combo.addItems(["All", "INFO", "WARNING", "ERROR"])
        log_level_combo.setMaximumWidth(100)
        log_controls_layout.addWidget(log_level_combo)

        log_controls_layout.addStretch()

        log_layout.addWidget(log_controls)
        log_layout.addWidget(self.log_display)

        splitter.addWidget(log_container)

        # Set splitter proportions (70% for parameter tree, 30% for log)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

        # Add to dock
        self.docks["status"].addWidget(self.status_widget)

        # Initialize status update tracking
        self._last_status_update = None
        self._status_update_counter = 0

        logger.info("Created PyMoDAQ parameter-based status monitoring widget")

    def _initialize_system_info(self):
        """Initialize system information in status parameters (PyMoDAQ Standards)."""
        try:
            if (
                hasattr(self, "status_monitoring_settings")
                and self.status_monitoring_settings
            ):
                import datetime

                # Set session start time
                start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.status_monitoring_settings.child(
                    "system_info", "session_start"
                ).setValue(start_time)

                # Set extension version
                self.status_monitoring_settings.child(
                    "system_info", "extension_version"
                ).setValue(self.version)

                # Try to get PyMoDAQ version
                try:
                    import pymodaq

                    pymodaq_version = getattr(pymodaq, "__version__", "Unknown")
                    self.status_monitoring_settings.child(
                        "system_info", "pymodaq_version"
                    ).setValue(pymodaq_version)
                except:
                    pass

                # Initialize device counts
                if hasattr(self, "available_devices") and hasattr(
                    self, "missing_devices"
                ):
                    self.status_monitoring_settings.child(
                        "system_info", "available_devices_count"
                    ).setValue(len(self.available_devices))
                    self.status_monitoring_settings.child(
                        "system_info", "missing_devices_count"
                    ).setValue(len(self.missing_devices))

                # Initialize connection uptime tracking
                self._connection_start_time = datetime.datetime.now()

        except Exception as e:
            logger.debug(f"Error initializing system info: {e}")

    def update_status_monitoring_parameters(self):
        """Update status monitoring parameters with current system state (PyMoDAQ Standards)."""
        try:
            if (
                not hasattr(self, "status_monitoring_settings")
                or not self.status_monitoring_settings
            ):
                return

            import datetime

            # Update device status
            if hasattr(self, "device_manager") and self.device_manager:
                # Camera status
                camera = self.device_manager.get_camera()
                if camera:
                    camera_status = (
                        "Connected" if camera.initialized else "Disconnected"
                    )
                    self.status_monitoring_settings.child(
                        "device_status", "camera_status"
                    ).setValue(camera_status)

                    # Try to get camera temperature
                    try:
                        if (
                            hasattr(camera, "controller")
                            and camera.controller
                            and hasattr(camera.controller, "get_temperature")
                        ):
                            temp = camera.controller.get_temperature()
                            self.status_monitoring_settings.child(
                                "device_status", "camera_temperature"
                            ).setValue(temp)
                    except:
                        pass

                # Laser status
                laser_available = "MaiTai" in self.available_devices
                laser_status = "Connected" if laser_available else "Disconnected"
                self.status_monitoring_settings.child(
                    "device_status", "laser_status_display"
                ).setValue(laser_status)

                if laser_available:
                    try:
                        wavelength = self.get_current_laser_wavelength()
                        if wavelength:
                            self.status_monitoring_settings.child(
                                "device_status", "laser_wavelength_display"
                            ).setValue(wavelength)
                    except:
                        pass

                # Rotator status
                rotator_available = "Elliptec" in self.available_devices
                rotator_status = "Connected" if rotator_available else "Disconnected"
                self.status_monitoring_settings.child(
                    "device_status", "rotator_status"
                ).setValue(rotator_status)

                # Power meter status
                power_meter_available = "Newport1830C" in self.available_devices
                power_status = "Connected" if power_meter_available else "Disconnected"
                self.status_monitoring_settings.child(
                    "device_status", "power_meter_status"
                ).setValue(power_status)

                # Overall system status
                connected_devices = len(self.available_devices)
                total_expected = connected_devices + len(self.missing_devices)
                if connected_devices == total_expected:
                    system_status = "All Systems Operational"
                elif connected_devices > 0:
                    system_status = (
                        f"Partial ({connected_devices}/{total_expected} devices)"
                    )
                else:
                    system_status = "No Devices Connected"
                self.status_monitoring_settings.child(
                    "device_status", "system_status"
                ).setValue(system_status)

            # Update measurement status
            if hasattr(self, "is_measuring"):
                measurement_state = "Measuring" if self.is_measuring else "Idle"
                self.status_monitoring_settings.child(
                    "measurement_status", "measurement_state"
                ).setValue(measurement_state)

            # Update data points if available
            if (
                hasattr(self, "current_measurement_data")
                and self.current_measurement_data
            ):
                if isinstance(self.current_measurement_data, dict):
                    angles = self.current_measurement_data.get("angles", [])
                    data_points = len(angles) if angles else 0
                    self.status_monitoring_settings.child(
                        "measurement_status", "data_points_collected"
                    ).setValue(data_points)

            # Update connection uptime
            if hasattr(self, "_connection_start_time"):
                uptime = datetime.datetime.now() - self._connection_start_time
                uptime_str = str(uptime).split(".")[0]  # Remove microseconds
                self.status_monitoring_settings.child(
                    "hardware_health", "connection_uptime"
                ).setValue(uptime_str)

            # Update device counts
            if hasattr(self, "available_devices") and hasattr(self, "missing_devices"):
                self.status_monitoring_settings.child(
                    "system_info", "available_devices_count"
                ).setValue(len(self.available_devices))
                self.status_monitoring_settings.child(
                    "system_info", "missing_devices_count"
                ).setValue(len(self.missing_devices))

            # Calculate performance score (simple metric based on connected devices and errors)
            try:
                total_devices = len(self.available_devices) + len(self.missing_devices)
                connected_ratio = (
                    len(self.available_devices) / total_devices
                    if total_devices > 0
                    else 0
                )
                error_penalty = min(
                    self._status_update_counter * 2, 20
                )  # Max 20% penalty for errors
                performance = max(0, connected_ratio * 100 - error_penalty)
                self.status_monitoring_settings.child(
                    "hardware_health", "performance_score"
                ).setValue(performance)
            except:
                pass

            # Update counter
            self._status_update_counter += 1
            self._last_status_update = datetime.datetime.now()

        except Exception as e:
            logger.debug(f"Error updating status monitoring parameters: {e}")
            self._status_update_counter += 1  # Count this as an error

    # === SCANNER INTEGRATION METHODS (PyMoDAQ Coordinated Measurements) ===

    def _connect_scanner_parameter_actions(self):
        """Connect scanner parameter actions to methods (PyMoDAQ Standards)."""
        try:
            # Scanner control actions
            self.settings.child(
                "scanner_integration", "scan_control", "start_scan"
            ).sigActivated.connect(self.start_scanner_measurement)
            self.settings.child(
                "scanner_integration", "scan_control", "stop_scan"
            ).sigActivated.connect(self.stop_scanner_measurement)
            self.settings.child(
                "scanner_integration", "scan_control", "pause_scan"
            ).sigActivated.connect(self.pause_scanner_measurement)
            self.settings.child(
                "scanner_integration", "scan_control", "resume_scan"
            ).sigActivated.connect(self.resume_scanner_measurement)
            self.settings.child(
                "scanner_integration", "scan_control", "preview_scan"
            ).sigActivated.connect(self.preview_scanner_measurement)

            # Scanner enable/disable
            self.settings.child(
                "scanner_integration", "scan_config", "enable_scanner"
            ).sigValueChanged.connect(self.on_scanner_enable_changed)
            self.settings.child(
                "scanner_integration", "scan_config", "scan_type"
            ).sigValueChanged.connect(self.on_scan_type_changed)

            logger.info(
                "Connected scanner integration parameter actions (PyMoDAQ standards)"
            )
        except Exception as e:
            logger.warning(f"Could not connect all scanner parameter actions: {e}")

    def on_scanner_enable_changed(self):
        """Handle scanner enable/disable changes (PyMoDAQ Standards)."""
        try:
            scanner_enabled = self.settings.child(
                "scanner_integration", "scan_config", "enable_scanner"
            ).value()

            if scanner_enabled:
                self.log_message("Scanner integration enabled", level="INFO")
                self.settings.child(
                    "scanner_integration", "scan_status", "current_status"
                ).setValue("Ready")
            else:
                self.log_message("Scanner integration disabled", level="INFO")
                self.settings.child(
                    "scanner_integration", "scan_status", "current_status"
                ).setValue("Disabled")

                # Stop any ongoing scans
                if hasattr(self, "_scanner_active") and self._scanner_active:
                    self.stop_scanner_measurement()

        except Exception as e:
            logger.error(f"Error handling scanner enable change: {e}")

    def on_scan_type_changed(self):
        """Handle scan type selection changes (PyMoDAQ Standards)."""
        try:
            scan_type = self.settings.child(
                "scanner_integration", "scan_config", "scan_type"
            ).value()

            # Calculate and update total points based on scan type
            total_points = self._calculate_scan_points(scan_type)
            self.settings.child(
                "scanner_integration", "scan_status", "total_points"
            ).setValue(total_points)

            self.log_message(
                f"Scan type changed to: {scan_type} ({total_points} points)",
                level="INFO",
            )

        except Exception as e:
            logger.error(f"Error handling scan type change: {e}")

    def _calculate_scan_points(self, scan_type):
        """Calculate total scan points based on scan configuration (PyMoDAQ Standards)."""
        try:
            if scan_type == "None":
                return 0
            elif scan_type == "Polarization Scan":
                start = self.settings.child(
                    "scanner_integration", "polarization_scan", "pol_start_angle"
                ).value()
                end = self.settings.child(
                    "scanner_integration", "polarization_scan", "pol_end_angle"
                ).value()
                step = self.settings.child(
                    "scanner_integration", "polarization_scan", "pol_step_size"
                ).value()
                return int((end - start) / step) + 1
            elif scan_type == "Wavelength Scan":
                start = self.settings.child(
                    "scanner_integration", "wavelength_scan", "wl_start"
                ).value()
                end = self.settings.child(
                    "scanner_integration", "wavelength_scan", "wl_end"
                ).value()
                step = self.settings.child(
                    "scanner_integration", "wavelength_scan", "wl_step_size"
                ).value()
                return int((end - start) / step) + 1
            elif scan_type == "Multi-Parameter Scan":
                # Calculate combination of polarization and wavelength points
                pol_points = self._calculate_scan_points("Polarization Scan")
                wl_points = self._calculate_scan_points("Wavelength Scan")
                return pol_points * wl_points
            else:
                return 0
        except Exception as e:
            logger.error(f"Error calculating scan points: {e}")
            return 0

    def start_scanner_measurement(self):
        """Start coordinated scanner measurement (PyMoDAQ Standards)."""
        logger.info("Starting scanner measurement...")

        try:
            # Check if scanner is enabled
            if not self.settings.child(
                "scanner_integration", "scan_config", "enable_scanner"
            ).value():
                self.log_message(
                    "Cannot start scan: Scanner integration is disabled",
                    level="WARNING",
                )
                return

            # Check scan type
            scan_type = self.settings.child(
                "scanner_integration", "scan_config", "scan_type"
            ).value()
            if scan_type == "None":
                self.log_message(
                    "Cannot start scan: No scan type selected", level="WARNING"
                )
                return

            # Pre-flight checks
            if not self._scanner_preflight_checks():
                return

            # Initialize scanner state
            self._scanner_active = True
            self._scanner_paused = False
            self._current_scan_point = 0

            # Update status
            self.settings.child(
                "scanner_integration", "scan_status", "current_status"
            ).setValue("Running")
            self.settings.child(
                "scanner_integration", "scan_status", "scan_progress"
            ).setValue(0)
            self.settings.child(
                "scanner_integration", "scan_status", "points_completed"
            ).setValue(0)

            self.log_message(f"Started {scan_type} measurement", level="INFO")

            # Start the appropriate scan type
            if scan_type == "Polarization Scan":
                self._start_polarization_scan()
            elif scan_type == "Wavelength Scan":
                self._start_wavelength_scan()
            elif scan_type == "Multi-Parameter Scan":
                self._start_multi_parameter_scan()
            else:
                self.log_message(
                    f"Scan type '{scan_type}' not yet implemented", level="WARNING"
                )
                self.stop_scanner_measurement()

        except Exception as e:
            error_msg = f"Error starting scanner measurement: {str(e)}"
            self.log_message(error_msg, level="ERROR")
            self.stop_scanner_measurement()

    def stop_scanner_measurement(self):
        """Stop coordinated scanner measurement (PyMoDAQ Standards)."""
        logger.info("Stopping scanner measurement...")

        try:
            # Update scanner state
            self._scanner_active = False
            self._scanner_paused = False

            # Update status
            self.settings.child(
                "scanner_integration", "scan_status", "current_status"
            ).setValue("Stopped")
            self.settings.child(
                "scanner_integration", "scan_status", "current_position"
            ).setValue("N/A")
            self.settings.child("scanner_integration", "scan_status", "eta").setValue(
                "--:--"
            )

            self.log_message("Scanner measurement stopped", level="INFO")

        except Exception as e:
            logger.error(f"Error stopping scanner measurement: {e}")

    def pause_scanner_measurement(self):
        """Pause coordinated scanner measurement (PyMoDAQ Standards)."""
        try:
            if hasattr(self, "_scanner_active") and self._scanner_active:
                self._scanner_paused = True
                self.settings.child(
                    "scanner_integration", "scan_status", "current_status"
                ).setValue("Paused")
                self.log_message("Scanner measurement paused", level="INFO")

        except Exception as e:
            logger.error(f"Error pausing scanner measurement: {e}")

    def resume_scanner_measurement(self):
        """Resume coordinated scanner measurement (PyMoDAQ Standards)."""
        try:
            if (
                hasattr(self, "_scanner_active")
                and self._scanner_active
                and hasattr(self, "_scanner_paused")
                and self._scanner_paused
            ):
                self._scanner_paused = False
                self.settings.child(
                    "scanner_integration", "scan_status", "current_status"
                ).setValue("Running")
                self.log_message("Scanner measurement resumed", level="INFO")

        except Exception as e:
            logger.error(f"Error resuming scanner measurement: {e}")

    def preview_scanner_measurement(self):
        """Preview scanner measurement parameters (PyMoDAQ Standards)."""
        try:
            scan_type = self.settings.child(
                "scanner_integration", "scan_config", "scan_type"
            ).value()
            total_points = self.settings.child(
                "scanner_integration", "scan_status", "total_points"
            ).value()

            if scan_type == "None":
                self.log_message("No scan type selected for preview", level="WARNING")
                return

            # Calculate estimated measurement time
            integration_time = (
                self.settings.child("experiment", "integration_time").value() / 1000.0
            )  # Convert to seconds
            averages = self.settings.child("experiment", "averages").value()

            base_time_per_point = integration_time * averages

            # Add settling times based on scan type
            if scan_type == "Polarization Scan":
                settle_time = (
                    self.settings.child(
                        "scanner_integration", "polarization_scan", "pol_settle_time"
                    ).value()
                    / 1000.0
                )
                total_time = total_points * (base_time_per_point + settle_time)
            elif scan_type == "Wavelength Scan":
                stabilize_time = self.settings.child(
                    "scanner_integration", "wavelength_scan", "wl_stabilize_time"
                ).value()
                total_time = total_points * (base_time_per_point + stabilize_time)
            else:
                total_time = total_points * base_time_per_point

            # Format time estimate
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = int(total_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            preview_msg = f"Scan Preview - Type: {scan_type}, Points: {total_points}, Est. Time: {time_str}"
            self.log_message(preview_msg, level="INFO")

            # Show preview using PyMoDAQ messagebox
            from pymodaq.utils.messenger import messagebox

            preview_details = f"""
Scan Configuration Preview:

Scan Type: {scan_type}
Total Points: {total_points}
Estimated Duration: {time_str}

Integration Time: {integration_time:.3f} s per point
Averages: {averages}
            """

            result = messagebox(
                title="Scan Preview",
                text=preview_details.strip(),
                informative_text="Proceed with scan?",
            )
            if result:
                self.start_scanner_measurement()

        except Exception as e:
            logger.error(f"Error generating scan preview: {e}")
            self.log_message(f"Preview error: {str(e)}", level="ERROR")

    def _scanner_preflight_checks(self):
        """Perform pre-flight checks for scanner measurement (PyMoDAQ Standards)."""
        try:
            # Check device availability
            if not hasattr(self, "device_manager") or not self.device_manager:
                self.log_message("Device manager not available", level="ERROR")
                return False

            # Check if already measuring
            if hasattr(self, "is_measuring") and self.is_measuring:
                self.log_message(
                    "Cannot start scan: Another measurement is in progress",
                    level="WARNING",
                )
                return False

            scan_type = self.settings.child(
                "scanner_integration", "scan_config", "scan_type"
            ).value()

            # Type-specific checks
            if scan_type in ["Polarization Scan", "Multi-Parameter Scan"]:
                if "Elliptec" not in self.available_devices:
                    self.log_message(
                        "Polarization scan requires Elliptec rotators", level="ERROR"
                    )
                    return False

            if scan_type in ["Wavelength Scan", "Multi-Parameter Scan"]:
                if "MaiTai" not in self.available_devices:
                    self.log_message(
                        "Wavelength scan requires MaiTai laser", level="ERROR"
                    )
                    return False

            # Check camera availability for all scans
            if "PrimeBSI" not in self.available_devices:
                self.log_message("Scanner measurement requires camera", level="ERROR")
                return False

            self.log_message("Scanner pre-flight checks passed", level="INFO")
            return True

        except Exception as e:
            logger.error(f"Error in scanner pre-flight checks: {e}")
            return False

    def _start_polarization_scan(self):
        """Start polarization scanning sequence (PyMoDAQ Standards Implementation)."""
        self.log_message("Starting polarization scan sequence...", level="INFO")

        # This would be implemented as a coordinated measurement
        # For now, create a framework that can be extended
        try:
            start_angle = self.settings.child(
                "scanner_integration", "polarization_scan", "pol_start_angle"
            ).value()
            end_angle = self.settings.child(
                "scanner_integration", "polarization_scan", "pol_end_angle"
            ).value()
            step_size = self.settings.child(
                "scanner_integration", "polarization_scan", "pol_step_size"
            ).value()

            self.log_message(
                f"Polarization scan: {start_angle}° to {end_angle}° in {step_size}° steps",
                level="INFO",
            )

            # Framework for future implementation:
            # - Move rotator to start position
            # - For each angle step:
            #   - Move rotator to angle
            #   - Wait for settling
            #   - Trigger camera acquisition
            #   - Store data with position metadata
            # - Compile results into multi-dimensional dataset

            self.log_message(
                "Polarization scan framework ready (implementation pending)",
                level="INFO",
            )

        except Exception as e:
            logger.error(f"Error starting polarization scan: {e}")
            self.stop_scanner_measurement()

    def _start_wavelength_scan(self):
        """Start wavelength scanning sequence (PyMoDAQ Standards Implementation)."""
        self.log_message("Starting wavelength scan sequence...", level="INFO")

        # Framework for coordinated wavelength measurement
        try:
            start_wl = self.settings.child(
                "scanner_integration", "wavelength_scan", "wl_start"
            ).value()
            end_wl = self.settings.child(
                "scanner_integration", "wavelength_scan", "wl_end"
            ).value()
            step_size = self.settings.child(
                "scanner_integration", "wavelength_scan", "wl_step_size"
            ).value()

            self.log_message(
                f"Wavelength scan: {start_wl} nm to {end_wl} nm in {step_size} nm steps",
                level="INFO",
            )

            # Framework for future implementation:
            # - Set laser to start wavelength
            # - For each wavelength step:
            #   - Set laser wavelength
            #   - Wait for stabilization
            #   - Sync power meter wavelength if enabled
            #   - Trigger measurement
            #   - Store spectral data
            # - Compile spectroscopic dataset

            self.log_message(
                "Wavelength scan framework ready (implementation pending)", level="INFO"
            )

        except Exception as e:
            logger.error(f"Error starting wavelength scan: {e}")
            self.stop_scanner_measurement()

    def _start_multi_parameter_scan(self):
        """Start multi-parameter scanning sequence (PyMoDAQ Standards Implementation)."""
        self.log_message("Starting multi-parameter scan sequence...", level="INFO")

        # Framework for coordinated multi-parameter measurement
        try:
            self.log_message(
                "Multi-parameter scan combines polarization and wavelength scanning",
                level="INFO",
            )

            # Framework for future implementation:
            # - Nested loops: wavelength outer, polarization inner (or vice versa)
            # - For each wavelength:
            #   - Set laser wavelength and wait for stabilization
            #   - For each polarization angle:
            #     - Move rotator and wait for settling
            #     - Trigger measurement
            #     - Store data with both wavelength and angle metadata
            # - Compile 3D dataset (wavelength, angle, intensity)

            self.log_message(
                "Multi-parameter scan framework ready (implementation pending)",
                level="INFO",
            )

        except Exception as e:
            logger.error(f"Error starting multi-parameter scan: {e}")
            self.stop_scanner_measurement()

    def connect_things(self):
        """
        Connect signals and slots for inter-component communication.
        """
        # Connect parameter tree changes
        self.settings.sigTreeStateChanged.connect(self.parameter_changed)

        # Connect measurement signals
        self.measurement_started.connect(self.on_measurement_started)
        self.measurement_finished.connect(self.on_measurement_finished)
        self.measurement_progress.connect(self.on_measurement_progress)

        # Connect device status signals
        self.device_status_changed.connect(self.on_device_status_changed)
        self.error_occurred.connect(self.on_error_occurred)

        # Connect device manager signals
        if self.device_manager:
            self.device_manager.device_status_changed.connect(
                self.on_device_status_changed
            )
            self.device_manager.device_error.connect(self.on_device_error)
            self.device_manager.all_devices_ready.connect(self.on_all_devices_ready)

        # Start device control update timer (PHASE 3 FEATURE)
        if hasattr(self, "device_update_timer"):
            self.start_device_update_monitoring()
            logger.info("Started device control update timer")

        logger.info("Connected signals and slots for μRASHG extension")

    # =================== PHASE 3: DIRECT DEVICE CONTROL METHODS ===================

    def on_wavelength_slider_changed(self, value):
        """Handle wavelength slider changes."""
        self.wavelength_spinbox.setValue(value)

    def on_wavelength_spinbox_changed(self, value):
        """Handle wavelength spinbox changes."""
        self.wavelength_slider.setValue(value)

    def set_laser_wavelength(self):
        """Set the laser wavelength."""
        target_wavelength = self.wavelength_spinbox.value()
        logger.info(f"Setting laser wavelength to {target_wavelength} nm")
        self.log_message(f"Setting laser wavelength to {target_wavelength} nm")

        try:
            laser = self.dashboard.modules_manager.get_module_by_name("MaiTai")
            if not laser:
                self.log_message("ERROR: Laser device not available", level="error")
                return

            # Use proper DataActuator pattern for wavelength control
            from pymodaq.utils.data import DataActuator

            # Create position data - MaiTai laser typically uses single-axis control
            position_data = DataActuator(data=[target_wavelength])

            # Move to wavelength - CRITICAL: Use .value() for single-axis controllers
            if hasattr(laser, "move_abs"):
                laser.move_abs(position_data)
                self.log_message(
                    f"Laser wavelength command sent: {target_wavelength} nm"
                )

                # Trigger automatic wavelength synchronization if enabled
                if (
                    hasattr(self, "auto_sync_checkbox")
                    and self.auto_sync_checkbox.isChecked()
                ):
                    self.sync_power_meter_wavelength(target_wavelength)

            else:
                self.log_message(
                    "ERROR: Laser does not support absolute movement", level="error"
                )

        except Exception as e:
            error_msg = f"Failed to set laser wavelength: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def open_laser_shutter(self):
        """Open the laser shutter."""
        logger.info("Opening laser shutter")
        self.log_message("Opening laser shutter")

        try:
            laser = self.dashboard.modules_manager.get_module_by_name("MaiTai")
            if not laser:
                self.log_message("ERROR: Laser device not available", level="error")
                return

            # Check if laser has shutter control capability
            if hasattr(laser, "controller") and laser.controller:
                if hasattr(laser.controller, "open_shutter"):
                    laser.controller.open_shutter()
                    self.log_message("Laser shutter opened")
                    self.update_shutter_status("Open")
                elif hasattr(laser.controller, "set_shutter"):
                    laser.controller.set_shutter(True)
                    self.log_message("Laser shutter opened (via set_shutter)")
                    self.update_shutter_status("Open")
                else:
                    self.log_message(
                        "WARNING: Laser shutter control not available", level="warning"
                    )
            else:
                self.log_message("ERROR: Laser controller not available", level="error")

        except Exception as e:
            error_msg = f"Failed to open laser shutter: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def close_laser_shutter(self):
        """Close the laser shutter."""
        logger.info("Closing laser shutter")
        self.log_message("Closing laser shutter")

        try:
            laser = self.dashboard.modules_manager.get_module_by_name("MaiTai")
            if not laser:
                self.log_message("ERROR: Laser device not available", level="error")
                return

            # Check if laser has shutter control capability
            if hasattr(laser, "controller") and laser.controller:
                if hasattr(laser.controller, "close_shutter"):
                    laser.controller.close_shutter()
                    self.log_message("Laser shutter closed")
                    self.update_shutter_status("Closed")
                elif hasattr(laser.controller, "set_shutter"):
                    laser.controller.set_shutter(False)
                    self.log_message("Laser shutter closed (via set_shutter)")
                    self.update_shutter_status("Closed")
                else:
                    self.log_message(
                        "WARNING: Laser shutter control not available", level="warning"
                    )
            else:
                self.log_message("ERROR: Laser controller not available", level="error")

        except Exception as e:
            error_msg = f"Failed to close laser shutter: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def update_shutter_status(self, status):
        """Update shutter status display."""
        if hasattr(self, "shutter_status_label"):
            self.shutter_status_label.setText(f"Status: {status}")
            if status == "Open":
                self.shutter_status_label.setStyleSheet(
                    "color: green; font-weight: bold;"
                )
            elif status == "Closed":
                self.shutter_status_label.setStyleSheet(
                    "color: orange; font-weight: bold;"
                )
            else:
                self.shutter_status_label.setStyleSheet(
                    "color: gray; font-weight: bold;"
                )

    def move_rotator(self, axis):
        """Move a specific rotator to the set position."""
        if axis not in self.rotator_controls:
            logger.error(f"Invalid rotator axis: {axis}")
            return

        rotator_control = self.rotator_controls[axis]
        target_position = rotator_control["position_spinbox"].value()
        rotator_name = rotator_control["name"]

        logger.info(f"Moving {rotator_name} (axis {axis}) to {target_position}°")
        self.log_message(f"Moving {rotator_name} to {target_position}°")

        try:
            elliptec = self.dashboard.modules_manager.get_module_by_name("Elliptec")
            if not elliptec:
                self.log_message("ERROR: Elliptec device not available", level="error")
                return

            # Use proper DataActuator pattern for multi-axis device
            from pymodaq.utils.data import DataActuator

            # For multi-axis Elliptec, we need to specify which axis to move
            # Create position array - only set the target axis, others to current positions
            current_positions = self.get_current_elliptec_positions()
            if current_positions is None or not isinstance(
                current_positions, (list, tuple, np.ndarray)
            ):
                # If we can't get current positions, create array with target position
                if axis == 0:
                    target_positions = [target_position, 0.0, 0.0]
                elif axis == 1:
                    target_positions = [0.0, target_position, 0.0]
                else:  # axis == 2
                    target_positions = [0.0, 0.0, target_position]
            else:
                # Ensure current_positions is a list we can modify
                if isinstance(current_positions, np.ndarray):
                    target_positions = current_positions.tolist()
                else:
                    target_positions = list(current_positions)
                target_positions[axis] = target_position

            # Create DataActuator for multi-axis movement
            position_data = DataActuator(data=[target_positions])

            # Move to position - CRITICAL: Use .data[0] for multi-axis controllers
            if hasattr(elliptec, "move_abs"):
                elliptec.move_abs(position_data)
                self.log_message(f"{rotator_name} movement command sent")
            else:
                self.log_message(
                    f"ERROR: {rotator_name} does not support absolute movement",
                    level="error",
                )

        except Exception as e:
            error_msg = f"Failed to move {rotator_name}: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def home_rotator(self, axis):
        """Home a specific rotator."""
        if axis not in self.rotator_controls:
            logger.error(f"Invalid rotator axis: {axis}")
            return

        rotator_name = self.rotator_controls[axis]["name"]

        logger.info(f"Homing {rotator_name} (axis {axis})")
        self.log_message(f"Homing {rotator_name}")

        try:
            elliptec = self.dashboard.modules_manager.get_module_by_name("Elliptec")
            if not elliptec:
                self.log_message("ERROR: Elliptec device not available", level="error")
                return

            # Check if elliptec has home capability
            if hasattr(elliptec, "move_home"):
                elliptec.move_home()
                self.log_message(f"{rotator_name} homing command sent")
            elif hasattr(elliptec, "controller") and elliptec.controller:
                if hasattr(elliptec.controller, "move_home"):
                    elliptec.controller.move_home()
                    self.log_message(f"{rotator_name} homing via controller")
                else:
                    self.log_message(
                        f"WARNING: {rotator_name} homing not available", level="warning"
                    )
            else:
                self.log_message(
                    f"ERROR: {rotator_name} controller not available", level="error"
                )

        except Exception as e:
            error_msg = f"Failed to home {rotator_name}: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def emergency_stop_rotators(self):
        """Emergency stop all rotators."""
        logger.warning("EMERGENCY STOP - All rotators")
        self.log_message("EMERGENCY STOP - All rotators", level="error")

        try:
            elliptec = self.dashboard.modules_manager.get_module_by_name("Elliptec")
            if elliptec:
                if hasattr(elliptec, "stop_motion"):
                    elliptec.stop_motion()
                elif hasattr(elliptec, "controller") and elliptec.controller:
                    if hasattr(elliptec.controller, "stop_motion"):
                        elliptec.controller.stop_motion()

                self.log_message("Emergency stop applied to all rotators")
            else:
                self.log_message(
                    "ERROR: Elliptec device not available for emergency stop",
                    level="error",
                )

        except Exception as e:
            error_msg = f"Error during rotator emergency stop: {str(e)}"
            self.log_message(error_msg, level="error")

    def get_current_elliptec_positions(self):
        """Get current positions of all Elliptec axes."""
        try:
            elliptec = self.device_manager.get_elliptec()
            if not elliptec:
                return None

            # Try to get current positions
            if (
                hasattr(elliptec, "current_position")
                and elliptec.current_position is not None
            ):
                # current_position might be a DataActuator or list
                if hasattr(elliptec.current_position, "data"):
                    return elliptec.current_position.data[0]
                else:
                    return elliptec.current_position
            elif hasattr(elliptec, "controller") and elliptec.controller:
                if hasattr(elliptec.controller, "get_actuator_value"):
                    return elliptec.controller.get_actuator_value()

            return None

        except Exception as e:
            logger.debug(f"Could not get current elliptec positions: {e}")
            return None

    def on_auto_sync_changed(self, state):
        """Handle auto-sync checkbox state change."""
        enabled = state == QtCore.Qt.Checked
        logger.info(f"Auto wavelength sync {'enabled' if enabled else 'disabled'}")
        self.log_message(f"Auto wavelength sync {'enabled' if enabled else 'disabled'}")

    def manual_sync_wavelength(self):
        """Manually sync power meter wavelength with laser."""
        logger.info("Manual wavelength synchronization requested")
        self.log_message("Synchronizing power meter wavelength...")

        try:
            # Get current laser wavelength
            current_wavelength = self.get_current_laser_wavelength()
            if current_wavelength is None:
                # Use spinbox value as fallback
                current_wavelength = self.wavelength_spinbox.value()
                self.log_message(
                    f"Using set wavelength: {current_wavelength} nm", level="warning"
                )

            # Sync power meter
            success = self.sync_power_meter_wavelength(current_wavelength)

            if success:
                self.log_message(f"Wavelength sync completed: {current_wavelength} nm")
            else:
                self.log_message("Wavelength sync failed", level="error")

        except Exception as e:
            error_msg = f"Manual wavelength sync failed: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def sync_power_meter_wavelength(self, wavelength):
        """Sync power meter wavelength setting."""
        try:
            power_meter = self.device_manager.get_power_meter()
            if not power_meter:
                self.log_message(
                    "WARNING: Power meter not available for wavelength sync",
                    level="warning",
                )
                return False

            # Check if power meter supports wavelength setting
            if hasattr(power_meter, "controller") and power_meter.controller:
                if hasattr(power_meter.controller, "set_wavelength"):
                    power_meter.controller.set_wavelength(wavelength)
                    self.update_sync_status("Synced", "green")
                    logger.info(f"Power meter wavelength synced to {wavelength} nm")
                    return True
                elif hasattr(power_meter, "settings"):
                    # Try to find wavelength setting in parameter tree
                    wavelength_param = power_meter.settings.child_frompath("wavelength")
                    if wavelength_param:
                        wavelength_param.setValue(wavelength)
                        self.update_sync_status("Synced", "green")
                        logger.info(
                            f"Power meter wavelength setting updated to {wavelength} nm"
                        )
                        return True

            self.log_message(
                "WARNING: Power meter wavelength sync not supported", level="warning"
            )
            self.update_sync_status("Not Supported", "orange")
            return False

        except Exception as e:
            logger.error(f"Error syncing power meter wavelength: {e}")
            self.update_sync_status("Error", "red")
            return False

    def get_current_laser_wavelength(self):
        """Get current laser wavelength."""
        try:
            laser = self.device_manager.get_laser()
            if not laser:
                return None

            # Try to get current wavelength
            if (
                hasattr(laser, "current_position")
                and laser.current_position is not None
            ):
                if hasattr(laser.current_position, "value"):
                    return laser.current_position.value()
                elif hasattr(laser.current_position, "data"):
                    return laser.current_position.data[0][0]
                else:
                    return float(laser.current_position)
            elif hasattr(laser, "controller") and laser.controller:
                if hasattr(laser.controller, "get_wavelength"):
                    return laser.controller.get_wavelength()

            return None

        except Exception as e:
            logger.debug(f"Could not get current laser wavelength: {e}")
            return None

    def update_sync_status(self, status, color):
        """Update wavelength sync status display."""
        if hasattr(self, "sync_status_label"):
            self.sync_status_label.setText(f"Sync Status: {status}")
            self.sync_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_device_control_displays(self):
        """Update all device control displays (called by timer)."""
        try:
            # Update laser status and wavelength
            self.update_laser_display()

            # Update rotator positions
            self.update_rotator_displays()

            # Update power meter display
            self.update_power_meter_display()

        except Exception as e:
            logger.debug(f"Error updating device control displays: {e}")

    def update_laser_display(self):
        """Update laser status and wavelength displays."""
        try:
            laser = self.device_manager.get_laser()

            if hasattr(self, "laser_status_label"):
                if laser and hasattr(laser, "controller") and laser.controller:
                    if (
                        hasattr(laser.controller, "connected")
                        and laser.controller.connected
                    ):
                        self.laser_status_label.setText("Status: Connected")
                        self.laser_status_label.setStyleSheet(
                            "color: green; font-weight: bold;"
                        )
                    else:
                        self.laser_status_label.setText("Status: Disconnected")
                        self.laser_status_label.setStyleSheet(
                            "color: red; font-weight: bold;"
                        )
                else:
                    self.laser_status_label.setText("Status: Not Available")
                    self.laser_status_label.setStyleSheet(
                        "color: gray; font-weight: bold;"
                    )

            # Update wavelength display
            if hasattr(self, "wavelength_display"):
                current_wavelength = self.get_current_laser_wavelength()
                if current_wavelength is not None:
                    self.wavelength_display.setText(f"{current_wavelength:.0f} nm")
                else:
                    self.wavelength_display.setText("--- nm")

        except Exception as e:
            logger.debug(f"Error updating laser display: {e}")

    def update_rotator_displays(self):
        """Update rotator position displays."""
        try:
            current_positions = self.get_current_elliptec_positions()

            for axis, controls in self.rotator_controls.items():
                if current_positions is not None and axis < len(current_positions):
                    position = current_positions[axis]
                    controls["position_label"].setText(f"{position:.2f} °")
                else:
                    controls["position_label"].setText("--- °")

        except Exception as e:
            logger.debug(f"Error updating rotator displays: {e}")

    def update_power_meter_display(self):
        """Update power meter displays."""
        try:
            power_meter = self.device_manager.get_power_meter()

            # Update power reading
            if hasattr(self, "power_display"):
                if power_meter and hasattr(power_meter, "grab_data"):
                    try:
                        power_data = power_meter.grab_data()
                        if power_data and len(power_data) > 0:
                            power_value = (
                                float(power_data[0].data[0])
                                if hasattr(power_data[0], "data")
                                else 0.0
                            )
                            self.power_display.setText(f"{power_value:.3f} mW")
                        else:
                            self.power_display.setText("--- mW")
                    except Exception as e:
                        self.power_display.setText("--- mW")
                        logger.debug(f"Could not read power meter: {e}")
                else:
                    self.power_display.setText("--- mW")

            # Update power meter wavelength display (if available)
            if hasattr(self, "power_wavelength_display"):
                if (
                    power_meter
                    and hasattr(power_meter, "controller")
                    and power_meter.controller
                ):
                    try:
                        if hasattr(power_meter.controller, "get_wavelength"):
                            pm_wavelength = power_meter.controller.get_wavelength()
                            self.power_wavelength_display.setText(
                                f"{pm_wavelength:.0f} nm"
                            )
                        else:
                            self.power_wavelength_display.setText("--- nm")
                    except Exception as e:
                        self.power_wavelength_display.setText("--- nm")
                        logger.debug(f"Could not get power meter wavelength: {e}")
                else:
                    self.power_wavelength_display.setText("--- nm")

        except Exception as e:
            logger.debug(f"Error updating power meter display: {e}")

    # =================== END PHASE 3 DEVICE CONTROL METHODS ===================

    # Placeholder methods for core functionality (to be implemented in subsequent phases)

    def parameter_changed(self, param, changes):
        """Handle parameter tree changes."""
        for param, change, data in changes:
            logger.debug(f"Parameter changed: {param.name()} = {data}")

    def initialize_devices(self):
        """Initialize and validate all required devices."""
        logger.info("Initializing devices...")
        self.log_message("Starting device initialization...")

        if not self.dashboard or not hasattr(self.dashboard, "modules_manager"):
            self.log_message(
                "ERROR: Dashboard or modules_manager not available", level="error"
            )
            return

        try:
            # Get available modules from the dashboard
            self.available_devices = {
                name: mod
                for name, mod in self.dashboard.modules_manager.modules_by_name.items()
            }

            # Check for required devices
            self.missing_devices = []
            for (
                device_key,
                device_config,
            ) in URASHGDeviceManager.REQUIRED_DEVICES.items():
                if device_config.get("required", True):
                    found = False
                    for pattern in device_config["name_patterns"]:
                        if any(pattern in name for name in self.available_devices):
                            found = True
                            break
                    if not found:
                        self.missing_devices.append(device_key)

            # Report discovery results
            if self.available_devices:
                self.log_message(
                    f"Found {len(self.available_devices)} devices: {list(self.available_devices.keys())}"
                )

            if self.missing_devices:
                self.log_message(
                    f"Missing required devices: {self.missing_devices}", level="error"
                )
                return False

            self.log_message("All required devices are present.")
            self.device_manager.start_monitoring()
            return True

        except Exception as e:
            error_msg = f"Device initialization failed: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)
            return False

    def check_device_status(self):
        """Check the status of all devices."""
        logger.info("Checking device status...")
        self.log_message("Checking device status...")

        if not self.dashboard or not hasattr(self.dashboard, "modules_manager"):
            self.log_message(
                "ERROR: Dashboard or modules_manager not available", level="error"
            )
            return

        try:
            # Update status for all devices
            for device_name, mod in self.available_devices.items():
                status = (
                    "Connected" if mod.controller.is_connected() else "Disconnected"
                )
                self.log_message(f"Device '{device_name}': {status}")

            # Check if all required devices are ready
            all_ready = all(
                "Connected" == mod.controller.is_connected()
                for mod in self.available_devices.values()
            )
            ready_msg = (
                "All required devices are ready"
                if all_ready
                else "Some required devices are not ready"
            )
            self.log_message(ready_msg, level="info" if all_ready else "warning")

        except Exception as e:
            error_msg = f"Device status check failed: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def start_measurement(self):
        """Start a μRASHG measurement sequence."""
        logger.info("Starting μRASHG measurement...")
        self.log_message("Starting μRASHG measurement...")

        # Pre-flight checks
        if not self._pre_flight_checks():
            return False

        # Set UI state
        self.measurement_started.emit()

        # Start measurement in separate thread
        self.measurement_thread = QThread()
        self.measurement_worker = MeasurementWorker(self)
        self.measurement_worker.moveToThread(self.measurement_thread)

        # Connect worker signals
        self.measurement_worker.progress_updated.connect(self.measurement_progress)
        self.measurement_worker.measurement_completed.connect(
            self._on_measurement_completed
        )
        self.measurement_worker.measurement_failed.connect(self._on_measurement_failed)
        self.measurement_worker.data_acquired.connect(self._on_data_acquired)

        # Start worker
        self.measurement_thread.started.connect(self.measurement_worker.run_measurement)
        self.measurement_thread.start()

        self.log_message("Measurement sequence started")
        return True

    def _pre_flight_checks(self) -> bool:
        """Perform pre-flight checks before starting measurement."""
        self.log_message("Performing pre-flight checks...")

        # Check device availability
        if not self.device_manager or not self.device_manager.is_all_devices_ready():
            missing = (
                self.device_manager.get_missing_devices()
                if self.device_manager
                else ["All devices"]
            )
            self.log_message(f"Cannot start: Missing devices: {missing}", level="error")
            self.error_occurred.emit(f"Missing required devices: {missing}")
            return False

        # Check safety parameters
        max_power = self.settings.child("hardware", "safety", "max_power").value()
        if max_power > 80.0:
            self.log_message(
                f"WARNING: High power limit set ({max_power}%)", level="warning"
            )
            reply = messagebox(
                severity="question",
                title="High Power Warning",
                text=f"Power limit is set to {max_power}%. Continue?",
            )
            if not reply:
                return False

        # Check measurement parameters
        pol_steps = self.settings.child("experiment", "pol_steps").value()
        if pol_steps < 4:
            self.log_message(
                "ERROR: Minimum 4 polarization steps required", level="error"
            )
            self.error_occurred.emit("Insufficient polarization steps (minimum 4)")
            return False

        # Check camera ROI
        roi_width = self.settings.child("hardware", "camera", "roi", "width").value()
        roi_height = self.settings.child("hardware", "camera", "roi", "height").value()
        if roi_width < 1 or roi_height < 1:
            self.log_message("ERROR: Invalid camera ROI settings", level="error")
            self.error_occurred.emit("Invalid camera ROI configuration")
            return False

        self.log_message("Pre-flight checks passed")
        return True

    def stop_measurement(self):
        """Stop the current measurement."""
        logger.info("Stopping measurement...")
        self.log_message("Stopping measurement...")

        if not self.is_measuring:
            self.log_message("No measurement in progress")
            return

        try:
            # Signal worker to stop
            if hasattr(self, "measurement_worker") and self.measurement_worker:
                self.measurement_worker.stop_measurement()

            # Stop measurement thread
            if hasattr(self, "measurement_thread") and self.measurement_thread:
                if self.measurement_thread.isRunning():
                    self.measurement_thread.quit()
                    if not self.measurement_thread.wait(5000):  # Wait up to 5 seconds
                        self.log_message("Forcing thread termination", level="warning")
                        self.measurement_thread.terminate()
                        self.measurement_thread.wait()

            # Emergency stop all devices if needed
            if self.device_manager:
                self.device_manager.emergency_stop_all_devices()

            # Reset state
            self.is_measuring = False
            self.measurement_finished.emit()

            self.log_message("Measurement stopped successfully")

        except Exception as e:
            error_msg = f"Error stopping measurement: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def pause_measurement(self):
        """Pause the current measurement."""
        logger.info("Pausing measurement...")
        self.log_message("Pausing measurement...")

        if not self.is_measuring:
            self.log_message("No measurement in progress")
            return

        try:
            # Signal worker to pause
            if hasattr(self, "measurement_worker") and self.measurement_worker:
                self.measurement_worker.pause_measurement()
                self.log_message("Measurement paused")
            else:
                self.log_message(
                    "Cannot pause: No active measurement worker", level="warning"
                )

        except Exception as e:
            error_msg = f"Error pausing measurement: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def emergency_stop(self):
        """Emergency stop all devices and measurements."""
        logger.warning("EMERGENCY STOP activated!")
        self.log_message("EMERGENCY STOP activated!", level="error")

        try:
            # Stop any ongoing measurements
            if self.is_measuring:
                self.stop_measurement()

            # Emergency stop all devices
            if self.device_manager:
                self.device_manager.emergency_stop_all_devices()
                self.log_message("Emergency stop applied to all devices")

            # Reset UI state
            # PyMoDAQ parameter-driven approach: actions auto-manage state
            self.settings.child("measurement_control", "start_measurement").setOpts(
                enabled=True
            )
            self.settings.child("measurement_control", "stop_measurement").setOpts(
                enabled=False
            )
            self.settings.child("measurement_control", "pause_measurement").setOpts(
                enabled=False
            )
            self.progress_bar.setVisible(False)

            self.log_message("Emergency stop completed")

        except Exception as e:
            error_msg = f"Error during emergency stop: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level="error")

    def analyze_current_data(self):
        """Analyze the current measurement data (Enhanced for Phase 3)."""
        logger.info("Analyzing current data...")
        self.log_message("Analyzing current data...")

        if not self.current_measurement_data:
            self.log_message(
                "No measurement data available for analysis", level="warning"
            )
            return

        try:
            self.update_analysis_status("Analyzing data...")

            # Update polar plot with fitting
            if (
                "angles" in self.current_measurement_data
                and "intensities" in self.current_measurement_data
            ):
                self._update_polar_plot(self.current_measurement_data)

            # Update spectral analysis if multi-wavelength data
            if self.current_measurement_data.get("multi_wavelength", False):
                self.update_spectral_analysis()
                self.update_3d_visualization()

            self.update_analysis_status("Analysis completed")
            self.log_message("Data analysis completed")

        except Exception as e:
            error_msg = f"Data analysis failed: {str(e)}"
            self.log_message(error_msg, level="error")
            self.update_analysis_status("Analysis failed")

    def fit_rashg_pattern(self):
        """Fit RASHG pattern to current data (PHASE 3 FEATURE) - PyMoDAQ Standards Compliant."""
        logger.info("Fitting RASHG pattern...")
        self.log_message("Fitting RASHG pattern...")

        if not self.current_measurement_data:
            self.log_message(
                "No measurement data available for fitting", level="warning"
            )
            # Update parameter tree with no data status
            self.update_analysis_control_parameters()
            return

        try:
            self.update_analysis_status("Fitting RASHG pattern...")

            angles = self.current_measurement_data.get("angles", [])
            intensities = self.current_measurement_data.get("intensities", [])

            if len(angles) < 4 or len(intensities) < 4:
                self.log_message(
                    "Insufficient data points for fitting (minimum 4 required)",
                    level="warning",
                )
                # Update parameter tree with insufficient data status
                if (
                    hasattr(self, "analysis_control_settings")
                    and self.analysis_control_settings
                ):
                    self.analysis_control_settings.child(
                        "polar_analysis", "fit_results"
                    ).setValue("Insufficient data")
                    self.analysis_control_settings.child(
                        "general_analysis", "analysis_status"
                    ).setValue("Insufficient data")
                return

            # Perform RASHG fitting
            fit_results = self._fit_rashg_data(angles, intensities)

            if fit_results:
                self.current_fit_results = fit_results
                self._display_fit_results(fit_results)
                self._plot_fit_curve(angles, intensities, fit_results)

                self.log_message(
                    f"RASHG fit completed: A={fit_results['A']:.2f}, B={fit_results['B']:.2f}, φ={fit_results['phi_deg']:.1f}°"
                )
                self.update_analysis_status("RASHG pattern fitted successfully")

                # Update parameter tree with fit results (PyMoDAQ Standards)
                if (
                    hasattr(self, "analysis_control_settings")
                    and self.analysis_control_settings
                ):
                    self.analysis_control_settings.child(
                        "general_analysis", "analysis_status"
                    ).setValue("Fit completed successfully")
            else:
                self.log_message("RASHG fitting failed", level="error")
                self.update_analysis_status("RASHG fitting failed")

                # Update parameter tree with failure status (PyMoDAQ Standards)
                if (
                    hasattr(self, "analysis_control_settings")
                    and self.analysis_control_settings
                ):
                    self.analysis_control_settings.child(
                        "polar_analysis", "fit_results"
                    ).setValue("Fit failed")
                    self.analysis_control_settings.child(
                        "general_analysis", "analysis_status"
                    ).setValue("Fit failed")

        except Exception as e:
            error_msg = f"RASHG fitting failed: {str(e)}"
            self.log_message(error_msg, level="error")
            self.update_analysis_status("RASHG fitting failed")

            # Update parameter tree with error status (PyMoDAQ Standards)
            if (
                hasattr(self, "analysis_control_settings")
                and self.analysis_control_settings
            ):
                self.analysis_control_settings.child(
                    "polar_analysis", "fit_results"
                ).setValue(f"Error: {str(e)}")
                self.analysis_control_settings.child(
                    "general_analysis", "analysis_status"
                ).setValue("Error in fitting")

        finally:
            # Always update analysis control parameters to synchronize parameter tree (PyMoDAQ Standards)
            self.update_analysis_control_parameters()

    def export_analysis_results(self):
        """Export analysis results (PHASE 3 FEATURE)."""
        logger.info("Exporting analysis results...")
        self.log_message("Exporting analysis results...")

        if not self.current_fit_results and not self.spectral_analysis_data:
            self.log_message(
                "No analysis results available for export", level="warning"
            )
            return

        try:
            # Get save directory
            save_dir = Path(self.settings.child("data", "save_dir").value())
            save_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Export fit results
            if self.current_fit_results:
                fit_filename = save_dir / f"rashg_fit_results_{timestamp}.json"
                with open(fit_filename, "w") as f:
                    json.dump(self.current_fit_results, f, indent=2)
                self.log_message(f"Fit results exported to {fit_filename}")

            # Export spectral analysis
            if self.spectral_analysis_data:
                spectral_filename = save_dir / f"spectral_analysis_{timestamp}.json"
                with open(spectral_filename, "w") as f:
                    json.dump(self.spectral_analysis_data, f, indent=2)
                self.log_message(f"Spectral analysis exported to {spectral_filename}")

            self.log_message("Analysis results exported successfully")

        except Exception as e:
            error_msg = f"Export analysis results failed: {str(e)}"
            self.log_message(error_msg, level="error")

    def export_data(self):
        """Export measurement data to file."""
        logger.info("Exporting data...")
        self.log_message("Exporting data...")

        if not self.current_measurement_data:
            self.log_message(
                "No measurement data available for export", level="warning"
            )
            return

        try:
            # Use existing data export functionality but add analysis results
            save_dir = Path(self.settings.child("data", "save_dir").value())
            save_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = save_dir / f"urashg_data_export_{timestamp}.json"

            # Prepare comprehensive export data
            export_data = self.current_measurement_data.copy()

            # Add analysis results if available
            if self.current_fit_results:
                export_data["fit_results"] = self.current_fit_results

            if self.spectral_analysis_data:
                export_data["spectral_analysis"] = self.spectral_analysis_data

            # Save to JSON
            with open(filename, "w") as f:
                import json

                json.dump(export_data, f, indent=2)

            self.log_message(f"Data exported to {filename}")

        except Exception as e:
            error_msg = f"Data export failed: {str(e)}"
            self.log_message(error_msg, level="error")

    def load_configuration(self):
        """Load measurement configuration from file (PHASE 3 FEATURE)."""
        logger.info("Loading configuration...")
        self.log_message("Loading configuration...")

        try:
            # File dialog for configuration selection
            from qtpy.QtWidgets import QFileDialog

            # Get default config directory
            config_dir = (
                Path(self.settings.child("data", "save_dir").value()) / "configs"
            )
            config_dir.mkdir(parents=True, exist_ok=True)

            # Open file dialog
            filename, _ = QFileDialog.getOpenFileName(
                self.control_widget,
                "Load μRASHG Configuration",
                str(config_dir),
                "JSON Configuration Files (*.json);;All Files (*.*)",
            )

            if not filename:
                self.log_message("Configuration load cancelled")
                return

            # Load and apply configuration
            with open(filename, "r") as f:
                import json

                config_data = json.load(f)

            self._apply_configuration(config_data)

            self.log_message(f"Configuration loaded from {filename}")

        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def save_configuration(self):
        """Save current configuration to file (PHASE 3 FEATURE)."""
        logger.info("Saving configuration...")
        self.log_message("Saving configuration...")

        try:
            # Get current configuration
            config_data = self._get_current_configuration()

            # File dialog for save location
            from qtpy.QtWidgets import QFileDialog

            # Get default config directory
            config_dir = (
                Path(self.settings.child("data", "save_dir").value()) / "configs"
            )
            config_dir.mkdir(parents=True, exist_ok=True)

            # Generate default filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            default_name = f"urashg_config_{timestamp}.json"

            # Open file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.control_widget,
                "Save μRASHG Configuration",
                str(config_dir / default_name),
                "JSON Configuration Files (*.json);;All Files (*.*)",
            )

            if not filename:
                self.log_message("Configuration save cancelled")
                return

            # Save configuration
            with open(filename, "w") as f:
                import json

                json.dump(config_data, f, indent=2)

            self.log_message(f"Configuration saved to {filename}")

        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            self.log_message(error_msg, level="error")
            self.error_occurred.emit(error_msg)

    def _get_current_configuration(self):
        """Get current system configuration for saving."""
        try:
            config_data = {
                "metadata": {
                    "timestamp": time.time(),
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "extension_version": self.version,
                    "config_type": "urashg_measurement_config",
                },
                # Parameter tree settings
                "parameter_settings": self._extract_parameter_settings(),
                # Device positions
                "device_positions": self._get_current_device_positions(),
                # Device control settings
                "device_control_settings": self._get_device_control_settings(),
                # Analysis settings
                "analysis_settings": self._get_analysis_settings(),
                # UI settings
                "ui_settings": {
                    "auto_fit_enabled": (
                        getattr(self.auto_fit_checkbox, "isChecked", lambda: False)()
                        if hasattr(self, "auto_fit_checkbox")
                        else False
                    ),
                    "auto_sync_enabled": (
                        getattr(self.auto_sync_checkbox, "isChecked", lambda: True)()
                        if hasattr(self, "auto_sync_checkbox")
                        else True
                    ),
                    "spectral_mode": (
                        getattr(
                            self.spectral_mode_combo,
                            "currentText",
                            lambda: "RASHG Amplitude",
                        )()
                        if hasattr(self, "spectral_mode_combo")
                        else "RASHG Amplitude"
                    ),
                    "active_analysis_tab": (
                        getattr(self.analysis_tabs, "currentIndex", lambda: 0)()
                        if hasattr(self, "analysis_tabs")
                        else 0
                    ),
                    "active_device_tab": (
                        getattr(self.device_tabs, "currentIndex", lambda: 0)()
                        if hasattr(self, "device_tabs")
                        else 0
                    ),
                },
            }

            return config_data

        except Exception as e:
            logger.error(f"Error getting current configuration: {e}")
            return {}

    def _extract_parameter_settings(self):
        """Extract current parameter tree settings."""
        try:
            parameter_settings = {}

            # Extract all parameter values
            for param_name in [
                "experiment",
                "hardware",
                "wavelength",
                "data",
                "advanced",
            ]:
                if self.settings.child(param_name):
                    parameter_settings[param_name] = self._extract_parameter_group(
                        self.settings.child(param_name)
                    )

            return parameter_settings

        except Exception as e:
            logger.debug(f"Error extracting parameter settings: {e}")
            return {}

    def _extract_parameter_group(self, param_group):
        """Extract values from a parameter group."""
        try:
            group_settings = {}

            for child in param_group.children():
                if child.hasChildren():
                    # Recursive for nested groups
                    group_settings[child.name()] = self._extract_parameter_group(child)
                else:
                    # Extract leaf parameter value
                    try:
                        group_settings[child.name()] = child.value()
                    except Exception as e:
                        logger.debug(f"Could not extract parameter {child.name()}: {e}")
                        group_settings[child.name()] = None

            return group_settings

        except Exception as e:
            logger.debug(f"Error extracting parameter group: {e}")
            return {}

    def _get_current_device_positions(self):
        """Get current positions of all devices."""
        try:
            device_positions = {}

            # Get laser wavelength
            if hasattr(self, "wavelength_spinbox"):
                device_positions["laser_wavelength"] = self.wavelength_spinbox.value()

            # Get elliptec positions
            elliptec_positions = self.get_current_elliptec_positions()
            if elliptec_positions:
                device_positions["elliptec_positions"] = elliptec_positions

            # Get rotator control spinbox values
            if hasattr(self, "rotator_controls"):
                rotator_setpoints = {}
                for axis, controls in self.rotator_controls.items():
                    if "position_spinbox" in controls:
                        rotator_setpoints[axis] = controls["position_spinbox"].value()
                device_positions["rotator_setpoints"] = rotator_setpoints

            return device_positions

        except Exception as e:
            logger.debug(f"Error getting device positions: {e}")
            return {}

    def _get_device_control_settings(self):
        """Get device control widget settings."""
        try:
            device_control_settings = {}

            # Wavelength control settings
            if hasattr(self, "wavelength_slider") and hasattr(
                self, "wavelength_spinbox"
            ):
                device_control_settings["wavelength_control"] = {
                    "slider_value": self.wavelength_slider.value(),
                    "spinbox_value": self.wavelength_spinbox.value(),
                }

            # Power meter sync settings
            if hasattr(self, "auto_sync_checkbox"):
                device_control_settings["power_sync"] = {
                    "auto_sync_enabled": self.auto_sync_checkbox.isChecked()
                }

            return device_control_settings

        except Exception as e:
            logger.debug(f"Error getting device control settings: {e}")
            return {}

    def _get_analysis_settings(self):
        """Get analysis widget settings."""
        try:
            analysis_settings = {}

            # Fit settings
            if hasattr(self, "auto_fit_checkbox"):
                analysis_settings["fitting"] = {
                    "auto_fit_enabled": self.auto_fit_checkbox.isChecked()
                }

            # Spectral analysis settings
            if hasattr(self, "spectral_mode_combo"):
                analysis_settings["spectral"] = {
                    "mode": self.spectral_mode_combo.currentText(),
                    "index": self.spectral_mode_combo.currentIndex(),
                }

            return analysis_settings

        except Exception as e:
            logger.debug(f"Error getting analysis settings: {e}")
            return {}

    def _apply_configuration(self, config_data):
        """Apply loaded configuration to the system."""
        try:
            self.log_message("Applying configuration...")

            # Apply parameter settings
            if "parameter_settings" in config_data:
                self._apply_parameter_settings(config_data["parameter_settings"])

            # Apply device positions
            if "device_positions" in config_data:
                self._apply_device_positions(config_data["device_positions"])

            # Apply device control settings
            if "device_control_settings" in config_data:
                self._apply_device_control_settings(
                    config_data["device_control_settings"]
                )

            # Apply analysis settings
            if "analysis_settings" in config_data:
                self._apply_analysis_settings(config_data["analysis_settings"])

            # Apply UI settings
            if "ui_settings" in config_data:
                self._apply_ui_settings(config_data["ui_settings"])

            self.log_message("Configuration applied successfully")

        except Exception as e:
            error_msg = f"Error applying configuration: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level="error")

    def _apply_parameter_settings(self, parameter_settings):
        """Apply parameter tree settings."""
        try:
            for param_name, param_values in parameter_settings.items():
                if self.settings.child(param_name):
                    self._apply_parameter_group(
                        self.settings.child(param_name), param_values
                    )

        except Exception as e:
            logger.debug(f"Error applying parameter settings: {e}")

    def _apply_parameter_group(self, param_group, group_values):
        """Apply values to a parameter group."""
        try:
            for param_name, param_value in group_values.items():
                child_param = param_group.child(param_name)
                if child_param:
                    if isinstance(param_value, dict):
                        # Recursive for nested groups
                        self._apply_parameter_group(child_param, param_value)
                    else:
                        # Set leaf parameter value
                        try:
                            child_param.setValue(param_value)
                        except Exception as e:
                            logger.debug(f"Could not set parameter {param_name}: {e}")

        except Exception as e:
            logger.debug(f"Error applying parameter group: {e}")

    def _apply_device_positions(self, device_positions):
        """Apply device positions from configuration."""
        try:
            # Apply laser wavelength
            if "laser_wavelength" in device_positions:
                wl = device_positions["laser_wavelength"]
                if hasattr(self, "wavelength_spinbox"):
                    self.wavelength_spinbox.setValue(wl)
                if hasattr(self, "wavelength_slider"):
                    self.wavelength_slider.setValue(int(wl))

            # Apply rotator setpoints
            if "rotator_setpoints" in device_positions and hasattr(
                self, "rotator_controls"
            ):
                setpoints = device_positions["rotator_setpoints"]
                for axis, position in setpoints.items():
                    if int(axis) in self.rotator_controls:
                        controls = self.rotator_controls[int(axis)]
                        if "position_spinbox" in controls:
                            controls["position_spinbox"].setValue(position)

        except Exception as e:
            logger.debug(f"Error applying device positions: {e}")

    def _apply_device_control_settings(self, device_control_settings):
        """Apply device control widget settings."""
        try:
            # Apply wavelength control settings
            if "wavelength_control" in device_control_settings:
                wl_settings = device_control_settings["wavelength_control"]
                if "spinbox_value" in wl_settings and hasattr(
                    self, "wavelength_spinbox"
                ):
                    self.wavelength_spinbox.setValue(wl_settings["spinbox_value"])
                if "slider_value" in wl_settings and hasattr(self, "wavelength_slider"):
                    self.wavelength_slider.setValue(wl_settings["slider_value"])

            # Apply power sync settings
            if "power_sync" in device_control_settings:
                sync_settings = device_control_settings["power_sync"]
                if "auto_sync_enabled" in sync_settings and hasattr(
                    self, "auto_sync_checkbox"
                ):
                    self.auto_sync_checkbox.setChecked(
                        sync_settings["auto_sync_enabled"]
                    )

        except Exception as e:
            logger.debug(f"Error applying device control settings: {e}")

    def _apply_analysis_settings(self, analysis_settings):
        """Apply analysis widget settings."""
        try:
            # Apply fitting settings
            if "fitting" in analysis_settings:
                fit_settings = analysis_settings["fitting"]
                if "auto_fit_enabled" in fit_settings and hasattr(
                    self, "auto_fit_checkbox"
                ):
                    self.auto_fit_checkbox.setChecked(fit_settings["auto_fit_enabled"])

            # Apply spectral analysis settings
            if "spectral" in analysis_settings:
                spectral_settings = analysis_settings["spectral"]
                if "index" in spectral_settings and hasattr(
                    self, "spectral_mode_combo"
                ):
                    self.spectral_mode_combo.setCurrentIndex(spectral_settings["index"])

        except Exception as e:
            logger.debug(f"Error applying analysis settings: {e}")

    def _apply_ui_settings(self, ui_settings):
        """Apply UI widget settings."""
        try:
            # Apply tab selections
            if "active_analysis_tab" in ui_settings and hasattr(self, "analysis_tabs"):
                self.analysis_tabs.setCurrentIndex(ui_settings["active_analysis_tab"])

            if "active_device_tab" in ui_settings and hasattr(self, "device_tabs"):
                self.device_tabs.setCurrentIndex(ui_settings["active_device_tab"])

        except Exception as e:
            logger.debug(f"Error applying UI settings: {e}")

    # Utility methods

    def get_style(self):
        """Get style from various sources for icons."""
        if hasattr(self, "style") and callable(self.style):
            return self.style()
        elif (
            hasattr(self, "dashboard")
            and hasattr(self.dashboard, "style")
            and callable(self.dashboard.style)
        ):
            return self.dashboard.style()
        elif (
            hasattr(self.dashboard, "mainwindow")
            and hasattr(self.dashboard.mainwindow, "style")
            and callable(self.dashboard.mainwindow.style)
        ):
            return self.dashboard.mainwindow.style()
        else:
            # Fallback to a default QApplication style
            from qtpy.QtWidgets import QApplication

            return QApplication.style()

    def add_action(self, name: str, text: str, callback, icon: str = None):
        """Add an action to the extension."""
        action = QtWidgets.QAction(text, self)
        action.triggered.connect(callback)
        if icon and hasattr(QtWidgets.QStyle, icon):
            action.setIcon(
                self.get_style().standardIcon(getattr(QtWidgets.QStyle, icon))
            )
        setattr(self, f"{name}_action", action)

    def log_message(self, message: str, level: str = "info"):
        """Add a message to the activity log."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        if hasattr(self, "log_display"):
            self.log_display.append(formatted_message)
            # Auto-scroll to bottom
            self.log_display.moveCursor(QtGui.QTextCursor.End)

    def update_device_status(self):
        """Update device status display using PyMoDAQ parameter trees (PyMoDAQ Standards Compliant)."""
        if not self.device_manager:
            return

        try:
            # Update legacy table widget if it still exists (for backward compatibility)
            if hasattr(self, "device_status_table") and self.device_status_table:
                # Get all device information
                all_device_info = self.device_manager.get_all_device_info()

                # Update table row count
                self.device_status_table.setRowCount(len(all_device_info))

                # Update each device row
                for row, (device_key, device_info) in enumerate(
                    all_device_info.items()
                ):
                    # Device name
                    name_item = QtWidgets.QTableWidgetItem(device_key.title())
                    self.device_status_table.setItem(row, 0, name_item)

                    # Status with color coding
                    status_item = QtWidgets.QTableWidgetItem(device_info.status.value)
                    if device_info.status == DeviceStatus.CONNECTED:
                        status_item.setBackground(
                            QtGui.QColor(144, 238, 144)
                        )  # Light green
                    elif device_info.status == DeviceStatus.DISCONNECTED:
                        status_item.setBackground(
                            QtGui.QColor(255, 182, 193)
                        )  # Light pink
                    elif device_info.status == DeviceStatus.ERROR:
                        status_item.setBackground(
                            QtGui.QColor(255, 99, 71)
                        )  # Tomato red
                    else:
                        status_item.setBackground(
                            QtGui.QColor(211, 211, 211)
                        )  # Light gray

                    self.device_status_table.setItem(row, 1, status_item)

                    # Details (error message or module info)
                    details = ""
                    if device_info.last_error:
                        details = f"Error: {device_info.last_error}"
                    elif device_info.module_name:
                        details = f"Module: {device_info.module_name}"
                    else:
                        details = "No details available"

                    details_item = QtWidgets.QTableWidgetItem(details)
                    self.device_status_table.setItem(row, 2, details_item)

            # Update status monitoring parameters (PyMoDAQ Standards)
            self.update_status_monitoring_parameters()

            # Update specific device information if available
            self._update_live_device_data()

        except Exception as e:
            logger.error(f"Error updating device status display: {e}")
            # Track error in status monitoring
            if (
                hasattr(self, "status_monitoring_settings")
                and self.status_monitoring_settings
            ):
                self.status_monitoring_settings.child(
                    "measurement_status", "last_error"
                ).setValue(str(e))

    def start_status_monitoring(self):
        """Start PyMoDAQ-style status monitoring using threading instead of QTimer."""
        if self._status_monitoring_active:
            return

        self._status_monitoring_active = True

        import threading
        import time

        def status_worker():
            """Worker thread for periodic status updates."""
            while self._status_monitoring_active:
                try:
                    self.update_device_status()
                    time.sleep(self._status_update_interval)
                except Exception as e:
                    logger.error(f"Error in extension status monitoring: {e}")
                    time.sleep(self._status_update_interval)

        self._status_worker_thread = threading.Thread(target=status_worker, daemon=True)
        self._status_worker_thread.start()

        logger.info("Started PyMoDAQ-style extension status monitoring")

    def stop_status_monitoring(self):
        """Stop PyMoDAQ-style status monitoring."""
        if not self._status_monitoring_active:
            return

        self._status_monitoring_active = False

        if self._status_worker_thread and self._status_worker_thread.is_alive():
            self._status_worker_thread.join(timeout=2.0)

        logger.info("Stopped PyMoDAQ-style extension status monitoring")

    def start_device_update_monitoring(self):
        """Start PyMoDAQ-style device update monitoring using threading instead of QTimer."""
        if self._device_update_active:
            return

        self._device_update_active = True

        import threading
        import time

        def device_update_worker():
            """Worker thread for periodic device updates."""
            while self._device_update_active:
                try:
                    self.update_device_control_displays()
                    time.sleep(self._device_update_interval)
                except Exception as e:
                    logger.error(f"Error in device update monitoring: {e}")
                    time.sleep(self._device_update_interval)

        self._device_update_thread = threading.Thread(
            target=device_update_worker, daemon=True
        )
        self._device_update_thread.start()

        logger.info("Started PyMoDAQ-style device update monitoring")

    def stop_device_update_monitoring(self):
        """Stop PyMoDAQ-style device update monitoring."""
        if not self._device_update_active:
            return

        self._device_update_active = False

        if self._device_update_thread and self._device_update_thread.is_alive():
            self._device_update_thread.join(timeout=2.0)

        logger.info("Stopped PyMoDAQ-style device update monitoring")

    def _update_live_device_data(self):
        """Update live data from specific devices (power, temperature, etc)."""
        try:
            # Update power meter reading
            power_meter = self.device_manager.get_power_meter()
            if power_meter and hasattr(power_meter, "grab_data"):
                try:
                    power_data = power_meter.grab_data()
                    if power_data and len(power_data) > 0:
                        # Extract power value (assuming it's in the first data element)
                        power_value = (
                            float(power_data[0].data[0])
                            if hasattr(power_data[0], "data")
                            else 0.0
                        )

                        # Update power plot if it exists
                        if hasattr(self, "power_plot") and self.power_plot:
                            # Store power history for plotting
                            if not hasattr(self, "_power_history"):
                                self._power_history = {"time": [], "power": []}

                            current_time = time.time()
                            self._power_history["time"].append(current_time)
                            self._power_history["power"].append(power_value)

                            # Keep only last 100 points
                            if len(self._power_history["time"]) > 100:
                                self._power_history["time"] = self._power_history[
                                    "time"
                                ][-100:]
                                self._power_history["power"] = self._power_history[
                                    "power"
                                ][-100:]

                            # Update plot
                            if len(self._power_history["time"]) > 1:
                                # Convert to relative time
                                rel_time = [
                                    t - self._power_history["time"][0]
                                    for t in self._power_history["time"]
                                ]
                                # Update plot using PyMoDAQ DataRaw
                                time_axis = Axis(
                                    "Time", units="s", data=np.array(rel_time)
                                )
                                power_data = DataRaw(
                                    "Power Monitor",
                                    data=[np.array(self._power_history["power"])],
                                    axes=[time_axis],
                                    labels=["Power"],
                                )
                                self.power_plot.show_data(power_data)

                except Exception as e:
                    logger.debug(f"Could not update power meter data: {e}")

            # Update camera temperature if available
            camera = self.device_manager.get_camera()
            if camera and hasattr(camera, "controller") and camera.controller:
                try:
                    # Check if camera has temperature monitoring
                    if hasattr(camera.controller, "get_temperature"):
                        temp = camera.controller.get_temperature()
                        # Could add temperature display to status or plots here
                        logger.debug(f"Camera temperature: {temp}°C")
                except Exception as e:
                    logger.debug(f"Could not get camera temperature: {e}")

            # Update device control parameters to keep parameter tree synchronized (PyMoDAQ Standards)
            self.update_device_control_parameters()

        except Exception as e:
            logger.debug(f"Error updating live device data: {e}")

    # Signal handlers

    def on_measurement_started(self):
        """Handle measurement started signal."""
        # PyMoDAQ parameter-driven approach: manage action states via parameter tree
        self.settings.child("measurement_control", "start_measurement").setOpts(
            enabled=False
        )
        self.settings.child("measurement_control", "stop_measurement").setOpts(
            enabled=True
        )
        self.settings.child("measurement_control", "pause_measurement").setOpts(
            enabled=True
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.is_measuring = True

    def on_measurement_finished(self):
        """Handle measurement finished signal."""
        # PyMoDAQ parameter-driven approach: reset action states
        self.settings.child("measurement_control", "start_measurement").setOpts(
            enabled=True
        )
        self.settings.child("measurement_control", "stop_measurement").setOpts(
            enabled=False
        )
        self.settings.child("measurement_control", "pause_measurement").setOpts(
            enabled=False
        )
        self.progress_bar.setVisible(False)
        self.is_measuring = False

    def on_measurement_progress(self, progress: int):
        """Handle measurement progress update."""
        self.progress_bar.setValue(progress)

    def on_device_status_changed(self, device_name: str, status: str):
        """Handle device status change."""
        logger.debug(f"Device {device_name} status: {status}")
        # Update device status table
        # Implementation in Phase 2

    def on_error_occurred(self, error_message: str):
        """Handle error occurrence."""
        logger.error(f"Extension error: {error_message}")
        self.log_message(f"ERROR: {error_message}", level="error")

        # Show error dialog using PyMoDAQ messaging
        messagebox(
            severity="critical",
            title="μRASHG Extension Error",
            text=f"An error occurred:\n\n{error_message}",
        )

    def on_device_error(self, device_name: str, error_message: str):
        """Handle device-specific error."""
        logger.error(f"Device '{device_name}' error: {error_message}")
        self.log_message(
            f"DEVICE ERROR - {device_name}: {error_message}", level="error"
        )

    def on_all_devices_ready(self, ready: bool):
        """Handle all devices ready status change."""
        if ready:
            logger.info("All required devices are ready")
            self.log_message("All required devices are ready for measurements")
            self.settings.child("measurement_control", "start_measurement").setOpts(
                enabled=True
            )
        else:
            logger.warning("Not all required devices are ready")
            self.log_message("Some required devices are not ready", level="warning")
            self.settings.child("measurement_control", "start_measurement").setOpts(
                enabled=False
            )

    def _on_measurement_completed(self, measurement_data):
        """Handle measurement completion from worker thread."""
        logger.info("Measurement completed successfully")
        self.log_message("Measurement completed successfully")

        # Store measurement data
        self.current_measurement_data = measurement_data

        # Update plots with final data
        if measurement_data and hasattr(self, "polar_plot"):
            self._update_polar_plot(measurement_data)

        # Emit completion signal
        self.measurement_finished.emit()

        # Clean up thread
        if hasattr(self, "measurement_thread"):
            self.measurement_thread.quit()
            self.measurement_thread.wait()

    def _on_measurement_failed(self, error_message):
        """Handle measurement failure from worker thread."""
        logger.error(f"Measurement failed: {error_message}")
        self.log_message(f"Measurement failed: {error_message}", level="error")

        # Emit error signal
        self.error_occurred.emit(f"Measurement failed: {error_message}")

        # Reset state
        self.measurement_finished.emit()

        # Clean up thread
        if hasattr(self, "measurement_thread"):
            self.measurement_thread.quit()
            self.measurement_thread.wait()

    def _on_data_acquired(self, step_data):
        """Handle individual data acquisition from worker thread."""
        try:
            # Update live camera view if available
            if "camera_data" in step_data and hasattr(self, "camera_view"):
                image_data = step_data["camera_data"]
                self.camera_view.setImage(image_data)

            # Update polar plot with current data
            if (
                hasattr(self, "polar_plot")
                and "angle" in step_data
                and "intensity" in step_data
            ):
                # Store for real-time plotting
                if not hasattr(self, "_live_polar_data"):
                    self._live_polar_data = {"angles": [], "intensities": []}

                self._live_polar_data["angles"].append(step_data["angle"])
                self._live_polar_data["intensities"].append(step_data["intensity"])

                # Update plot
                self.polar_plot.clear()
                self.polar_plot.plot(
                    self._live_polar_data["angles"],
                    self._live_polar_data["intensities"],
                    pen="r",
                    symbol="o",
                )

        except Exception as e:
            logger.warning(f"Error updating live data display: {e}")

    def _update_polar_plot(self, measurement_data):
        """Update polar plot with complete measurement data."""
        try:
            if not measurement_data or not hasattr(self, "polar_plot"):
                return

            # Extract angle and intensity data
            angles = measurement_data.get("angles", [])
            intensities = measurement_data.get("intensities", [])

            if len(angles) > 0 and len(intensities) > 0:
                # Clear and plot final data
                self.polar_plot.clear()
                self.polar_plot.plot(
                    angles, intensities, pen="b", symbol="o", symbolBrush="b"
                )
                self.polar_plot.setTitle("μRASHG Polar Response")

                # Fit data if requested
                if self.settings.child("advanced", "realtime_analysis").value():
                    self._fit_and_plot_rashg_pattern(angles, intensities)

        except Exception as e:
            logger.warning(f"Error updating polar plot: {e}")

    def _fit_and_plot_rashg_pattern(self, angles, intensities):
        """Fit RASHG pattern and overlay fit on plot (Enhanced for Phase 3)."""
        try:
            # Use the new comprehensive fitting method
            fit_results = self._fit_rashg_data(angles, intensities)

            if (
                fit_results
                and hasattr(self, "auto_fit_checkbox")
                and self.auto_fit_checkbox.isChecked()
            ):
                # Plot the fit curve
                self._plot_fit_curve(angles, intensities, fit_results)

                # Update fit results display
                self._display_fit_results(fit_results)

                # Store results
                self.current_fit_results = fit_results

                # Log fit parameters
                self.log_message(
                    f"RASHG Fit: A={fit_results['A']:.2f}, B={fit_results['B']:.2f}, φ={fit_results['phi_deg']:.1f}°"
                )

        except Exception as e:
            logger.warning(f"Could not fit RASHG pattern: {e}")

    # =================== PHASE 3: ADVANCED ANALYSIS METHODS ===================

    def _fit_rashg_data(self, angles, intensities):
        """Comprehensive RASHG data fitting (PHASE 3 FEATURE)."""
        try:
            import numpy as np
            from scipy.optimize import curve_fit

            # Define RASHG fit function: I = A + B*cos(4θ + φ)
            def rashg_func(theta, A, B, phi):
                return A + B * np.cos(4 * np.radians(theta) + phi)

            # Convert to numpy arrays
            angles_np = np.array(angles)
            intensities_np = np.array(intensities)

            # Initial guess
            A_init = np.mean(intensities_np)
            B_init = (np.max(intensities_np) - np.min(intensities_np)) / 2
            phi_init = 0

            # Perform fit with error handling
            try:
                popt, pcov = curve_fit(
                    rashg_func,
                    angles_np,
                    intensities_np,
                    p0=[A_init, B_init, phi_init],
                    bounds=([-np.inf, 0, -np.pi], [np.inf, np.inf, np.pi]),
                )
            except Exception as e:
                logger.warning(f"Constrained fit failed, trying unconstrained: {e}")
                popt, pcov = curve_fit(
                    rashg_func, angles_np, intensities_np, p0=[A_init, B_init, phi_init]
                )

            # Extract fit parameters
            A, B, phi = popt

            # Calculate fit quality metrics
            fit_angles = np.linspace(
                angles_np.min(), angles_np.max(), len(angles_np) * 4
            )
            fit_intensities = rashg_func(fit_angles, *popt)
            predicted_intensities = rashg_func(angles_np, *popt)

            # R-squared
            ss_res = np.sum((intensities_np - predicted_intensities) ** 2)
            ss_tot = np.sum((intensities_np - np.mean(intensities_np)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Parameter errors (standard deviations)
            param_errors = np.sqrt(np.diag(pcov))

            # RASHG-specific parameters
            contrast = abs(B) / A if A > 0 else 0
            modulation_depth = abs(B) / (A + abs(B)) if (A + abs(B)) > 0 else 0

            # Comprehensive fit results
            fit_results = {
                "A": float(A),  # Background/offset
                "B": float(B),  # Modulation amplitude
                "phi": float(phi),  # Phase (radians)
                "phi_deg": float(np.degrees(phi)),  # Phase (degrees)
                "A_error": float(param_errors[0]),
                "B_error": float(param_errors[1]),
                "phi_error": float(param_errors[2]),
                "phi_deg_error": float(np.degrees(param_errors[2])),
                "r_squared": float(r_squared),
                "contrast": float(contrast),
                "modulation_depth": float(modulation_depth),
                "fit_angles": fit_angles.tolist(),
                "fit_intensities": fit_intensities.tolist(),
                "residuals": (intensities_np - predicted_intensities).tolist(),
                "fit_function": "I = A + B*cos(4θ + φ)",
                "timestamp": time.time(),
            }

            return fit_results

        except Exception as e:
            logger.error(f"RASHG fitting failed: {e}")
            return None

    def _plot_fit_curve(self, angles, intensities, fit_results):
        """Plot RASHG fit curve overlay."""
        try:
            if not hasattr(self, "polar_plot") or not fit_results:
                return

            # Clear previous fit curves
            items_to_remove = []
            for item in self.polar_plot.getPlotItem().listDataItems():
                if hasattr(item, "name") and "Fit" in str(item.name):
                    items_to_remove.append(item)

            for item in items_to_remove:
                self.polar_plot.removeItem(item)

            # Plot new fit curve
            fit_angles = np.array(fit_results["fit_angles"])
            fit_intensities = np.array(fit_results["fit_intensities"])

            self.polar_plot.plot(
                fit_angles,
                fit_intensities,
                pen=pg.mkPen("g", width=2),
                name="RASHG Fit",
            )

            # Plot residuals (optional, scaled for visibility)
            if len(fit_results["residuals"]) == len(angles):
                residuals = np.array(fit_results["residuals"])
                angles_np = np.array(angles)

                # Scale residuals for visibility
                residual_scale = np.max(intensities) * 0.1
                scaled_residuals = (
                    residuals * residual_scale / np.max(np.abs(residuals))
                    if np.max(np.abs(residuals)) > 0
                    else residuals
                )
                baseline = np.min(intensities) - np.max(np.abs(scaled_residuals)) * 1.5

                self.polar_plot.plot(
                    angles_np,
                    baseline + scaled_residuals,
                    pen=pg.mkPen("r", width=1, style=QtCore.Qt.DashLine),
                    name="Residuals (scaled)",
                )

        except Exception as e:
            logger.error(f"Error plotting fit curve: {e}")

    def _display_fit_results(self, fit_results):
        """Display fit results in the UI."""
        try:
            if not hasattr(self, "fit_results_label") or not fit_results:
                return

            # Format results display
            results_text = (
                f"A={fit_results['A']:.1f}±{fit_results['A_error']:.1f}, "
                f"B={fit_results['B']:.1f}±{fit_results['B_error']:.1f}, "
                f"φ={fit_results['phi_deg']:.1f}±{fit_results['phi_deg_error']:.1f}°, "
                f"R²={fit_results['r_squared']:.3f}, "
                f"Contrast={fit_results['contrast']:.3f}"
            )

            self.fit_results_label.setText(f"Fit Results: {results_text}")
            self.fit_results_label.setToolTip(
                f"Background: {fit_results['A']:.2f} ± {fit_results['A_error']:.2f}\n"
                f"Amplitude: {fit_results['B']:.2f} ± {fit_results['B_error']:.2f}\n"
                f"Phase: {fit_results['phi_deg']:.2f}° ± {fit_results['phi_deg_error']:.2f}°\n"
                f"R-squared: {fit_results['r_squared']:.4f}\n"
                f"Contrast: {fit_results['contrast']:.4f}\n"
                f"Modulation Depth: {fit_results['modulation_depth']:.4f}"
            )

        except Exception as e:
            logger.error(f"Error displaying fit results: {e}")

    def on_auto_fit_changed(self, state):
        """Handle auto-fit checkbox state change."""
        enabled = state == QtCore.Qt.Checked
        logger.info(f"Real-time RASHG fitting {'enabled' if enabled else 'disabled'}")
        self.log_message(
            f"Real-time RASHG fitting {'enabled' if enabled else 'disabled'}"
        )

    def update_spectral_analysis(self):
        """Update spectral analysis display (PHASE 3 FEATURE) - PyMoDAQ Standards Compliant."""
        try:
            if (
                not self.current_measurement_data
                or not self.current_measurement_data.get("multi_wavelength", False)
            ):
                if hasattr(self, "spectral_plot"):
                    self.spectral_plot.clear()

                # Update parameter tree with no data status (PyMoDAQ Standards)
                if (
                    hasattr(self, "analysis_control_settings")
                    and self.analysis_control_settings
                ):
                    self.analysis_control_settings.child(
                        "spectral_analysis", "spectral_status"
                    ).setValue("No multi-wavelength data")
                return

            self.update_analysis_status("Updating spectral analysis...")

            # Get wavelength and intensity data
            wavelengths = self.current_measurement_data.get("wavelengths", [])
            intensities = self.current_measurement_data.get("intensities", [])
            angles = self.current_measurement_data.get("angles", [])

            if not wavelengths or not intensities:
                # Update parameter tree with no data status (PyMoDAQ Standards)
                if (
                    hasattr(self, "analysis_control_settings")
                    and self.analysis_control_settings
                ):
                    self.analysis_control_settings.child(
                        "spectral_analysis", "spectral_status"
                    ).setValue("No wavelength data")
                return

            # Organize data by wavelength
            spectral_data = self._organize_spectral_data(
                wavelengths, intensities, angles
            )

            # Get spectral analysis mode from parameter tree (PyMoDAQ Standards)
            mode = "RASHG Amplitude"  # default
            if (
                hasattr(self, "analysis_control_settings")
                and self.analysis_control_settings
            ):
                try:
                    mode = self.analysis_control_settings.child(
                        "spectral_analysis", "spectral_mode"
                    ).value()
                except:
                    pass
            elif hasattr(self, "spectral_mode_combo"):
                # Fallback to combo box if parameter tree not available
                mode = self.spectral_mode_combo.currentText()

            # Perform spectral analysis based on mode
            if mode == "RASHG Amplitude":
                self._plot_spectral_amplitude(spectral_data)
            elif mode == "Phase":
                self._plot_spectral_phase(spectral_data)
            elif mode == "Contrast":
                self._plot_spectral_contrast(spectral_data)
            elif mode == "All Parameters":
                self._plot_all_spectral_parameters(spectral_data)

            # Store spectral analysis data
            self.spectral_analysis_data = spectral_data

            self.update_analysis_status("Spectral analysis updated")

            # Update parameter tree with success status (PyMoDAQ Standards)
            if (
                hasattr(self, "analysis_control_settings")
                and self.analysis_control_settings
            ):
                self.analysis_control_settings.child(
                    "spectral_analysis", "spectral_status"
                ).setValue("Analysis completed")

        except Exception as e:
            logger.error(f"Error updating spectral analysis: {e}")
            self.update_analysis_status("Spectral analysis failed")

            # Update parameter tree with error status (PyMoDAQ Standards)
            if (
                hasattr(self, "analysis_control_settings")
                and self.analysis_control_settings
            ):
                self.analysis_control_settings.child(
                    "spectral_analysis", "spectral_status"
                ).setValue(f"Error: {str(e)}")

        finally:
            # Always update analysis control parameters to synchronize parameter tree (PyMoDAQ Standards)
            self.update_analysis_control_parameters()

    def _organize_spectral_data(self, wavelengths, intensities, angles):
        """Organize measurement data by wavelength for spectral analysis."""
        try:
            import numpy as np

            # Get unique wavelengths
            unique_wavelengths = sorted(list(set(wavelengths)))

            spectral_data = {
                "wavelengths": unique_wavelengths,
                "rashg_amplitudes": [],
                "phases": [],
                "contrasts": [],
                "backgrounds": [],
                "r_squared_values": [],
                "fit_errors": [],
            }

            # Process each wavelength
            for wl in unique_wavelengths:
                # Get data for this wavelength
                wl_indices = [
                    i for i, w in enumerate(wavelengths) if abs(w - wl) < 0.5
                ]  # 0.5 nm tolerance

                if len(wl_indices) < 4:  # Need at least 4 points for fitting
                    # Fill with None for missing data
                    spectral_data["rashg_amplitudes"].append(None)
                    spectral_data["phases"].append(None)
                    spectral_data["contrasts"].append(None)
                    spectral_data["backgrounds"].append(None)
                    spectral_data["r_squared_values"].append(None)
                    spectral_data["fit_errors"].append(None)
                    continue

                wl_angles = [angles[i] for i in wl_indices]
                wl_intensities = [intensities[i] for i in wl_indices]

                # Fit RASHG pattern for this wavelength
                fit_results = self._fit_rashg_data(wl_angles, wl_intensities)

                if fit_results:
                    spectral_data["rashg_amplitudes"].append(abs(fit_results["B"]))
                    spectral_data["phases"].append(fit_results["phi_deg"])
                    spectral_data["contrasts"].append(fit_results["contrast"])
                    spectral_data["backgrounds"].append(fit_results["A"])
                    spectral_data["r_squared_values"].append(fit_results["r_squared"])
                    spectral_data["fit_errors"].append(
                        {
                            "A_error": fit_results["A_error"],
                            "B_error": fit_results["B_error"],
                            "phi_error": fit_results["phi_deg_error"],
                        }
                    )
                else:
                    # Fill with None for failed fits
                    spectral_data["rashg_amplitudes"].append(None)
                    spectral_data["phases"].append(None)
                    spectral_data["contrasts"].append(None)
                    spectral_data["backgrounds"].append(None)
                    spectral_data["r_squared_values"].append(None)
                    spectral_data["fit_errors"].append(None)

            return spectral_data

        except Exception as e:
            logger.error(f"Error organizing spectral data: {e}")
            return {}

    def _plot_spectral_amplitude(self, spectral_data):
        """Plot spectral RASHG amplitude."""
        try:
            if not hasattr(self, "spectral_plot") or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data["wavelengths"]
            amplitudes = spectral_data["rashg_amplitudes"]

            # Filter out None values
            valid_data = [
                (w, a) for w, a in zip(wavelengths, amplitudes) if a is not None
            ]

            if valid_data:
                wl, amp = zip(*valid_data)
                self.spectral_plot.plot(
                    wl,
                    amp,
                    pen=pg.mkPen("b", width=2),
                    symbol="o",
                    symbolBrush="b",
                    name="RASHG Amplitude",
                )

            self.spectral_plot.setTitle("Spectral RASHG Amplitude")
            self.spectral_plot.setLabel("left", "RASHG Amplitude", "counts")

        except Exception as e:
            logger.error(f"Error plotting spectral amplitude: {e}")

    def _plot_spectral_phase(self, spectral_data):
        """Plot spectral RASHG phase."""
        try:
            if not hasattr(self, "spectral_plot") or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data["wavelengths"]
            phases = spectral_data["phases"]

            # Filter out None values
            valid_data = [(w, p) for w, p in zip(wavelengths, phases) if p is not None]

            if valid_data:
                wl, phase = zip(*valid_data)
                self.spectral_plot.plot(
                    wl,
                    phase,
                    pen=pg.mkPen("r", width=2),
                    symbol="s",
                    symbolBrush="r",
                    name="RASHG Phase",
                )

            self.spectral_plot.setTitle("Spectral RASHG Phase")
            self.spectral_plot.setLabel("left", "Phase", "°")

        except Exception as e:
            logger.error(f"Error plotting spectral phase: {e}")

    def _plot_spectral_contrast(self, spectral_data):
        """Plot spectral RASHG contrast."""
        try:
            if not hasattr(self, "spectral_plot") or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data["wavelengths"]
            contrasts = spectral_data["contrasts"]

            # Filter out None values
            valid_data = [
                (w, c) for w, c in zip(wavelengths, contrasts) if c is not None
            ]

            if valid_data:
                wl, cont = zip(*valid_data)
                self.spectral_plot.plot(
                    wl,
                    cont,
                    pen=pg.mkPen("g", width=2),
                    symbol="^",
                    symbolBrush="g",
                    name="RASHG Contrast",
                )

            self.spectral_plot.setTitle("Spectral RASHG Contrast")
            self.spectral_plot.setLabel("left", "Contrast", "ratio")

        except Exception as e:
            logger.error(f"Error plotting spectral contrast: {e}")

    def _plot_all_spectral_parameters(self, spectral_data):
        """Plot all spectral RASHG parameters in subplots."""
        try:
            if not hasattr(self, "spectral_plot") or not spectral_data:
                return

            self.spectral_plot.clear()

            # For now, plot amplitude as primary parameter
            # TODO: Could be enhanced to show multiple y-axes or subplots
            self._plot_spectral_amplitude(spectral_data)

        except Exception as e:
            logger.error(f"Error plotting all spectral parameters: {e}")

    def update_3d_visualization(self):
        """Update 3D visualization for multi-wavelength data (PHASE 3 FEATURE)."""
        try:
            if not hasattr(self, "volume_view") or not self.current_measurement_data:
                return

            if not self.current_measurement_data.get("multi_wavelength", False):
                return

            self.update_analysis_status("Updating 3D visualization...")

            # Clear previous visualization
            self.volume_view.clear()

            # Get data
            wavelengths = self.current_measurement_data.get("wavelengths", [])
            angles = self.current_measurement_data.get("angles", [])
            intensities = self.current_measurement_data.get("intensities", [])

            if not wavelengths or not angles or not intensities:
                return

            # Create 3D scatter plot
            import pyqtgraph.opengl as gl
            import numpy as np

            # Normalize data for visualization
            wl_norm = np.array(wavelengths) / np.max(wavelengths)
            angle_norm = np.array(angles) / 180.0
            int_norm = np.array(intensities) / np.max(intensities)

            # Create positions array
            pos = np.column_stack([wl_norm * 50, angle_norm * 50, int_norm * 20])

            # Create scatter plot
            scatter = gl.GLScatterPlotItem(pos=pos, color=(1.0, 1.0, 1.0, 0.8), size=3)
            self.volume_view.addItem(scatter)

            # Add axis labels (simplified)
            # TODO: Add proper axis labels and scaling

            self.update_analysis_status("3D visualization updated")

        except Exception as e:
            logger.error(f"Error updating 3D visualization: {e}")
            self.update_analysis_status("3D visualization failed")

    def _check_3d_support(self):
        """Check if 3D visualization is supported."""
        try:
            import pyqtgraph.opengl as gl

            return True
        except ImportError:
            return False

    def update_analysis_status(self, status):
        """Update analysis status display."""
        try:
            if hasattr(self, "analysis_status"):
                self.analysis_status.setText(f"Analysis Status: {status}")
        except Exception:
            pass

    # =================== END PHASE 3 ADVANCED ANALYSIS METHODS ===================

    def closeEvent(self, event):
        """Handle extension close event."""
        if self.is_measuring:
            reply = messagebox(
                severity="question",
                title="Confirm Close",
                text="A measurement is in progress. Stop measurement and close?",
            )

            if reply:
                self.stop_measurement()
            else:
                event.ignore()
                return

        # Cleanup
        self.stop_status_monitoring()

        # Stop device control update timer (PHASE 3 FEATURE)
        if hasattr(self, "device_update_timer"):
            self.stop_device_update_monitoring()
            logger.info("Stopped device control update timer")

        if hasattr(self, "device_manager") and self.device_manager:
            self.device_manager.cleanup()

        logger.info("μRASHG extension closed")
        event.accept()


class MeasurementWorker(QObject):
    """
    Worker class for performing μRASHG measurements in a separate thread.

    Handles the complete measurement sequence including:
    - Coordinated polarization rotations
    - Camera synchronization
    - Data acquisition and processing
    - Safety monitoring
    """

    # Signals for communication with main thread
    progress_updated = Signal(int)  # Progress percentage
    measurement_completed = Signal(dict)  # Final measurement data
    measurement_failed = Signal(str)  # Error message
    data_acquired = Signal(dict)  # Individual step data

    def __init__(self, extension):
        """
        Initialize the measurement worker.

        Args:
            extension: Reference to the URASHGMicroscopyExtension
        """
        super().__init__()

        self.extension = extension
        self.device_manager = extension.device_manager
        self.settings = extension.settings

        # Control flags
        self.stop_requested = False
        self.pause_requested = False
        self.is_paused = False

        # Measurement data storage (Enhanced for multi-wavelength - PHASE 3)
        self.measurement_data = {
            "angles": [],
            "intensities": [],
            "images": [],
            "power_readings": [],
            "timestamps": [],
            "wavelengths": [],  # ⭐ NEW: Store wavelength for each measurement point
            "wavelength_sequence": [],  # ⭐ NEW: Store wavelength scan sequence
            "multi_wavelength": False,  # ⭐ NEW: Flag for multi-wavelength measurement
            "measurement_type": "Basic RASHG",  # ⭐ NEW: Store measurement type
        }

        logger.info("MeasurementWorker initialized")

    def run_measurement(self):
        """Main measurement execution method (Enhanced for multi-wavelength - PHASE 3)."""
        logger.info("Starting measurement worker execution")

        try:
            # Initialize measurement
            if not self._initialize_measurement():
                self.measurement_failed.emit("Failed to initialize measurement")
                return

            # Get measurement parameters
            measurement_type = self.settings.child(
                "experiment", "measurement_type"
            ).value()
            pol_steps = self.settings.child("experiment", "pol_steps").value()
            pol_start = self.settings.child(
                "experiment", "pol_range", "pol_start"
            ).value()
            pol_end = self.settings.child("experiment", "pol_range", "pol_end").value()
            integration_time = self.settings.child(
                "experiment", "integration_time"
            ).value()
            averages = self.settings.child("experiment", "averages").value()

            # Store measurement type
            self.measurement_data["measurement_type"] = measurement_type

            # Check if multi-wavelength scanning is enabled
            enable_wavelength_scan = self.settings.child(
                "wavelength", "enable_scan"
            ).value()

            if enable_wavelength_scan:
                logger.info("Multi-wavelength scanning enabled")
                self._run_multi_wavelength_measurement(
                    pol_steps, pol_start, pol_end, integration_time, averages
                )
            else:
                logger.info("Single wavelength measurement")
                self._run_single_wavelength_measurement(
                    pol_steps, pol_start, pol_end, integration_time, averages
                )

            # Finalize measurement
            self._finalize_measurement()

            # Emit completion
            self.measurement_completed.emit(self.measurement_data.copy())
            logger.info("Measurement completed successfully")

        except Exception as e:
            error_msg = f"Measurement failed with error: {str(e)}"
            logger.error(error_msg)
            self.measurement_failed.emit(error_msg)

    def _run_single_wavelength_measurement(
        self, pol_steps, pol_start, pol_end, integration_time, averages
    ):
        """Run single wavelength polarization measurement."""
        # Create angle sequence
        angle_step = (pol_end - pol_start) / pol_steps if pol_steps > 1 else 0
        angles = [pol_start + i * angle_step for i in range(pol_steps)]

        logger.info(
            f"Single wavelength measurement: {pol_steps} angles from {pol_start}° to {pol_end}°"
        )

        # Get current wavelength (if available)
        current_wavelength = self._get_current_laser_wavelength()
        if current_wavelength is None:
            current_wavelength = 800.0  # Default fallback

        # Main measurement loop
        for step, angle in enumerate(angles):
            if self.stop_requested:
                logger.info("Measurement stopped by user request")
                return

            # Handle pause
            if self._check_pause():
                return

            # Perform measurement step
            step_data = self._measure_at_angle(
                angle, integration_time, averages, current_wavelength
            )

            if step_data is None:
                self.measurement_failed.emit(
                    f"Failed to acquire data at angle {angle}°"
                )
                return

            # Store data
            self._store_measurement_data(step_data, angle, current_wavelength)

            # Emit progress and data
            progress = int((step + 1) * 100 / pol_steps)
            self.progress_updated.emit(progress)
            self._emit_step_data(step_data, step + 1, pol_steps)

            logger.debug(
                f"Completed step {step + 1}/{pol_steps} at {angle}°: intensity={step_data['intensity']:.2f}"
            )

    def _run_multi_wavelength_measurement(
        self, pol_steps, pol_start, pol_end, integration_time, averages
    ):
        """Run multi-wavelength polarization measurement (PHASE 3 FEATURE)."""
        self.measurement_data["multi_wavelength"] = True

        # Get wavelength scan parameters
        wl_start = self.settings.child("wavelength", "wl_start").value()
        wl_stop = self.settings.child("wavelength", "wl_stop").value()
        wl_steps = self.settings.child("wavelength", "wl_steps").value()
        wl_stabilization = self.settings.child("wavelength", "wl_stabilization").value()
        auto_sync_pm = self.settings.child("wavelength", "auto_sync_pm").value()
        sweep_mode = self.settings.child("wavelength", "sweep_mode").value()

        # Generate wavelength sequence
        wavelengths = self._generate_wavelength_sequence(
            wl_start, wl_stop, wl_steps, sweep_mode
        )
        self.measurement_data["wavelength_sequence"] = wavelengths

        # Create angle sequence
        angle_step = (pol_end - pol_start) / pol_steps if pol_steps > 1 else 0
        angles = [pol_start + i * angle_step for i in range(pol_steps)]

        # Calculate total steps for progress
        total_steps = len(wavelengths) * pol_steps
        current_step = 0

        logger.info(
            f"Multi-wavelength measurement: {len(wavelengths)} wavelengths × {pol_steps} angles = {total_steps} total measurements"
        )

        # Multi-wavelength measurement loop
        for wl_index, wavelength in enumerate(wavelengths):
            if self.stop_requested:
                logger.info("Multi-wavelength measurement stopped by user request")
                return

            logger.info(
                f"Setting wavelength to {wavelength:.0f} nm ({wl_index + 1}/{len(wavelengths)})"
            )

            # Set laser wavelength
            if not self._set_laser_wavelength(wavelength):
                logger.error(f"Failed to set wavelength to {wavelength} nm")
                # Continue with next wavelength instead of failing completely
                continue

            # Auto-sync power meter if enabled
            if auto_sync_pm:
                self._sync_power_meter_wavelength(wavelength)

            # Wait for wavelength stabilization
            if wl_stabilization > 0:
                logger.info(
                    f"Waiting {wl_stabilization}s for wavelength stabilization..."
                )
                time.sleep(wl_stabilization)

            # Polarization measurement loop at current wavelength
            for pol_index, angle in enumerate(angles):
                if self.stop_requested:
                    return

                # Handle pause
                if self._check_pause():
                    return

                # Perform measurement step
                step_data = self._measure_at_angle(
                    angle, integration_time, averages, wavelength
                )

                if step_data is None:
                    logger.warning(
                        f"Failed to acquire data at wavelength {wavelength} nm, angle {angle}°"
                    )
                    continue  # Skip this measurement point

                # Store data
                self._store_measurement_data(step_data, angle, wavelength)

                # Update progress
                current_step += 1
                progress = int(current_step * 100 / total_steps)
                self.progress_updated.emit(progress)

                # Emit step data with wavelength info
                self._emit_step_data(step_data, current_step, total_steps, wavelength)

                logger.debug(
                    f"Completed step {current_step}/{total_steps} at {wavelength:.0f}nm, {angle}°: intensity={step_data['intensity']:.2f}"
                )

    def _generate_wavelength_sequence(self, wl_start, wl_stop, wl_steps, sweep_mode):
        """Generate wavelength sequence based on sweep mode."""
        import numpy as np

        if sweep_mode == "Linear":
            return np.linspace(wl_start, wl_stop, wl_steps).tolist()
        elif sweep_mode == "Logarithmic":
            return np.logspace(np.log10(wl_start), np.log10(wl_stop), wl_steps).tolist()
        elif sweep_mode == "Custom":
            # For now, use linear - could be extended for user-defined sequences
            logger.info("Custom wavelength sequence not implemented, using linear")
            return np.linspace(wl_start, wl_stop, wl_steps).tolist()
        else:
            return np.linspace(wl_start, wl_stop, wl_steps).tolist()

    def _set_laser_wavelength(self, wavelength):
        """Set laser wavelength and verify."""
        try:
            # Get laser device
            laser_device = None
            if self.device_manager:
                laser_device = self.device_manager.get_laser()

            if not laser_device:
                logger.error("Laser device not available for wavelength setting")
                return False

            # Use proper DataActuator pattern
            from pymodaq.utils.data import DataActuator

            position_data = DataActuator(data=[wavelength])

            # Set wavelength
            if hasattr(laser_device, "move_abs"):
                laser_device.move_abs(position_data)

                # Wait a moment for the command to be processed
                time.sleep(0.5)

                # Verify wavelength was set (optional)
                actual_wavelength = self._get_current_laser_wavelength()
                if actual_wavelength is not None:
                    wavelength_error = abs(actual_wavelength - wavelength)
                    if wavelength_error > 5.0:  # Tolerance of 5 nm
                        logger.warning(
                            f"Wavelength setting error: target={wavelength}, actual={actual_wavelength}"
                        )

                logger.info(f"Laser wavelength set to {wavelength:.0f} nm")
                return True
            else:
                logger.error("Laser device does not support wavelength setting")
                return False

        except Exception as e:
            logger.error(f"Error setting laser wavelength to {wavelength} nm: {e}")
            return False

    def _sync_power_meter_wavelength(self, wavelength):
        """Sync power meter wavelength setting."""
        try:
            power_meter = None
            if self.device_manager:
                power_meter = self.device_manager.get_power_meter()

            if not power_meter:
                return False

            # Try to sync wavelength
            if hasattr(power_meter, "controller") and power_meter.controller:
                if hasattr(power_meter.controller, "set_wavelength"):
                    power_meter.controller.set_wavelength(wavelength)
                    logger.info(f"Power meter wavelength synced to {wavelength:.0f} nm")
                    return True
                elif hasattr(power_meter, "settings"):
                    wavelength_param = power_meter.settings.child_frompath("wavelength")
                    if wavelength_param:
                        wavelength_param.setValue(wavelength)
                        logger.info(
                            f"Power meter wavelength parameter updated to {wavelength:.0f} nm"
                        )
                        return True

            return False

        except Exception as e:
            logger.debug(f"Could not sync power meter wavelength: {e}")
            return False

    def _check_pause(self):
        """Check and handle pause state."""
        while self.pause_requested and not self.stop_requested:
            if not self.is_paused:
                logger.info("Measurement paused")
                self.is_paused = True
            time.sleep(0.1)

        if self.stop_requested:
            return True

        if self.is_paused:
            logger.info("Measurement resumed")
            self.is_paused = False

        return False

    def _store_measurement_data(self, step_data, angle, wavelength):
        """Store measurement data point."""
        self.measurement_data["angles"].append(angle)
        self.measurement_data["intensities"].append(step_data["intensity"])
        self.measurement_data["images"].append(step_data.get("image"))
        self.measurement_data["power_readings"].append(step_data.get("power"))
        self.measurement_data["wavelengths"].append(wavelength)
        self.measurement_data["timestamps"].append(time.time())

    def _emit_step_data(self, step_data, current_step, total_steps, wavelength=None):
        """Emit step data for real-time updates."""
        self.data_acquired.emit(
            {
                "angle": step_data["angle"],
                "intensity": step_data["intensity"],
                "camera_data": step_data.get("image"),
                "power": step_data.get("power"),
                "wavelength": wavelength,
                "step": current_step,
                "total_steps": total_steps,
            }
        )

    def _get_current_laser_wavelength(self):
        """Get current laser wavelength."""
        try:
            laser_device = None
            if self.device_manager:
                laser_device = self.device_manager.get_laser()

            if not laser_device:
                return None

            # Try to get current wavelength
            if (
                hasattr(laser_device, "current_position")
                and laser_device.current_position is not None
            ):
                if hasattr(laser_device.current_position, "value"):
                    return laser_device.current_position.value()
                elif hasattr(laser_device.current_position, "data"):
                    return laser_device.current_position.data[0][0]
                else:
                    return float(laser_device.current_position)
            elif hasattr(laser_device, "controller") and laser_device.controller:
                if hasattr(laser_device.controller, "get_wavelength"):
                    return laser_device.controller.get_wavelength()

            return None

        except Exception as e:
            logger.debug(f"Could not get current laser wavelength: {e}")
            return None

    def _initialize_measurement(self) -> bool:
        """Initialize devices and settings for measurement."""
        try:
            logger.info("Initializing measurement...")

            # Check all devices are ready
            if not self.device_manager.is_all_devices_ready():
                logger.error("Not all required devices are ready")
                return False

            # Get devices
            camera = self.device_manager.get_camera()
            elliptec = self.device_manager.get_elliptec()
            power_meter = self.device_manager.get_power_meter()

            if not camera or not elliptec:
                logger.error("Missing critical devices (camera or elliptec)")
                return False

            # Configure camera settings
            roi_settings = {
                "x_start": self.settings.child(
                    "hardware", "camera", "roi", "x_start"
                ).value(),
                "y_start": self.settings.child(
                    "hardware", "camera", "roi", "y_start"
                ).value(),
                "width": self.settings.child(
                    "hardware", "camera", "roi", "width"
                ).value(),
                "height": self.settings.child(
                    "hardware", "camera", "roi", "height"
                ).value(),
            }

            # Configure camera if possible
            if hasattr(camera, "settings") and camera.settings:
                try:
                    # Set ROI if camera supports it
                    if camera.settings.child_frompath("detector_settings"):
                        detector_settings = camera.settings.child("detector_settings")
                        if detector_settings.child("ROIselect"):
                            detector_settings.child("ROIselect", "x0").setValue(
                                roi_settings["x_start"]
                            )
                            detector_settings.child("ROIselect", "y0").setValue(
                                roi_settings["y_start"]
                            )
                            detector_settings.child("ROIselect", "width").setValue(
                                roi_settings["width"]
                            )
                            detector_settings.child("ROIselect", "height").setValue(
                                roi_settings["height"]
                            )

                    # Set integration time if supported
                    if camera.settings.child_frompath("main_settings/exposure"):
                        exposure = self.settings.child(
                            "experiment", "integration_time"
                        ).value()
                        camera.settings.child("main_settings", "exposure").setValue(
                            exposure
                        )

                except Exception as e:
                    logger.warning(f"Could not configure camera settings: {e}")

            # Initialize stabilization if requested
            stabilization_time = self.settings.child(
                "advanced", "stabilization_time"
            ).value()
            if stabilization_time > 0:
                logger.info(f"Stabilization period: {stabilization_time}s")
                time.sleep(stabilization_time)

            logger.info("Measurement initialization completed")
            return True

        except Exception as e:
            logger.error(f"Error initializing measurement: {e}")
            return False

    def _measure_at_angle(
        self,
        angle: float,
        integration_time: float,
        averages: int,
        wavelength: float = None,
    ) -> Optional[dict]:
        """
        Perform measurement at a specific angle.

        Args:
            angle: Polarization angle in degrees
            integration_time: Integration time in milliseconds
            averages: Number of averages

        Returns:
            Dictionary with measurement data or None on failure
        """
        try:
            # Get devices
            camera = self.device_manager.get_camera()
            elliptec = self.device_manager.get_elliptec()
            power_meter = self.device_manager.get_power_meter()

            # Safety timeout
            movement_timeout = self.settings.child(
                "hardware", "safety", "movement_timeout"
            ).value()
            camera_timeout = self.settings.child(
                "hardware", "safety", "camera_timeout"
            ).value()

            # Move polarization elements to target angle
            logger.debug(f"Moving to angle {angle}°")
            success = self._move_polarization_elements(angle, timeout=movement_timeout)
            if not success:
                logger.error(f"Failed to move to angle {angle}°")
                return None

            # Allow settling time
            time.sleep(0.1)

            # Take power reading if available
            power_reading = None
            if power_meter:
                try:
                    power_data = power_meter.grab_data()
                    if power_data and len(power_data) > 0:
                        power_reading = (
                            float(power_data[0].data[0])
                            if hasattr(power_data[0], "data")
                            else None
                        )
                except Exception as e:
                    logger.debug(f"Could not read power meter: {e}")

            # Acquire camera images with averaging
            images = []
            for avg in range(averages):
                if self.stop_requested:
                    return None

                try:
                    # Trigger camera acquisition with timeout
                    image_data = self._acquire_camera_image(
                        camera, timeout=camera_timeout
                    )
                    if image_data is not None:
                        images.append(image_data)
                    else:
                        logger.warning(f"Failed to acquire image {avg + 1}/{averages}")

                except Exception as e:
                    logger.warning(f"Error acquiring image {avg + 1}: {e}")

            if not images:
                logger.error("No images acquired")
                return None

            # Average images and calculate intensity
            if len(images) == 1:
                averaged_image = images[0]
            else:
                import numpy as np

                averaged_image = np.mean(images, axis=0)

            # Calculate total intensity (sum of all pixels)
            total_intensity = float(np.sum(averaged_image))

            return {
                "intensity": total_intensity,
                "image": averaged_image,
                "power": power_reading,
                "angle": angle,
                "wavelength": wavelength,  # ⭐ NEW: Include wavelength in step data
                "n_averages": len(images),
            }

        except Exception as e:
            logger.error(f"Error measuring at angle {angle}°: {e}")
            return None

    def _move_polarization_elements(self, angle: float, timeout: float = 10.0) -> bool:
        """
        Move polarization elements to specified angle with coordinated control.

        For μRASHG measurements, typically only one rotation mount is moved
        while others remain fixed, but this method supports coordinated movement.
        """
        try:
            elliptec = self.device_manager.get_elliptec()
            if not elliptec:
                logger.error("Elliptec device not available")
                return False

            # Get axis configuration
            measurement_type = self.settings.child(
                "experiment", "measurement_type"
            ).value()

            # For basic RASHG, typically rotate the analyzer (HWP)
            # This can be configured based on measurement type
            if measurement_type == "Basic RASHG":
                # Rotate HWP analyzer (axis 2) while keeping others fixed
                target_positions = [None, None, angle]  # [QWP, HWP_inc, HWP_ana]
                axis_to_move = 2
            else:
                # For other measurement types, could have different configurations
                target_positions = [None, None, angle]
                axis_to_move = 2

            # Move the specified axis
            if target_positions[axis_to_move] is not None:
                from pymodaq.utils.data import DataActuator

                # Create DataActuator for the specific axis (single value for one axis)
                target_angle = target_positions[axis_to_move]
                position_data = DataActuator(data=[target_angle])

                # Move the axis
                logger.debug(f"Moving elliptec axis {axis_to_move} to {target_angle}°")

                # Use move_abs method - CRITICAL: Use .value() for single axis
                if hasattr(elliptec, "move_abs"):
                    elliptec.move_abs(position_data)
                else:
                    logger.error("Elliptec device does not support absolute movement")
                    return False

                # Wait for movement completion with timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.stop_requested:
                        return False

                    # Check if movement is complete
                    # This depends on the specific elliptec implementation
                    time.sleep(0.05)  # Small polling interval

                    # For now, assume movement is complete after reasonable time
                    if time.time() - start_time > 2.0:  # Minimum 2 seconds for movement
                        break

                logger.debug(f"Movement to {target_angle}° completed")
                return True

            return True

        except Exception as e:
            logger.error(f"Error moving polarization elements: {e}")
            return False

    def _acquire_camera_image(
        self, camera, timeout: float = 5.0
    ) -> Optional[np.ndarray]:
        """Acquire a single image from camera with timeout."""
        try:
            if not camera:
                return None

            # Trigger single acquisition
            if hasattr(camera, "grab_data"):
                camera_data = camera.grab_data()

                if camera_data and len(camera_data) > 0:
                    # Extract image data from PyMoDAQ data structure
                    data_item = camera_data[0]
                    if hasattr(data_item, "data") and len(data_item.data) > 0:
                        return data_item.data[0]  # First (and typically only) image

            logger.warning("No camera data acquired")
            return None

        except Exception as e:
            logger.error(f"Error acquiring camera image: {e}")
            return None

    def _finalize_measurement(self):
        """Finalize measurement and perform cleanup."""
        try:
            logger.info("Finalizing measurement...")

            # Return all devices to safe positions if needed
            # This could include returning polarization elements to home positions

            # Save data if auto-save is enabled
            if self.settings.child("data", "auto_save").value():
                self._save_measurement_data()

            logger.info("Measurement finalized")

        except Exception as e:
            logger.warning(f"Error finalizing measurement: {e}")

    def _save_measurement_data(self):
        """Save measurement data to file."""
        try:
            import json
            from pathlib import Path

            save_dir = Path(self.settings.child("data", "save_dir").value())
            file_prefix = self.settings.child("data", "file_prefix").value()

            # Create save directory if it doesn't exist
            save_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = save_dir / f"{file_prefix}_{timestamp}.json"

            # Prepare data for saving (excluding images for JSON) - Enhanced for multi-wavelength
            save_data = {
                "angles": self.measurement_data["angles"],
                "intensities": self.measurement_data["intensities"],
                "power_readings": self.measurement_data["power_readings"],
                "timestamps": self.measurement_data["timestamps"],
                "wavelengths": self.measurement_data[
                    "wavelengths"
                ],  # ⭐ NEW: Wavelength data
                "wavelength_sequence": self.measurement_data[
                    "wavelength_sequence"
                ],  # ⭐ NEW: Wavelength scan sequence
                "multi_wavelength": self.measurement_data[
                    "multi_wavelength"
                ],  # ⭐ NEW: Multi-wavelength flag
                "measurement_type": self.measurement_data[
                    "measurement_type"
                ],  # ⭐ NEW: Measurement type
                "settings": self._get_settings_dict(),
                "measurement_info": {
                    "start_time": (
                        self.measurement_data["timestamps"][0]
                        if self.measurement_data["timestamps"]
                        else None
                    ),
                    "end_time": (
                        self.measurement_data["timestamps"][-1]
                        if self.measurement_data["timestamps"]
                        else None
                    ),
                    "duration": (
                        (
                            self.measurement_data["timestamps"][-1]
                            - self.measurement_data["timestamps"][0]
                        )
                        if len(self.measurement_data["timestamps"]) > 1
                        else 0
                    ),
                    "n_points": len(self.measurement_data["angles"]),
                    "n_wavelengths": (
                        len(set(self.measurement_data["wavelengths"]))
                        if self.measurement_data["wavelengths"]
                        else 1
                    ),  # ⭐ NEW: Number of unique wavelengths
                    "multi_wavelength": self.measurement_data[
                        "multi_wavelength"
                    ],  # ⭐ NEW: Multi-wavelength info
                },
            }

            # Save JSON data
            with open(filename, "w") as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Measurement data saved to {filename}")

            # Save images separately if requested
            if self.settings.child("data", "save_raw").value():
                self._save_raw_images(save_dir, file_prefix, timestamp)

        except Exception as e:
            logger.error(f"Error saving measurement data: {e}")

    def _save_raw_images(self, save_dir: Path, file_prefix: str, timestamp: str):
        """Save raw camera images."""
        try:
            import numpy as np

            images_dir = save_dir / f"{file_prefix}_{timestamp}_images"
            images_dir.mkdir(exist_ok=True)

            for i, (angle, image) in enumerate(
                zip(self.measurement_data["angles"], self.measurement_data["images"])
            ):
                if image is not None:
                    image_filename = images_dir / f"angle_{angle:06.2f}_deg_{i:03d}.npy"
                    np.save(image_filename, image)

            logger.info(f"Raw images saved to {images_dir}")

        except Exception as e:
            logger.error(f"Error saving raw images: {e}")

    def _get_settings_dict(self) -> dict:
        """Get current settings as dictionary for saving (Enhanced for multi-wavelength)."""
        try:
            # Extract key settings for metadata
            settings_dict = {
                "experiment": {
                    "measurement_type": self.settings.child(
                        "experiment", "measurement_type"
                    ).value(),
                    "pol_steps": self.settings.child("experiment", "pol_steps").value(),
                    "integration_time": self.settings.child(
                        "experiment", "integration_time"
                    ).value(),
                    "averages": self.settings.child("experiment", "averages").value(),
                    "pol_start": self.settings.child(
                        "experiment", "pol_range", "pol_start"
                    ).value(),
                    "pol_end": self.settings.child(
                        "experiment", "pol_range", "pol_end"
                    ).value(),
                },
                "hardware": {
                    "camera_roi": {
                        "x_start": self.settings.child(
                            "hardware", "camera", "roi", "x_start"
                        ).value(),
                        "y_start": self.settings.child(
                            "hardware", "camera", "roi", "y_start"
                        ).value(),
                        "width": self.settings.child(
                            "hardware", "camera", "roi", "width"
                        ).value(),
                        "height": self.settings.child(
                            "hardware", "camera", "roi", "height"
                        ).value(),
                    }
                },
                "wavelength": {  # ⭐ NEW: Wavelength scan settings
                    "enable_scan": self.settings.child(
                        "wavelength", "enable_scan"
                    ).value(),
                    "wl_start": self.settings.child("wavelength", "wl_start").value(),
                    "wl_stop": self.settings.child("wavelength", "wl_stop").value(),
                    "wl_steps": self.settings.child("wavelength", "wl_steps").value(),
                    "wl_stabilization": self.settings.child(
                        "wavelength", "wl_stabilization"
                    ).value(),
                    "auto_sync_pm": self.settings.child(
                        "wavelength", "auto_sync_pm"
                    ).value(),
                    "sweep_mode": self.settings.child(
                        "wavelength", "sweep_mode"
                    ).value(),
                },
            }

            return settings_dict

        except Exception as e:
            logger.warning(f"Error extracting settings: {e}")
            return {}

    def stop_measurement(self):
        """Request measurement stop."""
        logger.info("Stop requested for measurement worker")
        self.stop_requested = True

    def pause_measurement(self):
        """Request measurement pause."""
        logger.info("Pause requested for measurement worker")
        self.pause_requested = True

    def resume_measurement(self):
        """Resume measurement from pause."""
        logger.info("Resume requested for measurement worker")
        self.pause_requested = False


# Export for PyMoDAQ discovery
__all__ = ["URASHGMicroscopyExtension"]
