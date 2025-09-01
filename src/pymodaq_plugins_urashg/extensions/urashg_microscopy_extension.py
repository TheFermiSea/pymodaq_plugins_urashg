# -*- coding: utf-8 -*-
"""
μRASHG Microscopy Extension for PyMoDAQ (Refactored)

This extension provides comprehensive multi-device coordination for μRASHG
microscopy measurements, refactored to use PyMoDAQ's standard preset and
module management system, enhancing stability and maintainability.
"""

import time
from pathlib import Path
import numpy as np

from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.config import get_set_preset_path
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_utils.logger import get_module_name, set_logger
from qtpy import QtWidgets
from qtpy.QtCore import Qt, QThread, Signal

EXTENSION_NAME = "μRASHG Microscopy System"
CLASS_NAME = "URASHGMicroscopyExtension"

logger = set_logger(get_module_name(__file__))

class MeasurementWorker(QThread):
    """
    Worker thread for RASHG measurements using device handles passed from the extension.
    """
    measurement_progress = Signal(int)
    measurement_finished = Signal(bool)
    status_message = Signal(str, str)

    def __init__(self, devices: dict, params: dict):
        super().__init__()
        self.devices = devices
        self.params = params
        self._is_running = True

    def run(self):
        try:
            self.status_message.emit("Starting measurement...", "info")
            measurement_type = self.params.get("measurement_type")

            if measurement_type == "Basic RASHG":
                self._run_basic_rashg()
            else:
                raise ValueError(f"Measurement type '{measurement_type}' not implemented yet.")
            
            self.measurement_finished.emit(True)
        except Exception as e:
            logger.error(f"Measurement error: {e}")
            self.status_message.emit(f"Measurement error: {e}", "error")
            self.measurement_finished.emit(False)
        finally:
            self._is_running = False

    def _run_basic_rashg(self):
        """Execute a basic RASHG polarization sweep."""
        pol_steps = self.params.get("pol_steps", 36)
        
        elliptec = self.devices.get("elliptec")
        camera = self.devices.get("camera")

        if not all([elliptec, camera]):
            raise RuntimeError("Required devices (Elliptec, Camera) are not available.")

        angles = np.linspace(0, 180, pol_steps)
        for i, angle in enumerate(angles):
            if not self._is_running:
                self.status_message.emit("Measurement stopped by user.", "warning")
                break

            # Move the HWP incident polarizer (assumed to be the first axis)
            elliptec.move_abs(value=angle, axis='HWP_Incident')
            time.sleep(0.5)  # Simple wait for move completion

            camera.grab_data(Naverage=1)
            
            progress = int((i + 1) / len(angles) * 100)
            self.measurement_progress.emit(progress)
            self.status_message.emit(f"Measured angle {angle:.1f}°", "info")

    def stop(self):
        self._is_running = False

