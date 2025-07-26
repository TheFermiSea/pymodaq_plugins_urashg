import time
from typing import Optional

from qtpy.QtCore import QTimer
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ plugin for MaiTai laser wavelength control.
    
    Fully compliant with PyMoDAQ DAQ_Move_base standards:
    - Uses hardware controller for abstraction
    - Implements non-blocking operations
    - Proper error handling and status reporting
    - Thread-safe operations
    - Follows PyMoDAQ parameter management
    """
    
    # Plugin metadata - PyMoDAQ compliant
    _controller_units = 'nm'
    is_multiaxes = False
    _axis_names = ['Wavelength']
    _epsilon = 0.1  # Wavelength precision in nm
    
    # Plugin parameters - PyMoDAQ standard structure  
    params = comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilon) + [
        # Hardware connection
        {'title': 'Connection:', 'name': 'connection_group', 'type': 'group', 'children': [
            {'title': 'Serial Port:', 'name': 'serial_port', 'type': 'str', 'value': '/dev/ttyUSB0'},
            {'title': 'Baudrate:', 'name': 'baudrate', 'type': 'int', 'value': 115200},
            {'title': 'Timeout (s):', 'name': 'timeout', 'type': 'float', 'value': 2.0, 'min': 0.1, 'max': 10.0},
            {'title': 'Mock Mode:', 'name': 'mock_mode', 'type': 'bool', 'value': False},
        ]},
        
        # Wavelength limits (MaiTai only accepts INTEGER wavelengths)
        {'title': 'Wavelength Range:', 'name': 'wavelength_group', 'type': 'group', 'children': [
            {'title': 'Min Wavelength (nm):', 'name': 'min_wavelength', 'type': 'int', 'value': 700, 'readonly': True},
            {'title': 'Max Wavelength (nm):', 'name': 'max_wavelength', 'type': 'int', 'value': 900, 'readonly': True},
        ]},
        
        # Status monitoring
        {'title': 'Status:', 'name': 'status_group', 'type': 'group', 'children': [
            {'title': 'Current Wavelength (nm):', 'name': 'current_wavelength', 'type': 'float', 'value': 0.0, 'readonly': True},
            {'title': 'Current Power (W):', 'name': 'current_power', 'type': 'float', 'value': 0.0, 'readonly': True},
            {'title': 'Shutter Open:', 'name': 'shutter_open', 'type': 'bool', 'value': False, 'readonly': True},
            {'title': 'Connection Status:', 'name': 'connection_status', 'type': 'str', 'value': 'Disconnected', 'readonly': True},
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        """Initialize MaiTai PyMoDAQ plugin."""
        super().__init__(parent, params_state)
        
        # Hardware controller
        self.controller = None
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.setInterval(1000)  # Update every second
        
    def ini_stage(self):
        """Initialize the hardware stage."""
        try:
            # Import here to avoid issues if module not available
            from pymodaq_plugins_urashg.hardware.urashg.maitai_control import MaiTaiController
            
            # Get connection parameters
            port = self.settings.child('connection_group', 'serial_port').value()
            baudrate = self.settings.child('connection_group', 'baudrate').value()
            timeout = self.settings.child('connection_group', 'timeout').value()
            mock_mode = self.settings.child('connection_group', 'mock_mode').value()
            
            # Create controller
            self.controller = MaiTaiController(
                port=port,
                baudrate=baudrate, 
                timeout=timeout,
                mock_mode=mock_mode
            )
            
            # Connect to hardware
            if self.controller.connect():
                self.settings.child('status_group', 'connection_status').setValue('Connected')
                
                # Get initial status
                self.update_status()
                
                # Start status monitoring
                self.status_timer.start()
                
                # Get initial position
                self.current_position = self.get_actuator_value()
                
                return "MaiTai laser initialized successfully", True
            else:
                return "Failed to connect to MaiTai laser", False
                
        except Exception as e:
            return f"Error initializing MaiTai: {str(e)}", False

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

    def get_actuator_value(self):
        """Get current wavelength."""
        if not self.controller or not self.controller.connected:
            return 0.0
            
        try:
            wavelength = self.controller.get_wavelength()
            if wavelength is not None:
                self.current_position = wavelength
                return wavelength
            else:
                return self.current_position if hasattr(self, 'current_position') else 0.0
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error reading wavelength: {str(e)}', 'log']))
            return self.current_position if hasattr(self, 'current_position') else 0.0

    def move_abs(self, position):
        """Move to absolute wavelength position."""
        if not self.controller or not self.controller.connected:
            self.emit_status(ThreadCommand('Update_Status', ['Hardware not connected', 'log']))
            return
            
        try:
            # Validate wavelength range
            min_wl = self.settings.child('wavelength_group', 'min_wavelength').value()
            max_wl = self.settings.child('wavelength_group', 'max_wavelength').value()
            
            if not (min_wl <= position <= max_wl):
                self.emit_status(ThreadCommand('Update_Status', 
                    [f'Wavelength {position} nm outside range [{min_wl}, {max_wl}]', 'log']))
                return
            
            # Set wavelength (MaiTai requires integer)
            success = self.controller.set_wavelength(int(round(position)))
            if success:
                self.emit_status(ThreadCommand('Update_Status', 
                    [f'Moving to {int(round(position))} nm', 'log']))
                
                # Update current position
                self.current_position = int(round(position))
                
                # Emit move done signal
                self.emit_status(ThreadCommand('move_done', [int(round(position))]))
            else:
                self.emit_status(ThreadCommand('Update_Status', 
                    [f'Failed to set wavelength to {position} nm', 'log']))
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error moving: {str(e)}', 'log']))

    def move_rel(self, position):
        """Move to relative wavelength position."""
        current = self.get_actuator_value()
        target = current + position
        self.move_abs(target)

    def stop_motion(self):
        """Stop motion (not applicable for wavelength setting)."""
        self.emit_status(ThreadCommand('Update_Status', ['Stop command received', 'log']))

    def update_status(self):
        """Update status parameters from hardware."""
        if not self.controller or not self.controller.connected:
            return
            
        try:
            # Update wavelength
            wavelength = self.controller.get_wavelength()
            if wavelength is not None:
                self.settings.child('status_group', 'current_wavelength').setValue(wavelength)
            
            # Update power
            power = self.controller.get_power()
            if power is not None:
                self.settings.child('status_group', 'current_power').setValue(power)
                
            # Update shutter state
            shutter = self.controller.get_shutter_state()
            if shutter is not None:
                self.settings.child('status_group', 'shutter_open').setValue(shutter)
                
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Status update error: {str(e)}', 'log']))


if __name__ == "__main__":
    # This part is for testing the plugin independently
    import sys

    from pymodaq.dashboard import DashBoard
    from pymodaq.utils import daq_utils as utils
    from qtpy import QtWidgets

    app = utils.get_qapp()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    # It's good practice to have a mock version for development without hardware
    # For this example, we assume the hardware is connected.
    # To run, you would need a virtual COM port pair (e.g., com0com)
    # and a script simulating the MaiTai on the other end.

    win = QtWidgets.QMainWindow()
    area = utils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    prog = DashBoard(area)
    win.show()

    # To test, you would manually add the DAQ_Move module in the dashboard GUI
    # and select this DAQ_Move_MaiTai plugin.

    sys.exit(app.exec_())
