from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, DataActuator, comon_parameters_fun, main
from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport
from qtpy.QtCore import Signal, QTimer
import numpy as np

from pymodaq_plugins_urashg.daq_move_plugins.elliptec_ui import ElliptecUI
from pymodaq_plugins_urashg.hardware.elliptec_wrapper import ElliptecController, ElliptecError

try:
    from pymodaq_plugins_urashg.utils.config import get_config
    config = get_config()
    elliptec_config = config.get('hardware', {}).get('elliptec', {})
except (ImportError, FileNotFoundError):
    elliptec_config = {}

class DAQ_Move_Elliptec(DAQ_Move_base):
    """
    PyMoDAQ plugin for Thorlabs Elliptec rotation mounts.
    """
    _ui_file = "elliptec_ui.py"
    _ui_class_name = "ElliptecUI"

    _controller_units = 'degrees'
    is_multiaxes = True
    _axis_names = ['HWP_Incident', 'QWP', 'HWP_Analyzer']
    _epsilon = 0.1

    positions_signal = Signal(list)

    params = comon_parameters_fun(is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon) + [
        {"title": "Serial Port:", "name": "serial_port", "type": "str", "value": elliptec_config.get("serial_port", "/dev/ttyUSB0")},
        {"title": "Mount Addresses:", "name": "mount_addresses", "type": "str", "value": elliptec_config.get("mount_addresses", "2,3,8")},
        {"title": "Mock Mode:", "name": "mock_mode", "type": "bool", "value": elliptec_config.get("mock_mode", False)},
        {"title": "Polling Interval (ms):", "name": "polling_interval", "type": "int", "value": 500, "min": 100},
    ]

    def ini_attributes(self):
        self.controller: ElliptecController = None
        self.ui = ElliptecUI(axis_names=self._axis_names)
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_positions)

    def ini_stage(self, controller=None):
        self.initialized = False
        try:
            mount_addresses = [int(addr.strip()) for addr in self.settings.child("mount_addresses").value().split(',')]
            self.controller = controller or ElliptecController(
                port=self.settings.child("serial_port").value(),
                mount_addresses=mount_addresses,
                mock_mode=self.settings.child("mock_mode").value()
            )
            
            self.controller.connect()
            self.poll_timer.start(self.settings.child("polling_interval").value())
            self.connect_ui()
            self.poll_positions()
            self.initialized = True
            return "Elliptec Initialized", True

        except ElliptecError as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Initialization failed: {e}", "error"]))
            return f"Failed to initialize Elliptec: {e}", False

    def connect_ui(self):
        """Connect signals from the custom UI."""
        if self.ui:
            self.ui.move_abs_signal.connect(self.move_abs_axis)
            self.ui.move_rel_signal.connect(self.move_rel_axis)
            self.ui.home_signal.connect(self.home_axis)
            self.ui.home_all_signal.connect(self.move_home)
            self.positions_signal.connect(self.ui.update_positions)

    def poll_positions(self):
        """Polls and emits the current positions of all axes."""
        try:
            positions = self.controller.get_all_positions()
            ordered_positions = [positions.get(addr, 0.0) for addr in self.controller.mount_addresses]
            self.positions_signal.emit(ordered_positions)
            
            dwa = DataToExport(name='Elliptec', data=[DataActuator(axis, data=np.array([pos]))
                                                     for axis, pos in zip(self._axis_names, ordered_positions)])
            self.dte_signal.emit(dwa)
        except ElliptecError as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error polling positions: {e}", "log"]))

    def close(self):
        self.poll_timer.stop()
        if self.controller:
            self.controller.disconnect()

    def get_actuator_value(self):
        """Get current position of all axes."""
        positions = self.controller.get_all_positions()
        ordered_positions = [positions.get(addr, 0.0) for addr in self.controller.mount_addresses]
        return DataActuator(data=[np.array(ordered_positions)])

    def move_abs(self, position: DataActuator):
        """Move all axes to absolute positions."""
        for i, pos in enumerate(position.value()):
            self.move_abs_axis(i, pos)
        self.move_done()

    def move_rel(self, position: DataActuator):
        """Move all axes by relative positions."""
        for i, rel_pos in enumerate(position.value()):
            self.move_rel_axis(i, rel_pos)
        self.move_done()

    def move_home(self):
        """Home all axes."""
        self.controller.home_all()
        self.move_done()

    def move_abs_axis(self, axis_index: int, position: float):
        """Move a single axis to an absolute position."""
        addr = self.controller.mount_addresses[axis_index]
        self.controller.move_absolute(addr, position)

    def move_rel_axis(self, axis_index: int, relative_pos: float):
        """Move a single axis by a relative amount."""
        addr = self.controller.mount_addresses[axis_index]
        self.controller.move_relative(addr, relative_pos)
    
    def home_axis(self, axis_index: int):
        """Home a single axis."""
        addr = self.controller.mount_addresses[axis_index]
        self.controller.home(addr)

if __name__ == "__main__":
    main(__file__)
