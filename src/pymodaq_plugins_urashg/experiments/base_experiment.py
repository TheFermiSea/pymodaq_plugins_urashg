"""
Base experiment class for μRASHG measurements in PyMoDAQ

This module provides the foundational URASHGBaseExperiment class that implements:
- Common parameter trees for hardware configuration
- Hardware module management and initialization
- Data structure definitions for multi-dimensional experiments
- Error handling and safety protocols
- Calibration data loading and management

All specific μRASHG experiments inherit from this base class.
"""

import os
import numpy as np
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
from datetime import datetime
import logging

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QThread

from pymodaq.utils.parameter import Parameter
from pymodaq.utils.data import DataWithAxes, DataToExport, Axis
from pymodaq.utils.enums import BaseEnum
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.dock import DockArea
from pymodaq.utils.data import DataActuator


logger = logging.getLogger(__name__)


class ExperimentState(BaseEnum):
    """Experiment execution states"""
    IDLE = "Idle"
    INITIALIZING = "Initializing"
    CALIBRATING = "Calibrating"
    RUNNING = "Running"
    PAUSED = "Paused"
    STOPPING = "Stopping"
    COMPLETED = "Completed"
    ERROR = "Error"


class ExperimentError(Exception):
    """Custom exception for experiment-related errors"""
    pass


