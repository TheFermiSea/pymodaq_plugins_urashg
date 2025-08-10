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
        # Implementation in Phase 3
        
    def stop_measurement(self):
        """Stop the current measurement."""
        logger.info("Stopping measurement...")
        self.log_message("Stopping measurement...")
        # Implementation in Phase 3
    
    def pause_measurement(self):
        """Pause the current measurement."""
        logger.info("Pausing measurement...")
        self.log_message("Pausing measurement...")
        # Implementation in Phase 3
    
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
        # Implementation in Phase 2
        pass
    
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


# Export for PyMoDAQ discovery
__all__ = ['URASHGMicroscopyExtension']