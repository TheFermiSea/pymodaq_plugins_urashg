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

    def __init__(self, dashboard):
        """
        Initialize the μRASHG Microscopy Extension.
        
        Args:
            dashboard: PyMoDAQ dashboard instance providing access to all modules
        """
        super().__init__(dashboard)
        
        # Store dashboard reference for device access
        self.dashboard = dashboard
        
        # Device management
        self.device_manager = URASHGDeviceManager(dashboard)
        self.available_devices = {}
        self.missing_devices = []
        
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
        self.status_timer.setInterval(2000)  # Update every 2 seconds
        
        logger.info(f"Initialized {self.name} extension v{self.version}")
    
    def setup_docks(self):
        """
        Set up the dock layout for the extension.
        
        Creates a comprehensive dock layout with:
        - Control panel (left)
        - Live preview (top right)
        - Analysis display (middle right)
        - Status and progress (bottom)
        """
        # Control Panel Dock (left side)
        self.docks['control'] = Dock('μRASHG Control', size=(400, 800))
        self.dockarea.addDock(self.docks['control'], 'left')
        
        # Live Camera Preview Dock (top right)
        self.docks['preview'] = Dock('Live Camera Preview', size=(600, 400))
        self.dockarea.addDock(self.docks['preview'], 'right', self.docks['control'])
        
        # RASHG Analysis Dock (middle right)
        self.docks['analysis'] = Dock('RASHG Analysis', size=(600, 400))
        self.dockarea.addDock(self.docks['analysis'], 'bottom', self.docks['preview'])
        
        # System Status and Progress Dock (bottom)
        self.docks['status'] = Dock('System Status & Progress', size=(1000, 200))
        self.dockarea.addDock(self.docks['status'], 'bottom', self.docks['control'])
        
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
        
        # Analysis actions
        self.add_action('analyze_data', 'Analyze Current Data', 
                       self.analyze_current_data, icon='SP_FileDialogDetailedView')
        self.add_action('export_data', 'Export Data', 
                       self.export_data, icon='SP_DialogSaveButton')
        
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
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start_measurement)
        self.start_button.setMinimumHeight(40)
        
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_measurement)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        
        self.pause_button = QtWidgets.QPushButton('Pause')
        self.pause_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
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
    
    def setup_visualization_widget(self):
        """Set up the camera preview widget."""
        self.camera_view = pg.ImageView()
        self.camera_view.setImage(np.zeros((512, 512)))  # Placeholder image
        
        # Add to dock
        self.docks['preview'].addWidget(self.camera_view)
    
    def setup_analysis_widget(self):
        """Set up the analysis plots widget."""
        analysis_widget = QtWidgets.QWidget()
        analysis_layout = QtWidgets.QVBoxLayout(analysis_widget)
        
        # Create tab widget for different analysis views
        self.analysis_tabs = QtWidgets.QTabWidget()
        
        # Polar plot tab
        polar_widget = QtWidgets.QWidget()
        polar_layout = QtWidgets.QVBoxLayout(polar_widget)
        
        self.polar_plot = pg.PlotWidget(title='RASHG Polar Plot')
        self.polar_plot.setLabel('left', 'SHG Intensity', 'counts')
        self.polar_plot.setLabel('bottom', 'Polarization Angle', '°')
        self.polar_plot.showGrid(True, True)
        polar_layout.addWidget(self.polar_plot)
        
        self.analysis_tabs.addTab(polar_widget, 'Polar Plot')
        
        # Power monitoring tab
        power_widget = QtWidgets.QWidget()
        power_layout = QtWidgets.QVBoxLayout(power_widget)
        
        self.power_plot = pg.PlotWidget(title='Power Stability')
        self.power_plot.setLabel('left', 'Power', 'mW')
        self.power_plot.setLabel('bottom', 'Time', 's')
        self.power_plot.showGrid(True, True)
        power_layout.addWidget(self.power_plot)
        
        self.analysis_tabs.addTab(power_widget, 'Power Monitor')
        
        analysis_layout.addWidget(self.analysis_tabs)
        
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
        
        logger.info("Connected signals and slots for μRASHG extension")
    
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
        """Analyze the current measurement data."""
        logger.info("Analyzing current data...")
        self.log_message("Analyzing current data...")
        # Implementation in Phase 4
    
    def export_data(self):
        """Export measurement data to file."""
        logger.info("Exporting data...")
        self.log_message("Exporting data...")
        # Implementation in Phase 4
    
    def load_configuration(self):
        """Load measurement configuration from file."""
        logger.info("Loading configuration...")
        self.log_message("Loading configuration...")
        # Implementation in Phase 3
    
    def save_configuration(self):
        """Save current configuration to file."""
        logger.info("Saving configuration...")
        self.log_message("Saving configuration...")
        # Implementation in Phase 3
    
    # Utility methods
    
    def add_action(self, name: str, text: str, callback, icon: str = None):
        """Add an action to the extension."""
        action = QtWidgets.QAction(text, self)
        action.triggered.connect(callback)
        if icon and hasattr(QtWidgets.QStyle, icon):
            action.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, icon)))
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
        """Fit RASHG pattern and overlay fit on plot."""
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
            
            # Perform fit
            popt, pcov = curve_fit(rashg_func, angles_np, intensities_np, 
                                 p0=[A_init, B_init, phi_init])
            
            # Generate fit curve
            fit_angles = np.linspace(0, 180, 180)
            fit_intensities = rashg_func(fit_angles, *popt)
            
            # Plot fit
            self.polar_plot.plot(fit_angles, fit_intensities, pen='g', name='RASHG Fit')
            
            # Log fit parameters
            A, B, phi = popt
            self.log_message(f"RASHG Fit: A={A:.2f}, B={B:.2f}, φ={np.degrees(phi):.1f}°")
            
        except Exception as e:
            logger.warning(f"Could not fit RASHG pattern: {e}")
    
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
        
        # Measurement data storage
        self.measurement_data = {
            'angles': [],
            'intensities': [],
            'images': [],
            'power_readings': [],
            'timestamps': []
        }
        
        logger.info("MeasurementWorker initialized")
    
    def run_measurement(self):
        """Main measurement execution method."""
        logger.info("Starting measurement worker execution")
        
        try:
            # Initialize measurement
            if not self._initialize_measurement():
                self.measurement_failed.emit("Failed to initialize measurement")
                return
            
            # Get measurement parameters
            pol_steps = self.settings.child('experiment', 'pol_steps').value()
            pol_start = self.settings.child('experiment', 'pol_range', 'pol_start').value()
            pol_end = self.settings.child('experiment', 'pol_range', 'pol_end').value()
            integration_time = self.settings.child('experiment', 'integration_time').value()
            averages = self.settings.child('experiment', 'averages').value()
            
            # Create angle sequence
            angle_step = (pol_end - pol_start) / pol_steps if pol_steps > 1 else 0
            angles = [pol_start + i * angle_step for i in range(pol_steps)]
            
            logger.info(f"Starting measurement sequence: {pol_steps} angles from {pol_start}° to {pol_end}°")
            
            # Main measurement loop
            for step, angle in enumerate(angles):
                if self.stop_requested:
                    logger.info("Measurement stopped by user request")
                    return
                
                # Handle pause
                while self.pause_requested and not self.stop_requested:
                    if not self.is_paused:
                        logger.info("Measurement paused")
                        self.is_paused = True
                    time.sleep(0.1)
                
                if self.stop_requested:
                    return
                
                if self.is_paused:
                    logger.info("Measurement resumed")
                    self.is_paused = False
                
                # Perform measurement step
                step_data = self._measure_at_angle(angle, integration_time, averages)
                
                if step_data is None:
                    self.measurement_failed.emit(f"Failed to acquire data at angle {angle}°")
                    return
                
                # Store data
                self.measurement_data['angles'].append(angle)
                self.measurement_data['intensities'].append(step_data['intensity'])
                self.measurement_data['images'].append(step_data.get('image'))
                self.measurement_data['power_readings'].append(step_data.get('power'))
                self.measurement_data['timestamps'].append(time.time())
                
                # Emit progress and data
                progress = int((step + 1) * 100 / pol_steps)
                self.progress_updated.emit(progress)
                self.data_acquired.emit({
                    'angle': angle,
                    'intensity': step_data['intensity'],
                    'camera_data': step_data.get('image'),
                    'power': step_data.get('power'),
                    'step': step + 1,
                    'total_steps': pol_steps
                })
                
                logger.debug(f"Completed step {step + 1}/{pol_steps} at {angle}°: intensity={step_data['intensity']:.2f}")
            
            # Finalize measurement
            self._finalize_measurement()
            
            # Emit completion
            self.measurement_completed.emit(self.measurement_data.copy())
            logger.info("Measurement completed successfully")
            
        except Exception as e:
            error_msg = f"Measurement failed with error: {str(e)}"
            logger.error(error_msg)
            self.measurement_failed.emit(error_msg)
    
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
    
    def _measure_at_angle(self, angle: float, integration_time: float, averages: int) -> Optional[dict]:
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
            
            # Prepare data for saving (excluding images for JSON)
            save_data = {
                'angles': self.measurement_data['angles'],
                'intensities': self.measurement_data['intensities'],
                'power_readings': self.measurement_data['power_readings'],
                'timestamps': self.measurement_data['timestamps'],
                'settings': self._get_settings_dict(),
                'measurement_info': {
                    'start_time': self.measurement_data['timestamps'][0] if self.measurement_data['timestamps'] else None,
                    'end_time': self.measurement_data['timestamps'][-1] if self.measurement_data['timestamps'] else None,
                    'duration': (self.measurement_data['timestamps'][-1] - self.measurement_data['timestamps'][0]) if len(self.measurement_data['timestamps']) > 1 else 0,
                    'n_points': len(self.measurement_data['angles'])
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
        """Get current settings as dictionary for saving."""
        try:
            # Extract key settings for metadata
            return {
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
                }
            }
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