class URASHGBaseExperiment:
    """
    Base class for all μRASHG experiments providing common functionality.
    
    This class implements:
    - Hardware module management (MaiTai, Elliptec, Camera, Power Meter)
    - Parameter tree structure for experimental settings
    - Common data structures for multi-dimensional measurements
    - Calibration data loading and management
    - Safety protocols and error handling
    - Progress tracking and status reporting
    
    Attributes:
        experiment_name (str): Human-readable name for the experiment
        experiment_type (str): Technical identifier for the experiment type
        required_modules (List[str]): List of required PyMoDAQ modules
        optional_modules (List[str]): List of optional PyMoDAQ modules
        state (ExperimentState): Current experiment execution state
    """
    
    # Class attributes to be overridden by subclasses
    experiment_name = "Base μRASHG Experiment"
    experiment_type = "base_urashg"
    required_modules = []  # Override in subclasses
    optional_modules = []  # Override in subclasses
    
    def __init__(self, dashboard):
        """
        Initialize the base experiment.
        
        Args:
            dashboard: PyMoDAQ dashboard instance for module access
        """
        # Store dashboard but don't call super().__init__ yet (requires Qt widgets)
        self.dashboard = dashboard
        
        # Experiment state management
        self.state = ExperimentState.IDLE
        self.current_step = 0
        self.total_steps = 0
        self.start_time = None
        self.progress_callback = None
        
        # Hardware module references
        self.modules = {}
        self.hardware_initialized = False
        
        # Calibration data storage
        self.calibration_data = {}
        
        # Data storage
        self.experimental_data = {}
        self.metadata = {}
        
        # Thread management for non-blocking execution
        self.experiment_thread = None
        
        # GUI components (initialized on demand)
        self.main_widget = None
        self.settings = None
        self.dock_area = None
        self.param_tree = None
        self._customapp_initialized = False
        
        # Initialize parameters (does not create GUI)
        self.setup_parameters()
        
        logger.info(f"Initialized {self.experiment_name}")

    def ensure_gui_initialized(self):
        """Ensure GUI is initialized when needed."""
        if self.main_widget is None:
            self.setup_gui()
        return self.main_widget
    
    def setup_parameters(self):
        """Set up the parameter tree for experiment configuration."""
        self.settings = Parameter.create(
            name='urashg_experiment',
            type='group',
            children=[
                {
                    'name': 'experiment_info',
                    'type': 'group',
                    'children': [
                        {'name': 'experiment_name', 'type': 'str', 
                         'value': self.experiment_name, 'readonly': True},
                        {'name': 'experiment_type', 'type': 'str', 
                         'value': self.experiment_type, 'readonly': True},
                        {'name': 'state', 'type': 'str', 
                         'value': self.state.value, 'readonly': True},
                        {'name': 'progress', 'type': 'float', 
                         'value': 0.0, 'readonly': True, 'suffix': '%'},
                    ]
                },
                {
                    'name': 'file_settings',
                    'type': 'group',
                    'children': [
                        {'name': 'save_path', 'type': 'browsepath', 
                         'value': str(Path.home() / 'urashg_data')},
                        {'name': 'filename_prefix', 'type': 'str', 
                         'value': f'{self.experiment_type}'},
                        {'name': 'use_timestamp', 'type': 'bool', 'value': True},
                        {'name': 'data_format', 'type': 'list', 
                         'limits': ['HDF5', 'NPY'], 'value': 'HDF5'},
                    ]
                },
                {
                    'name': 'hardware_settings',
                    'type': 'group',
                    'children': [
                        {'name': 'maitai_wavelength', 'type': 'float', 
                         'value': 800.0, 'limits': [700, 1000], 'suffix': 'nm'},
                        {'name': 'stabilization_time', 'type': 'float', 
                         'value': 60.0, 'limits': [0, 300], 'suffix': 's'},
                        {'name': 'safety_shutter', 'type': 'bool', 'value': True},
                    ]
                },
                {
                    'name': 'calibration_settings',
                    'type': 'group',
                    'children': [
                        {'name': 'eom_calibration_file', 'type': 'browsepath', 
                         'value': ''},
                        {'name': 'rotator_calibration_file', 'type': 'browsepath', 
                         'value': ''},
                        {'name': 'power_calibration_file', 'type': 'browsepath', 
                         'value': ''},
                        {'name': 'verify_calibration', 'type': 'bool', 'value': True},
                    ]
                },
                {
                    'name': 'safety_settings',
                    'type': 'group',
                    'children': [
                        {'name': 'max_power', 'type': 'float', 
                         'value': 0.010, 'limits': [0.001, 0.100], 'suffix': 'W'},
                        {'name': 'min_power', 'type': 'float', 
                         'value': 0.001, 'limits': [0.0001, 0.010], 'suffix': 'W'},
                        {'name': 'timeout_seconds', 'type': 'float', 
                         'value': 3600.0, 'limits': [60, 86400], 'suffix': 's'},
                        {'name': 'auto_pause_on_error', 'type': 'bool', 'value': True},
                    ]
                }
            ]
        )
        
        # Signal connection will be done in setup_gui() when Qt application exists
    
    def setup_gui(self):
        """Set up the graphical user interface."""
        if self.main_widget is not None:
            return  # GUI already initialized
            
        # Create main widget first
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        
        # CustomApp initialization is handled by the extension wrapper
        
        # Create dock area for organized layout
        self.dock_area = DockArea()
        self.main_layout.addWidget(self.dock_area)
        
        # Connect parameter change signals now that Qt application exists
        if self.settings is not None:
            self.settings.sigTreeStateChanged.connect(self.parameter_changed)
        
        # Create control panel
        self.create_control_panel()
        
        # Create status panel
        self.create_status_panel()
        
        # Create progress panel
        self.create_progress_panel()
    
    def create_control_panel(self):
        """Create experiment control buttons and settings."""
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_widget)
        
        # Parameter tree widget
        from pymodaq.utils.parameter import ParameterTree
        self.param_tree = ParameterTree()
        self.param_tree.setParameters(self.settings, showTop=False)
        control_layout.addWidget(self.param_tree)
        
        # Control buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.initialize_btn = QtWidgets.QPushButton("Initialize Hardware")
        self.initialize_btn.clicked.connect(self.initialize_hardware)
        button_layout.addWidget(self.initialize_btn)
        
        self.start_btn = QtWidgets.QPushButton("Start Experiment")
        self.start_btn.clicked.connect(self.start_experiment)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_experiment)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_experiment)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(button_layout)
        
        # Add to dock area
        from pymodaq_gui.utils.dock import Dock
        control_dock = Dock("Experiment Control", size=(400, 600))
        control_dock.addWidget(control_widget)
        self.dock_area.addDock(control_dock, 'left')
    
    def create_status_panel(self):
        """Create status monitoring panel."""
        status_widget = QtWidgets.QWidget()
        status_layout = QtWidgets.QVBoxLayout(status_widget)
        
        # Status text display
        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        status_layout.addWidget(QtWidgets.QLabel("Experiment Status:"))
        status_layout.addWidget(self.status_text)
        
        # Hardware status indicators
        hardware_group = QtWidgets.QGroupBox("Hardware Status")
        hardware_layout = QtWidgets.QGridLayout(hardware_group)
        
        self.hardware_status = {}
        hardware_modules = ['MaiTai', 'Camera', 'H800', 'H400', 'Q800', 'Newport']
        
        for i, module in enumerate(hardware_modules):
            label = QtWidgets.QLabel(f"{module}:")
            status_indicator = QtWidgets.QLabel("●")
            status_indicator.setStyleSheet("color: red; font-size: 16px;")
            hardware_layout.addWidget(label, i, 0)
            hardware_layout.addWidget(status_indicator, i, 1)
            self.hardware_status[module] = status_indicator
        
        status_layout.addWidget(hardware_group)
        
        # Add to dock area
        from pymodaq_gui.utils.dock import Dock
        status_dock = Dock("Status Monitor", size=(300, 400))
        status_dock.addWidget(status_widget)
        self.dock_area.addDock(status_dock, 'right')
    
    def create_progress_panel(self):
        """Create experiment progress monitoring panel."""
        progress_widget = QtWidgets.QWidget()
        progress_layout = QtWidgets.QVBoxLayout(progress_widget)
        
        # Overall progress bar
        progress_layout.addWidget(QtWidgets.QLabel("Overall Progress:"))
        self.overall_progress = QtWidgets.QProgressBar()
        self.overall_progress.setRange(0, 100)
        progress_layout.addWidget(self.overall_progress)
        
        # Current step progress bar
        progress_layout.addWidget(QtWidgets.QLabel("Current Step:"))
        self.step_progress = QtWidgets.QProgressBar()
        self.step_progress.setRange(0, 100)
        progress_layout.addWidget(self.step_progress)
        
        # Time information
        self.time_info = QtWidgets.QLabel("Time: Not started")
        progress_layout.addWidget(self.time_info)
        
        # Estimated completion
        self.eta_info = QtWidgets.QLabel("ETA: --")
        progress_layout.addWidget(self.eta_info)
        
        # Add to dock area
        from pymodaq_gui.utils.dock import Dock
        progress_dock = Dock("Progress Monitor", size=(300, 200))
        progress_dock.addWidget(progress_widget)
        self.dock_area.addDock(progress_dock, 'bottom')
    
    def parameter_changed(self, param, changes):
        """Handle parameter changes."""
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
                logger.debug(f"Parameter changed: {childName} = {data}")
                
                # Handle specific parameter changes
                if 'wavelength' in childName:
                    self.on_wavelength_changed(data)
                elif 'calibration_file' in childName:
                    self.on_calibration_file_changed(childName, data)
    
    def on_wavelength_changed(self, wavelength):
        """Handle wavelength parameter changes."""
        logger.info(f"Wavelength changed to {wavelength} nm")
        # Validate wavelength range
        if not (700 <= wavelength <= 1000):
            logger.warning(f"Wavelength {wavelength} nm outside valid range")
    
    def on_calibration_file_changed(self, param_name, filepath):
        """Handle calibration file parameter changes."""
        if filepath and os.path.exists(filepath):
            logger.info(f"Loading calibration file: {filepath}")
            self.load_calibration_file(param_name, filepath)
        elif filepath:
            logger.warning(f"Calibration file not found: {filepath}")
    
    def load_calibration_file(self, param_name, filepath):
        """Load calibration data from file."""
        try:
            # Implementation depends on calibration file format
            # This is a placeholder for the actual loading logic
            logger.info(f"Loading calibration from {filepath}")
            # TODO: Implement actual calibration file loading
            pass
        except Exception as e:
            logger.error(f"Failed to load calibration file {filepath}: {e}")
            raise ExperimentError(f"Calibration loading failed: {e}")
    
    def initialize_hardware(self):
        """Initialize all required hardware modules."""
        try:
            self.set_state(ExperimentState.INITIALIZING)
            self.log_status("Initializing hardware modules...")
            
            # Get required modules from dashboard
            for module_name in self.required_modules:
                if hasattr(self.dashboard, 'get_module'):
                    module = self.dashboard.get_module(module_name)
                    if module is not None:
                        self.modules[module_name] = module
                        self.update_hardware_status(module_name, True)
                        logger.info(f"Connected to {module_name}")
                    else:
                        raise ExperimentError(f"Required module {module_name} not found")
                else:
                    logger.warning("Dashboard does not have get_module method")
            
            # Check optional modules
            for module_name in self.optional_modules:
                if hasattr(self.dashboard, 'get_module'):
                    module = self.dashboard.get_module(module_name)
                    if module is not None:
                        self.modules[module_name] = module
                        self.update_hardware_status(module_name, True)
                        logger.info(f"Connected to optional module {module_name}")
                    else:
                        logger.info(f"Optional module {module_name} not available")
            
            # Perform hardware-specific initialization
            self.initialize_specific_hardware()
            
            self.hardware_initialized = True
            self.set_state(ExperimentState.IDLE)
            self.start_btn.setEnabled(True)
            self.log_status("Hardware initialization completed successfully")
            
        except Exception as e:
            self.set_state(ExperimentState.ERROR)
            self.log_status(f"Hardware initialization failed: {e}")
            logger.error(f"Hardware initialization error: {e}")
            raise
    
    def initialize_specific_hardware(self):
        """Initialize hardware specific to this experiment type."""
        # Override in subclasses for specific initialization requirements
        pass
    
    def update_hardware_status(self, module_name, connected):
        """Update hardware status indicator."""
        if module_name in self.hardware_status:
            indicator = self.hardware_status[module_name]
            if connected:
                indicator.setStyleSheet("color: green; font-size: 16px;")
            else:
                indicator.setStyleSheet("color: red; font-size: 16px;")
    
    def start_experiment(self):
        """Start the experiment execution."""
        try:
            if not self.hardware_initialized:
                raise ExperimentError("Hardware not initialized")
            
            if self.state != ExperimentState.IDLE:
                raise ExperimentError(f"Cannot start experiment in state {self.state}")
            
            # Validate experimental parameters
            self.validate_parameters()
            
            # Prepare experiment
            self.prepare_experiment()
            
            # Start experiment thread
            self.experiment_thread = ExperimentThread(self)
            self.experiment_thread.progress_updated.connect(self.update_progress)
            self.experiment_thread.status_updated.connect(self.log_status)
            self.experiment_thread.experiment_completed.connect(self.on_experiment_completed)
            self.experiment_thread.experiment_failed.connect(self.on_experiment_failed)
            
            self.experiment_thread.start()
            
            # Update UI state
            self.set_state(ExperimentState.RUNNING)
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.start_time = datetime.now()
            
            self.log_status("Experiment started")
            
        except Exception as e:
            self.set_state(ExperimentState.ERROR)
            self.log_status(f"Failed to start experiment: {e}")
            logger.error(f"Experiment start error: {e}")
    
    def pause_experiment(self):
        """Pause the running experiment."""
        if self.state == ExperimentState.RUNNING:
            self.set_state(ExperimentState.PAUSED)
            self.log_status("Experiment paused")
        elif self.state == ExperimentState.PAUSED:
            self.set_state(ExperimentState.RUNNING)
            self.log_status("Experiment resumed")
    
    def stop_experiment(self):
        """Stop the running experiment."""
        if self.experiment_thread and self.experiment_thread.isRunning():
            self.set_state(ExperimentState.STOPPING)
            self.experiment_thread.stop()
            self.log_status("Stopping experiment...")
        else:
            self.set_state(ExperimentState.IDLE)
            self.reset_ui_state()
    
    def validate_parameters(self):
        """Validate experimental parameters before starting."""
        # Override in subclasses for specific validation
        pass
    
    def prepare_experiment(self):
        """Prepare the experiment before execution."""
        # Create data structures
        self.create_data_structures()
        
        # Set up file paths
        self.setup_file_paths()
        
        # Initialize metadata
        self.initialize_metadata()
    
    def create_data_structures(self):
        """Create data structures for experiment results."""
        # Override in subclasses for specific data structures
        pass
    
    def setup_file_paths(self):
        """Set up file paths for data saving."""
        save_path = Path(self.settings.child('file_settings', 'save_path').value())
        prefix = self.settings.child('file_settings', 'filename_prefix').value()
        use_timestamp = self.settings.child('file_settings', 'use_timestamp').value()
        
        if use_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}"
        else:
            filename = prefix
        
        self.data_filepath = save_path / f"{filename}.h5"
        self.metadata_filepath = save_path / f"{filename}_metadata.json"
        
        # Create directory if it doesn't exist
        save_path.mkdir(parents=True, exist_ok=True)
    
    def initialize_metadata(self):
        """Initialize experiment metadata."""
        self.metadata = {
            'experiment_name': self.experiment_name,
            'experiment_type': self.experiment_type,
            'start_time': datetime.now().isoformat(),
            'parameters': self.settings.saveState(),
            'hardware_modules': list(self.modules.keys()),
            'software_version': '1.0.0',  # TODO: Get from package
        }
    
    def run_experiment(self):
        """Execute the main experiment logic."""
        # Override in subclasses for specific experiment implementation
        raise NotImplementedError("Subclasses must implement run_experiment method")
    
    def update_progress(self, overall_progress, step_progress=None):
        """Update experiment progress."""
        self.overall_progress.setValue(int(overall_progress))
        if step_progress is not None:
            self.step_progress.setValue(int(step_progress))
        
        # Update parameter tree
        self.settings.child('experiment_info', 'progress').setValue(overall_progress)
        
        # Update time information
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
            self.time_info.setText(f"Elapsed: {elapsed_str}")
            
            # Estimate completion time
            if overall_progress > 0:
                total_time = elapsed.total_seconds() * 100 / overall_progress
                remaining_time = total_time - elapsed.total_seconds()
                if remaining_time > 0:
                    from datetime import timedelta
                    eta = datetime.now() + timedelta(seconds=remaining_time)
                    self.eta_info.setText(f"ETA: {eta.strftime('%H:%M:%S')}")
    
    def on_experiment_completed(self):
        """Handle experiment completion."""
        self.set_state(ExperimentState.COMPLETED)
        self.reset_ui_state()
        self.log_status("Experiment completed successfully")
        
        # Save final metadata
        self.save_metadata()
    
    def on_experiment_failed(self, error_message):
        """Handle experiment failure."""
        self.set_state(ExperimentState.ERROR)
        self.reset_ui_state()
        self.log_status(f"Experiment failed: {error_message}")
        logger.error(f"Experiment failed: {error_message}")
    
    def reset_ui_state(self):
        """Reset UI to idle state."""
        self.start_btn.setEnabled(self.hardware_initialized)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.overall_progress.setValue(0)
        self.step_progress.setValue(0)
    
    def set_state(self, new_state):
        """Update experiment state."""
        self.state = new_state
        self.settings.child('experiment_info', 'state').setValue(new_state.value)
        logger.info(f"Experiment state: {new_state.value}")
    
    def log_status(self, message):
        """Log status message to GUI and logger."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Add to status text widget
        self.status_text.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.End)
        self.status_text.setTextCursor(cursor)
        
        # Log to Python logger
        logger.info(message)
    
    def save_metadata(self):
        """Save experiment metadata to file."""
        try:
            import json
            with open(self.metadata_filepath, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def cleanup(self):
        """Clean up resources when experiment is finished."""
        # Stop experiment thread if running
        if self.experiment_thread and self.experiment_thread.isRunning():
            self.experiment_thread.stop()
            self.experiment_thread.wait()
        
        # Close hardware connections
        for module_name, module in self.modules.items():
            try:
                if hasattr(module, 'close'):
                    module.close()
                logger.info(f"Closed connection to {module_name}")
            except Exception as e:
                logger.warning(f"Error closing {module_name}: {e}")


class ExperimentThread(QThread):
    """Thread for running experiments without blocking the GUI."""
    
    progress_updated = QtCore.Signal(float, float)  # overall, step
    status_updated = QtCore.Signal(str)
    experiment_completed = QtCore.Signal()
    experiment_failed = QtCore.Signal(str)
    
    def __init__(self, experiment):
        super().__init__()
        self.experiment = experiment
        self._stop_requested = False
    
    def stop(self):
        """Request thread to stop."""
        self._stop_requested = True
    
    def run(self):
        """Execute the experiment in a separate thread."""
        try:
            self.experiment.run_experiment()
            if not self._stop_requested:
                self.experiment_completed.emit()
        except Exception as e:
            self.experiment_failed.emit(str(e))