class URASHGMicroscopyExtension(gutils.CustomApp):
    """
    μRASHG Extension refactored to use PyMoDAQ's standard PresetManager.
    """
    # Metadata
    name = EXTENSION_NAME
    
    # Signals
    measurement_started = Signal()
    measurement_finished = Signal(bool)
    measurement_progress = Signal(int)

    params = [
        {'title': 'Preset File:', 'name': 'preset_file', 'type': 'browsepath', 'filetype': True},
        {'title': 'Load Preset', 'name': 'load_preset', 'type': 'action'},
        {'title': 'Experiment', 'name': 'experiment', 'type': 'group', 'children': [
            {'title': 'Measurement Type:', 'name': 'measurement_type', 'type': 'list', 
             'limits': ['Basic RASHG', 'Multi-Wavelength RASHG', 'Calibration']},
            {'title': 'Polarization Steps:', 'name': 'pol_steps', 'type': 'int', 'value': 36},
        ]},
        {'title': 'Device Status', 'name': 'device_status', 'type': 'group', 'children': [
            {'title': 'Elliptec:', 'name': 'elliptec_status', 'type': 'str', 'value': 'N/A', 'readonly': True},
            {'title': 'Camera:', 'name': 'camera_status', 'type': 'str', 'value': 'N/A', 'readonly': True},
            {'title': 'Laser:', 'name': 'laser_status', 'type': 'str', 'value': 'N/A', 'readonly': True},
        ]},
    ]

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent)
        self.dashboard = dashboard
        self.measurement_worker = None
        self.setup_ui()

    def setup_docks(self):
        self.docks['control'] = gutils.Dock("URASHG Control")
        self.dockarea.addDock(self.docks['control'])
        self.docks['control'].addWidget(self.settings_tree)

        self.docks['camera'] = gutils.Dock("SHG Camera Data")
        self.dockarea.addDock(self.docks['camera'], 'right', self.docks['control'])
        self.camera_viewer = Viewer2D(parent=self.docks['camera'])
        self.docks['camera'].addWidget(self.camera_viewer.parent)

        self.docks['plots'] = gutils.Dock("RASHG Analysis")
        self.dockarea.addDock(self.docks['plots'], 'bottom', self.docks['camera'])
        self.plot_viewer = Viewer1D(parent=self.docks['plots'])
        self.docks['plots'].addWidget(self.plot_viewer.parent)

        self.docks["status"] = gutils.Dock("System Status")
        self.dockarea.addDock(self.docks["status"], "bottom", self.docks["control"])
        self.status_widget = QtWidgets.QTextEdit(readOnly=True)
        self.docks["status"].addWidget(self.status_widget)

    def setup_actions(self):
        self.add_action('start', 'Start Measurement', 'run', checkable=False)
        self.add_action('stop', 'Stop Measurement', 'stop', checkable=False)
        self.add_action('quit', 'Quit', 'close2')

    def connect_things(self):
        self.settings.child('load_preset').sigActivated.connect(self.load_preset)
        self.get_action('start').triggered.connect(self.start_measurement)
        self.get_action('stop').triggered.connect(self.stop_measurement)
        self.get_action('quit').triggered.connect(self.quit_app)

    def log_message(self, message: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.status_widget.append(formatted_msg)
        logger.info(message)

    def load_preset(self):
        preset_path = self.settings.child('preset_file').value()
        if not Path(preset_path).is_file():
            self.log_message(f"Preset file not found: {preset_path}", "error")
            return
        
        self.log_message(f"Loading preset: {preset_path}", "info")
        self.dashboard.preset_manager.load_preset_from_file(preset_path)
        self.dashboard.preset_manager.preset_loaded.connect(self.update_device_status)

    def update_device_status(self):
        # Access modules via the dashboard's module manager
        actuators = self.dashboard.modules_manager.actuators
        detectors = self.dashboard.modules_manager.detectors
        
        self.settings.child('device_status', 'elliptec_status').setValue(
            'Connected' if 'Elliptec' in actuators else 'Disconnected')
        self.settings.child('device_status', 'camera_status').setValue(
            'Connected' if 'PrimeBSI' in detectors else 'Disconnected')
        self.settings.child('device_status', 'laser_status').setValue(
            'Connected' if 'MaiTai' in actuators else 'Disconnected')
        self.log_message("Device status updated.")

    def start_measurement(self):
        if self.measurement_worker and self.measurement_worker.isRunning():
            self.log_message("Measurement is already in progress.", "warning")
            return

        devices = {
            "elliptec": self.dashboard.modules_manager.get_mod_from_name('Elliptec', 'actuator'),
            "camera": self.dashboard.modules_manager.get_mod_from_name('PrimeBSI', 'detector'),
        }

        if not all(devices.values()):
            self.log_message("Not all required devices are loaded. Please load the preset.", "error")
            return
            
        params = {
            'measurement_type': self.settings.child('experiment', 'measurement_type').value(),
            'pol_steps': self.settings.child('experiment', 'pol_steps').value(),
        }

        self.measurement_worker = MeasurementWorker(devices, params)
        self.measurement_worker.status_message.connect(self.log_message)
        self.measurement_worker.measurement_progress.connect(self.measurement_progress)
        self.measurement_worker.measurement_finished.connect(self.stop_measurement)
        
        self.measurement_worker.start()
        self.measurement_started.emit()

    def stop_measurement(self):
        if self.measurement_worker and self.measurement_worker.isRunning():
            self.measurement_worker.stop()
            self.measurement_worker.wait(2000) # wait 2s for thread to finish
        self.log_message("Measurement stopped.", "info")
        self.measurement_finished.emit(True)

    def quit_app(self):
        self.stop_measurement()
        if hasattr(self, 'parent') and hasattr(self.parent, 'close'):
            self.parent.close()

if __name__ == '__main__':
    import sys
    from pymodaq.dashboard import DashBoard
    
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    
    # It is mandatory that the extension can be initialized without a dashboard
    # for testing purposes.
    area = gutils.DockArea()
    win.setCentralWidget(area)
    
    # To test the extension with a dashboard
    dashboard = DashBoard(area)
    prog = URASHGMicroscopyExtension(area, dashboard)
    
    win.show()
    sys.exit(app.exec_())
