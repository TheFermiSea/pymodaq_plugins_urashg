import time
from typing import List

from qtpy.QtCore import QTimer
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand


class DAQ_Move_Elliptec(DAQ_Move_base):
    """
    PyMoDAQ plugin for Thorlabs Elliptec rotation mounts (ELL14).
    
    Supports multi-axis control of up to 3 rotation mounts:
    - HWP incident polarizer (address 2)
    - QWP quarter wave plate (address 3) 
    - HWP analyzer (address 8)
    """
    
    # Plugin metadata
    _controller_units = 'degrees'
    is_multiaxes = True
    _axis_names = ['Mount_2', 'Mount_3', 'Mount_8']  # Mount addresses
    _epsilon = 0.1  # Position precision in degrees
    
    # Plugin parameters
    params = comon_parameters_fun(is_multiaxes=True, axis_names=_axis_names, epsilon=_epsilon) + [
        # Hardware connection
        {'title': 'Connection:', 'name': 'connection_group', 'type': 'group', 'children': [
            {'title': 'Serial Port:', 'name': 'serial_port', 'type': 'str', 'value': '/dev/ttyUSB1'},
            {'title': 'Baudrate:', 'name': 'baudrate', 'type': 'int', 'value': 9600},
            {'title': 'Timeout (s):', 'name': 'timeout', 'type': 'float', 'value': 2.0, 'min': 0.1, 'max': 10.0},
            {'title': 'Mount Addresses:', 'name': 'mount_addresses', 'type': 'str', 'value': '2,3,8'},
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False},
        ]},
        
        # Device actions
        {'title': 'Actions:', 'name': 'actions_group', 'type': 'group', 'children': [
            {'title': 'Home All Mounts:', 'name': 'home_all', 'type': 'action'},
        ]},
        
        # Status monitoring
        {'title': 'Status:', 'name': 'status_group', 'type': 'group', 'children': [
            {'title': 'Mount 2 Position (deg):', 'name': 'mount_2_pos', 'type': 'float', 'value': 0.0, 'readonly': True},
            {'title': 'Mount 3 Position (deg):', 'name': 'mount_3_pos', 'type': 'float', 'value': 0.0, 'readonly': True},
            {'title': 'Mount 8 Position (deg):', 'name': 'mount_8_pos', 'type': 'float', 'value': 0.0, 'readonly': True},
            {'title': 'Connection Status:', 'name': 'connection_status', 'type': 'str', 'value': 'Disconnected', 'readonly': True},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        """Initialize Elliptec PyMoDAQ plugin."""
        super().__init__(parent, params_state)
        
        # Hardware controller
        self.controller = None
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.setInterval(2000)  # Update every 2 seconds
        
    def ini_stage(self):
        """Initialize the hardware stage."""
        try:
            # Import here to avoid issues if module not available
            from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController
            
            # Get connection parameters
            port = self.settings.child('connection_group', 'serial_port').value()
            baudrate = self.settings.child('connection_group', 'baudrate').value()
            timeout = self.settings.child('connection_group', 'timeout').value()
            mount_addresses = self.settings.child('connection_group', 'mount_addresses').value()
            mock_mode = self.settings.child('connection_group', 'mock_mode').value()
            
            # Create controller
            self.controller = ElliptecController(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                mount_addresses=mount_addresses,
                mock_mode=mock_mode
            )
            
            # Connect to hardware
            if self.controller.connect():
                self.settings.child('status_group', 'connection_status').setValue('Connected')
                
                # Get initial status
                self.update_status()
                
                # Start status monitoring
                self.status_timer.start()
                
                # Get initial positions
                self.current_position = self.get_actuator_value()
                
                return "Elliptec mounts initialized successfully", True
            else:
                return "Failed to connect to Elliptec mounts", False
                
        except Exception as e:
            return f"Error initializing Elliptec: {str(e)}", False

    def close(self):
        """Close the hardware connection."""
        try:
            # Stop status monitoring
            if self.status_timer.isActive():
                self.status_timer.stop()
            
            # Disconnect hardware
            if self.controller and self.controller.connected:
                self.controller.disconnect()
                
            self.settings.child('status_group', 'connection_status').setValue('Disconnected')
            
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error closing: {str(e)}', 'log']))

    def commit_settings(self, param):
        """Handle parameter changes."""
        if param.name() == 'home_all':
            self.home_all_mounts()

    def home_all_mounts(self):
        """Home all rotation mounts."""
        if not self.controller or not self.controller.connected:
            self.emit_status(ThreadCommand('Update_Status', ['Hardware not connected', 'log']))
            return
            
        try:
            self.emit_status(ThreadCommand('Update_Status', ['Homing all mounts...', 'log']))
            success = self.controller.home_all()
            if success:
                self.emit_status(ThreadCommand('Update_Status', ['All mounts homed successfully', 'log']))
                self.update_status()
            else:
                self.emit_status(ThreadCommand('Update_Status', ['Homing failed', 'log']))
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error homing: {str(e)}', 'log']))

    def get_actuator_value(self):
        """Get current positions of all mounts."""
        if not self.controller or not self.controller.connected:
            return [0.0] * len(self.controller.mount_addresses) if self.controller else [0.0, 0.0, 0.0]
            
        try:
            positions = self.controller.get_all_positions()
            # Convert dict to list in correct order
            position_list = []
            for addr in self.controller.mount_addresses:
                position_list.append(positions.get(addr, 0.0))
            
            self.current_position = position_list
            return position_list
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error reading positions: {str(e)}', 'log']))
            return self.current_position if hasattr(self, 'current_position') else [0.0, 0.0, 0.0]

    def move_abs(self, positions):
        """Move to absolute positions."""
        if not self.controller or not self.controller.connected:
            self.emit_status(ThreadCommand('Update_Status', ['Hardware not connected', 'log']))
            return
            
        try:
            # Move each mount to its target position
            for i, (addr, position) in enumerate(zip(self.controller.mount_addresses, positions)):
                success = self.controller.move_absolute(addr, position)
                if success:
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f'Mount {addr} moving to {position:.2f} degrees', 'log']))
                else:
                    self.emit_status(ThreadCommand('Update_Status', 
                        [f'Failed to move mount {addr}', 'log']))
            
            # Update current position
            self.current_position = positions
            
            # Emit move done signal
            self.emit_status(ThreadCommand('move_done', [positions]))
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error moving: {str(e)}', 'log']))

    def move_rel(self, positions):
        """Move to relative positions."""
        current = self.get_actuator_value()
        target = [c + p for c, p in zip(current, positions)]
        self.move_abs(target)

    def stop_motion(self):
        """Stop motion (not implemented for Elliptec)."""
        self.emit_status(ThreadCommand('Update_Status', ['Stop command received', 'log']))

    def update_status(self):
        """Update status parameters from hardware."""
        if not self.controller or not self.controller.connected:
            return
            
        try:
            # Update positions
            positions = self.controller.get_all_positions()
            
            # Update individual mount positions in UI
            if '2' in positions:
                self.settings.child('status_group', 'mount_2_pos').setValue(positions['2'])
            if '3' in positions:
                self.settings.child('status_group', 'mount_3_pos').setValue(positions['3'])
            if '8' in positions:
                self.settings.child('status_group', 'mount_8_pos').setValue(positions['8'])
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Status update error: {str(e)}', 'log']))


if __name__ == "__main__":
    import sys

    from pymodaq.dashboard import DashBoard
    from pymodaq.utils import daq_utils as utils
    from qtpy import QtWidgets

    app = utils.get_qapp()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    win = QtWidgets.QMainWindow()
    area = utils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    prog = DashBoard(area)
    win.show()

    sys.exit(app.exec_())
