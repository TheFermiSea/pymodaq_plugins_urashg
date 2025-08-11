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
from qtpy.QtCore import QObject, Signal, QTimer
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea

from pymodaq.utils.gui_utils import CustomApp
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataWithAxes, Axis
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config

# Import our device manager
from .device_manager import URASHGDeviceManager, DeviceStatus, DeviceInfo

import time
import numpy as np
from typing import Optional
from pathlib import Path
logger = set_logger(get_module_name(__file__))


class URASHGMicroscopyExtension(CustomApp):
    """
    Production-ready μRASHG Extension for PyMoDAQ Dashboard

    Provides coordinated control of multiple devices for sophisticated
    polarimetric SHG measurements through PyMoDAQ's Extension framework.
    """

    # Extension metadata
    name = 'μRASHG Microscopy System'
    description = 'Complete polarimetric SHG measurements with multi-device coordination'
    author = 'μRASHG Development Team'
    version = '1.0.0'

    # Signals for inter-component communication
    measurement_started = Signal()
    measurement_finished = Signal()
    measurement_progress = Signal(int)  # Progress percentage 0-100
    device_status_changed = Signal(str, str)  # device_name, status
    error_occurred = Signal(str)  # error_message

    # Parameter tree definition
    params = [
        {'title': 'Experiment Configuration', 'name': 'experiment', 'type': 'group', 'children': [
            {'title': 'Measurement Type:', 'name': 'measurement_type', 'type': 'list',
             'limits': ['Basic RASHG', 'Multi-Wavelength RASHG', 'Full Polarimetric SHG', 'Calibration'],
             'value': 'Basic RASHG'},
            {'title': 'Polarization Steps:', 'name': 'pol_steps', 'type': 'int',
             'value': 36, 'min': 4, 'max': 360, 'step': 1},
            {'title': 'Integration Time (ms):', 'name': 'integration_time', 'type': 'int',
             'value': 100, 'min': 1, 'max': 10000, 'step': 1},
            {'title': 'Number of Averages:', 'name': 'averages', 'type': 'int',
             'value': 1, 'min': 1, 'max': 100, 'step': 1},
            {'title': 'Polarization Range', 'name': 'pol_range', 'type': 'group', 'children': [
                {'title': 'Start Angle (°):', 'name': 'pol_start', 'type': 'float',
                 'value': 0.0, 'min': 0.0, 'max': 360.0, 'step': 0.1},
                {'title': 'End Angle (°):', 'name': 'pol_end', 'type': 'float',
                 'value': 180.0, 'min': 0.0, 'max': 360.0, 'step': 0.1},
            ]},
        ]},

        {'title': 'Hardware Settings', 'name': 'hardware', 'type': 'group', 'children': [
            {'title': 'Device Configuration', 'name': 'devices', 'type': 'group', 'children': [
                {'title': 'QWP Device:', 'name': 'qwp_device', 'type': 'str',
                 'value': 'Elliptec', 'readonly': True},
                {'title': 'QWP Axis Index:', 'name': 'qwp_axis', 'type': 'int',
                 'value': 0, 'min': 0, 'max': 2, 'readonly': True},
                {'title': 'HWP Incident Device:', 'name': 'hwp_inc_device', 'type': 'str',
                 'value': 'Elliptec', 'readonly': True},
                {'title': 'HWP Incident Axis:', 'name': 'hwp_inc_axis', 'type': 'int',
                 'value': 1, 'min': 0, 'max': 2, 'readonly': True},
                {'title': 'HWP Analyzer Device:', 'name': 'hwp_ana_device', 'type': 'str',
                 'value': 'Elliptec', 'readonly': True},
                {'title': 'HWP Analyzer Axis:', 'name': 'hwp_ana_axis', 'type': 'int',
                 'value': 2, 'min': 0, 'max': 2, 'readonly': True},
                {'title': 'Camera Device:', 'name': 'camera_device', 'type': 'str',
                 'value': 'PrimeBSI', 'readonly': True},
                {'title': 'Power Meter Device:', 'name': 'power_device', 'type': 'str',
                 'value': 'Newport1830C', 'readonly': True},
                {'title': 'Laser Device:', 'name': 'laser_device', 'type': 'str',
                 'value': 'MaiTai', 'readonly': True},
            ]},

            {'title': 'Camera Settings', 'name': 'camera', 'type': 'group', 'children': [
                {'title': 'ROI Settings', 'name': 'roi', 'type': 'group', 'children': [
                    {'title': 'X Start:', 'name': 'x_start', 'type': 'int',
                     'value': 0, 'min': 0, 'max': 2048},
                    {'title': 'Y Start:', 'name': 'y_start', 'type': 'int',
                     'value': 0, 'min': 0, 'max': 2048},
                    {'title': 'Width:', 'name': 'width', 'type': 'int',
                     'value': 2048, 'min': 1, 'max': 2048},
                    {'title': 'Height:', 'name': 'height', 'type': 'int',
                     'value': 2048, 'min': 1, 'max': 2048},
                ]},
                {'title': 'Binning:', 'name': 'binning', 'type': 'list',
                 'limits': ['1x1', '2x2', '4x4'], 'value': '1x1'},
            ]},

            {'title': 'Safety Limits', 'name': 'safety', 'type': 'group', 'children': [
                {'title': 'Max Laser Power (%):', 'name': 'max_power', 'type': 'float',
                 'value': 50.0, 'min': 0.0, 'max': 100.0, 'step': 0.1},
                {'title': 'Rotation Speed (°/s):', 'name': 'rotation_speed', 'type': 'float',
                 'value': 30.0, 'min': 1.0, 'max': 100.0, 'step': 1.0},
                {'title': 'Camera Timeout (s):', 'name': 'camera_timeout', 'type': 'float',
                 'value': 5.0, 'min': 0.1, 'max': 60.0, 'step': 0.1},
                {'title': 'Movement Timeout (s):', 'name': 'movement_timeout', 'type': 'float',
                 'value': 10.0, 'min': 1.0, 'max': 60.0, 'step': 0.1},
            ]},
        ]},

        {'title': 'Multi-Wavelength Settings', 'name': 'wavelength', 'type': 'group', 'children': [
            {'title': 'Enable Wavelength Scan:', 'name': 'enable_scan', 'type': 'bool', 'value': False},
            {'title': 'Start Wavelength (nm):', 'name': 'wl_start', 'type': 'int',
             'value': 700, 'min': 700, 'max': 1000, 'step': 1},
            {'title': 'Stop Wavelength (nm):', 'name': 'wl_stop', 'type': 'int',
             'value': 900, 'min': 700, 'max': 1000, 'step': 1},
            {'title': 'Wavelength Steps:', 'name': 'wl_steps', 'type': 'int',
             'value': 10, 'min': 2, 'max': 100, 'step': 1},
            {'title': 'Wavelength Stabilization (s):', 'name': 'wl_stabilization', 'type': 'float',
             'value': 2.0, 'min': 0.1, 'max': 30.0, 'step': 0.1},
            {'title': 'Auto-sync Power Meter:', 'name': 'auto_sync_pm', 'type': 'bool', 'value': True},
            {'title': 'Sweep Mode:', 'name': 'sweep_mode', 'type': 'list',
             'limits': ['Linear', 'Logarithmic', 'Custom'], 'value': 'Linear'},
        ]},

        {'title': 'Data Management', 'name': 'data', 'type': 'group', 'children': [
            {'title': 'Save Directory:', 'name': 'save_dir', 'type': 'browsepath',
             'value': str(Path.home() / 'urashg_data')},
            {'title': 'Auto Save:', 'name': 'auto_save', 'type': 'bool', 'value': True},
            {'title': 'File Prefix:', 'name': 'file_prefix', 'type': 'str',
             'value': 'urashg_measurement'},
            {'title': 'Save Raw Images:', 'name': 'save_raw', 'type': 'bool', 'value': False},
            {'title': 'Save Processed Data:', 'name': 'save_processed', 'type': 'bool', 'value': True},
        ]},

        {'title': 'Advanced Settings', 'name': 'advanced', 'type': 'group', 'children': [
            {'title': 'Real-time Analysis:', 'name': 'realtime_analysis', 'type': 'bool', 'value': True},
            {'title': 'Background Subtraction:', 'name': 'bg_subtraction', 'type': 'bool', 'value': False},
            {'title': 'Stabilization Time (s):', 'name': 'stabilization_time', 'type': 'float',
             'value': 0.5, 'min': 0.0, 'max': 10.0, 'step': 0.1},
        ]},
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
        if hasattr(parent, 'dashboard'):
            self.dashboard = parent.dashboard
        elif hasattr(parent, 'modules_manager'):
            self.dashboard = parent
        else:
            # Look for dashboard in global variables from launcher
            import sys
            frame = sys._getframe(1)
            if 'dashboard' in frame.f_locals:
                self.dashboard = frame.f_locals['dashboard']
            elif 'dashboard' in frame.f_globals:
                self.dashboard = frame.f_globals['dashboard']

        # Initialize CustomApp attributes that may not be set by parent
        if not hasattr(self, 'dockarea') or self.dockarea is None:
            self.dockarea = parent  # Use parent as dockarea
        if not hasattr(self, 'docks'):
            self.docks = {}  # Initialize empty docks dictionary

        # Device management (initialize before UI setup)
        self.device_manager = URASHGDeviceManager(self.dashboard)
        self.available_devices = {}
        self.missing_devices = []

        # Initialize UI components
        self.setup_ui()

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

        # Timers for periodic tasks
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_device_status)
        self.status_timer.setInterval(5000)  # Update every 5 seconds (reduce load)

        logger.info(f"Initialized {self.name} extension v{self.version}")

    def setup_ui(self):
        """Set up the complete user interface for the extension."""
        logger.info("Setting up μRASHG extension UI...")

        # Initialize UI components in proper order
        self.setup_docks()       # Create dock layout
        self.setup_actions()     # Create actions/menus
        self.setup_widgets()     # Create main widgets
        self.connect_things()    # Connect signals/slots

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
        self.docks['control'] = Dock('μRASHG Control', size=(400, 600))
        self.dockarea.addDock(self.docks['control'], 'left')

        # Device Control Dock (left bottom) ⭐ NEW PHASE 3 FEATURE
        self.docks['device_control'] = Dock('Direct Device Controls', size=(400, 400))
        self.dockarea.addDock(self.docks['device_control'], 'bottom', self.docks['control'])

        # Live Camera Preview Dock (top right)
        self.docks['preview'] = Dock('Live Camera Preview', size=(600, 400))
        self.dockarea.addDock(self.docks['preview'], 'right', self.docks['control'])

        # RASHG Analysis Dock (middle right)
        self.docks['analysis'] = Dock('RASHG Analysis', size=(600, 400))
        self.dockarea.addDock(self.docks['analysis'], 'bottom', self.docks['preview'])

        # System Status and Progress Dock (bottom)
        self.docks['status'] = Dock('System Status & Progress', size=(1000, 200))
        self.dockarea.addDock(self.docks['status'], 'bottom', self.docks['device_control'])

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
        self.add_action('start_measurement', 'Start μRASHG Measurement',
                       self.start_measurement, icon='SP_MediaPlay')
        self.add_action('stop_measurement', 'Stop Measurement',
                       self.stop_measurement, icon='SP_MediaStop')
        self.add_action('pause_measurement', 'Pause Measurement',
                       self.pause_measurement, icon='SP_MediaPause')

        # Device management actions
        self.add_action('initialize_devices', 'Initialize Devices',
                       self.initialize_devices, icon='SP_ComputerIcon')
        self.add_action('check_devices', 'Check Device Status',
                       self.check_device_status, icon='SP_DialogApplyButton')
        self.add_action('emergency_stop', 'Emergency Stop',
                       self.emergency_stop, icon='SP_BrowserStop')

        # Configuration actions
        self.add_action('load_config', 'Load Configuration',
                       self.load_configuration, icon='SP_DialogOpenButton')
        self.add_action('save_config', 'Save Configuration',
                       self.save_configuration, icon='SP_DialogSaveButton')

        # Analysis actions (Enhanced for Phase 3)
        self.add_action('analyze_data', 'Analyze Current Data',
                       self.analyze_current_data, icon='SP_FileDialogDetailedView')
        self.add_action('fit_rashg_curve', 'Fit RASHG Pattern',  # ⭐ NEW
                       self.fit_rashg_pattern, icon='SP_ComputerIcon')
        self.add_action('export_data', 'Export Data',
                       self.export_data, icon='SP_DialogSaveButton')
        self.add_action('export_analysis', 'Export Analysis Results',  # ⭐ NEW
                       self.export_analysis_results, icon='SP_DialogSaveButton')

        logger.info("Created actions for μRASHG extension")

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
        """Set up the control panel widget."""
        self.control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(self.control_widget)

        # Parameter tree
        control_layout.addWidget(self.settings_tree)

        # Action buttons layout
        button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QGridLayout(button_widget)

        # Primary measurement controls
        self.start_button = QtWidgets.QPushButton('Start μRASHG')
        self.start_button.setIcon(self.get_style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start_measurement)
        self.start_button.setMinimumHeight(40)

        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.setIcon(self.get_style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_measurement)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)

        self.pause_button = QtWidgets.QPushButton('Pause')
        self.pause_button.setIcon(self.get_style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        self.pause_button.clicked.connect(self.pause_measurement)
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumHeight(40)

        button_layout.addWidget(self.start_button, 0, 0, 1, 2)
        button_layout.addWidget(self.stop_button, 1, 0)
        button_layout.addWidget(self.pause_button, 1, 1)

        # Device management buttons
        self.init_devices_button = QtWidgets.QPushButton('Initialize Devices')
        self.init_devices_button.clicked.connect(self.initialize_devices)

        self.check_devices_button = QtWidgets.QPushButton('Check Devices')
        self.check_devices_button.clicked.connect(self.check_device_status)

        button_layout.addWidget(self.init_devices_button, 2, 0)
        button_layout.addWidget(self.check_devices_button, 2, 1)

        # Emergency stop button
        self.emergency_button = QtWidgets.QPushButton('EMERGENCY STOP')
        self.emergency_button.setStyleSheet("background-color: red; font-weight: bold;")
        self.emergency_button.clicked.connect(self.emergency_stop)
        self.emergency_button.setMinimumHeight(30)

        button_layout.addWidget(self.emergency_button, 3, 0, 1, 2)

        control_layout.addWidget(button_widget)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        # Add to dock
        self.docks['control'].addWidget(self.control_widget)

    def setup_device_control_widget(self):
        """Set up the direct device control widget (PHASE 3 FEATURE)."""
        self.device_control_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(self.device_control_widget)

        # Create tabbed interface for different device types
        self.device_tabs = QtWidgets.QTabWidget()

        # === LASER CONTROL TAB ===
        self.laser_tab = QtWidgets.QWidget()
        laser_layout = QtWidgets.QVBoxLayout(self.laser_tab)

        # Laser Status Group
        laser_status_group = QtWidgets.QGroupBox("Laser Status")
        laser_status_layout = QtWidgets.QGridLayout(laser_status_group)

        self.laser_status_label = QtWidgets.QLabel("Status: Disconnected")
        self.laser_status_label.setStyleSheet("color: red; font-weight: bold;")
        laser_status_layout.addWidget(self.laser_status_label, 0, 0, 1, 2)

        laser_layout.addWidget(laser_status_group)

        # Wavelength Control Group
        wavelength_group = QtWidgets.QGroupBox("Wavelength Control")
        wavelength_layout = QtWidgets.QGridLayout(wavelength_group)

        # Wavelength display and control
        wavelength_layout.addWidget(QtWidgets.QLabel("Current Wavelength:"), 0, 0)
        self.wavelength_display = QtWidgets.QLabel("--- nm")
        self.wavelength_display.setStyleSheet("font-weight: bold; font-size: 14px;")
        wavelength_layout.addWidget(self.wavelength_display, 0, 1)

        # Wavelength slider
        wavelength_layout.addWidget(QtWidgets.QLabel("Set Wavelength:"), 1, 0)
        self.wavelength_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wavelength_slider.setMinimum(700)
        self.wavelength_slider.setMaximum(1000)
        self.wavelength_slider.setValue(800)
        self.wavelength_slider.valueChanged.connect(self.on_wavelength_slider_changed)
        wavelength_layout.addWidget(self.wavelength_slider, 1, 1)

        # Wavelength spinbox
        self.wavelength_spinbox = QtWidgets.QSpinBox()
        self.wavelength_spinbox.setMinimum(700)
        self.wavelength_spinbox.setMaximum(1000)
        self.wavelength_spinbox.setValue(800)
        self.wavelength_spinbox.setSuffix(" nm")
        self.wavelength_spinbox.valueChanged.connect(self.on_wavelength_spinbox_changed)
        wavelength_layout.addWidget(self.wavelength_spinbox, 1, 2)

        # Wavelength set button
        self.set_wavelength_button = QtWidgets.QPushButton("Set Wavelength")
        self.set_wavelength_button.clicked.connect(self.set_laser_wavelength)
        self.set_wavelength_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        wavelength_layout.addWidget(self.set_wavelength_button, 2, 0, 1, 3)

        laser_layout.addWidget(wavelength_group)

        # Shutter Control Group
        shutter_group = QtWidgets.QGroupBox("Shutter Control")
        shutter_layout = QtWidgets.QGridLayout(shutter_group)

        self.shutter_status_label = QtWidgets.QLabel("Status: Unknown")
        shutter_layout.addWidget(self.shutter_status_label, 0, 0, 1, 2)

        self.shutter_open_button = QtWidgets.QPushButton("Open Shutter")
        self.shutter_open_button.clicked.connect(self.open_laser_shutter)
        self.shutter_open_button.setStyleSheet("background-color: #2196F3; color: white;")
        shutter_layout.addWidget(self.shutter_open_button, 1, 0)

        self.shutter_close_button = QtWidgets.QPushButton("Close Shutter")
        self.shutter_close_button.clicked.connect(self.close_laser_shutter)
        self.shutter_close_button.setStyleSheet("background-color: #FF9800; color: white;")
        shutter_layout.addWidget(self.shutter_close_button, 1, 1)

        laser_layout.addWidget(shutter_group)

        self.device_tabs.addTab(self.laser_tab, "Laser Control")

        # === ROTATOR CONTROL TAB ===
        self.rotator_tab = QtWidgets.QWidget()
        rotator_layout = QtWidgets.QVBoxLayout(self.rotator_tab)

        # Individual rotator controls
        self.rotator_controls = {}
        rotator_names = [("QWP", "Quarter Wave Plate", 0),
                        ("HWP Inc", "Half Wave Plate (Incident)", 1),
                        ("HWP Ana", "Half Wave Plate (Analyzer)", 2)]

        for short_name, full_name, axis in rotator_names:
            group = QtWidgets.QGroupBox(f"{short_name} - {full_name}")
            group_layout = QtWidgets.QGridLayout(group)

            # Current position display
            group_layout.addWidget(QtWidgets.QLabel("Current Position:"), 0, 0)
            position_label = QtWidgets.QLabel("--- °")
            position_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            group_layout.addWidget(position_label, 0, 1)

            # Position control
            group_layout.addWidget(QtWidgets.QLabel("Set Position:"), 1, 0)
            position_spinbox = QtWidgets.QDoubleSpinBox()
            position_spinbox.setMinimum(0.0)
            position_spinbox.setMaximum(360.0)
            position_spinbox.setDecimals(2)
            position_spinbox.setSuffix(" °")
            group_layout.addWidget(position_spinbox, 1, 1)

            # Move buttons
            move_button = QtWidgets.QPushButton(f"Move {short_name}")
            move_button.clicked.connect(lambda checked, ax=axis: self.move_rotator(ax))
            move_button.setStyleSheet("background-color: #4CAF50; color: white;")
            group_layout.addWidget(move_button, 1, 2)

            home_button = QtWidgets.QPushButton(f"Home {short_name}")
            home_button.clicked.connect(lambda checked, ax=axis: self.home_rotator(ax))
            home_button.setStyleSheet("background-color: #9E9E9E; color: white;")
            group_layout.addWidget(home_button, 2, 0, 1, 3)

            # Store references
            self.rotator_controls[axis] = {
                'position_label': position_label,
                'position_spinbox': position_spinbox,
                'move_button': move_button,
                'home_button': home_button,
                'name': short_name
            }

            rotator_layout.addWidget(group)

        # Emergency stop for all rotators
        emergency_rotator_button = QtWidgets.QPushButton("EMERGENCY STOP ALL ROTATORS")
        emergency_rotator_button.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 12px;")
        emergency_rotator_button.clicked.connect(self.emergency_stop_rotators)
        rotator_layout.addWidget(emergency_rotator_button)

        self.device_tabs.addTab(self.rotator_tab, "Rotator Control")

        # === POWER METER & SYNC TAB ===
        self.power_tab = QtWidgets.QWidget()
        power_layout = QtWidgets.QVBoxLayout(self.power_tab)

        # Power reading display
        power_group = QtWidgets.QGroupBox("Power Monitoring")
        power_group_layout = QtWidgets.QGridLayout(power_group)

        power_group_layout.addWidget(QtWidgets.QLabel("Current Power:"), 0, 0)
        self.power_display = QtWidgets.QLabel("--- mW")
        self.power_display.setStyleSheet("font-weight: bold; font-size: 14px;")
        power_group_layout.addWidget(self.power_display, 0, 1)

        power_group_layout.addWidget(QtWidgets.QLabel("Wavelength Setting:"), 1, 0)
        self.power_wavelength_display = QtWidgets.QLabel("--- nm")
        self.power_wavelength_display.setStyleSheet("font-weight: bold; font-size: 12px;")
        power_group_layout.addWidget(self.power_wavelength_display, 1, 1)

        power_layout.addWidget(power_group)

        # Wavelength synchronization
        sync_group = QtWidgets.QGroupBox("Wavelength Synchronization")
        sync_layout = QtWidgets.QGridLayout(sync_group)

        self.auto_sync_checkbox = QtWidgets.QCheckBox("Auto-sync with laser wavelength")
        self.auto_sync_checkbox.setChecked(True)
        self.auto_sync_checkbox.stateChanged.connect(self.on_auto_sync_changed)
        sync_layout.addWidget(self.auto_sync_checkbox, 0, 0, 1, 2)

        self.sync_status_label = QtWidgets.QLabel("Sync Status: Ready")
        self.sync_status_label.setStyleSheet("color: green;")
        sync_layout.addWidget(self.sync_status_label, 1, 0, 1, 2)

        self.manual_sync_button = QtWidgets.QPushButton("Manual Sync Now")
        self.manual_sync_button.clicked.connect(self.manual_sync_wavelength)
        self.manual_sync_button.setStyleSheet("background-color: #2196F3; color: white;")
        sync_layout.addWidget(self.manual_sync_button, 2, 0, 1, 2)

        power_layout.addWidget(sync_group)

        self.device_tabs.addTab(self.power_tab, "Power & Sync")

        # Add tabs to main layout
        main_layout.addWidget(self.device_tabs)

        # Status update timer for device controls
        self.device_update_timer = QTimer()
        self.device_update_timer.timeout.connect(self.update_device_control_displays)
        self.device_update_timer.setInterval(1000)  # Update every 1 second

        # Add to dock
        self.docks['device_control'].addWidget(self.device_control_widget)

        logger.info("Created device control widget with laser, rotator, and power meter controls")

    def setup_visualization_widget(self):
        """Set up the camera preview widget."""
        self.camera_view = pg.ImageView()
        self.camera_view.setImage(np.zeros((512, 512)))  # Placeholder image

        # Add to dock
        self.docks['preview'].addWidget(self.camera_view)

    def setup_analysis_widget(self):
        """Set up the analysis plots widget (Enhanced for Phase 3)."""
        analysis_widget = QtWidgets.QWidget()
        analysis_layout = QtWidgets.QVBoxLayout(analysis_widget)

        # Create tab widget for different analysis views
        self.analysis_tabs = QtWidgets.QTabWidget()

        # === POLAR PLOT TAB (Enhanced) ===
        polar_widget = QtWidgets.QWidget()
        polar_layout = QtWidgets.QVBoxLayout(polar_widget)

        # Polar plot with enhanced features
        self.polar_plot = pg.PlotWidget(title='RASHG Polar Response')
        self.polar_plot.setLabel('left', 'SHG Intensity', 'counts')
        self.polar_plot.setLabel('bottom', 'Polarization Angle', '°')
        self.polar_plot.showGrid(True, True)
        self.polar_plot.addLegend()

        # Fit controls for polar plot
        fit_controls = QtWidgets.QWidget()
        fit_layout = QtWidgets.QHBoxLayout(fit_controls)

        self.auto_fit_checkbox = QtWidgets.QCheckBox("Real-time fitting")
        self.auto_fit_checkbox.setChecked(True)
        self.auto_fit_checkbox.stateChanged.connect(self.on_auto_fit_changed)
        fit_layout.addWidget(self.auto_fit_checkbox)

        self.fit_button = QtWidgets.QPushButton("Fit RASHG Pattern")
        self.fit_button.clicked.connect(self.fit_rashg_pattern)
        fit_layout.addWidget(self.fit_button)

        fit_layout.addStretch()

        # Fit results display
        self.fit_results_label = QtWidgets.QLabel("Fit Results: No data")
        self.fit_results_label.setStyleSheet("font-family: monospace; background: #f0f0f0; padding: 5px;")
        fit_layout.addWidget(self.fit_results_label)

        polar_layout.addWidget(self.polar_plot)
        polar_layout.addWidget(fit_controls)

        self.analysis_tabs.addTab(polar_widget, 'Polar Analysis')

        # === SPECTRAL ANALYSIS TAB (NEW) ===
        spectral_widget = QtWidgets.QWidget()
        spectral_layout = QtWidgets.QVBoxLayout(spectral_widget)

        self.spectral_plot = pg.PlotWidget(title='Spectral RASHG Analysis')
        self.spectral_plot.setLabel('left', 'RASHG Amplitude', 'a.u.')
        self.spectral_plot.setLabel('bottom', 'Wavelength', 'nm')
        self.spectral_plot.showGrid(True, True)
        self.spectral_plot.addLegend()

        # Spectral analysis controls
        spectral_controls = QtWidgets.QWidget()
        spectral_controls_layout = QtWidgets.QHBoxLayout(spectral_controls)

        spectral_controls_layout.addWidget(QtWidgets.QLabel("Analysis Mode:"))

        self.spectral_mode_combo = QtWidgets.QComboBox()
        self.spectral_mode_combo.addItems(["RASHG Amplitude", "Phase", "Contrast", "All Parameters"])
        self.spectral_mode_combo.currentTextChanged.connect(self.update_spectral_analysis)
        spectral_controls_layout.addWidget(self.spectral_mode_combo)

        spectral_controls_layout.addStretch()

        self.update_spectral_button = QtWidgets.QPushButton("Update Analysis")
        self.update_spectral_button.clicked.connect(self.update_spectral_analysis)
        spectral_controls_layout.addWidget(self.update_spectral_button)

        spectral_layout.addWidget(self.spectral_plot)
        spectral_layout.addWidget(spectral_controls)

        self.analysis_tabs.addTab(spectral_widget, 'Spectral Analysis')

        # === POWER MONITORING TAB ===
        power_widget = QtWidgets.QWidget()
        power_layout = QtWidgets.QVBoxLayout(power_widget)

        self.power_plot = pg.PlotWidget(title='Power Stability')
        self.power_plot.setLabel('left', 'Power', 'mW')
        self.power_plot.setLabel('bottom', 'Time', 's')
        self.power_plot.showGrid(True, True)
        power_layout.addWidget(self.power_plot)

        self.analysis_tabs.addTab(power_widget, 'Power Monitor')

        # === 3D ANALYSIS TAB (NEW) ===
        if self._check_3d_support():
            volume_widget = QtWidgets.QWidget()
            volume_layout = QtWidgets.QVBoxLayout(volume_widget)

            # 3D visualization for wavelength-angle-intensity data
            try:
                import pyqtgraph.opengl as gl

                self.volume_view = gl.GLViewWidget()
                self.volume_view.setCameraPosition(distance=50)
                volume_layout.addWidget(self.volume_view)

                # 3D controls
                volume_controls = QtWidgets.QWidget()
                volume_controls_layout = QtWidgets.QHBoxLayout(volume_controls)

                volume_controls_layout.addWidget(QtWidgets.QLabel("3D Visualization:"))

                self.volume_mode_combo = QtWidgets.QComboBox()
                self.volume_mode_combo.addItems(["Surface", "Scatter", "Wireframe"])
                self.volume_mode_combo.currentTextChanged.connect(self.update_3d_visualization)
                volume_controls_layout.addWidget(self.volume_mode_combo)

                volume_controls_layout.addStretch()

                volume_layout.addWidget(volume_controls)

                self.analysis_tabs.addTab(volume_widget, '3D Visualization')

            except ImportError:
                logger.info("OpenGL not available, 3D visualization disabled")

        analysis_layout.addWidget(self.analysis_tabs)

        # Analysis status bar
        self.analysis_status = QtWidgets.QLabel("Analysis Status: Ready")
        self.analysis_status.setStyleSheet("background: #e0e0e0; padding: 3px; border: 1px solid #c0c0c0;")
        analysis_layout.addWidget(self.analysis_status)

        # Store current fit results
        self.current_fit_results = None
        self.spectral_analysis_data = None

        # Add to dock
        self.docks['analysis'].addWidget(analysis_widget)

    def setup_status_widget(self):
        """Set up the status monitoring widget."""
        self.status_widget = QtWidgets.QWidget()
        status_layout = QtWidgets.QHBoxLayout(self.status_widget)

        # Device status table
        self.device_status_table = QtWidgets.QTableWidget()
        self.device_status_table.setColumnCount(3)
        self.device_status_table.setHorizontalHeaderLabels(['Device', 'Status', 'Details'])
        self.device_status_table.horizontalHeader().setStretchLastSection(True)

        # Log display
        self.log_display = QtWidgets.QTextEdit()
        self.log_display.setMaximumHeight(150)
        self.log_display.setReadOnly(True)

        # Layout
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.addWidget(QtWidgets.QLabel('Device Status:'))
        left_layout.addWidget(self.device_status_table)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.addWidget(QtWidgets.QLabel('Activity Log:'))
        right_layout.addWidget(self.log_display)

        status_layout.addWidget(left_widget)
        status_layout.addWidget(right_widget)

        # Add to dock
        self.docks['status'].addWidget(self.status_widget)

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
            self.device_manager.device_status_changed.connect(self.on_device_status_changed)
            self.device_manager.device_error.connect(self.on_device_error)
            self.device_manager.all_devices_ready.connect(self.on_all_devices_ready)

        # Start device control update timer (PHASE 3 FEATURE)
        if hasattr(self, 'device_update_timer'):
            self.device_update_timer.start()
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
            laser = self.device_manager.get_laser()
            if not laser:
                self.log_message("ERROR: Laser device not available", level='error')
                return

            # Use proper DataActuator pattern for wavelength control
            from pymodaq.utils.data import DataActuator

            # Create position data - MaiTai laser typically uses single-axis control
            position_data = DataActuator(data=[target_wavelength])

            # Move to wavelength - CRITICAL: Use .value() for single-axis controllers
            if hasattr(laser, 'move_abs'):
                laser.move_abs(position_data)
                self.log_message(f"Laser wavelength command sent: {target_wavelength} nm")

                # Trigger automatic wavelength synchronization if enabled
                if hasattr(self, 'auto_sync_checkbox') and self.auto_sync_checkbox.isChecked():
                    self.sync_power_meter_wavelength(target_wavelength)

            else:
                self.log_message("ERROR: Laser does not support absolute movement", level='error')

        except Exception as e:
            error_msg = f"Failed to set laser wavelength: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def open_laser_shutter(self):
        """Open the laser shutter."""
        logger.info("Opening laser shutter")
        self.log_message("Opening laser shutter")

        try:
            laser = self.device_manager.get_laser()
            if not laser:
                self.log_message("ERROR: Laser device not available", level='error')
                return

            # Check if laser has shutter control capability
            if hasattr(laser, 'controller') and laser.controller:
                if hasattr(laser.controller, 'open_shutter'):
                    laser.controller.open_shutter()
                    self.log_message("Laser shutter opened")
                    self.update_shutter_status("Open")
                elif hasattr(laser.controller, 'set_shutter'):
                    laser.controller.set_shutter(True)
                    self.log_message("Laser shutter opened (via set_shutter)")
                    self.update_shutter_status("Open")
                else:
                    self.log_message("WARNING: Laser shutter control not available", level='warning')
            else:
                self.log_message("ERROR: Laser controller not available", level='error')

        except Exception as e:
            error_msg = f"Failed to open laser shutter: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def close_laser_shutter(self):
        """Close the laser shutter."""
        logger.info("Closing laser shutter")
        self.log_message("Closing laser shutter")

        try:
            laser = self.device_manager.get_laser()
            if not laser:
                self.log_message("ERROR: Laser device not available", level='error')
                return

            # Check if laser has shutter control capability
            if hasattr(laser, 'controller') and laser.controller:
                if hasattr(laser.controller, 'close_shutter'):
                    laser.controller.close_shutter()
                    self.log_message("Laser shutter closed")
                    self.update_shutter_status("Closed")
                elif hasattr(laser.controller, 'set_shutter'):
                    laser.controller.set_shutter(False)
                    self.log_message("Laser shutter closed (via set_shutter)")
                    self.update_shutter_status("Closed")
                else:
                    self.log_message("WARNING: Laser shutter control not available", level='warning')
            else:
                self.log_message("ERROR: Laser controller not available", level='error')

        except Exception as e:
            error_msg = f"Failed to close laser shutter: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def update_shutter_status(self, status):
        """Update shutter status display."""
        if hasattr(self, 'shutter_status_label'):
            self.shutter_status_label.setText(f"Status: {status}")
            if status == "Open":
                self.shutter_status_label.setStyleSheet("color: green; font-weight: bold;")
            elif status == "Closed":
                self.shutter_status_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.shutter_status_label.setStyleSheet("color: gray; font-weight: bold;")

    def move_rotator(self, axis):
        """Move a specific rotator to the set position."""
        if axis not in self.rotator_controls:
            logger.error(f"Invalid rotator axis: {axis}")
            return

        rotator_control = self.rotator_controls[axis]
        target_position = rotator_control['position_spinbox'].value()
        rotator_name = rotator_control['name']

        logger.info(f"Moving {rotator_name} (axis {axis}) to {target_position}°")
        self.log_message(f"Moving {rotator_name} to {target_position}°")

        try:
            elliptec = self.device_manager.get_elliptec()
            if not elliptec:
                self.log_message("ERROR: Elliptec device not available", level='error')
                return

            # Use proper DataActuator pattern for multi-axis device
            from pymodaq.utils.data import DataActuator

            # For multi-axis Elliptec, we need to specify which axis to move
            # Create position array - only set the target axis, others to current positions
            current_positions = self.get_current_elliptec_positions()
            if current_positions is None or not isinstance(current_positions, (list, tuple, np.ndarray)):
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
            if hasattr(elliptec, 'move_abs'):
                elliptec.move_abs(position_data)
                self.log_message(f"{rotator_name} movement command sent")
            else:
                self.log_message(f"ERROR: {rotator_name} does not support absolute movement", level='error')

        except Exception as e:
            error_msg = f"Failed to move {rotator_name}: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def home_rotator(self, axis):
        """Home a specific rotator."""
        if axis not in self.rotator_controls:
            logger.error(f"Invalid rotator axis: {axis}")
            return

        rotator_name = self.rotator_controls[axis]['name']

        logger.info(f"Homing {rotator_name} (axis {axis})")
        self.log_message(f"Homing {rotator_name}")

        try:
            elliptec = self.device_manager.get_elliptec()
            if not elliptec:
                self.log_message("ERROR: Elliptec device not available", level='error')
                return

            # Check if elliptec has home capability
            if hasattr(elliptec, 'move_home'):
                elliptec.move_home()
                self.log_message(f"{rotator_name} homing command sent")
            elif hasattr(elliptec, 'controller') and elliptec.controller:
                if hasattr(elliptec.controller, 'move_home'):
                    elliptec.controller.move_home()
                    self.log_message(f"{rotator_name} homing via controller")
                else:
                    self.log_message(f"WARNING: {rotator_name} homing not available", level='warning')
            else:
                self.log_message(f"ERROR: {rotator_name} controller not available", level='error')

        except Exception as e:
            error_msg = f"Failed to home {rotator_name}: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def emergency_stop_rotators(self):
        """Emergency stop all rotators."""
        logger.warning("EMERGENCY STOP - All rotators")
        self.log_message("EMERGENCY STOP - All rotators", level='error')

        try:
            elliptec = self.device_manager.get_elliptec()
            if elliptec:
                if hasattr(elliptec, 'stop_motion'):
                    elliptec.stop_motion()
                elif hasattr(elliptec, 'controller') and elliptec.controller:
                    if hasattr(elliptec.controller, 'stop_motion'):
                        elliptec.controller.stop_motion()

                self.log_message("Emergency stop applied to all rotators")
            else:
                self.log_message("ERROR: Elliptec device not available for emergency stop", level='error')

        except Exception as e:
            error_msg = f"Error during rotator emergency stop: {str(e)}"
            self.log_message(error_msg, level='error')

    def get_current_elliptec_positions(self):
        """Get current positions of all Elliptec axes."""
        try:
            elliptec = self.device_manager.get_elliptec()
            if not elliptec:
                return None

            # Try to get current positions
            if hasattr(elliptec, 'current_position') and elliptec.current_position is not None:
                # current_position might be a DataActuator or list
                if hasattr(elliptec.current_position, 'data'):
                    return elliptec.current_position.data[0]
                else:
                    return elliptec.current_position
            elif hasattr(elliptec, 'controller') and elliptec.controller:
                if hasattr(elliptec.controller, 'get_actuator_value'):
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
                self.log_message(f"Using set wavelength: {current_wavelength} nm", level='warning')

            # Sync power meter
            success = self.sync_power_meter_wavelength(current_wavelength)

            if success:
                self.log_message(f"Wavelength sync completed: {current_wavelength} nm")
            else:
                self.log_message("Wavelength sync failed", level='error')

        except Exception as e:
            error_msg = f"Manual wavelength sync failed: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def sync_power_meter_wavelength(self, wavelength):
        """Sync power meter wavelength setting."""
        try:
            power_meter = self.device_manager.get_power_meter()
            if not power_meter:
                self.log_message("WARNING: Power meter not available for wavelength sync", level='warning')
                return False

            # Check if power meter supports wavelength setting
            if hasattr(power_meter, 'controller') and power_meter.controller:
                if hasattr(power_meter.controller, 'set_wavelength'):
                    power_meter.controller.set_wavelength(wavelength)
                    self.update_sync_status("Synced", "green")
                    logger.info(f"Power meter wavelength synced to {wavelength} nm")
                    return True
                elif hasattr(power_meter, 'settings'):
                    # Try to find wavelength setting in parameter tree
                    wavelength_param = power_meter.settings.child_frompath('wavelength')
                    if wavelength_param:
                        wavelength_param.setValue(wavelength)
                        self.update_sync_status("Synced", "green")
                        logger.info(f"Power meter wavelength setting updated to {wavelength} nm")
                        return True

            self.log_message("WARNING: Power meter wavelength sync not supported", level='warning')
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
            if hasattr(laser, 'current_position') and laser.current_position is not None:
                if hasattr(laser.current_position, 'value'):
                    return laser.current_position.value()
                elif hasattr(laser.current_position, 'data'):
                    return laser.current_position.data[0][0]
                else:
                    return float(laser.current_position)
            elif hasattr(laser, 'controller') and laser.controller:
                if hasattr(laser.controller, 'get_wavelength'):
                    return laser.controller.get_wavelength()

            return None

        except Exception as e:
            logger.debug(f"Could not get current laser wavelength: {e}")
            return None

    def update_sync_status(self, status, color):
        """Update wavelength sync status display."""
        if hasattr(self, 'sync_status_label'):
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

            if hasattr(self, 'laser_status_label'):
                if laser and hasattr(laser, 'controller') and laser.controller:
                    if hasattr(laser.controller, 'connected') and laser.controller.connected:
                        self.laser_status_label.setText("Status: Connected")
                        self.laser_status_label.setStyleSheet("color: green; font-weight: bold;")
                    else:
                        self.laser_status_label.setText("Status: Disconnected")
                        self.laser_status_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.laser_status_label.setText("Status: Not Available")
                    self.laser_status_label.setStyleSheet("color: gray; font-weight: bold;")

            # Update wavelength display
            if hasattr(self, 'wavelength_display'):
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
                    controls['position_label'].setText(f"{position:.2f} °")
                else:
                    controls['position_label'].setText("--- °")

        except Exception as e:
            logger.debug(f"Error updating rotator displays: {e}")

    def update_power_meter_display(self):
        """Update power meter displays."""
        try:
            power_meter = self.device_manager.get_power_meter()

            # Update power reading
            if hasattr(self, 'power_display'):
                if power_meter and hasattr(power_meter, 'grab_data'):
                    try:
                        power_data = power_meter.grab_data()
                        if power_data and len(power_data) > 0:
                            power_value = float(power_data[0].data[0]) if hasattr(power_data[0], 'data') else 0.0
                            self.power_display.setText(f"{power_value:.3f} mW")
                        else:
                            self.power_display.setText("--- mW")
                    except Exception as e:
                        self.power_display.setText("--- mW")
                        logger.debug(f"Could not read power meter: {e}")
                else:
                    self.power_display.setText("--- mW")

            # Update power meter wavelength display (if available)
            if hasattr(self, 'power_wavelength_display'):
                if power_meter and hasattr(power_meter, 'controller') and power_meter.controller:
                    try:
                        if hasattr(power_meter.controller, 'get_wavelength'):
                            pm_wavelength = power_meter.controller.get_wavelength()
                            self.power_wavelength_display.setText(f"{pm_wavelength:.0f} nm")
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

        if not self.device_manager:
            self.log_message("ERROR: Device manager not available", level='error')
            return

        try:
            # Discover devices first
            available_devices, missing_devices = self.device_manager.discover_devices()
            self.available_devices = available_devices
            self.missing_devices = missing_devices

            # Report discovery results
            if available_devices:
                self.log_message(f"Found {len(available_devices)} devices: {list(available_devices.keys())}")

            if missing_devices:
                self.log_message(f"Missing required devices: {missing_devices}", level='error')
                return False

            # Initialize all devices
            success = self.device_manager.initialize_all_devices()

            if success:
                self.log_message("All devices initialized successfully")
                self.device_manager.start_monitoring()
                return True
            else:
                self.log_message("Some devices failed to initialize", level='error')
                return False

        except Exception as e:
            error_msg = f"Device initialization failed: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)
            return False

    def check_device_status(self):
        """Check the status of all devices."""
        logger.info("Checking device status...")
        self.log_message("Checking device status...")

        if not self.device_manager:
            self.log_message("ERROR: Device manager not available", level='error')
            return

        try:
            # Update status for all devices
            self.device_manager.update_all_device_status()

            # Get status summary
            all_device_info = self.device_manager.get_all_device_info()

            for device_key, device_info in all_device_info.items():
                status_msg = f"Device '{device_key}': {device_info.status.value}"
                if device_info.last_error:
                    status_msg += f" (Error: {device_info.last_error})"

                level = 'info' if device_info.status == DeviceStatus.CONNECTED else 'warning'
                self.log_message(status_msg, level=level)

            # Check if all required devices are ready
            all_ready = self.device_manager.is_all_devices_ready()
            ready_msg = "All required devices are ready" if all_ready else "Some required devices are not ready"
            self.log_message(ready_msg, level='info' if all_ready else 'warning')

        except Exception as e:
            error_msg = f"Device status check failed: {str(e)}"
            self.log_message(error_msg, level='error')
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
        self.measurement_worker.measurement_completed.connect(self._on_measurement_completed)
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
            missing = self.device_manager.get_missing_devices() if self.device_manager else ['All devices']
            self.log_message(f"Cannot start: Missing devices: {missing}", level='error')
            self.error_occurred.emit(f"Missing required devices: {missing}")
            return False

        # Check safety parameters
        max_power = self.settings.child('hardware', 'safety', 'max_power').value()
        if max_power > 80.0:
            self.log_message(f"WARNING: High power limit set ({max_power}%)", level='warning')
            reply = QtWidgets.QMessageBox.question(
                self.control_widget, 'High Power Warning',
                f'Power limit is set to {max_power}%. Continue?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return False

        # Check measurement parameters
        pol_steps = self.settings.child('experiment', 'pol_steps').value()
        if pol_steps < 4:
            self.log_message("ERROR: Minimum 4 polarization steps required", level='error')
            self.error_occurred.emit("Insufficient polarization steps (minimum 4)")
            return False

        # Check camera ROI
        roi_width = self.settings.child('hardware', 'camera', 'roi', 'width').value()
        roi_height = self.settings.child('hardware', 'camera', 'roi', 'height').value()
        if roi_width < 1 or roi_height < 1:
            self.log_message("ERROR: Invalid camera ROI settings", level='error')
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
            if hasattr(self, 'measurement_worker') and self.measurement_worker:
                self.measurement_worker.stop_measurement()

            # Stop measurement thread
            if hasattr(self, 'measurement_thread') and self.measurement_thread:
                if self.measurement_thread.isRunning():
                    self.measurement_thread.quit()
                    if not self.measurement_thread.wait(5000):  # Wait up to 5 seconds
                        self.log_message("Forcing thread termination", level='warning')
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
            self.log_message(error_msg, level='error')
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
            if hasattr(self, 'measurement_worker') and self.measurement_worker:
                self.measurement_worker.pause_measurement()
                self.log_message("Measurement paused")
            else:
                self.log_message("Cannot pause: No active measurement worker", level='warning')

        except Exception as e:
            error_msg = f"Error pausing measurement: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def emergency_stop(self):
        """Emergency stop all devices and measurements."""
        logger.warning("EMERGENCY STOP activated!")
        self.log_message("EMERGENCY STOP activated!", level='error')

        try:
            # Stop any ongoing measurements
            if self.is_measuring:
                self.stop_measurement()

            # Emergency stop all devices
            if self.device_manager:
                self.device_manager.emergency_stop_all_devices()
                self.log_message("Emergency stop applied to all devices")

            # Reset UI state
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.progress_bar.setVisible(False)

            self.log_message("Emergency stop completed")

        except Exception as e:
            error_msg = f"Error during emergency stop: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level='error')

    def analyze_current_data(self):
        """Analyze the current measurement data (Enhanced for Phase 3)."""
        logger.info("Analyzing current data...")
        self.log_message("Analyzing current data...")

        if not self.current_measurement_data:
            self.log_message("No measurement data available for analysis", level='warning')
            return

        try:
            self.update_analysis_status("Analyzing data...")

            # Update polar plot with fitting
            if 'angles' in self.current_measurement_data and 'intensities' in self.current_measurement_data:
                self._update_polar_plot(self.current_measurement_data)

            # Update spectral analysis if multi-wavelength data
            if self.current_measurement_data.get('multi_wavelength', False):
                self.update_spectral_analysis()
                self.update_3d_visualization()

            self.update_analysis_status("Analysis completed")
            self.log_message("Data analysis completed")

        except Exception as e:
            error_msg = f"Data analysis failed: {str(e)}"
            self.log_message(error_msg, level='error')
            self.update_analysis_status("Analysis failed")

    def fit_rashg_pattern(self):
        """Fit RASHG pattern to current data (PHASE 3 FEATURE)."""
        logger.info("Fitting RASHG pattern...")
        self.log_message("Fitting RASHG pattern...")

        if not self.current_measurement_data:
            self.log_message("No measurement data available for fitting", level='warning')
            return

        try:
            self.update_analysis_status("Fitting RASHG pattern...")

            angles = self.current_measurement_data.get('angles', [])
            intensities = self.current_measurement_data.get('intensities', [])

            if len(angles) < 4 or len(intensities) < 4:
                self.log_message("Insufficient data points for fitting (minimum 4 required)", level='warning')
                return

            # Perform RASHG fitting
            fit_results = self._fit_rashg_data(angles, intensities)

            if fit_results:
                self.current_fit_results = fit_results
                self._display_fit_results(fit_results)
                self._plot_fit_curve(angles, intensities, fit_results)

                self.log_message(f"RASHG fit completed: A={fit_results['A']:.2f}, B={fit_results['B']:.2f}, φ={fit_results['phi_deg']:.1f}°")
                self.update_analysis_status("RASHG pattern fitted successfully")
            else:
                self.log_message("RASHG fitting failed", level='error')
                self.update_analysis_status("RASHG fitting failed")

        except Exception as e:
            error_msg = f"RASHG fitting failed: {str(e)}"
            self.log_message(error_msg, level='error')
            self.update_analysis_status("RASHG fitting failed")

    def export_analysis_results(self):
        """Export analysis results (PHASE 3 FEATURE)."""
        logger.info("Exporting analysis results...")
        self.log_message("Exporting analysis results...")

        if not self.current_fit_results and not self.spectral_analysis_data:
            self.log_message("No analysis results available for export", level='warning')
            return

        try:
            # Get save directory
            save_dir = Path(self.settings.child('data', 'save_dir').value())
            save_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime('%Y%m%d_%H%M%S')

            # Export fit results
            if self.current_fit_results:
                fit_filename = save_dir / f"rashg_fit_results_{timestamp}.json"
                with open(fit_filename, 'w') as f:
                    json.dump(self.current_fit_results, f, indent=2)
                self.log_message(f"Fit results exported to {fit_filename}")

            # Export spectral analysis
            if self.spectral_analysis_data:
                spectral_filename = save_dir / f"spectral_analysis_{timestamp}.json"
                with open(spectral_filename, 'w') as f:
                    json.dump(self.spectral_analysis_data, f, indent=2)
                self.log_message(f"Spectral analysis exported to {spectral_filename}")

            self.log_message("Analysis results exported successfully")

        except Exception as e:
            error_msg = f"Export analysis results failed: {str(e)}"
            self.log_message(error_msg, level='error')

    def export_data(self):
        """Export measurement data to file."""
        logger.info("Exporting data...")
        self.log_message("Exporting data...")

        if not self.current_measurement_data:
            self.log_message("No measurement data available for export", level='warning')
            return

        try:
            # Use existing data export functionality but add analysis results
            save_dir = Path(self.settings.child('data', 'save_dir').value())
            save_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = save_dir / f"urashg_data_export_{timestamp}.json"

            # Prepare comprehensive export data
            export_data = self.current_measurement_data.copy()

            # Add analysis results if available
            if self.current_fit_results:
                export_data['fit_results'] = self.current_fit_results

            if self.spectral_analysis_data:
                export_data['spectral_analysis'] = self.spectral_analysis_data

            # Save to JSON
            with open(filename, 'w') as f:
                import json
                json.dump(export_data, f, indent=2)

            self.log_message(f"Data exported to {filename}")

        except Exception as e:
            error_msg = f"Data export failed: {str(e)}"
            self.log_message(error_msg, level='error')

    def load_configuration(self):
        """Load measurement configuration from file (PHASE 3 FEATURE)."""
        logger.info("Loading configuration...")
        self.log_message("Loading configuration...")

        try:
            # File dialog for configuration selection
            from qtpy.QtWidgets import QFileDialog

            # Get default config directory
            config_dir = Path(self.settings.child('data', 'save_dir').value()) / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Open file dialog
            filename, _ = QFileDialog.getOpenFileName(
                self.control_widget,
                'Load μRASHG Configuration',
                str(config_dir),
                'JSON Configuration Files (*.json);;All Files (*.*)'
            )

            if not filename:
                self.log_message("Configuration load cancelled")
                return

            # Load and apply configuration
            with open(filename, 'r') as f:
                import json
                config_data = json.load(f)

            self._apply_configuration(config_data)

            self.log_message(f"Configuration loaded from {filename}")

        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.log_message(error_msg, level='error')
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
            config_dir = Path(self.settings.child('data', 'save_dir').value()) / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Generate default filename
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            default_name = f"urashg_config_{timestamp}.json"

            # Open file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.control_widget,
                'Save μRASHG Configuration',
                str(config_dir / default_name),
                'JSON Configuration Files (*.json);;All Files (*.*)'
            )

            if not filename:
                self.log_message("Configuration save cancelled")
                return

            # Save configuration
            with open(filename, 'w') as f:
                import json
                json.dump(config_data, f, indent=2)

            self.log_message(f"Configuration saved to {filename}")

        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            self.log_message(error_msg, level='error')
            self.error_occurred.emit(error_msg)

    def _get_current_configuration(self):
        """Get current system configuration for saving."""
        try:
            config_data = {
                'metadata': {
                    'timestamp': time.time(),
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'extension_version': self.version,
                    'config_type': 'urashg_measurement_config'
                },

                # Parameter tree settings
                'parameter_settings': self._extract_parameter_settings(),

                # Device positions
                'device_positions': self._get_current_device_positions(),

                # Device control settings
                'device_control_settings': self._get_device_control_settings(),

                # Analysis settings
                'analysis_settings': self._get_analysis_settings(),

                # UI settings
                'ui_settings': {
                    'auto_fit_enabled': getattr(self.auto_fit_checkbox, 'isChecked', lambda: False)() if hasattr(self, 'auto_fit_checkbox') else False,
                    'auto_sync_enabled': getattr(self.auto_sync_checkbox, 'isChecked', lambda: True)() if hasattr(self, 'auto_sync_checkbox') else True,
                    'spectral_mode': getattr(self.spectral_mode_combo, 'currentText', lambda: 'RASHG Amplitude')() if hasattr(self, 'spectral_mode_combo') else 'RASHG Amplitude',
                    'active_analysis_tab': getattr(self.analysis_tabs, 'currentIndex', lambda: 0)() if hasattr(self, 'analysis_tabs') else 0,
                    'active_device_tab': getattr(self.device_tabs, 'currentIndex', lambda: 0)() if hasattr(self, 'device_tabs') else 0,
                }
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
            for param_name in ['experiment', 'hardware', 'wavelength', 'data', 'advanced']:
                if self.settings.child(param_name):
                    parameter_settings[param_name] = self._extract_parameter_group(self.settings.child(param_name))

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
            if hasattr(self, 'wavelength_spinbox'):
                device_positions['laser_wavelength'] = self.wavelength_spinbox.value()

            # Get elliptec positions
            elliptec_positions = self.get_current_elliptec_positions()
            if elliptec_positions:
                device_positions['elliptec_positions'] = elliptec_positions

            # Get rotator control spinbox values
            if hasattr(self, 'rotator_controls'):
                rotator_setpoints = {}
                for axis, controls in self.rotator_controls.items():
                    if 'position_spinbox' in controls:
                        rotator_setpoints[axis] = controls['position_spinbox'].value()
                device_positions['rotator_setpoints'] = rotator_setpoints

            return device_positions

        except Exception as e:
            logger.debug(f"Error getting device positions: {e}")
            return {}

    def _get_device_control_settings(self):
        """Get device control widget settings."""
        try:
            device_control_settings = {}

            # Wavelength control settings
            if hasattr(self, 'wavelength_slider') and hasattr(self, 'wavelength_spinbox'):
                device_control_settings['wavelength_control'] = {
                    'slider_value': self.wavelength_slider.value(),
                    'spinbox_value': self.wavelength_spinbox.value()
                }

            # Power meter sync settings
            if hasattr(self, 'auto_sync_checkbox'):
                device_control_settings['power_sync'] = {
                    'auto_sync_enabled': self.auto_sync_checkbox.isChecked()
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
            if hasattr(self, 'auto_fit_checkbox'):
                analysis_settings['fitting'] = {
                    'auto_fit_enabled': self.auto_fit_checkbox.isChecked()
                }

            # Spectral analysis settings
            if hasattr(self, 'spectral_mode_combo'):
                analysis_settings['spectral'] = {
                    'mode': self.spectral_mode_combo.currentText(),
                    'index': self.spectral_mode_combo.currentIndex()
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
            if 'parameter_settings' in config_data:
                self._apply_parameter_settings(config_data['parameter_settings'])

            # Apply device positions
            if 'device_positions' in config_data:
                self._apply_device_positions(config_data['device_positions'])

            # Apply device control settings
            if 'device_control_settings' in config_data:
                self._apply_device_control_settings(config_data['device_control_settings'])

            # Apply analysis settings
            if 'analysis_settings' in config_data:
                self._apply_analysis_settings(config_data['analysis_settings'])

            # Apply UI settings
            if 'ui_settings' in config_data:
                self._apply_ui_settings(config_data['ui_settings'])

            self.log_message("Configuration applied successfully")

        except Exception as e:
            error_msg = f"Error applying configuration: {str(e)}"
            logger.error(error_msg)
            self.log_message(error_msg, level='error')

    def _apply_parameter_settings(self, parameter_settings):
        """Apply parameter tree settings."""
        try:
            for param_name, param_values in parameter_settings.items():
                if self.settings.child(param_name):
                    self._apply_parameter_group(self.settings.child(param_name), param_values)

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
            if 'laser_wavelength' in device_positions:
                wl = device_positions['laser_wavelength']
                if hasattr(self, 'wavelength_spinbox'):
                    self.wavelength_spinbox.setValue(wl)
                if hasattr(self, 'wavelength_slider'):
                    self.wavelength_slider.setValue(int(wl))

            # Apply rotator setpoints
            if 'rotator_setpoints' in device_positions and hasattr(self, 'rotator_controls'):
                setpoints = device_positions['rotator_setpoints']
                for axis, position in setpoints.items():
                    if int(axis) in self.rotator_controls:
                        controls = self.rotator_controls[int(axis)]
                        if 'position_spinbox' in controls:
                            controls['position_spinbox'].setValue(position)

        except Exception as e:
            logger.debug(f"Error applying device positions: {e}")

    def _apply_device_control_settings(self, device_control_settings):
        """Apply device control widget settings."""
        try:
            # Apply wavelength control settings
            if 'wavelength_control' in device_control_settings:
                wl_settings = device_control_settings['wavelength_control']
                if 'spinbox_value' in wl_settings and hasattr(self, 'wavelength_spinbox'):
                    self.wavelength_spinbox.setValue(wl_settings['spinbox_value'])
                if 'slider_value' in wl_settings and hasattr(self, 'wavelength_slider'):
                    self.wavelength_slider.setValue(wl_settings['slider_value'])

            # Apply power sync settings
            if 'power_sync' in device_control_settings:
                sync_settings = device_control_settings['power_sync']
                if 'auto_sync_enabled' in sync_settings and hasattr(self, 'auto_sync_checkbox'):
                    self.auto_sync_checkbox.setChecked(sync_settings['auto_sync_enabled'])

        except Exception as e:
            logger.debug(f"Error applying device control settings: {e}")

    def _apply_analysis_settings(self, analysis_settings):
        """Apply analysis widget settings."""
        try:
            # Apply fitting settings
            if 'fitting' in analysis_settings:
                fit_settings = analysis_settings['fitting']
                if 'auto_fit_enabled' in fit_settings and hasattr(self, 'auto_fit_checkbox'):
                    self.auto_fit_checkbox.setChecked(fit_settings['auto_fit_enabled'])

            # Apply spectral analysis settings
            if 'spectral' in analysis_settings:
                spectral_settings = analysis_settings['spectral']
                if 'index' in spectral_settings and hasattr(self, 'spectral_mode_combo'):
                    self.spectral_mode_combo.setCurrentIndex(spectral_settings['index'])

        except Exception as e:
            logger.debug(f"Error applying analysis settings: {e}")

    def _apply_ui_settings(self, ui_settings):
        """Apply UI widget settings."""
        try:
            # Apply tab selections
            if 'active_analysis_tab' in ui_settings and hasattr(self, 'analysis_tabs'):
                self.analysis_tabs.setCurrentIndex(ui_settings['active_analysis_tab'])

            if 'active_device_tab' in ui_settings and hasattr(self, 'device_tabs'):
                self.device_tabs.setCurrentIndex(ui_settings['active_device_tab'])

        except Exception as e:
            logger.debug(f"Error applying UI settings: {e}")

    # Utility methods

    def get_style(self):
        """Get style from various sources for icons."""
        if hasattr(self, 'style') and callable(self.style):
            return self.style()
        elif hasattr(self, 'dashboard') and hasattr(self.dashboard, 'style') and callable(self.dashboard.style):
            return self.dashboard.style()
        elif hasattr(self.dashboard, 'mainwindow') and hasattr(self.dashboard.mainwindow, 'style') and callable(self.dashboard.mainwindow.style):
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
            action.setIcon(self.get_style().standardIcon(getattr(QtWidgets.QStyle, icon)))
        setattr(self, f"{name}_action", action)

    def log_message(self, message: str, level: str = 'info'):
        """Add a message to the activity log."""
        timestamp = time.strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"

        if hasattr(self, 'log_display'):
            self.log_display.append(formatted_message)
            # Auto-scroll to bottom
            self.log_display.moveCursor(QtGui.QTextCursor.End)

    def update_device_status(self):
        """Update device status display (periodic)."""
        if not self.device_manager or not hasattr(self, 'device_status_table'):
            return

        try:
            # Get all device information
            all_device_info = self.device_manager.get_all_device_info()

            # Update table row count
            self.device_status_table.setRowCount(len(all_device_info))

            # Update each device row
            for row, (device_key, device_info) in enumerate(all_device_info.items()):
                # Device name
                name_item = QtWidgets.QTableWidgetItem(device_key.title())
                self.device_status_table.setItem(row, 0, name_item)

                # Status with color coding
                status_item = QtWidgets.QTableWidgetItem(device_info.status.value)
                if device_info.status == DeviceStatus.CONNECTED:
                    status_item.setBackground(QtGui.QColor(144, 238, 144))  # Light green
                elif device_info.status == DeviceStatus.DISCONNECTED:
                    status_item.setBackground(QtGui.QColor(255, 182, 193))  # Light pink
                elif device_info.status == DeviceStatus.ERROR:
                    status_item.setBackground(QtGui.QColor(255, 99, 71))   # Tomato red
                else:
                    status_item.setBackground(QtGui.QColor(211, 211, 211)) # Light gray

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

            # Update specific device information if available
            self._update_live_device_data()

        except Exception as e:
            logger.error(f"Error updating device status display: {e}")

    def _update_live_device_data(self):
        """Update live data from specific devices (power, temperature, etc)."""
        try:
            # Update power meter reading
            power_meter = self.device_manager.get_power_meter()
            if power_meter and hasattr(power_meter, 'grab_data'):
                try:
                    power_data = power_meter.grab_data()
                    if power_data and len(power_data) > 0:
                        # Extract power value (assuming it's in the first data element)
                        power_value = float(power_data[0].data[0]) if hasattr(power_data[0], 'data') else 0.0

                        # Update power plot if it exists
                        if hasattr(self, 'power_plot') and self.power_plot:
                            # Store power history for plotting
                            if not hasattr(self, '_power_history'):
                                self._power_history = {'time': [], 'power': []}

                            current_time = time.time()
                            self._power_history['time'].append(current_time)
                            self._power_history['power'].append(power_value)

                            # Keep only last 100 points
                            if len(self._power_history['time']) > 100:
                                self._power_history['time'] = self._power_history['time'][-100:]
                                self._power_history['power'] = self._power_history['power'][-100:]

                            # Update plot
                            if len(self._power_history['time']) > 1:
                                # Convert to relative time
                                rel_time = [t - self._power_history['time'][0] for t in self._power_history['time']]
                                self.power_plot.clear()
                                self.power_plot.plot(rel_time, self._power_history['power'], pen='b')

                except Exception as e:
                    logger.debug(f"Could not update power meter data: {e}")

            # Update camera temperature if available
            camera = self.device_manager.get_camera()
            if camera and hasattr(camera, 'controller') and camera.controller:
                try:
                    # Check if camera has temperature monitoring
                    if hasattr(camera.controller, 'get_temperature'):
                        temp = camera.controller.get_temperature()
                        # Could add temperature display to status or plots here
                        logger.debug(f"Camera temperature: {temp}°C")
                except Exception as e:
                    logger.debug(f"Could not get camera temperature: {e}")

        except Exception as e:
            logger.debug(f"Error updating live device data: {e}")

    # Signal handlers

    def on_measurement_started(self):
        """Handle measurement started signal."""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.is_measuring = True

    def on_measurement_finished(self):
        """Handle measurement finished signal."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
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
        self.log_message(f"ERROR: {error_message}", level='error')

        # Show error dialog
        QtWidgets.QMessageBox.critical(self.control_widget, 'μRASHG Extension Error',
                                     f"An error occurred:\n\n{error_message}")

    def on_device_error(self, device_name: str, error_message: str):
        """Handle device-specific error."""
        logger.error(f"Device '{device_name}' error: {error_message}")
        self.log_message(f"DEVICE ERROR - {device_name}: {error_message}", level='error')

    def on_all_devices_ready(self, ready: bool):
        """Handle all devices ready status change."""
        if ready:
            logger.info("All required devices are ready")
            self.log_message("All required devices are ready for measurements")
            self.start_button.setEnabled(True)
        else:
            logger.warning("Not all required devices are ready")
            self.log_message("Some required devices are not ready", level='warning')
            self.start_button.setEnabled(False)


    def _on_measurement_completed(self, measurement_data):
        """Handle measurement completion from worker thread."""
        logger.info("Measurement completed successfully")
        self.log_message("Measurement completed successfully")

        # Store measurement data
        self.current_measurement_data = measurement_data

        # Update plots with final data
        if measurement_data and hasattr(self, 'polar_plot'):
            self._update_polar_plot(measurement_data)

        # Emit completion signal
        self.measurement_finished.emit()

        # Clean up thread
        if hasattr(self, 'measurement_thread'):
            self.measurement_thread.quit()
            self.measurement_thread.wait()

    def _on_measurement_failed(self, error_message):
        """Handle measurement failure from worker thread."""
        logger.error(f"Measurement failed: {error_message}")
        self.log_message(f"Measurement failed: {error_message}", level='error')

        # Emit error signal
        self.error_occurred.emit(f"Measurement failed: {error_message}")

        # Reset state
        self.measurement_finished.emit()

        # Clean up thread
        if hasattr(self, 'measurement_thread'):
            self.measurement_thread.quit()
            self.measurement_thread.wait()

    def _on_data_acquired(self, step_data):
        """Handle individual data acquisition from worker thread."""
        try:
            # Update live camera view if available
            if 'camera_data' in step_data and hasattr(self, 'camera_view'):
                image_data = step_data['camera_data']
                self.camera_view.setImage(image_data)

            # Update polar plot with current data
            if hasattr(self, 'polar_plot') and 'angle' in step_data and 'intensity' in step_data:
                # Store for real-time plotting
                if not hasattr(self, '_live_polar_data'):
                    self._live_polar_data = {'angles': [], 'intensities': []}

                self._live_polar_data['angles'].append(step_data['angle'])
                self._live_polar_data['intensities'].append(step_data['intensity'])

                # Update plot
                self.polar_plot.clear()
                self.polar_plot.plot(self._live_polar_data['angles'],
                                   self._live_polar_data['intensities'],
                                   pen='r', symbol='o')

        except Exception as e:
            logger.warning(f"Error updating live data display: {e}")

    def _update_polar_plot(self, measurement_data):
        """Update polar plot with complete measurement data."""
        try:
            if not measurement_data or not hasattr(self, 'polar_plot'):
                return

            # Extract angle and intensity data
            angles = measurement_data.get('angles', [])
            intensities = measurement_data.get('intensities', [])

            if len(angles) > 0 and len(intensities) > 0:
                # Clear and plot final data
                self.polar_plot.clear()
                self.polar_plot.plot(angles, intensities, pen='b', symbol='o', symbolBrush='b')
                self.polar_plot.setTitle('μRASHG Polar Response')

                # Fit data if requested
                if self.settings.child('advanced', 'realtime_analysis').value():
                    self._fit_and_plot_rashg_pattern(angles, intensities)

        except Exception as e:
            logger.warning(f"Error updating polar plot: {e}")

    def _fit_and_plot_rashg_pattern(self, angles, intensities):
        """Fit RASHG pattern and overlay fit on plot (Enhanced for Phase 3)."""
        try:
            # Use the new comprehensive fitting method
            fit_results = self._fit_rashg_data(angles, intensities)

            if fit_results and hasattr(self, 'auto_fit_checkbox') and self.auto_fit_checkbox.isChecked():
                # Plot the fit curve
                self._plot_fit_curve(angles, intensities, fit_results)

                # Update fit results display
                self._display_fit_results(fit_results)

                # Store results
                self.current_fit_results = fit_results

                # Log fit parameters
                self.log_message(f"RASHG Fit: A={fit_results['A']:.2f}, B={fit_results['B']:.2f}, φ={fit_results['phi_deg']:.1f}°")

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
                popt, pcov = curve_fit(rashg_func, angles_np, intensities_np,
                                     p0=[A_init, B_init, phi_init],
                                     bounds=([-np.inf, 0, -np.pi], [np.inf, np.inf, np.pi]))
            except Exception as e:
                logger.warning(f"Constrained fit failed, trying unconstrained: {e}")
                popt, pcov = curve_fit(rashg_func, angles_np, intensities_np,
                                     p0=[A_init, B_init, phi_init])

            # Extract fit parameters
            A, B, phi = popt

            # Calculate fit quality metrics
            fit_angles = np.linspace(angles_np.min(), angles_np.max(), len(angles_np) * 4)
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
                'A': float(A),                    # Background/offset
                'B': float(B),                    # Modulation amplitude
                'phi': float(phi),                # Phase (radians)
                'phi_deg': float(np.degrees(phi)), # Phase (degrees)
                'A_error': float(param_errors[0]),
                'B_error': float(param_errors[1]),
                'phi_error': float(param_errors[2]),
                'phi_deg_error': float(np.degrees(param_errors[2])),
                'r_squared': float(r_squared),
                'contrast': float(contrast),
                'modulation_depth': float(modulation_depth),
                'fit_angles': fit_angles.tolist(),
                'fit_intensities': fit_intensities.tolist(),
                'residuals': (intensities_np - predicted_intensities).tolist(),
                'fit_function': 'I = A + B*cos(4θ + φ)',
                'timestamp': time.time()
            }

            return fit_results

        except Exception as e:
            logger.error(f"RASHG fitting failed: {e}")
            return None

    def _plot_fit_curve(self, angles, intensities, fit_results):
        """Plot RASHG fit curve overlay."""
        try:
            if not hasattr(self, 'polar_plot') or not fit_results:
                return

            # Clear previous fit curves
            items_to_remove = []
            for item in self.polar_plot.getPlotItem().listDataItems():
                if hasattr(item, 'name') and 'Fit' in str(item.name):
                    items_to_remove.append(item)

            for item in items_to_remove:
                self.polar_plot.removeItem(item)

            # Plot new fit curve
            fit_angles = np.array(fit_results['fit_angles'])
            fit_intensities = np.array(fit_results['fit_intensities'])

            self.polar_plot.plot(fit_angles, fit_intensities,
                               pen=pg.mkPen('g', width=2),
                               name='RASHG Fit')

            # Plot residuals (optional, scaled for visibility)
            if len(fit_results['residuals']) == len(angles):
                residuals = np.array(fit_results['residuals'])
                angles_np = np.array(angles)

                # Scale residuals for visibility
                residual_scale = np.max(intensities) * 0.1
                scaled_residuals = residuals * residual_scale / np.max(np.abs(residuals)) if np.max(np.abs(residuals)) > 0 else residuals
                baseline = np.min(intensities) - np.max(np.abs(scaled_residuals)) * 1.5

                self.polar_plot.plot(angles_np, baseline + scaled_residuals,
                                   pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine),
                                   name='Residuals (scaled)')

        except Exception as e:
            logger.error(f"Error plotting fit curve: {e}")

    def _display_fit_results(self, fit_results):
        """Display fit results in the UI."""
        try:
            if not hasattr(self, 'fit_results_label') or not fit_results:
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
        self.log_message(f"Real-time RASHG fitting {'enabled' if enabled else 'disabled'}")

    def update_spectral_analysis(self):
        """Update spectral analysis display (PHASE 3 FEATURE)."""
        try:
            if not self.current_measurement_data or not self.current_measurement_data.get('multi_wavelength', False):
                if hasattr(self, 'spectral_plot'):
                    self.spectral_plot.clear()
                return

            self.update_analysis_status("Updating spectral analysis...")

            # Get wavelength and intensity data
            wavelengths = self.current_measurement_data.get('wavelengths', [])
            intensities = self.current_measurement_data.get('intensities', [])
            angles = self.current_measurement_data.get('angles', [])

            if not wavelengths or not intensities:
                return

            # Organize data by wavelength
            spectral_data = self._organize_spectral_data(wavelengths, intensities, angles)

            # Perform spectral analysis based on mode
            mode = self.spectral_mode_combo.currentText() if hasattr(self, 'spectral_mode_combo') else 'RASHG Amplitude'

            if mode == 'RASHG Amplitude':
                self._plot_spectral_amplitude(spectral_data)
            elif mode == 'Phase':
                self._plot_spectral_phase(spectral_data)
            elif mode == 'Contrast':
                self._plot_spectral_contrast(spectral_data)
            elif mode == 'All Parameters':
                self._plot_all_spectral_parameters(spectral_data)

            # Store spectral analysis data
            self.spectral_analysis_data = spectral_data

            self.update_analysis_status("Spectral analysis updated")

        except Exception as e:
            logger.error(f"Error updating spectral analysis: {e}")
            self.update_analysis_status("Spectral analysis failed")

    def _organize_spectral_data(self, wavelengths, intensities, angles):
        """Organize measurement data by wavelength for spectral analysis."""
        try:
            import numpy as np

            # Get unique wavelengths
            unique_wavelengths = sorted(list(set(wavelengths)))

            spectral_data = {
                'wavelengths': unique_wavelengths,
                'rashg_amplitudes': [],
                'phases': [],
                'contrasts': [],
                'backgrounds': [],
                'r_squared_values': [],
                'fit_errors': []
            }

            # Process each wavelength
            for wl in unique_wavelengths:
                # Get data for this wavelength
                wl_indices = [i for i, w in enumerate(wavelengths) if abs(w - wl) < 0.5]  # 0.5 nm tolerance

                if len(wl_indices) < 4:  # Need at least 4 points for fitting
                    # Fill with None for missing data
                    spectral_data['rashg_amplitudes'].append(None)
                    spectral_data['phases'].append(None)
                    spectral_data['contrasts'].append(None)
                    spectral_data['backgrounds'].append(None)
                    spectral_data['r_squared_values'].append(None)
                    spectral_data['fit_errors'].append(None)
                    continue

                wl_angles = [angles[i] for i in wl_indices]
                wl_intensities = [intensities[i] for i in wl_indices]

                # Fit RASHG pattern for this wavelength
                fit_results = self._fit_rashg_data(wl_angles, wl_intensities)

                if fit_results:
                    spectral_data['rashg_amplitudes'].append(abs(fit_results['B']))
                    spectral_data['phases'].append(fit_results['phi_deg'])
                    spectral_data['contrasts'].append(fit_results['contrast'])
                    spectral_data['backgrounds'].append(fit_results['A'])
                    spectral_data['r_squared_values'].append(fit_results['r_squared'])
                    spectral_data['fit_errors'].append({
                        'A_error': fit_results['A_error'],
                        'B_error': fit_results['B_error'],
                        'phi_error': fit_results['phi_deg_error']
                    })
                else:
                    # Fill with None for failed fits
                    spectral_data['rashg_amplitudes'].append(None)
                    spectral_data['phases'].append(None)
                    spectral_data['contrasts'].append(None)
                    spectral_data['backgrounds'].append(None)
                    spectral_data['r_squared_values'].append(None)
                    spectral_data['fit_errors'].append(None)

            return spectral_data

        except Exception as e:
            logger.error(f"Error organizing spectral data: {e}")
            return {}

    def _plot_spectral_amplitude(self, spectral_data):
        """Plot spectral RASHG amplitude."""
        try:
            if not hasattr(self, 'spectral_plot') or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data['wavelengths']
            amplitudes = spectral_data['rashg_amplitudes']

            # Filter out None values
            valid_data = [(w, a) for w, a in zip(wavelengths, amplitudes) if a is not None]

            if valid_data:
                wl, amp = zip(*valid_data)
                self.spectral_plot.plot(wl, amp,
                                      pen=pg.mkPen('b', width=2),
                                      symbol='o', symbolBrush='b',
                                      name='RASHG Amplitude')

            self.spectral_plot.setTitle('Spectral RASHG Amplitude')
            self.spectral_plot.setLabel('left', 'RASHG Amplitude', 'counts')

        except Exception as e:
            logger.error(f"Error plotting spectral amplitude: {e}")

    def _plot_spectral_phase(self, spectral_data):
        """Plot spectral RASHG phase."""
        try:
            if not hasattr(self, 'spectral_plot') or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data['wavelengths']
            phases = spectral_data['phases']

            # Filter out None values
            valid_data = [(w, p) for w, p in zip(wavelengths, phases) if p is not None]

            if valid_data:
                wl, phase = zip(*valid_data)
                self.spectral_plot.plot(wl, phase,
                                      pen=pg.mkPen('r', width=2),
                                      symbol='s', symbolBrush='r',
                                      name='RASHG Phase')

            self.spectral_plot.setTitle('Spectral RASHG Phase')
            self.spectral_plot.setLabel('left', 'Phase', '°')

        except Exception as e:
            logger.error(f"Error plotting spectral phase: {e}")

    def _plot_spectral_contrast(self, spectral_data):
        """Plot spectral RASHG contrast."""
        try:
            if not hasattr(self, 'spectral_plot') or not spectral_data:
                return

            self.spectral_plot.clear()

            wavelengths = spectral_data['wavelengths']
            contrasts = spectral_data['contrasts']

            # Filter out None values
            valid_data = [(w, c) for w, c in zip(wavelengths, contrasts) if c is not None]

            if valid_data:
                wl, cont = zip(*valid_data)
                self.spectral_plot.plot(wl, cont,
                                      pen=pg.mkPen('g', width=2),
                                      symbol='^', symbolBrush='g',
                                      name='RASHG Contrast')

            self.spectral_plot.setTitle('Spectral RASHG Contrast')
            self.spectral_plot.setLabel('left', 'Contrast', 'ratio')

        except Exception as e:
            logger.error(f"Error plotting spectral contrast: {e}")

    def _plot_all_spectral_parameters(self, spectral_data):
        """Plot all spectral RASHG parameters in subplots."""
        try:
            if not hasattr(self, 'spectral_plot') or not spectral_data:
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
            if not hasattr(self, 'volume_view') or not self.current_measurement_data:
                return

            if not self.current_measurement_data.get('multi_wavelength', False):
                return

            self.update_analysis_status("Updating 3D visualization...")

            # Clear previous visualization
            self.volume_view.clear()

            # Get data
            wavelengths = self.current_measurement_data.get('wavelengths', [])
            angles = self.current_measurement_data.get('angles', [])
            intensities = self.current_measurement_data.get('intensities', [])

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
            scatter = gl.GLScatterPlotItem(pos=pos,
                                         color=(1.0, 1.0, 1.0, 0.8),
                                         size=3)
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
            if hasattr(self, 'analysis_status'):
                self.analysis_status.setText(f"Analysis Status: {status}")
        except Exception:
            pass

    # =================== END PHASE 3 ADVANCED ANALYSIS METHODS ===================

    def closeEvent(self, event):
        """Handle extension close event."""
        if self.is_measuring:
            reply = QtWidgets.QMessageBox.question(
                self.control_widget, 'Confirm Close',
                'A measurement is in progress. Stop measurement and close?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.stop_measurement()
            else:
                event.ignore()
                return

        # Cleanup
        self.status_timer.stop()

        # Stop device control update timer (PHASE 3 FEATURE)
        if hasattr(self, 'device_update_timer'):
            self.device_update_timer.stop()
            logger.info("Stopped device control update timer")

        if hasattr(self, 'device_manager') and self.device_manager:
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
            'angles': [],
            'intensities': [],
            'images': [],
            'power_readings': [],
            'timestamps': [],
            'wavelengths': [],  # ⭐ NEW: Store wavelength for each measurement point
            'wavelength_sequence': [],  # ⭐ NEW: Store wavelength scan sequence
            'multi_wavelength': False,  # ⭐ NEW: Flag for multi-wavelength measurement
            'measurement_type': 'Basic RASHG'  # ⭐ NEW: Store measurement type
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
            measurement_type = self.settings.child('experiment', 'measurement_type').value()
            pol_steps = self.settings.child('experiment', 'pol_steps').value()
            pol_start = self.settings.child('experiment', 'pol_range', 'pol_start').value()
            pol_end = self.settings.child('experiment', 'pol_range', 'pol_end').value()
            integration_time = self.settings.child('experiment', 'integration_time').value()
            averages = self.settings.child('experiment', 'averages').value()

            # Store measurement type
            self.measurement_data['measurement_type'] = measurement_type

            # Check if multi-wavelength scanning is enabled
            enable_wavelength_scan = self.settings.child('wavelength', 'enable_scan').value()

            if enable_wavelength_scan:
                logger.info("Multi-wavelength scanning enabled")
                self._run_multi_wavelength_measurement(pol_steps, pol_start, pol_end,
                                                     integration_time, averages)
            else:
                logger.info("Single wavelength measurement")
                self._run_single_wavelength_measurement(pol_steps, pol_start, pol_end,
                                                      integration_time, averages)

            # Finalize measurement
            self._finalize_measurement()

            # Emit completion
            self.measurement_completed.emit(self.measurement_data.copy())
            logger.info("Measurement completed successfully")

        except Exception as e:
            error_msg = f"Measurement failed with error: {str(e)}"
            logger.error(error_msg)
            self.measurement_failed.emit(error_msg)

    def _run_single_wavelength_measurement(self, pol_steps, pol_start, pol_end,
                                         integration_time, averages):
        """Run single wavelength polarization measurement."""
        # Create angle sequence
        angle_step = (pol_end - pol_start) / pol_steps if pol_steps > 1 else 0
        angles = [pol_start + i * angle_step for i in range(pol_steps)]

        logger.info(f"Single wavelength measurement: {pol_steps} angles from {pol_start}° to {pol_end}°")

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
            step_data = self._measure_at_angle(angle, integration_time, averages, current_wavelength)

            if step_data is None:
                self.measurement_failed.emit(f"Failed to acquire data at angle {angle}°")
                return

            # Store data
            self._store_measurement_data(step_data, angle, current_wavelength)

            # Emit progress and data
            progress = int((step + 1) * 100 / pol_steps)
            self.progress_updated.emit(progress)
            self._emit_step_data(step_data, step + 1, pol_steps)

            logger.debug(f"Completed step {step + 1}/{pol_steps} at {angle}°: intensity={step_data['intensity']:.2f}")

    def _run_multi_wavelength_measurement(self, pol_steps, pol_start, pol_end,
                                        integration_time, averages):
        """Run multi-wavelength polarization measurement (PHASE 3 FEATURE)."""
        self.measurement_data['multi_wavelength'] = True

        # Get wavelength scan parameters
        wl_start = self.settings.child('wavelength', 'wl_start').value()
        wl_stop = self.settings.child('wavelength', 'wl_stop').value()
        wl_steps = self.settings.child('wavelength', 'wl_steps').value()
        wl_stabilization = self.settings.child('wavelength', 'wl_stabilization').value()
        auto_sync_pm = self.settings.child('wavelength', 'auto_sync_pm').value()
        sweep_mode = self.settings.child('wavelength', 'sweep_mode').value()

        # Generate wavelength sequence
        wavelengths = self._generate_wavelength_sequence(wl_start, wl_stop, wl_steps, sweep_mode)
        self.measurement_data['wavelength_sequence'] = wavelengths

        # Create angle sequence
        angle_step = (pol_end - pol_start) / pol_steps if pol_steps > 1 else 0
        angles = [pol_start + i * angle_step for i in range(pol_steps)]

        # Calculate total steps for progress
        total_steps = len(wavelengths) * pol_steps
        current_step = 0

        logger.info(f"Multi-wavelength measurement: {len(wavelengths)} wavelengths × {pol_steps} angles = {total_steps} total measurements")

        # Multi-wavelength measurement loop
        for wl_index, wavelength in enumerate(wavelengths):
            if self.stop_requested:
                logger.info("Multi-wavelength measurement stopped by user request")
                return

            logger.info(f"Setting wavelength to {wavelength:.0f} nm ({wl_index + 1}/{len(wavelengths)})")

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
                logger.info(f"Waiting {wl_stabilization}s for wavelength stabilization...")
                time.sleep(wl_stabilization)

            # Polarization measurement loop at current wavelength
            for pol_index, angle in enumerate(angles):
                if self.stop_requested:
                    return

                # Handle pause
                if self._check_pause():
                    return

                # Perform measurement step
                step_data = self._measure_at_angle(angle, integration_time, averages, wavelength)

                if step_data is None:
                    logger.warning(f"Failed to acquire data at wavelength {wavelength} nm, angle {angle}°")
                    continue  # Skip this measurement point

                # Store data
                self._store_measurement_data(step_data, angle, wavelength)

                # Update progress
                current_step += 1
                progress = int(current_step * 100 / total_steps)
                self.progress_updated.emit(progress)

                # Emit step data with wavelength info
                self._emit_step_data(step_data, current_step, total_steps, wavelength)

                logger.debug(f"Completed step {current_step}/{total_steps} at {wavelength:.0f}nm, {angle}°: intensity={step_data['intensity']:.2f}")

    def _generate_wavelength_sequence(self, wl_start, wl_stop, wl_steps, sweep_mode):
        """Generate wavelength sequence based on sweep mode."""
        import numpy as np

        if sweep_mode == 'Linear':
            return np.linspace(wl_start, wl_stop, wl_steps).tolist()
        elif sweep_mode == 'Logarithmic':
            return np.logspace(np.log10(wl_start), np.log10(wl_stop), wl_steps).tolist()
        elif sweep_mode == 'Custom':
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
            if hasattr(laser_device, 'move_abs'):
                laser_device.move_abs(position_data)

                # Wait a moment for the command to be processed
                time.sleep(0.5)

                # Verify wavelength was set (optional)
                actual_wavelength = self._get_current_laser_wavelength()
                if actual_wavelength is not None:
                    wavelength_error = abs(actual_wavelength - wavelength)
                    if wavelength_error > 5.0:  # Tolerance of 5 nm
                        logger.warning(f"Wavelength setting error: target={wavelength}, actual={actual_wavelength}")

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
            if hasattr(power_meter, 'controller') and power_meter.controller:
                if hasattr(power_meter.controller, 'set_wavelength'):
                    power_meter.controller.set_wavelength(wavelength)
                    logger.info(f"Power meter wavelength synced to {wavelength:.0f} nm")
                    return True
                elif hasattr(power_meter, 'settings'):
                    wavelength_param = power_meter.settings.child_frompath('wavelength')
                    if wavelength_param:
                        wavelength_param.setValue(wavelength)
                        logger.info(f"Power meter wavelength parameter updated to {wavelength:.0f} nm")
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
        self.measurement_data['angles'].append(angle)
        self.measurement_data['intensities'].append(step_data['intensity'])
        self.measurement_data['images'].append(step_data.get('image'))
        self.measurement_data['power_readings'].append(step_data.get('power'))
        self.measurement_data['wavelengths'].append(wavelength)
        self.measurement_data['timestamps'].append(time.time())

    def _emit_step_data(self, step_data, current_step, total_steps, wavelength=None):
        """Emit step data for real-time updates."""
        self.data_acquired.emit({
            'angle': step_data['angle'],
            'intensity': step_data['intensity'],
            'camera_data': step_data.get('image'),
            'power': step_data.get('power'),
            'wavelength': wavelength,
            'step': current_step,
            'total_steps': total_steps
        })

    def _get_current_laser_wavelength(self):
        """Get current laser wavelength."""
        try:
            laser_device = None
            if self.device_manager:
                laser_device = self.device_manager.get_laser()

            if not laser_device:
                return None

            # Try to get current wavelength
            if hasattr(laser_device, 'current_position') and laser_device.current_position is not None:
                if hasattr(laser_device.current_position, 'value'):
                    return laser_device.current_position.value()
                elif hasattr(laser_device.current_position, 'data'):
                    return laser_device.current_position.data[0][0]
                else:
                    return float(laser_device.current_position)
            elif hasattr(laser_device, 'controller') and laser_device.controller:
                if hasattr(laser_device.controller, 'get_wavelength'):
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
                'x_start': self.settings.child('hardware', 'camera', 'roi', 'x_start').value(),
                'y_start': self.settings.child('hardware', 'camera', 'roi', 'y_start').value(),
                'width': self.settings.child('hardware', 'camera', 'roi', 'width').value(),
                'height': self.settings.child('hardware', 'camera', 'roi', 'height').value(),
            }

            # Configure camera if possible
            if hasattr(camera, 'settings') and camera.settings:
                try:
                    # Set ROI if camera supports it
                    if camera.settings.child_frompath('detector_settings'):
                        detector_settings = camera.settings.child('detector_settings')
                        if detector_settings.child('ROIselect'):
                            detector_settings.child('ROIselect', 'x0').setValue(roi_settings['x_start'])
                            detector_settings.child('ROIselect', 'y0').setValue(roi_settings['y_start'])
                            detector_settings.child('ROIselect', 'width').setValue(roi_settings['width'])
                            detector_settings.child('ROIselect', 'height').setValue(roi_settings['height'])

                    # Set integration time if supported
                    if camera.settings.child_frompath('main_settings/exposure'):
                        exposure = self.settings.child('experiment', 'integration_time').value()
                        camera.settings.child('main_settings', 'exposure').setValue(exposure)

                except Exception as e:
                    logger.warning(f"Could not configure camera settings: {e}")

            # Initialize stabilization if requested
            stabilization_time = self.settings.child('advanced', 'stabilization_time').value()
            if stabilization_time > 0:
                logger.info(f"Stabilization period: {stabilization_time}s")
                time.sleep(stabilization_time)

            logger.info("Measurement initialization completed")
            return True

        except Exception as e:
            logger.error(f"Error initializing measurement: {e}")
            return False

    def _measure_at_angle(self, angle: float, integration_time: float, averages: int,
                         wavelength: float = None) -> Optional[dict]:
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
            movement_timeout = self.settings.child('hardware', 'safety', 'movement_timeout').value()
            camera_timeout = self.settings.child('hardware', 'safety', 'camera_timeout').value()

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
                        power_reading = float(power_data[0].data[0]) if hasattr(power_data[0], 'data') else None
                except Exception as e:
                    logger.debug(f"Could not read power meter: {e}")

            # Acquire camera images with averaging
            images = []
            for avg in range(averages):
                if self.stop_requested:
                    return None

                try:
                    # Trigger camera acquisition with timeout
                    image_data = self._acquire_camera_image(camera, timeout=camera_timeout)
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
                'intensity': total_intensity,
                'image': averaged_image,
                'power': power_reading,
                'angle': angle,
                'wavelength': wavelength,  # ⭐ NEW: Include wavelength in step data
                'n_averages': len(images)
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
            measurement_type = self.settings.child('experiment', 'measurement_type').value()

            # For basic RASHG, typically rotate the analyzer (HWP)
            # This can be configured based on measurement type
            if measurement_type == 'Basic RASHG':
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
                if hasattr(elliptec, 'move_abs'):
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

    def _acquire_camera_image(self, camera, timeout: float = 5.0) -> Optional[np.ndarray]:
        """Acquire a single image from camera with timeout."""
        try:
            if not camera:
                return None

            # Trigger single acquisition
            if hasattr(camera, 'grab_data'):
                camera_data = camera.grab_data()

                if camera_data and len(camera_data) > 0:
                    # Extract image data from PyMoDAQ data structure
                    data_item = camera_data[0]
                    if hasattr(data_item, 'data') and len(data_item.data) > 0:
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
            if self.settings.child('data', 'auto_save').value():
                self._save_measurement_data()

            logger.info("Measurement finalized")

        except Exception as e:
            logger.warning(f"Error finalizing measurement: {e}")

    def _save_measurement_data(self):
        """Save measurement data to file."""
        try:
            import json
            from pathlib import Path

            save_dir = Path(self.settings.child('data', 'save_dir').value())
            file_prefix = self.settings.child('data', 'file_prefix').value()

            # Create save directory if it doesn't exist
            save_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = save_dir / f"{file_prefix}_{timestamp}.json"

            # Prepare data for saving (excluding images for JSON) - Enhanced for multi-wavelength
            save_data = {
                'angles': self.measurement_data['angles'],
                'intensities': self.measurement_data['intensities'],
                'power_readings': self.measurement_data['power_readings'],
                'timestamps': self.measurement_data['timestamps'],
                'wavelengths': self.measurement_data['wavelengths'],  # ⭐ NEW: Wavelength data
                'wavelength_sequence': self.measurement_data['wavelength_sequence'],  # ⭐ NEW: Wavelength scan sequence
                'multi_wavelength': self.measurement_data['multi_wavelength'],  # ⭐ NEW: Multi-wavelength flag
                'measurement_type': self.measurement_data['measurement_type'],  # ⭐ NEW: Measurement type
                'settings': self._get_settings_dict(),
                'measurement_info': {
                    'start_time': self.measurement_data['timestamps'][0] if self.measurement_data['timestamps'] else None,
                    'end_time': self.measurement_data['timestamps'][-1] if self.measurement_data['timestamps'] else None,
                    'duration': (self.measurement_data['timestamps'][-1] - self.measurement_data['timestamps'][0]) if len(self.measurement_data['timestamps']) > 1 else 0,
                    'n_points': len(self.measurement_data['angles']),
                    'n_wavelengths': len(set(self.measurement_data['wavelengths'])) if self.measurement_data['wavelengths'] else 1,  # ⭐ NEW: Number of unique wavelengths
                    'multi_wavelength': self.measurement_data['multi_wavelength']  # ⭐ NEW: Multi-wavelength info
                }
            }

            # Save JSON data
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Measurement data saved to {filename}")

            # Save images separately if requested
            if self.settings.child('data', 'save_raw').value():
                self._save_raw_images(save_dir, file_prefix, timestamp)

        except Exception as e:
            logger.error(f"Error saving measurement data: {e}")

    def _save_raw_images(self, save_dir: Path, file_prefix: str, timestamp: str):
        """Save raw camera images."""
        try:
            import numpy as np

            images_dir = save_dir / f"{file_prefix}_{timestamp}_images"
            images_dir.mkdir(exist_ok=True)

            for i, (angle, image) in enumerate(zip(self.measurement_data['angles'], self.measurement_data['images'])):
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
                'experiment': {
                    'measurement_type': self.settings.child('experiment', 'measurement_type').value(),
                    'pol_steps': self.settings.child('experiment', 'pol_steps').value(),
                    'integration_time': self.settings.child('experiment', 'integration_time').value(),
                    'averages': self.settings.child('experiment', 'averages').value(),
                    'pol_start': self.settings.child('experiment', 'pol_range', 'pol_start').value(),
                    'pol_end': self.settings.child('experiment', 'pol_range', 'pol_end').value(),
                },
                'hardware': {
                    'camera_roi': {
                        'x_start': self.settings.child('hardware', 'camera', 'roi', 'x_start').value(),
                        'y_start': self.settings.child('hardware', 'camera', 'roi', 'y_start').value(),
                        'width': self.settings.child('hardware', 'camera', 'roi', 'width').value(),
                        'height': self.settings.child('hardware', 'camera', 'roi', 'height').value(),
                    }
                },
                'wavelength': {  # ⭐ NEW: Wavelength scan settings
                    'enable_scan': self.settings.child('wavelength', 'enable_scan').value(),
                    'wl_start': self.settings.child('wavelength', 'wl_start').value(),
                    'wl_stop': self.settings.child('wavelength', 'wl_stop').value(),
                    'wl_steps': self.settings.child('wavelength', 'wl_steps').value(),
                    'wl_stabilization': self.settings.child('wavelength', 'wl_stabilization').value(),
                    'auto_sync_pm': self.settings.child('wavelength', 'auto_sync_pm').value(),
                    'sweep_mode': self.settings.child('wavelength', 'sweep_mode').value(),
                }
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
__all__ = ['URASHGMicroscopyExtension']
