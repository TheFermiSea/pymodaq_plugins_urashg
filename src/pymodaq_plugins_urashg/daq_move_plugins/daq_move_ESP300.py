# -*- coding: utf-8 -*-
"""
PyMoDAQ plugin for Newport ESP300 multi-axis motion controller.
"""
from typing import List, Union
import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    comon_parameters_fun,
    main,
)
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand
from qtpy.QtCore import QTimer

from pymodaq_plugins_urashg.hardware.esp300_controller import (
    AxisConfig,
    ESP300Controller,
    MockESP300Controller,
    ESP300Error,
)
try:
    from pymodaq_plugins_urashg.utils.config import get_config
    config = get_config()
    esp300_config = config.get('hardware', {}).get('esp300', {})
except (ImportError, FileNotFoundError):
    esp300_config = {}


class DAQ_Move_ESP300(DAQ_Move_base):
    """
    PyMoDAQ plugin for Newport ESP300 multi-axis motion controller.
    """
    _controller_units = "mm"
    _axis_names = ["X Stage", "Y Stage", "Z Focus"]
    _epsilon = 0.001
    is_multiaxes = True

    params = comon_parameters_fun(is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon) + [
        {"title": "Serial Port:", "name": "serial_port", "type": "str", "value": esp300_config.get("serial_port", "/dev/ttyUSB1")},
        {"title": "Mock Mode:", "name": "mock_mode", "type": "bool", "value": esp300_config.get("mock_mode", False)},
        {"title": "Polling Interval (ms):", "name": "polling_interval", "type": "int", "value": 200, "min": 50},
    ]

    def ini_attributes(self):
        self.controller: ESP300Controller = None
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._update_status)

    def ini_stage(self, controller=None):
        self.initialized = False
        try:
            axes_config = self._build_axes_config()
            ControllerClass = MockESP300Controller if self.settings.child("mock_mode").value() else ESP300Controller
            
            self.controller = controller or ControllerClass(
                port=self.settings.child("serial_port").value(),
                axes_config=axes_config
            )
            
            self.controller.connect()
            self.poll_timer.start(self.settings.child("polling_interval").value())
            
            self.initialized = True
            return f"ESP300 Initialized on {self.settings.child('serial_port').value()}", True

        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Initialization failed: {e}", "error"]))
            return f"Failed to initialize ESP300: {e}", False

    def _build_axes_config(self) -> List[AxisConfig]:
        """Build axes configuration from predefined settings."""
        # This can be expanded to read from YAML or UI in a real scenario
        return [
            AxisConfig(number=1, name="X Stage", units="millimeter"),
            AxisConfig(number=2, name="Y Stage", units="millimeter"),
            AxisConfig(number=3, name="Z Focus", units="micrometer"),
        ]

    def _update_status(self):
        """Periodically poll controller for position and update UI."""
        try:
            positions = self.controller.get_all_positions()
            for axis_num, pos in positions.items():
                self.settings.child('multiaxes', 'axis' + str(axis_num-1), 'move_abs', 'value').setValue(pos)

        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Status update error: {e}", "log"]))

    def close(self):
        """Close connection to ESP300."""
        self.poll_timer.stop()
        if self.controller:
            self.controller.disconnect()

    def get_actuator_value(self):
        """Get current position(s) of the actuator(s)."""
        positions = self.controller.get_all_positions()
        return DataActuator(data=[np.array(list(positions.values()))])

    def move_abs(self, position: DataActuator):
        """Move to absolute position(s)."""
        try:
            target_positions = {i + 1: pos for i, pos in enumerate(position.value())}
            self.controller.move_multiple_axes(target_positions, wait=False)
            self.emit_status(ThreadCommand("Update_Status", [f"Moving to {target_positions}"]))
        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Move error: {e}", "error"]))

    def move_rel(self, position: DataActuator):
        """Move by relative distance(s)."""
        try:
            current_positions = self.get_actuator_value().value()
            relative_moves = position.value()
            target_positions = [current + rel for current, rel in zip(current_positions, relative_moves)]
            self.move_abs(DataActuator(data=target_positions))
        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Relative move error: {e}", "error"]))

    def move_home(self):
        """Move all axes to home position."""
        try:
            self.controller.home_all_axes()
        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Homing error: {e}", "error"]))

    def stop_motion(self):
        """Stop all axis motion immediately."""
        try:
            self.controller.stop_all_axes()
        except ESP300Error as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Stop error: {e}", "error"]))


if __name__ == "__main__":
    main(__file__)
