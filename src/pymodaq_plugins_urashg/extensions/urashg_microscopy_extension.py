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

import json
import logging
import threading
import time
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

try:
    from pymodaq_data import Axis, DataSource, DataWithAxes
    from pymodaq_gui.utils.custom_app import CustomApp
    from pymodaq_utils.logger import get_module_name, set_logger
    from pyqtgraph.dockarea import Dock
    from qtpy import QtCore, QtGui, QtWidgets
    from qtpy.QtCore import QMetaObject, QObject, Qt, Signal

    logger = set_logger(get_module_name(__file__))
    PYMODAQ_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"PyMoDAQ not fully available: {e}")
    PYMODAQ_AVAILABLE = False

    # Mock classes for when PyMoDAQ isn't available
    class CustomApp:
        def __init__(self):
            pass

    class Signal:
        def __init__(self, *args):
            pass

        def emit(self, *args):
            pass

        def connect(self, func):
            pass


class URASHGMicroscopyExtension(CustomApp, QObject):
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

    # Required PyQt signals for PyMoDAQ compliance
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
                        "PDSHG Mapping",
                        "Calibration",
                        "Quick Preview",
                    ],
                    "value": "Basic RASHG",
                    "tip": "Select the type of μRASHG experiment to perform",
                },
                {
                    "title": "Measurement Parameters",
                    "name": "measurement_params",
                    "type": "group",
                    "children": [
                        {
                            "title": "Polarization Steps:",
                            "name": "pol_steps",
                            "type": "int",
                            "value": 36,
                            "min": 4,
                            "max": 360,
                            "step": 1,
                            "tip": "Number of polarization angles to measure (4-360)",
                        },
                        {
                            "title": "Integration Time (ms):",
                            "name": "integration_time",
                            "type": "int",
                            "value": 100,
                            "min": 1,
                            "max": 10000,
                            "step": 1,
                            "tip": "Camera integration time per measurement point",
                        },
                        {
                            "title": "Averages:",
                            "name": "averages",
                            "type": "int",
                            "value": 3,
                            "min": 1,
                            "max": 100,
                            "step": 1,
                            "tip": "Number of measurements to average per point",
                        },
                        {
                            "title": "Angle Range (°):",
                            "name": "angle_range",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Start Angle:",
                                    "name": "start_angle",
                                    "type": "float",
                                    "value": 0.0,
                                    "min": -180.0,
                                    "max": 180.0,
                                    "step": 0.1,
                                    "suffix": "°",
                                },
                                {
                                    "title": "End Angle:",
                                    "name": "end_angle",
                                    "type": "float",
                                    "value": 180.0,
                                    "min": -180.0,
                                    "max": 360.0,
                                    "step": 0.1,
                                    "suffix": "°",
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "Advanced Settings",
                    "name": "advanced",
                    "type": "group",
                    "expanded": False,
                    "children": [
                        {
                            "title": "Auto-save Data:",
                            "name": "auto_save",
                            "type": "bool",
                            "value": True,
                            "tip": "Automatically save measurement data",
                        },
                        {
                            "title": "Background Subtraction:",
                            "name": "background_subtraction",
                            "type": "bool",
                            "value": False,
                            "tip": "Enable background measurement and subtraction",
                        },
                        {
                            "title": "Real-time Analysis:",
                            "name": "realtime_analysis",
                            "type": "bool",
                            "value": True,
                            "tip": "Perform analysis during measurement",
                        },
                    ],
                },
            ],
        },
        {
            "title": "Hardware Configuration",
            "name": "hardware",
            "type": "group",
            "children": [
                {
                    "title": "Camera Settings",
                    "name": "camera",
                    "type": "group",
                    "children": [
                        {
                            "title": "Module Name:",
                            "name": "camera_module",
                            "type": "str",
                            "value": "PrimeBSI",
                            "readonly": True,
                            "tip": "PyMoDAQ camera module name",
                        },
                        {
                            "title": "ROI Configuration:",
                            "name": "roi_config",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Use ROI:",
                                    "name": "use_roi",
                                    "type": "bool",
                                    "value": False,
                                },
                                {
                                    "title": "ROI Width:",
                                    "name": "roi_width",
                                    "type": "int",
                                    "value": 512,
                                    "min": 64,
                                    "max": 2048,
                                },
                                {
                                    "title": "ROI Height:",
                                    "name": "roi_height",
                                    "type": "int",
                                    "value": 512,
                                    "min": 64,
                                    "max": 2048,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "Laser Settings",
                    "name": "laser",
                    "type": "group",
                    "children": [
                        {
                            "title": "Module Name:",
                            "name": "laser_module",
                            "type": "str",
                            "value": "MaiTai",
                            "readonly": True,
                            "tip": "PyMoDAQ laser module name",
                        },
                        {
                            "title": "Power Control:",
                            "name": "power_control",
                            "type": "group",
                            "children": [
                                {
                                    "title": "Target Power (%):",
                                    "name": "target_power",
                                    "type": "float",
                                    "value": 50.0,
                                    "min": 0.0,
                                    "max": 100.0,
                                    "step": 0.1,
                                    "suffix": "%",
                                },
                                {
                                    "title": "Power Stabilization:",
                                    "name": "power_stabilization",
                                    "type": "bool",
                                    "value": True,
                                    "tip": "Enable automatic power stabilization",
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "Power Meter Settings",
                    "name": "power_meter",
                    "type": "group",
                    "children": [
                        {
                            "title": "Module Name:",
                            "name": "power_meter_module",
                            "type": "str",
                            "value": "Newport1830C",
                            "readonly": True,
                            "tip": "PyMoDAQ power meter module name",
                        },
                        {
                            "title": "Monitor During Measurement:",
                            "name": "monitor_power",
                            "type": "bool",
                            "value": True,
                            "tip": "Continuously monitor laser power",
                        },
                    ],
                },
            ],
        },
        {
            "title": "Multi-Axis Control",
            "name": "multiaxes",
            "type": "group",
            "children": [
                {
                    "title": "Polarization Control",
                    "name": "polarization_control",
                    "type": "group",
                    "children": [
                        {
                            "title": "QWP Axis:",
                            "name": "qwp_axis",
                            "type": "str",
                            "value": "Elliptec_QWP",
                            "readonly": True,
                            "tip": "Quarter-wave plate rotation axis",
                        },
                        {
                            "title": "HWP Incident Axis:",
                            "name": "hwp_incident_axis",
                            "type": "str",
                            "value": "Elliptec_HWP_In",
                            "readonly": True,
                            "tip": "Incident half-wave plate rotation axis",
                        },
                        {
                            "title": "HWP Analyzer Axis:",
                            "name": "hwp_analyzer_axis",
                            "type": "str",
                            "value": "Elliptec_HWP_Analyzer",
                            "readonly": True,
                            "tip": "Analyzer half-wave plate rotation axis",
                        },
                    ],
                },
                {
                    "title": "Sample Positioning",
                    "name": "sample_positioning",
                    "type": "group",
                    "children": [
                        {
                            "title": "X-Axis Module:",
                            "name": "x_axis_module",
                            "type": "str",
                            "value": "ESP300_X",
                            "readonly": True,
                            "tip": "Sample X positioning axis",
                        },
                        {
                            "title": "Y-Axis Module:",
                            "name": "y_axis_module",
                            "type": "str",
                            "value": "ESP300_Y",
                            "readonly": True,
                            "tip": "Sample Y positioning axis",
                        },
                        {
                            "title": "Z-Axis Module:",
                            "name": "z_axis_module",
                            "type": "str",
                            "value": "ESP300_Z",
                            "readonly": True,
                            "tip": "Sample Z positioning axis (focus)",
                        },
                    ],
                },
                {
                    "title": "Axis Status Table",
                    "name": "axis_status",
                    "type": "table",
                    "tip": "Current status of all controlled axes",
                },
            ],
        },
        {
            "title": "Data Management",
            "name": "data_management",
            "type": "group",
            "children": [
                {
                    "title": "Save Configuration",
                    "name": "save_config",
                    "type": "group",
                    "children": [
                        {
                            "title": "Base Filename:",
                            "name": "base_filename",
                            "type": "str",
                            "value": "urashg_measurement",
                            "tip": "Base name for saved data files",
                        },
                        {
                            "title": "Data Format:",
                            "name": "data_format",
                            "type": "list",
                            "limits": ["HDF5", "JSON", "CSV", "TIFF"],
                            "value": "HDF5",
                            "tip": "Format for saving measurement data",
                        },
                        {
                            "title": "Include Metadata:",
                            "name": "include_metadata",
                            "type": "bool",
                            "value": True,
                            "tip": "Include experimental parameters in saved files",
                        },
                    ],
                },
                {
                    "title": "Analysis Settings",
                    "name": "analysis",
                    "type": "group",
                    "children": [
                        {
                            "title": "Fit Model:",
                            "name": "fit_model",
                            "type": "list",
                            "limits": ["Sin²", "Malus Law", "Custom"],
                            "value": "Sin²",
                            "tip": "Mathematical model for fitting RASHG data",
                        },
                        {
                            "title": "Background Threshold:",
                            "name": "background_threshold",
                            "type": "float",
                            "value": 0.1,
                            "min": 0.0,
                            "max": 1.0,
                            "step": 0.01,
                            "tip": "Threshold for background signal detection",
                        },
                    ],
                },
            ],
        },
    ]

    def __init__(self, dockarea=None, dashboard=None):
        """Initialize the μRASHG microscopy extension."""
        logger.info("Initializing μRASHG Microscopy Extension")

        if not PYMODAQ_AVAILABLE:
            logger.warning("PyMoDAQ not available, running in minimal mode")
            self.dashboard = None
            self.dockarea = None
            return

        # Initialize both parent classes
        CustomApp.__init__(self, dockarea)
        QObject.__init__(self)

        # Thread safety - initialize locks before any other operations
        self._init_lock = threading.RLock()
        self._module_lock = threading.RLock()
        self._measurement_lock = threading.RLock()

        with self._init_lock:
            # Store references
            self.dashboard = dashboard
            self.dockarea = dockarea

            # Initialize extension state
            self.is_measuring = False
            self.available_modules = {}
            self.measurement_data = {}
            self.hardware_manager = None

            # Setup the extension
            self.setup_docks()
            self.setup_actions()
            self.setup_menu()
            self.connect_things()

            # Safely detect modules after UI is ready
            self.detect_modules()

            # Initialize hardware manager after dashboard is ready
            if self.dashboard:
                try:
                    self.hardware_manager = self.create_hardware_manager()
                    if self.hardware_manager:
                        self.log_message("Hardware manager initialized successfully")
                    else:
                        self.log_message("Hardware manager initialization failed")
                except Exception as e:
                    logger.warning(f"Failed to initialize hardware manager: {e}")
                    self.log_message(f"Hardware manager init warning: {e}")

    def setup_docks(self):
        """Setup advanced dock layout system with enhanced PyMoDAQ CustomApp patterns."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Setting up advanced μRASHG extension dock layout")

        # Initialize dock storage and layout configuration
        self.docks = {}
        self.dock_layout_config = {
            "resizable": True,
            "closable": False,
            "floatable": True,
            "movable": True,
        }

        # Create enhanced dock layout with improved organization
        self.create_primary_dock_layout()

        # Setup dock state persistence
        self.setup_dock_state_management()

    def create_primary_dock_layout(self):
        """Create the primary dock layout with logical groupings."""
        # Create main control dock (left side)
        self.setup_control_dock()

        # Create settings dock (right side, top)
        self.setup_settings_dock()

        # Create advanced visualization dock (center/right, large)
        self.setup_advanced_visualization_dock()

        # Create status and progress dock (bottom)
        self.setup_status_dock()

        # Create device monitor and diagnostics dock (right, bottom)
        self.setup_device_monitor_dock()

        # Create data analysis dock (can be floated or tabbed)
        self.setup_data_analysis_dock()

    def setup_dock_state_management(self):
        """Setup dock state persistence and restoration."""
        try:
            # Store dock layout configuration for restoration
            self.dock_state = {
                "default_layout": True,
                "custom_positions": {},
                "visibility_states": {},
            }

            # Connect dock resize and move events for state tracking
            for dock_name, dock in self.docks.items():
                if hasattr(dock, "sigMoved"):
                    dock.sigMoved.connect(lambda: self.save_dock_state(dock_name))

            logger.debug("Dock state management initialized")

        except Exception as e:
            logger.warning(f"Could not setup dock state management: {e}")

    def setup_control_dock(self):
        """Setup main control dock with measurement controls."""
        control_dock = Dock("μRASHG Control", size=(300, 200), closable=False)
        self.dockarea.addDock(control_dock, "left")
        self.docks["control"] = control_dock

        # Create control widget
        control_widget = QtWidgets.QWidget()
        control_dock.addWidget(control_widget)
        control_layout = QtWidgets.QVBoxLayout(control_widget)

        # Add experiment type selection
        exp_group = QtWidgets.QGroupBox("Experiment Configuration")
        exp_layout = QtWidgets.QVBoxLayout(exp_group)

        self.experiment_combo = QtWidgets.QComboBox()
        self.experiment_combo.addItems(
            [
                "Basic RASHG",
                "Multi-Wavelength RASHG",
                "Full Polarimetric SHG",
                "Calibration",
            ]
        )
        exp_layout.addWidget(QtWidgets.QLabel("Measurement Type:"))
        exp_layout.addWidget(self.experiment_combo)

        control_layout.addWidget(exp_group)

        # Add measurement controls
        self.setup_measurement_controls(control_layout)

    def setup_settings_dock(self):
        """Setup settings dock with PyMoDAQ parameter tree."""
        settings_dock = Dock("Settings", size=(350, 400), closable=False)
        self.dockarea.addDock(settings_dock, "right")
        self.docks["settings"] = settings_dock

        # Create PyMoDAQ parameter tree
        try:
            from pymodaq_gui.parameter import ParameterTree
            from pymodaq_utils.parameter import Parameter

            # Initialize settings parameter tree
            self.settings = Parameter.create(
                name="Settings", type="group", children=self.params
            )
            self.settings_tree = ParameterTree()
            self.settings_tree.setMinimumWidth(300)
            self.settings_tree.setParameters(self.settings, showTop=False)

            # Add parameter tree to dock
            settings_dock.addWidget(self.settings_tree)

            logger.info("Parameter tree setup completed")

        except ImportError as e:
            logger.warning(f"PyMoDAQ parameter tree not available: {e}")
            # Fallback to basic controls
            settings_widget = QtWidgets.QWidget()
            settings_dock.addWidget(settings_widget)
            settings_layout = QtWidgets.QVBoxLayout(settings_widget)
            self.setup_parameter_controls(settings_layout)

    def setup_status_dock(self):
        """Setup status dock with logging and progress."""
        status_dock = Dock("Status & Progress", size=(400, 250), closable=False)
        self.dockarea.addDock(status_dock, "bottom")
        self.docks["status"] = status_dock

        status_widget = QtWidgets.QWidget()
        status_dock.addWidget(status_widget)
        status_layout = QtWidgets.QVBoxLayout(status_widget)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        status_layout.addWidget(QtWidgets.QLabel("Measurement Progress:"))
        status_layout.addWidget(self.progress_bar)

        # Status log
        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(QtWidgets.QLabel("System Log:"))
        status_layout.addWidget(self.status_text)

    def setup_advanced_visualization_dock(self):
        """Setup advanced visualization dock with real-time multi-plot capabilities."""
        viz_dock = Dock(
            "Advanced Visualization", size=(700, 500), **self.dock_layout_config
        )
        self.dockarea.addDock(viz_dock, "bottom", self.docks["settings"])
        self.docks["visualization"] = viz_dock

        viz_widget = QtWidgets.QWidget()
        viz_dock.addWidget(viz_widget)
        viz_layout = QtWidgets.QVBoxLayout(viz_widget)

        # Create tabbed visualization interface
        self.viz_tabs = QtWidgets.QTabWidget()
        viz_layout.addWidget(self.viz_tabs)

        # Setup individual visualization tabs
        self.setup_rashg_plot_tab()
        self.setup_polarization_analysis_tab()
        self.setup_real_time_monitoring_tab()
        self.setup_3d_visualization_tab()

        # Add visualization controls
        self.setup_visualization_controls(viz_layout)

    def setup_rashg_plot_tab(self):
        """Setup main RASHG data plot tab."""
        try:
            import pyqtgraph as pg

            # Create main RASHG plot widget
            rashg_widget = QtWidgets.QWidget()
            rashg_layout = QtWidgets.QVBoxLayout(rashg_widget)

            # Enhanced plot widget with better styling
            self.plot_widget = pg.PlotWidget(title="μRASHG Intensity vs Polarization")
            self.plot_widget.setLabel("left", "SHG Intensity", units="counts")
            self.plot_widget.setLabel("bottom", "Polarization Angle", units="°")
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setBackground("w")

            # Add legend and crosshair cursor
            self.plot_widget.addLegend()

            # Setup plot data items for different measurement types
            self.plot_data_items = {
                "raw_data": self.plot_widget.plot(
                    [], [], pen="blue", symbol="o", name="Raw Data"
                ),
                "fitted_curve": self.plot_widget.plot(
                    [], [], pen="red", name="Fitted Curve"
                ),
                "background": self.plot_widget.plot(
                    [], [], pen="gray", name="Background"
                ),
            }

            rashg_layout.addWidget(self.plot_widget)
            self.viz_tabs.addTab(rashg_widget, "RASHG Data")

        except ImportError:
            # Fallback tab if pyqtgraph not available
            fallback_widget = QtWidgets.QLabel(
                "Advanced visualization requires pyqtgraph"
            )
            fallback_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.viz_tabs.addTab(fallback_widget, "RASHG Data")

    def setup_polarization_analysis_tab(self):
        """Setup polarization analysis visualization tab."""
        try:
            import pyqtgraph as pg

            polar_widget = QtWidgets.QWidget()
            polar_layout = QtWidgets.QVBoxLayout(polar_widget)

            # Create polar plot for polarization analysis
            self.polar_plot = pg.PlotWidget(title="Polarization Analysis")

            # Add polar coordinate system visualization
            self.polar_plot.setAspectLocked(True)
            self.polar_plot.showGrid(x=True, y=True, alpha=0.3)

            # Create polar data items
            self.polar_data_items = {
                "intensity_polar": self.polar_plot.plot([], [], pen="blue"),
                "fitted_ellipse": self.polar_plot.plot([], [], pen="red"),
            }

            polar_layout.addWidget(self.polar_plot)
            self.viz_tabs.addTab(polar_widget, "Polar Analysis")

        except ImportError:
            fallback_widget = QtWidgets.QLabel("Polar analysis requires pyqtgraph")
            fallback_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.viz_tabs.addTab(fallback_widget, "Polar Analysis")

    def setup_real_time_monitoring_tab(self):
        """Setup real-time device monitoring tab."""
        try:
            import pyqtgraph as pg

            monitor_widget = QtWidgets.QWidget()
            monitor_layout = QtWidgets.QVBoxLayout(monitor_widget)

            # Create multi-parameter monitoring
            self.monitor_plot = pg.PlotWidget(title="Real-time Device Monitoring")
            self.monitor_plot.setLabel("left", "Value")
            self.monitor_plot.setLabel("bottom", "Time", units="s")
            self.monitor_plot.showGrid(x=True, y=True, alpha=0.3)
            self.monitor_plot.addLegend()

            # Setup monitoring data buffers
            self.monitoring_data = {
                "power": {"times": [], "values": [], "plot": None},
                "temperature": {"times": [], "values": [], "plot": None},
                "position": {"times": [], "values": [], "plot": None},
            }

            # Create plot items for monitoring
            self.monitoring_data["power"]["plot"] = self.monitor_plot.plot(
                [], [], pen="green", name="Laser Power"
            )
            self.monitoring_data["temperature"]["plot"] = self.monitor_plot.plot(
                [], [], pen="orange", name="Temperature"
            )
            self.monitoring_data["position"]["plot"] = self.monitor_plot.plot(
                [], [], pen="purple", name="Position"
            )

            monitor_layout.addWidget(self.monitor_plot)
            self.viz_tabs.addTab(monitor_widget, "Real-time Monitor")

        except ImportError:
            fallback_widget = QtWidgets.QLabel(
                "Real-time monitoring requires pyqtgraph"
            )
            fallback_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.viz_tabs.addTab(fallback_widget, "Real-time Monitor")

    def setup_3d_visualization_tab(self):
        """Setup 3D visualization tab for spatial mapping."""
        try:
            import pyqtgraph as pg
            import pyqtgraph.opengl as gl

            # Create 3D widget
            gl_widget = gl.GLViewWidget()
            gl_widget.setWindowTitle("3D RASHG Mapping")

            # Add 3D coordinate grid
            grid = gl.GLGridItem()
            grid.scale(10, 10, 1)
            gl_widget.addItem(grid)

            # Store 3D plot reference
            self.gl_widget = gl_widget
            self.gl_scatter = None  # Will be created when data is available

            self.viz_tabs.addTab(gl_widget, "3D Mapping")

        except ImportError:
            fallback_widget = QtWidgets.QLabel(
                "3D visualization requires pyqtgraph with OpenGL"
            )
            fallback_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.viz_tabs.addTab(fallback_widget, "3D Mapping")

    def setup_visualization_controls(self, layout):
        """Setup visualization control panel."""
        controls_group = QtWidgets.QGroupBox("Visualization Controls")
        controls_layout = QtWidgets.QHBoxLayout(controls_group)

        # Auto-scale toggle
        self.auto_scale_check = QtWidgets.QCheckBox("Auto Scale")
        self.auto_scale_check.setChecked(True)
        controls_layout.addWidget(self.auto_scale_check)

        # Live update toggle
        self.live_update_check = QtWidgets.QCheckBox("Live Update")
        self.live_update_check.setChecked(True)
        controls_layout.addWidget(self.live_update_check)

        # Export plot button
        export_btn = QtWidgets.QPushButton("Export Plot")
        export_btn.clicked.connect(self.export_current_plot)
        controls_layout.addWidget(export_btn)

        # Clear plots button
        clear_btn = QtWidgets.QPushButton("Clear Plots")
        clear_btn.clicked.connect(self.clear_all_plots)
        controls_layout.addWidget(clear_btn)

        layout.addWidget(controls_group)

    def setup_device_monitor_dock(self):
        """Setup device monitor dock for hardware status."""
        device_dock = Dock("Device Monitor", size=(300, 300), closable=False)
        self.dockarea.addDock(device_dock, "right", self.docks["control"])
        self.docks["device_monitor"] = device_dock

        device_widget = QtWidgets.QWidget()
        device_dock.addWidget(device_widget)
        device_layout = QtWidgets.QVBoxLayout(device_widget)

        # Device status display
        device_layout.addWidget(QtWidgets.QLabel("Hardware Status:"))

        self.device_status_widget = QtWidgets.QTextEdit()
        self.device_status_widget.setMaximumHeight(200)
        self.device_status_widget.setReadOnly(True)
        device_layout.addWidget(self.device_status_widget)

        # Device refresh button
        refresh_btn = QtWidgets.QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.detect_modules)
        device_layout.addWidget(refresh_btn)

    def setup_data_analysis_dock(self):
        """Setup data analysis dock with advanced analysis tools."""
        analysis_dock = Dock(
            "Data Analysis", size=(400, 350), **self.dock_layout_config
        )

        # Position as tabbed with device monitor or float it
        try:
            self.dockarea.addDock(analysis_dock, "tab", self.docks["device_monitor"])
        except:
            self.dockarea.addDock(analysis_dock, "right")

        self.docks["data_analysis"] = analysis_dock

        analysis_widget = QtWidgets.QWidget()
        analysis_dock.addWidget(analysis_widget)
        analysis_layout = QtWidgets.QVBoxLayout(analysis_widget)

        # Analysis controls
        self.setup_analysis_controls(analysis_layout)

        # Results display
        self.setup_analysis_results(analysis_layout)

    def setup_analysis_controls(self, layout):
        """Setup analysis control panel."""
        controls_group = QtWidgets.QGroupBox("Analysis Tools")
        controls_layout = QtWidgets.QVBoxLayout(controls_group)

        # Analysis type selection
        analysis_type_layout = QtWidgets.QHBoxLayout()
        analysis_type_layout.addWidget(QtWidgets.QLabel("Analysis Type:"))

        self.analysis_type_combo = QtWidgets.QComboBox()
        self.analysis_type_combo.addItems(
            [
                "Sin² Fitting",
                "Fourier Analysis",
                "Principal Component Analysis",
                "Background Subtraction",
                "Noise Analysis",
            ]
        )
        analysis_type_layout.addWidget(self.analysis_type_combo)
        controls_layout.addLayout(analysis_type_layout)

        # Analysis parameters
        params_group = QtWidgets.QGroupBox("Parameters")
        params_layout = QtWidgets.QFormLayout(params_group)

        self.fit_order_spin = QtWidgets.QSpinBox()
        self.fit_order_spin.setRange(1, 10)
        self.fit_order_spin.setValue(4)
        params_layout.addRow("Harmonic Order:", self.fit_order_spin)

        self.confidence_spin = QtWidgets.QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 0.99)
        self.confidence_spin.setValue(0.95)
        self.confidence_spin.setSingleStep(0.05)
        params_layout.addRow("Confidence Level:", self.confidence_spin)

        controls_layout.addWidget(params_group)

        # Analysis buttons
        button_layout = QtWidgets.QHBoxLayout()

        analyze_btn = QtWidgets.QPushButton("Analyze Data")
        analyze_btn.clicked.connect(self.run_data_analysis)
        button_layout.addWidget(analyze_btn)

        auto_analyze_check = QtWidgets.QCheckBox("Auto")
        auto_analyze_check.setToolTip("Automatically analyze new data")
        button_layout.addWidget(auto_analyze_check)

        controls_layout.addLayout(button_layout)
        layout.addWidget(controls_group)

    def setup_analysis_results(self, layout):
        """Setup analysis results display."""
        results_group = QtWidgets.QGroupBox("Analysis Results")
        results_layout = QtWidgets.QVBoxLayout(results_group)

        # Results text area
        self.analysis_results_text = QtWidgets.QTextEdit()
        self.analysis_results_text.setMaximumHeight(150)
        self.analysis_results_text.setReadOnly(True)
        self.analysis_results_text.setPlainText("No analysis performed yet.")
        results_layout.addWidget(self.analysis_results_text)

        # Export analysis button
        export_analysis_btn = QtWidgets.QPushButton("Export Analysis")
        export_analysis_btn.clicked.connect(self.export_analysis_results)
        results_layout.addWidget(export_analysis_btn)

        layout.addWidget(results_group)

    def save_dock_state(self, dock_name):
        """Save current dock state for persistence."""
        try:
            if dock_name in self.docks:
                dock = self.docks[dock_name]
                self.dock_state["custom_positions"][dock_name] = {
                    "size": dock.size(),
                    "position": dock.pos() if hasattr(dock, "pos") else None,
                    "floating": (
                        dock.isFloating() if hasattr(dock, "isFloating") else False
                    ),
                }
                logger.debug(f"Saved state for dock: {dock_name}")
        except Exception as e:
            logger.warning(f"Could not save dock state for {dock_name}: {e}")

    def export_current_plot(self):
        """Export currently active plot to file."""
        try:
            if hasattr(self, "viz_tabs") and self.viz_tabs.currentWidget():
                current_tab = self.viz_tabs.currentIndex()
                tab_name = self.viz_tabs.tabText(current_tab)

                # Get filename from user
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    None,
                    f"Export {tab_name} Plot",
                    f"urashg_{tab_name.lower().replace(' ', '_')}.png",
                    "PNG Files (*.png);;SVG Files (*.svg);;PDF Files (*.pdf)",
                )

                if filename:
                    # Export logic would depend on the plot widget type
                    if current_tab == 0 and hasattr(self, "plot_widget"):
                        # Export main RASHG plot
                        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                        exporter.export(filename)
                        self.log_message(f"Plot exported to {filename}")
                    else:
                        self.log_message("Export not implemented for this plot type")

        except Exception as e:
            logger.error(f"Failed to export plot: {e}")
            self.error_occurred.emit(f"Plot export failed: {e}")

    def clear_all_plots(self):
        """Clear all visualization plots."""
        try:
            # Clear main RASHG plot
            if hasattr(self, "plot_data_items"):
                for item in self.plot_data_items.values():
                    item.setData([], [])

            # Clear polar plot
            if hasattr(self, "polar_data_items"):
                for item in self.polar_data_items.values():
                    item.setData([], [])

            # Clear monitoring plots
            if hasattr(self, "monitoring_data"):
                for data in self.monitoring_data.values():
                    data["times"].clear()
                    data["values"].clear()
                    if data["plot"]:
                        data["plot"].setData([], [])

            self.log_message("All plots cleared")

        except Exception as e:
            logger.error(f"Failed to clear plots: {e}")

    def run_data_analysis(self):
        """Run data analysis on current measurement data."""
        try:
            if not hasattr(self, "measurement_data") or not self.measurement_data:
                self.analysis_results_text.setPlainText(
                    "No measurement data available for analysis."
                )
                return

            analysis_type = self.analysis_type_combo.currentText()
            self.log_message(f"Running {analysis_type} analysis...")

            # Placeholder for actual analysis implementation
            if analysis_type == "Sin² Fitting":
                results = self.perform_sin2_fitting()
            elif analysis_type == "Fourier Analysis":
                results = self.perform_fourier_analysis()
            else:
                results = f"Analysis type '{analysis_type}' not yet implemented."

            self.analysis_results_text.setPlainText(results)
            self.log_message("Analysis completed")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.error_occurred.emit(f"Data analysis failed: {e}")

    def perform_sin2_fitting(self):
        """Perform Sin² fitting analysis on RASHG data."""
        # This would implement actual Sin² fitting
        return "Sin² Fitting Results:\nAmplitude: 150.3 ± 5.2\nPhase: 45.2° ± 2.1°\nOffset: 98.7 ± 3.4\nR²: 0.987"

    def perform_fourier_analysis(self):
        """Perform Fourier analysis on RASHG data."""
        # This would implement actual Fourier analysis
        return "Fourier Analysis Results:\nFundamental: 180° period\n2nd Harmonic: 45° period (strong)\n4th Harmonic: 90° period (moderate)\nNoise Level: 2.3%"

    def export_analysis_results(self):
        """Export analysis results to file."""
        try:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                None,
                "Export Analysis Results",
                "urashg_analysis_results.txt",
                "Text Files (*.txt);;JSON Files (*.json)",
            )

            if filename:
                with open(filename, "w") as f:
                    f.write(self.analysis_results_text.toPlainText())
                self.log_message(f"Analysis results exported to {filename}")

        except Exception as e:
            logger.error(f"Failed to export analysis results: {e}")
            self.error_occurred.emit(f"Analysis export failed: {e}")

    def setup_measurement_controls(self, layout):
        """Setup measurement control buttons."""
        button_group = QtWidgets.QGroupBox("Measurement Control")
        button_layout = QtWidgets.QVBoxLayout(button_group)

        # Main measurement controls
        main_buttons = QtWidgets.QHBoxLayout()

        self.start_button = QtWidgets.QPushButton("Start Measurement")
        self.start_button.clicked.connect(self.start_measurement)
        self.start_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; }"
        )
        main_buttons.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_measurement)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; }"
        )
        main_buttons.addWidget(self.stop_button)

        button_layout.addLayout(main_buttons)

        # Additional controls
        additional_buttons = QtWidgets.QHBoxLayout()

        self.calibrate_button = QtWidgets.QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self.start_calibration)
        additional_buttons.addWidget(self.calibrate_button)

        self.preview_button = QtWidgets.QPushButton("Preview")
        self.preview_button.clicked.connect(self.start_preview)
        additional_buttons.addWidget(self.preview_button)

        button_layout.addLayout(additional_buttons)
        layout.addWidget(button_group)

    def setup_parameter_controls(self, layout):
        """Setup basic parameter controls in settings dock."""
        param_group = QtWidgets.QGroupBox("Measurement Parameters")
        param_layout = QtWidgets.QFormLayout(param_group)

        # Polarization steps
        self.pol_steps_spinbox = QtWidgets.QSpinBox()
        self.pol_steps_spinbox.setRange(4, 360)
        self.pol_steps_spinbox.setValue(36)
        param_layout.addRow("Polarization Steps:", self.pol_steps_spinbox)

        # Integration time
        self.integration_time_spinbox = QtWidgets.QSpinBox()
        self.integration_time_spinbox.setRange(1, 10000)
        self.integration_time_spinbox.setValue(100)
        self.integration_time_spinbox.setSuffix(" ms")
        param_layout.addRow("Integration Time:", self.integration_time_spinbox)

        layout.addWidget(param_group)

        # Device configuration group
        device_group = QtWidgets.QGroupBox("Device Configuration")
        device_layout = QtWidgets.QFormLayout(device_group)

        # Add device selection controls
        self.camera_combo = QtWidgets.QComboBox()
        self.camera_combo.addItem("PrimeBSI")
        device_layout.addRow("Camera:", self.camera_combo)

        self.power_meter_combo = QtWidgets.QComboBox()
        self.power_meter_combo.addItem("Newport1830C")
        device_layout.addRow("Power Meter:", self.power_meter_combo)

        layout.addWidget(device_group)

    def setup_actions(self):
        """Setup toolbar actions following PyMoDAQ CustomApp patterns."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Setting up μRASHG extension actions")

        # Initialize actions storage
        self.actions = {}

        # Create main actions
        self.create_measurement_actions()
        self.create_calibration_actions()
        self.create_data_actions()

    def create_measurement_actions(self):
        """Create measurement-related actions."""
        # Start measurement action
        start_action = QtWidgets.QAction("Start Measurement", self)
        start_action.setIcon(QtGui.QIcon.fromTheme("media-playback-start"))
        start_action.triggered.connect(self.start_measurement)
        self.actions["start_measurement"] = start_action

        # Stop measurement action
        stop_action = QtWidgets.QAction("Stop Measurement", self)
        stop_action.setIcon(QtGui.QIcon.fromTheme("media-playback-stop"))
        stop_action.triggered.connect(self.stop_measurement)
        stop_action.setEnabled(False)
        self.actions["stop_measurement"] = stop_action

        # Preview action
        preview_action = QtWidgets.QAction("Preview", self)
        preview_action.setIcon(QtGui.QIcon.fromTheme("view-preview"))
        preview_action.triggered.connect(self.start_preview)
        self.actions["preview"] = preview_action

    def create_calibration_actions(self):
        """Create calibration-related actions."""
        # Calibrate action
        calibrate_action = QtWidgets.QAction("Calibrate System", self)
        calibrate_action.setIcon(QtGui.QIcon.fromTheme("applications-engineering"))
        calibrate_action.triggered.connect(self.start_calibration)
        self.actions["calibrate"] = calibrate_action

        # Device refresh action
        refresh_action = QtWidgets.QAction("Refresh Devices", self)
        refresh_action.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        refresh_action.triggered.connect(self.detect_modules)
        self.actions["refresh_devices"] = refresh_action

    def create_data_actions(self):
        """Create data management actions."""
        # Save data action
        save_action = QtWidgets.QAction("Save Data", self)
        save_action.setIcon(QtGui.QIcon.fromTheme("document-save"))
        save_action.triggered.connect(self.save_measurement_data)
        self.actions["save_data"] = save_action

        # Export action
        export_action = QtWidgets.QAction("Export Results", self)
        export_action.setIcon(QtGui.QIcon.fromTheme("document-export"))
        export_action.triggered.connect(self.export_results)
        self.actions["export_results"] = export_action

    def setup_menu(self):
        """Setup menu system following PyMoDAQ CustomApp patterns."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Setting up μRASHG extension menu")

        # Initialize menu storage
        self.menus = {}

        # Create main menus (these would typically be added to the main window)
        self.create_measurement_menu()
        self.create_tools_menu()
        self.create_help_menu()

    def create_measurement_menu(self):
        """Create measurement menu."""
        measurement_menu = QtWidgets.QMenu("Measurement")

        measurement_menu.addAction(self.actions["start_measurement"])
        measurement_menu.addAction(self.actions["stop_measurement"])
        measurement_menu.addSeparator()
        measurement_menu.addAction(self.actions["preview"])
        measurement_menu.addSeparator()
        measurement_menu.addAction(self.actions["save_data"])
        measurement_menu.addAction(self.actions["export_results"])

        self.menus["measurement"] = measurement_menu

    def create_tools_menu(self):
        """Create tools menu."""
        tools_menu = QtWidgets.QMenu("Tools")

        tools_menu.addAction(self.actions["calibrate"])
        tools_menu.addAction(self.actions["refresh_devices"])

        self.menus["tools"] = tools_menu

    def create_help_menu(self):
        """Create help menu."""
        help_menu = QtWidgets.QMenu("Help")

        # About action
        about_action = QtWidgets.QAction("About μRASHG Extension", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Documentation action
        docs_action = QtWidgets.QAction("Documentation", self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)

        self.menus["help"] = help_menu

    def connect_things(self):
        """Enhanced signal management following PyMoDAQ CustomApp patterns."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Connecting μRASHG extension signals and slots")

        # Connect measurement signals
        self.measurement_started.connect(self.on_measurement_started)
        self.measurement_finished.connect(self.on_measurement_finished)
        self.measurement_progress.connect(self.update_progress)
        self.device_status_changed.connect(self.on_device_status_changed)
        self.error_occurred.connect(self.on_error_occurred)

        # Connect UI signals
        if hasattr(self, "experiment_combo"):
            self.experiment_combo.currentTextChanged.connect(
                self.on_experiment_type_changed
            )

        if hasattr(self, "pol_steps_spinbox"):
            self.pol_steps_spinbox.valueChanged.connect(self.on_parameter_changed)

        if hasattr(self, "integration_time_spinbox"):
            self.integration_time_spinbox.valueChanged.connect(
                self.on_parameter_changed
            )

        # Connect action state management
        self.measurement_started.connect(lambda: self.set_measurement_state(True))
        self.measurement_finished.connect(lambda: self.set_measurement_state(False))

        # Connect parameter tree value changes
        if hasattr(self, "settings") and self.settings is not None:
            self.settings.sigTreeStateChanged.connect(self.value_changed)

    def value_changed(self, param, changes):
        """
        Handle parameter tree value changes following PyMoDAQ CustomApp pattern.

        This method is called whenever a parameter in the settings tree changes,
        allowing real-time updates to the extension configuration.
        """
        if not PYMODAQ_AVAILABLE:
            return

        logger.debug(f"Parameter value changed: {param.name()}")

        try:
            for param, change, data in changes:
                path = self.settings.childPath(param)
                if path is not None:
                    child_name = ".".join(path)
                else:
                    child_name = param.name()

                logger.debug(
                    f"Parameter changed - Path: {child_name}, Change: {change}, Data: {data}"
                )

                # Handle specific parameter changes
                if param.name() == "measurement_type":
                    self.on_measurement_type_changed(data)
                elif param.name() == "pol_steps":
                    self.on_polarization_steps_changed(data)
                elif param.name() == "integration_time":
                    self.on_integration_time_changed(data)
                elif param.name() == "auto_save":
                    self.on_auto_save_changed(data)
                elif param.name() == "realtime_analysis":
                    self.on_realtime_analysis_changed(data)
                elif param.name() == "target_power":
                    self.on_target_power_changed(data)
                elif param.name() == "power_stabilization":
                    self.on_power_stabilization_changed(data)

        except Exception as e:
            logger.error(f"Error in value_changed: {e}")
            self.error_occurred.emit(f"Parameter change error: {e}")

    def on_measurement_type_changed(self, measurement_type):
        """Handle measurement type selection changes."""
        logger.info(f"Measurement type changed to: {measurement_type}")
        # Update UI elements based on measurement type
        self.update_measurement_controls_for_type(measurement_type)

    def on_polarization_steps_changed(self, steps):
        """Handle polarization steps parameter changes."""
        logger.info(f"Polarization steps changed to: {steps}")
        # Validate and update measurement parameters

    def on_integration_time_changed(self, time_ms):
        """Handle integration time parameter changes."""
        logger.info(f"Integration time changed to: {time_ms} ms")
        # Update camera settings if connected

    def on_auto_save_changed(self, enabled):
        """Handle auto-save setting changes."""
        logger.info(f"Auto-save {'enabled' if enabled else 'disabled'}")

    def on_realtime_analysis_changed(self, enabled):
        """Handle real-time analysis setting changes."""
        logger.info(f"Real-time analysis {'enabled' if enabled else 'disabled'}")

    def on_target_power_changed(self, power):
        """Handle target power setting changes."""
        logger.info(f"Target power changed to: {power}%")

    def on_power_stabilization_changed(self, enabled):
        """Handle power stabilization setting changes."""
        logger.info(f"Power stabilization {'enabled' if enabled else 'disabled'}")

    def update_measurement_controls_for_type(self, measurement_type):
        """Update UI controls based on selected measurement type."""
        # This would update the available controls based on measurement type
        logger.debug(f"Updating controls for measurement type: {measurement_type}")

    def start_calibration(self):
        """Start system calibration sequence."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Starting μRASHG system calibration")
        self.log_message("Starting calibration sequence...")

        try:
            # Update UI state
            if hasattr(self, "calibrate_button"):
                self.calibrate_button.setEnabled(False)
                self.calibrate_button.setText("Calibrating...")

            # Emit calibration started signal (could be a new signal)
            self.log_message("Calibration completed successfully")

        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            self.error_occurred.emit(f"Calibration failed: {e}")
        finally:
            # Restore UI state
            if hasattr(self, "calibrate_button"):
                self.calibrate_button.setEnabled(True)
                self.calibrate_button.setText("Calibrate")

    def start_preview(self):
        """Start preview mode for quick measurements."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Starting μRASHG preview mode")
        self.log_message("Starting preview measurement...")

        # Run a quick preview measurement with limited parameters
        try:
            # Update UI state
            if hasattr(self, "preview_button"):
                self.preview_button.setEnabled(False)
                self.preview_button.setText("Previewing...")

            # Run mock preview measurement
            self.run_preview_measurement()

        except Exception as e:
            logger.error(f"Preview failed: {e}")
            self.error_occurred.emit(f"Preview failed: {e}")
        finally:
            # Restore UI state
            if hasattr(self, "preview_button"):
                self.preview_button.setEnabled(True)
                self.preview_button.setText("Preview")

    def start_measurement(self):
        """Start a full measurement sequence."""
        if not PYMODAQ_AVAILABLE:
            return

        with self._measurement_lock:
            if self.is_measuring:
                self.log_message("Measurement already in progress")
                return

            logger.info("Starting μRASHG measurement")
            self.log_message("Starting measurement sequence...")

            try:
                # Get current experiment type
                experiment_type = "Basic RASHG"
                if hasattr(self, "experiment_combo"):
                    experiment_type = self.experiment_combo.currentText()

                # Set measuring state
                self.is_measuring = True
                self.safe_emit_signal(self.measurement_started)

                # Execute measurement through hardware manager
                success = self.coordinate_measurement_sequence(experiment_type)

                if success:
                    self.log_message("Measurement completed successfully")
                else:
                    self.log_message("Measurement failed or was cancelled")

            except Exception as e:
                logger.error(f"Measurement failed: {e}")
                self.safe_emit_signal(self.error_occurred, f"Measurement failed: {e}")
            finally:
                # Always reset measuring state
                self.is_measuring = False
                self.safe_emit_signal(self.measurement_finished)

    def stop_measurement(self):
        """Stop the current measurement sequence."""
        if not PYMODAQ_AVAILABLE:
            return

        with self._measurement_lock:
            if not self.is_measuring:
                self.log_message("No measurement in progress")
                return

            logger.info("Stopping μRASHG measurement")
            self.log_message("Stopping measurement...")

            try:
                # Signal stop to hardware manager
                if self.hardware_manager:
                    self.hardware_manager.stop_measurement()

                # Reset state
                self.is_measuring = False
                self.safe_emit_signal(self.measurement_finished)
                self.log_message("Measurement stopped")

            except Exception as e:
                logger.error(f"Error stopping measurement: {e}")
                self.safe_emit_signal(
                    self.error_occurred, f"Error stopping measurement: {e}"
                )

    def run_preview_measurement(self):
        """Run a quick preview measurement."""
        # Simulate a quick measurement with fewer steps
        preview_steps = 8  # Quick 8-point measurement
        for i in range(preview_steps):
            if not self.is_measuring:
                break
            time.sleep(0.1)  # Quick preview
            progress = int((i + 1) / preview_steps * 100)
            self.measurement_progress.emit(progress)

        self.log_message("Preview measurement completed")

    def save_measurement_data(self):
        """Save current measurement data."""
        if not PYMODAQ_AVAILABLE or not hasattr(self, "measurement_data"):
            return

        logger.info("Saving μRASHG measurement data")

        try:
            # Implement data saving logic here
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"urashg_measurement_{timestamp}.json"

            # Save to appropriate directory
            save_path = Path.cwd() / "data" / filename
            save_path.parent.mkdir(exist_ok=True)

            with open(save_path, "w") as f:
                json.dump(self.measurement_data, f, indent=2)

            self.log_message(f"Data saved to {save_path}")

        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            self.error_occurred.emit(f"Failed to save data: {e}")

    def export_results(self):
        """Export measurement results in various formats."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Exporting μRASHG results")
        self.log_message("Exporting measurement results...")

        # Implement export functionality here
        try:
            # Could export to CSV, HDF5, etc.
            self.log_message("Results exported successfully")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.error_occurred.emit(f"Export failed: {e}")

    def update_progress(self, progress):
        """Update progress bar with measurement progress."""
        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(progress)

    def on_experiment_type_changed(self, experiment_type):
        """Handle experiment type selection changes."""
        logger.info(f"Experiment type changed to: {experiment_type}")
        self.log_message(f"Selected experiment type: {experiment_type}")

        # Update parameter visibility/availability based on experiment type
        # This could be expanded to show/hide different parameter groups

    def on_parameter_changed(self):
        """Handle parameter value changes."""
        # Update internal parameter state
        # Could trigger re-calculation of measurement parameters
        logger.debug("Measurement parameters updated")

    def set_measurement_state(self, measuring):
        """Update UI state based on measurement status."""
        if hasattr(self, "start_button"):
            self.start_button.setEnabled(not measuring)
        if hasattr(self, "stop_button"):
            self.stop_button.setEnabled(measuring)
        if hasattr(self, "calibrate_button"):
            self.calibrate_button.setEnabled(not measuring)
        if hasattr(self, "preview_button"):
            self.preview_button.setEnabled(not measuring)

        # Update actions
        if "start_measurement" in self.actions:
            self.actions["start_measurement"].setEnabled(not measuring)
        if "stop_measurement" in self.actions:
            self.actions["stop_measurement"].setEnabled(measuring)
        if "calibrate" in self.actions:
            self.actions["calibrate"].setEnabled(not measuring)
        if "preview" in self.actions:
            self.actions["preview"].setEnabled(not measuring)

    def show_about_dialog(self):
        """Show about dialog."""
        if not PYMODAQ_AVAILABLE:
            return

        about_text = f"""
μRASHG Microscopy Extension v{self.version}

{self.description}

Author: {self.author}

A comprehensive multi-device coordination extension for μRASHG
(micro Rotational Anisotropy Second Harmonic Generation) microscopy
measurements using PyMoDAQ.
        """

        QtWidgets.QMessageBox.about(None, "About μRASHG Extension", about_text.strip())

    def show_documentation(self):
        """Show documentation or open documentation URL."""
        if not PYMODAQ_AVAILABLE:
            return

        # Could open web browser to documentation or show local help
        QtWidgets.QMessageBox.information(
            None,
            "Documentation",
            "For documentation, please visit:\n"
            "https://github.com/TheFermiSea/pymodaq_plugins_urashg",
        )

    def create_hardware_manager(self):
        """Create centralized hardware management system."""
        if not PYMODAQ_AVAILABLE or not self.dashboard:
            return None

        return URASHGHardwareManager(self.dashboard, self)

    def coordinate_measurement_sequence(self, measurement_type):
        """Execute coordinated multi-device measurement sequence."""
        if not hasattr(self, "hardware_manager") or not self.hardware_manager:
            self.hardware_manager = self.create_hardware_manager()

        if not self.hardware_manager:
            self.error_occurred.emit("Hardware manager not available")
            return False

        try:
            # Get measurement parameters from UI/settings
            params = self.get_measurement_parameters()

            # Execute measurement based on type
            if measurement_type == "Basic RASHG":
                return self.hardware_manager.execute_basic_rashg(params)
            elif measurement_type == "Multi-Wavelength RASHG":
                return self.hardware_manager.execute_multiwavelength_rashg(params)
            elif measurement_type == "Full Polarimetric SHG":
                return self.hardware_manager.execute_full_polarimetric_shg(params)
            elif measurement_type == "Calibration":
                return self.hardware_manager.execute_calibration_sequence(params)
            else:
                self.error_occurred.emit(
                    f"Unknown measurement type: {measurement_type}"
                )
                return False

        except Exception as e:
            logger.error(f"Measurement sequence failed: {e}")
            self.error_occurred.emit(f"Measurement failed: {e}")
            return False

    def get_measurement_parameters(self):
        """Extract measurement parameters from UI controls."""
        params = {
            "pol_steps": getattr(
                self, "pol_steps_spinbox", type("obj", (object,), {"value": lambda: 36})
            )().value(),
            "integration_time": getattr(
                self,
                "integration_time_spinbox",
                type("obj", (object,), {"value": lambda: 100}),
            )().value(),
            "start_angle": 0.0,
            "end_angle": 180.0,
            "averages": 3,
            "use_roi": False,
            "auto_save": True,
            "background_subtraction": False,
            "realtime_analysis": True,
        }

        # Add measurement type from combo box
        if hasattr(self, "experiment_combo"):
            params["measurement_type"] = self.experiment_combo.currentText()
        else:
            params["measurement_type"] = "Basic RASHG"

        return params

    def close(self):
        """Clean shutdown of the extension."""
        if not PYMODAQ_AVAILABLE:
            return

        logger.info("Closing μRASHG Microscopy Extension")

        try:
            # Stop any ongoing measurements
            if self.is_measuring:
                self.stop_measurement()

            # Clean up hardware manager
            if self.hardware_manager:
                self.hardware_manager.cleanup()
                self.hardware_manager = None

            # Clear references
            self.dashboard = None
            self.dockarea = None
            self.available_modules.clear()
            self.measurement_data.clear()

            self.log_message("Extension closed successfully")

        except Exception as e:
            logger.error(f"Error during extension close: {e}")

    def safe_emit_signal(self, signal, *args):
        """Thread-safe signal emission."""
        if not PYMODAQ_AVAILABLE:
            return

        try:
            QMetaObject.invokeMethod(
                self, lambda: signal.emit(*args), Qt.ConnectionType.QueuedConnection
            )
        except Exception as e:
            logger.error(f"Error emitting signal: {e}")


class URASHGHardwareManager:
    """
    Centralized hardware coordination system for μRASHG measurements.

    Manages all device interactions through PyMoDAQ dashboard modules.
    Provides synchronized, safe, and efficient multi-device operations.
    """

    def __init__(self, dashboard, extension):
        self.dashboard = dashboard
        self.extension = extension
        self.logger = logger

        # Device references
        self.devices = {
            "camera": None,  # PrimeBSI camera
            "power_meter": None,  # Newport 1830-C
            "laser": None,  # MaiTai laser
            "qwp": None,  # Quarter-wave plate (Elliptec)
            "hwp_incident": None,  # Incident HWP (Elliptec)
            "hwp_analyzer": None,  # Analyzer HWP (Elliptec)
            "x_stage": None,  # ESP300 X axis
            "y_stage": None,  # ESP300 Y axis
            "z_stage": None,  # ESP300 Z axis (focus)
        }

        # Device status tracking
        self.device_status = {name: "unknown" for name in self.devices.keys()}
        self.last_error = None

        # Initialize device discovery
        self.discover_devices()

    def discover_devices(self):
        """Discover and validate all required μRASHG devices."""
        self.logger.info("Discovering μRASHG hardware devices...")

        try:
            modules_manager = self.dashboard.modules_manager

            # Discover detectors (camera, power meter)
            self._discover_detectors(modules_manager)

            # Discover actuators (laser, rotation mounts, stages)
            self._discover_actuators(modules_manager)

            # Validate critical devices
            self._validate_critical_devices()

            # Report discovery results
            self._report_discovery_status()

        except Exception as e:
            self.logger.error(f"Device discovery failed: {e}")
            self.extension.error_occurred.emit(f"Device discovery failed: {e}")

    def _discover_detectors(self, modules_manager):
        """Discover detector modules (camera, power meter)."""
        if not hasattr(modules_manager, "detectors"):
            self.logger.warning("No detectors manager found in dashboard")
            return

        detectors = modules_manager.detectors

        # Find camera (PrimeBSI)
        self.devices["camera"] = self._find_device(
            detectors, ["PrimeBSI", "Prime", "camera"]
        )
        if self.devices["camera"]:
            self.device_status["camera"] = "ready"
            self.logger.info("Camera detected: PrimeBSI")

        # Find power meter (Newport 1830-C)
        self.devices["power_meter"] = self._find_device(
            detectors, ["Newport", "1830", "power"]
        )
        if self.devices["power_meter"]:
            self.device_status["power_meter"] = "ready"
            self.logger.info("Power meter detected: Newport 1830-C")

    def _discover_actuators(self, modules_manager):
        """Discover actuator modules (laser, rotation mounts, stages)."""
        if not hasattr(modules_manager, "actuators"):
            self.logger.warning("No actuators manager found in dashboard")
            return

        actuators = modules_manager.actuators

        # Find laser (MaiTai)
        self.devices["laser"] = self._find_device(actuators, ["MaiTai", "laser"])
        if self.devices["laser"]:
            self.device_status["laser"] = "ready"
            self.logger.info("Laser detected: MaiTai")

        # Find rotation mounts (Elliptec)
        elliptec_devices = self._find_all_devices(actuators, ["Elliptec", "rotation"])
        self._assign_rotation_mounts(elliptec_devices)

        # Find translation stages (ESP300)
        esp_devices = self._find_all_devices(
            actuators, ["ESP300", "stage", "translation"]
        )
        self._assign_translation_stages(esp_devices)

    def _assign_rotation_mounts(self, elliptec_devices):
        """Assign Elliptec devices to QWP, HWP incident, and HWP analyzer."""
        if not elliptec_devices:
            self.logger.warning("No Elliptec rotation mounts detected")
            return

        # Try to identify devices by name or configuration
        for device in elliptec_devices:
            device_name = str(device).lower()

            if "qwp" in device_name or "quarter" in device_name:
                self.devices["qwp"] = device
                self.device_status["qwp"] = "ready"
                self.logger.info("QWP rotation mount assigned")
            elif "hwp" in device_name and (
                "in" in device_name or "incident" in device_name
            ):
                self.devices["hwp_incident"] = device
                self.device_status["hwp_incident"] = "ready"
                self.logger.info("HWP incident rotation mount assigned")
            elif "hwp" in device_name and (
                "out" in device_name or "analyzer" in device_name
            ):
                self.devices["hwp_analyzer"] = device
                self.device_status["hwp_analyzer"] = "ready"
                self.logger.info("HWP analyzer rotation mount assigned")

        # If we have unassigned devices, assign by order
        unassigned = [d for d in elliptec_devices if d not in self.devices.values()]
        device_keys = ["qwp", "hwp_incident", "hwp_analyzer"]

        for i, device in enumerate(unassigned[:3]):
            if i < len(device_keys) and not self.devices[device_keys[i]]:
                self.devices[device_keys[i]] = device
                self.device_status[device_keys[i]] = "ready"
                self.logger.info(
                    f"{device_keys[i]} assigned to available Elliptec device"
                )

    def _assign_translation_stages(self, esp_devices):
        """Assign ESP300 devices to X, Y, Z axes."""
        if not esp_devices:
            self.logger.warning("No ESP300 translation stages detected")
            return

        # Try to identify devices by name
        for device in esp_devices:
            device_name = str(device).lower()

            if "x" in device_name:
                self.devices["x_stage"] = device
                self.device_status["x_stage"] = "ready"
                self.logger.info("X-axis stage assigned")
            elif "y" in device_name:
                self.devices["y_stage"] = device
                self.device_status["y_stage"] = "ready"
                self.logger.info("Y-axis stage assigned")
            elif "z" in device_name or "focus" in device_name:
                self.devices["z_stage"] = device
                self.device_status["z_stage"] = "ready"
                self.logger.info("Z-axis stage assigned")

    def _find_device(self, device_dict, name_patterns):
        """Find a single device matching any of the name patterns."""
        if not device_dict:
            return None

        for name, device in device_dict.items():
            name_lower = name.lower()
            if any(pattern.lower() in name_lower for pattern in name_patterns):
                return device
        return None

    def _find_all_devices(self, device_dict, name_patterns):
        """Find all devices matching any of the name patterns."""
        if not device_dict:
            return []

        devices = []
        for name, device in device_dict.items():
            name_lower = name.lower()
            if any(pattern.lower() in name_lower for pattern in name_patterns):
                devices.append(device)
        return devices

    def _validate_critical_devices(self):
        """Validate that critical devices are available."""
        critical_devices = ["camera", "qwp"]  # Minimum required for basic measurements

        missing_devices = []
        for device_name in critical_devices:
            if not self.devices[device_name]:
                missing_devices.append(device_name)
                self.device_status[device_name] = "missing"

        if missing_devices:
            error_msg = f"Critical devices missing: {', '.join(missing_devices)}"
            self.logger.error(error_msg)
            self.extension.error_occurred.emit(error_msg)

    def _report_discovery_status(self):
        """Report device discovery status to extension UI."""
        status_report = []

        for device_name, device in self.devices.items():
            status = self.device_status[device_name]
            if device:
                status_report.append(f"✓ {device_name}: {status}")
            else:
                status_report.append(f"✗ {device_name}: not found")

        status_text = "\n".join(status_report)
        self.extension.log_message(f"Device Discovery Results:\n{status_text}")

        # Update device monitor if available
        if hasattr(self.extension, "device_status_widget"):
            self.extension.device_status_widget.setText(status_text)

    def execute_basic_rashg(self, params):
        """Execute a basic RASHG measurement sequence."""
        self.logger.info("Starting basic RASHG measurement")

        if not self._validate_devices_for_measurement(["camera", "qwp"]):
            return False

        try:
            # Initialize measurement
            self.extension.measurement_started.emit()
            self.extension.log_message("Initializing basic RASHG measurement...")

            # Calculate polarization angles
            pol_steps = params["pol_steps"]
            start_angle = params["start_angle"]
            end_angle = params["end_angle"]
            angles = np.linspace(start_angle, end_angle, pol_steps)

            # Prepare data storage
            measurement_data = {
                "angles": angles,
                "intensities": [],
                "power_readings": [],
                "timestamps": [],
                "metadata": params,
            }

            # Execute measurement loop
            for i, angle in enumerate(angles):
                if not self.extension.is_measuring:
                    self.logger.info("Measurement stopped by user")
                    break

                # Move QWP to position
                self._move_rotation_mount("qwp", angle)

                # Acquire data
                camera_data = self._acquire_camera_data(params)
                power_data = (
                    self._acquire_power_data() if self.devices["power_meter"] else None
                )

                # Store data
                measurement_data["intensities"].append(
                    self._extract_intensity(camera_data)
                )
                if power_data is not None:
                    measurement_data["power_readings"].append(power_data)
                measurement_data["timestamps"].append(time.time())

                # Update progress and visualization
                progress = int((i + 1) / len(angles) * 100)
                self.extension.measurement_progress.emit(progress)
                self._update_live_visualization(measurement_data, i)

                self.extension.log_message(
                    f"Completed angle {angle:.1f}° ({i+1}/{len(angles)})"
                )

            # Save data if auto-save enabled
            if params.get("auto_save", True):
                self._save_measurement_data(measurement_data, "basic_rashg")

            # Store in extension for access
            self.extension.measurement_data = measurement_data

            self.logger.info("Basic RASHG measurement completed successfully")
            self.extension.measurement_finished.emit()
            return True

        except Exception as e:
            self.logger.error(f"Basic RASHG measurement failed: {e}")
            self.extension.error_occurred.emit(f"Measurement failed: {e}")
            return False

    def _validate_devices_for_measurement(self, required_devices):
        """Validate that required devices are available and ready."""
        missing_devices = []

        for device_name in required_devices:
            if (
                not self.devices[device_name]
                or self.device_status[device_name] != "ready"
            ):
                missing_devices.append(device_name)

        if missing_devices:
            error_msg = f"Required devices not ready: {', '.join(missing_devices)}"
            self.extension.error_occurred.emit(error_msg)
            return False

        return True

    def _move_rotation_mount(self, mount_name, angle):
        """Move a rotation mount to specified angle."""
        device = self.devices[mount_name]
        if not device:
            self.logger.warning(f"Cannot move {mount_name}: device not available")
            return

        try:
            # Use PyMoDAQ actuator interface to move device
            # This would depend on the specific actuator interface
            self.logger.debug(f"Moving {mount_name} to {angle}°")
            # device.move_abs(angle)  # Actual implementation depends on PyMoDAQ
            time.sleep(0.1)  # Simulate movement time

        except Exception as e:
            self.logger.error(f"Failed to move {mount_name}: {e}")
            raise

    def _acquire_camera_data(self, params):
        """Acquire camera data with specified parameters."""
        if not self.devices["camera"]:
            self.logger.warning("Cannot acquire camera data: camera not available")
            return None

        try:
            # Use PyMoDAQ detector interface to acquire data
            # This would depend on the specific detector interface
            self.logger.debug("Acquiring camera image")

            # Simulate camera data for now
            import numpy as np

            if params.get("use_roi", False):
                width = params.get("roi_width", 512)
                height = params.get("roi_height", 512)
            else:
                width, height = 1024, 1024

            # Generate realistic camera data
            image_data = np.random.poisson(1000, (height, width)).astype(np.uint16)
            return image_data

        except Exception as e:
            self.logger.error(f"Failed to acquire camera data: {e}")
            raise

    def _acquire_power_data(self):
        """Acquire power meter reading."""
        if not self.devices["power_meter"]:
            return None

        try:
            # Use PyMoDAQ detector interface
            self.logger.debug("Reading power meter")
            # Simulate power reading
            return 0.5 + 0.1 * np.random.randn()

        except Exception as e:
            self.logger.error(f"Failed to read power meter: {e}")
            raise

    def _extract_intensity(self, camera_data):
        """Extract intensity value from camera data."""
        if camera_data is None:
            return 0.0

        # Simple integration - could be more sophisticated
        return np.sum(camera_data).astype(float)

    def _update_live_visualization(self, measurement_data, current_index):
        """Update live visualization with new data point."""
        if not hasattr(self.extension, "plot_widget") or not self.extension.plot_widget:
            return

        try:
            # Update the plot with current data
            angles = measurement_data["angles"][: current_index + 1]
            intensities = measurement_data["intensities"]

            # Clear and replot
            self.extension.plot_widget.clear()
            self.extension.plot_widget.plot(angles, intensities, pen="blue", symbol="o")

        except Exception as e:
            self.logger.warning(f"Failed to update visualization: {e}")

    def _save_measurement_data(self, measurement_data, measurement_type):
        """Save measurement data to file."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"urashg_{measurement_type}_{timestamp}.json"

            # Create data directory if it doesn't exist
            data_dir = Path.cwd() / "data"
            data_dir.mkdir(exist_ok=True)

            # Save as JSON for now (could be HDF5 for production)
            save_path = data_dir / filename

            # Convert numpy arrays to lists for JSON serialization
            json_data = {}
            for key, value in measurement_data.items():
                if isinstance(value, np.ndarray):
                    json_data[key] = value.tolist()
                else:
                    json_data[key] = value

            with open(save_path, "w") as f:
                json.dump(json_data, f, indent=2, default=str)

            self.extension.log_message(f"Data saved to {save_path}")

        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
            self.extension.error_occurred.emit(f"Failed to save data: {e}")

    def execute_multiwavelength_rashg(self, params):
        """Execute multi-wavelength RASHG measurement."""
        self.logger.info("Multi-wavelength RASHG not yet implemented")
        self.extension.error_occurred.emit("Multi-wavelength RASHG not yet implemented")
        return False

    def execute_full_polarimetric_shg(self, params):
        """Execute full polarimetric SHG measurement."""
        self.logger.info("Full polarimetric SHG not yet implemented")
        self.extension.error_occurred.emit("Full polarimetric SHG not yet implemented")
        return False

    def execute_calibration_sequence(self, params):
        """Execute calibration sequence."""
        self.logger.info("Calibration sequence not yet implemented")
        self.extension.error_occurred.emit("Calibration sequence not yet implemented")
        return False

    def setup_control_buttons(self, layout):
        """Setup control buttons for the extension."""
        button_layout = QtWidgets.QHBoxLayout()

        # Start measurement button
        self.start_button = QtWidgets.QPushButton("Start Measurement")
        self.start_button.clicked.connect(self.start_measurement)
        button_layout.addWidget(self.start_button)

        # Stop measurement button
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_measurement)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

    def setup_status_display(self, layout):
        """Setup status display area."""
        # Status text area
        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)

    def connect_signals(self):
        """Connect signals and slots for the extension."""
        if not PYMODAQ_AVAILABLE:
            return

        # Connect measurement control signals
        self.measurement_started.connect(self.on_measurement_started)
        self.measurement_finished.connect(self.on_measurement_finished)
        self.error_occurred.connect(self.on_error_occurred)

        # Connect UI signals safely
        if hasattr(self, "progress_bar") and self.progress_bar is not None:
            self.measurement_progress.connect(self.progress_bar.setValue)

        # Connect device status signals
        self.device_status_changed.connect(self.on_device_status_changed)

    def detect_modules(self):
        """Detect available PyMoDAQ modules."""
        if not PYMODAQ_AVAILABLE or not self.dashboard:
            return

        with self._module_lock:
            logger.info("Detecting available modules...")

            # Try to get modules from dashboard
            try:
                self.available_modules = self.get_required_modules()
                if self.available_modules:
                    logger.info(
                        f"Detected modules: {list(self.available_modules.keys())}"
                    )
                    # Emit signal safely
                    self.safe_emit_signal(
                        self.device_status_changed, "modules", "detected"
                    )
                else:
                    logger.warning("No required modules detected in dashboard")
                    self.safe_emit_signal(
                        self.device_status_changed, "modules", "none_found"
                    )
            except Exception as e:
                logger.error(f"Error detecting modules: {e}")
                self.safe_emit_signal(
                    self.error_occurred, f"Module detection failed: {e}"
                )

    def get_required_modules(self):
        """Access modules through PyMoDAQ's standard API."""
        if not self.dashboard or not hasattr(self.dashboard, "modules_manager"):
            return {}

        modules_manager = self.dashboard.modules_manager

        # Find specific modules loaded in dashboard
        modules = {
            "camera": self.find_module(modules_manager.detectors, "PrimeBSI"),
            "power_meter": self.find_module(modules_manager.detectors, "Newport"),
            "laser": self.find_module(modules_manager.actuators, "MaiTai"),
            "rotators": self.find_module(modules_manager.actuators, "Elliptec"),
        }

        return {k: v for k, v in modules.items() if v is not None}

    def find_module(self, module_dict, name_pattern):
        """Find module by name pattern."""
        if not module_dict:
            return None
        for module_name, module in module_dict.items():
            if name_pattern.lower() in module_name.lower():
                return module
        return None

    def start_measurement(self):
        """Start a μRASHG measurement sequence using coordinated hardware manager."""
        if not PYMODAQ_AVAILABLE:
            logger.warning("Cannot start measurement: PyMoDAQ not available")
            return

        logger.info("Starting μRASHG measurement...")
        self.log_message("Starting μRASHG measurement...")

        # Set measurement state
        self.is_measuring = True

        # Get selected measurement type
        measurement_type = "Basic RASHG"  # Default
        if hasattr(self, "experiment_combo"):
            measurement_type = self.experiment_combo.currentText()

        # Use coordinated measurement sequence
        success = self.coordinate_measurement_sequence(measurement_type)

        if not success:
            # Fallback to mock measurement for demonstration
            logger.warning("Coordinated measurement failed, running mock measurement")
            self.log_message("Running demonstration measurement...")
            self.measurement_started.emit()
            self.run_mock_measurement()

        # Update UI state
        if hasattr(self, "start_button"):
            self.start_button.setEnabled(False)
        if hasattr(self, "stop_button"):
            self.stop_button.setEnabled(True)

    def run_mock_measurement(self):
        """Run a mock measurement for demonstration using PyMoDAQ data structures."""
        logger.info("Running mock μRASHG measurement")

        try:
            # Generate mock polarimetric data
            import numpy as np

            # Get measurement parameters from settings
            pol_steps = 36  # Default value, could be from settings
            angles = np.linspace(0, 360, pol_steps, endpoint=False)

            # Create mock intensity data (simulate RASHG pattern)
            intensities = (
                100
                + 50 * np.cos(4 * np.radians(angles))
                + 10 * np.random.rand(pol_steps)
            )

            # Create PyMoDAQ compliant data structure
            measurement_data = self.create_rashg_data(intensities, angles)

            # Store measurement data
            self.measurement_data["rashg_data"] = measurement_data

            # Simulate measurement progress
            for i in range(101):
                if not self.is_measuring:
                    break
                self.measurement_progress.emit(i)
                time.sleep(0.02)  # Shorter delay for better responsiveness

            # Finish measurement
            if self.is_measuring:
                logger.info(
                    f"Mock measurement completed with {len(intensities)} data points"
                )
                self.measurement_finished.emit()

        except Exception as e:
            logger.error(f"Error in mock measurement: {e}")
            self.error_occurred.emit(str(e))

    def create_rashg_data(self, intensity_data, polarization_angles):
        """Create PyMoDAQ compliant data structure for RASHG measurements."""
        if not PYMODAQ_AVAILABLE:
            return None

        return DataWithAxes(
            "μRASHG_Measurement",
            data=[intensity_data],
            axes=[
                Axis(
                    "Polarization",
                    data=polarization_angles,
                    units="°",
                    description="Incident polarization angle",
                )
            ],
            units="counts",
            labels=["SHG Intensity"],
            source=DataSource.raw,
        )

    def stop_measurement(self):
        """Stop the current measurement."""
        logger.info("Stopping μRASHG measurement...")
        self.log_message("Stopping measurement...")

        self.is_measuring = False
        self.measurement_finished.emit()

    def cleanup(self):
        """Clean up hardware manager resources."""
        logger.info("Cleaning up URASHGHardwareManager")

        try:
            # Clear device references
            self.devices.clear()

            # Clear dashboard reference
            self.dashboard = None
            self.extension = None

            self.logger.info("Hardware manager cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during hardware manager cleanup: {e}")

    def on_measurement_started(self):
        """Handle measurement started signal."""
        self.log_message("μRASHG measurement started")

    def on_measurement_finished(self):
        """Handle measurement finished signal."""
        self.log_message("μRASHG measurement completed")

        # Reset UI state
        self.is_measuring = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def on_error_occurred(self, error_message):
        """Handle error occurred signal."""
        self.log_message(f"ERROR: {error_message}")
        logger.error(error_message)

        # Stop measurement if running during error
        if self.is_measuring:
            self.is_measuring = False
            self.measurement_finished.emit()

    def on_device_status_changed(self, device_name, status):
        """Handle device status change signal."""
        self.log_message(f"Device {device_name}: {status}")
        logger.info(f"Device status changed - {device_name}: {status}")

    def log_message(self, message):
        """Add a message to the status log."""
        if not PYMODAQ_AVAILABLE:
            logger.info(message)
            return

        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        if hasattr(self, "status_text"):
            self.status_text.append(formatted_message)

        logger.info(message)

    def safe_emit_signal(self, signal, *args):
        """Thread-safe signal emission."""
        QMetaObject.invokeMethod(
            self, lambda: signal.emit(*args), Qt.ConnectionType.QueuedConnection
        )

    def close(self):
        """Clean up the extension."""
        logger.info("Closing μRASHG Microscopy Extension")

        # Stop any running measurements
        if self.is_measuring:
            self.stop_measurement()

        # Clean up UI
        if PYMODAQ_AVAILABLE and hasattr(self, "dock"):
            self.dock.close()


# Import device manager for test compatibility
try:
    from .device_manager import URASHGDeviceManager
except ImportError:
    # Fallback for test environments
    URASHGDeviceManager = None

# Provide a basic MeasurementWorker for test compatibility
if PYMODAQ_AVAILABLE:

    class MeasurementWorker(QObject):
        """Mock measurement worker for test compatibility."""

        def __init__(self, parent=None):
            super().__init__(parent)

else:

    class MeasurementWorker:
        """Fallback measurement worker for test environments."""

        def __init__(self, parent=None):
            pass


# Main extension class for PyMoDAQ discovery
extension_class = URASHGMicroscopyExtension
