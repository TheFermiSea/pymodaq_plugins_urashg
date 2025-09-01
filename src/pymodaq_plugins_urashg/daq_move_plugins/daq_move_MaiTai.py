import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    comon_parameters_fun,
    main,
)
from pymodaq_utils.utils import ThreadCommand
from qtpy.QtCore import Signal, QTimer

from pymodaq_plugins_urashg.daq_move_plugins.maitai_ui import MaiTaiUI
from pymodaq_plugins_urashg.hardware.maitai_control import MaiTaiController, MockMaiTaiController, MaiTaiError

# Import URASHG configuration safely
try:
    from pymodaq_plugins_urashg.utils.config import get_config
    config = get_config()
    maitai_config = config.get('hardware', {}).get('maitai', {})
except (ImportError, FileNotFoundError):
    maitai_config = {}


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ plugin for controlling MaiTai Ti:Sapphire laser.
    """
    _ui_file = "maitai_ui.py"
    _ui_class_name = "MaiTaiUI"
    
    _controller_units = "nm"
    is_multiaxes = False
    _axis_names = ["Wavelength"]
    _epsilon = 0.1

    status_signal = Signal(dict)

    params = comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilon) + [
        {"title": "Serial Port:", "name": "serial_port", "type": "str", "value": maitai_config.get("serial_port", "/dev/ttyUSB2")},
        {"title": "Mock Mode:", "name": "mock_mode", "type": "bool", "value": maitai_config.get("mock_mode", False)},
        {"title": "Polling Interval (ms):", "name": "polling_interval", "type": "int", "value": 1000, "min": 100},
    ]

    def ini_attributes(self):
        """Initialize attributes before __init__."""
        self.controller: MaiTaiController = None
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_status)

    def ini_stage(self, controller=None):
        """Initialize the MaiTai laser controller."""
        self.initialized = False
        try:
            if self.settings.child("mock_mode").value():
                self.controller = MockMaiTaiController(self.settings.child("serial_port").value())
            else:
                self.controller = controller or MaiTaiController(self.settings.child("serial_port").value())
            
            self.controller.connect()
            self.poll_timer.start(self.settings.child("polling_interval").value())
            
            self.connect_ui()
            self.poll_status()
            self.initialized = True
            return f"MaiTai Initialized on {self.settings.child('serial_port').value()}", True

        except MaiTaiError as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Initialization failed: {e}", "error"]))
            return f"Failed to initialize MaiTai: {e}", False

    def connect_ui(self):
        """Connect signals from the custom UI."""
        if self.ui:
            self.ui.open_shutter_signal.connect(self.open_shutter)
            self.ui.close_shutter_signal.connect(self.close_shutter)
            self.ui.set_wavelength_signal.connect(self.move_abs)
            self.status_signal.connect(self.ui.update_status)

    def poll_status(self):
        """Poll the laser for its current status and emit a signal."""
        if not self.controller:
            return
        try:
            status = {
                'wavelength': self.controller.get_wavelength(),
                'power': self.controller.get_power(),
                'shutter_open': self.controller.get_shutter_state(),
            }
            self.status_signal.emit(status)
        except MaiTaiError as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error polling status: {e}", "log"]))

    def get_actuator_value(self):
        """Get current wavelength position."""
        return DataActuator(data=self.controller.get_wavelength())

    def move_abs(self, position):
        """Move to an absolute wavelength position."""
        try:
            target_wavelength = float(position)
            self.controller.set_wavelength(target_wavelength)
            self.emit_status(ThreadCommand("Update_Status", [f"Moving to {target_wavelength} nm"]))
        except (MaiTaiError, ValueError) as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error moving: {e}", "error"]))

    def move_rel(self, position):
        """Move by a relative wavelength amount."""
        try:
            current_wavelength = self.get_actuator_value().value()
            target_wavelength = current_wavelength + float(position)
            self.move_abs(target_wavelength)
        except (MaiTaiError, ValueError) as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error in relative move: {e}", "error"]))

    def move_home(self):
        """Move to the home wavelength position (e.g., 800nm)."""
        self.move_abs(800.0)

    def stop_motion(self):
        """MaiTai movement is set-and-forget; this method simply updates status."""
        self.poll_status()
        self.move_done()

    def close(self):
        """Close the connection to the laser controller."""
        self.poll_timer.stop()
        if self.controller:
            self.controller.disconnect()

    def open_shutter(self):
        """Open the laser shutter."""
        self.controller.set_shutter(True)

    def close_shutter(self):
        """Close the laser shutter."""
        self.controller.set_shutter(False)

if __name__ == "__main__":
    main(__file__)
