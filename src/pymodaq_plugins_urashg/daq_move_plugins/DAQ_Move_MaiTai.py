import threading
import time

import serial
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

# Removed unused imports: get_param_path, iter_children


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ Plugin for the Spectra-Physics MaiTai Ti:Sapphire Laser.

    This plugin provides control over the laser's wavelength and shutter,
    and includes asynchronous monitoring of key laser parameters such as
    output power, status, and current operating wavelength.

    It communicates with the laser via an RS-22 serial connection.
    """

    # Complete command reference from the MaiTai manual (Chapter 6)
    _command_reference = {
        "CONTrol:PHAse": "Sets/reads the RF phase control for the modelocker.",
        "CONTrol:MLENable": "Turns the modelocker RF drive signal on (1) or off (0).",
        "ON": "Turns on the pump laser.",
        "OFF": "Turns off the pump laser diodes.",
        "MODE": "Sets the control mode to pump power (PPOWer) or pump current (PCURrent).",
        "PLASer:ERRCode?": "Returns the pump laser error code.",
        "PLASer:HISTory?": "Returns the 16 most recent status codes from the history buffer.",
        "PLASer:AHISTory?": "Returns an ASCII version of the history buffer.",
        "PLASer:PCURrent": "Sets the pump laser percentage of available current.",
        "PLASer:POWer": "Sets the pump laser output power in Watts.",
        "READ:PCTWarmedup?": "Reads the system warm-up status as a percentage.",
        "READ:PLASer:POWer?": "Reads the actual output power of the pump laser.",
        "READ:PLASer:PCURrent?": "Reads the percentage of full operating current for the pump laser.",
        "READ:PLASer:SHGS?": "Reads the pump laser SHG crystal temperature status.",
        "READ:PLASer:DIODe#:CURRent?": "Reads the current of a specific pump diode (1 or 2).",
        "READ:PLASer:DIODe#:TEMPerature?": "Reads the temperature of a specific pump diode (1 or 2).",
        "READ:POWer?": "Reads the output power of the Mai Tai laser.",
        "READ:WAVelength?": "Reads the current operating wavelength of the Mai Tai.",
        "SAVE": "Saves the current Mai Tai status to non-volatile memory.",
        "SHUTter": "Opens (1) or closes (0) the shutter.",
        "SYSTem:COMMunications:SERial:BAUD": "Sets the serial communication baud rate.",
        "SYSTem:ERR?": "Returns the last communication error message.",
        "TIMer:WATChdog": "Sets the software watchdog timer in seconds (0 disables).",
        "WAVelength": "Sets the Mai Tai output wavelength in nm.",
        "WAVelength:MIN?": "Returns the minimum configurable wavelength.",
        "WAVelength:MAX?": "Returns the maximum configurable wavelength.",
        "*IDN?": "Returns the system identification string.",
        "*STB?": "Returns the status byte, indicating modelocking, emission, etc.",
    }

    # Define the specific settings for this plugin
    params = [
        {
            "title": "Multi-axis settings:",
            "name": "multi_axis",
            "type": "group",
            "children": [
                {
                    "title": "Axes names:",
                    "name": "axis_names",
                    "type": "list",
                    "limits": ["Wavelength", "Shutter"],
                },
                {
                    "title": "Selected axis:",
                    "name": "selected_axis",
                    "type": "str",
                    "value": "Wavelength",
                    "readonly": True,
                },
            ],
        },
        {
            "title": "MaiTai Status:",
            "name": "maitai_status",
            "type": "group",
            "children": [
                {
                    "title": "Warmup (%):",
                    "name": "warmup_percent",
                    "type": "int",
                    "value": 0,
                    "readonly": True,
                },
                {
                    "title": "Pulsing:",
                    "name": "pulsing",
                    "type": "bool",
                    "value": False,
                    "readonly": True,
                },
                {
                    "title": "Output Power (W):",
                    "name": "output_power",
                    "type": "float",
                    "value": 0.0,
                    "readonly": True,
                    "si": True,
                },
                {
                    "title": "System Status:",
                    "name": "system_status_message",
                    "type": "str",
                    "value": "Disconnected",
                    "readonly": True,
                },
                {
                    "title": "Laser On:",
                    "name": "laser_on",
                    "type": "led",
                    "value": False,
                },
            ],
        },
    ]

    # PyMoDAQ 5 handles common parameters differently
    # Common parameters are automatically added by the base class

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controller: serial.Serial = None
        self.monitoring_thread = None
        self.stop_thread_flag = threading.Event()

    def commit_settings(self, param: Parameter):
        """
        Apply changes made in the GUI settings.
        Establishes the serial connection when the 'connect' button is pressed.
        """
        if param.name() == "connect" and param.value():
            try:
                self.controller = serial.Serial(
                    self.settings.child("serial", "com_port").value(),
                    baudrate=9600,  # Default baud rate on power-up
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                )
                self.settings.child("maitai_status", "system_status_message").setValue(
                    "Connected"
                )
                self.start_monitoring()
                self.get_actuator_value()  # Update initial position
            except serial.SerialException as e:
                self.emit_status(
                    ThreadCommand("status", [f"Connection failed: {str(e)}", "log"])
                )
                self.settings.child("connect").setValue(False)
        elif param.name() == "connect" and not param.value():
            self.close()

    def close(self):
        """
        Cleanly close the serial connection and stop the monitoring thread.
        """
        self.stop_thread_flag.set()
        if self.monitoring_thread is not None:
            self.monitoring_thread.join()
        if self.controller is not None and self.controller.is_open:
            self.controller.close()
        self.settings.child("maitai_status", "system_status_message").setValue(
            "Disconnected"
        )

    def _send_command(self, command: str, expect_response=True):
        """
        Sends a command to the laser and optionally reads the response.
        All commands must be terminated with a carriage return and line feed.
        """
        if self.controller is None or not self.controller.is_open:
            return None
        try:
            full_command = f"{command}\r\n".encode()
            self.controller.write(full_command)
            if expect_response:
                response = self.controller.readline().decode().strip()
                return response
        except serial.SerialException as e:
            self.emit_status(
                ThreadCommand("status", [f"Command failed: {str(e)}", "log"])
            )
            return None
        return None

    def move_abs(self, position: float):
        """
        Move the selected actuator to an absolute position.
        """
        axis = self.settings.child("multiaxes", "selected_axis").value()
        command = ""
        if axis == "Wavelength":
            command = f"WAVelength {position:.1f}"
        elif axis == "Shutter":
            # 1 for open, 0 for closed
            command = f"SHUTter {int(position)}"

        if command:
            self._send_command(command, expect_response=False)
            # The laser takes time to adjust, so we don't immediately get a move_done.
            # A better implementation would poll the status until the move is complete.
            # For simplicity here, we assume the command is sent and will eventually complete.
            self.get_actuator_value()  # Update the current position display
        self.emit_status(ThreadCommand("move_abs_done", [position]))

    def get_actuator_value(self):
        """
        Get the current value of the selected actuator.
        """
        axis = self.settings.child("multiaxes", "selected_axis").value()
        response = ""
        if self.controller is None:
            return 0.0

        if axis == "Wavelength":
            response = self._send_command("READ:WAVelength?")
            if response:
                try:
                    current_pos = float(response)
                    self.current_position = current_pos
                    return current_pos
                except (ValueError, TypeError):
                    return 0.0
        elif axis == "Shutter":
            response = self._send_command("SHUTter?")
            if response:
                try:
                    current_pos = int(response)
                    self.current_position = current_pos
                    return current_pos
                except (ValueError, TypeError):
                    return 0
        return self.current_position

    def stop_motion(self):
        """
        Stop the current motion. Not directly applicable for setting wavelength or shutter state,
        but required by the base class.
        """
        # No direct stop command for these actions.
        self.emit_status(ThreadCommand("move_abs_done", [self.current_position]))

    def start_monitoring(self):
        """
        Start the background thread for asynchronous status monitoring.
        """
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.stop_thread_flag.clear()
            self.monitoring_thread = threading.Thread(target=self.run_monitoring)
            self.monitoring_thread.start()
            self.emit_status(
                ThreadCommand("status", ["Monitoring thread started.", "log"])
            )

    def run_monitoring(self):
        """
        The main loop for the monitoring thread. Periodically queries the laser status.
        """
        while not self.stop_thread_flag.is_set():
            try:
                # Query output power
                power_str = self._send_command("READ:POWer?")
                if power_str:
                    self.settings.child("maitai_status", "output_power").setValue(
                        float(power_str)
                    )

                # Query system status byte (*STB?)
                # Bit 1 (value 2) indicates modelocked operation (pulsing)
                stb_str = self._send_command("*STB?")
                if stb_str:
                    status_byte = int(stb_str)
                    is_pulsing = bool(status_byte & 2)
                    self.settings.child("maitai_status", "pulsing").setValue(is_pulsing)

                # Query warmup status
                warmup_str = self._send_command("READ:PCTWarmedup?")
                if warmup_str:
                    self.settings.child("maitai_status", "warmup_percent").setValue(
                        int(warmup_str)
                    )

                # Query if laser is on
                # The LASER_ON bit (6) in the status byte indicates emission is possible
                if stb_str:
                    status_byte = int(stb_str)
                    is_on = bool(status_byte & 64)
                    self.settings.child("maitai_status", "laser_on").setValue(is_on)

                # Update the main status message
                if self.settings.child("maitai_status", "laser_on").value():
                    status_msg = "Laser ON"
                    if self.settings.child("maitai_status", "pulsing").value():
                        status_msg += " & Pulsing"
                else:
                    status_msg = "Laser OFF"
                self.settings.child("maitai_status", "system_status_message").setValue(
                    status_msg
                )

                time.sleep(1)  # Polling interval of 1 second

            except (serial.SerialException, ValueError, TypeError) as e:
                self.emit_status(
                    ThreadCommand("status", [f"Monitoring error: {str(e)}", "log"])
                )
                break  # Exit loop on error

        self.emit_status(ThreadCommand("status", ["Monitoring thread stopped.", "log"]))


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
