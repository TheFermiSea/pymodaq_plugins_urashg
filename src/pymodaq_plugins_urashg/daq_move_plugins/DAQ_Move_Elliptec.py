import time
import serial
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    comon_parameters_fun,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter


class DAQ_Move_Elliptec(DAQ_Move_base):
    """
    PyMoDAQ Plugin for Thorlabs Elliptec (ELLx) series rotation mounts.

    This plugin communicates with ELL14 and similar devices using the native
    serial protocol. It specifically supports multi-drop communication, allowing
    control of multiple devices on a single serial bus via unique addresses.

    This version dynamically queries each device for its calibration values
    (pulses per degree) and includes robust error handling and a motor
    optimization function.
    """

    # Define the default axis names and their corresponding default addresses
    _axis_names = ["HWP_inc", "QWP", "HWP_ana"]
    _default_addresses = ["2", "3", "8"]

    # Error codes from the manual (page 11)
    _error_codes = {
        "00": "OK, no error",
        "01": "Communication time out",
        "02": "Mechanical time out",
        "03": "Command error or not supported",
        "04": "Value out of range",
        "05": "Module isolated",
        "06": "Module out of isolation",
        "07": "Initializing error",
        "08": "Thermal error",
        "09": "Busy",
        "0A": "Sensor Error",  # 10 decimal
        "0B": "Motor Error",  # 11 decimal
        "0C": "Out of Range",  # 12 decimal
        "0D": "Over Current error",  # 13 decimal
    }

    # Complete command reference from the ELLx manual
    _command_reference = {
        "in": "Get device information (model, SN, firmware, travel, pulses)",
        "gs": "Get status/error code",
        "us": "Save user data (like motor frequencies) to non-volatile memory",
        "ca": "Change the device address",
        "i1": "Get information for Motor 1 (state, current, frequencies)",
        "f1": "Set the forward frequency period for Motor 1",
        "b1": "Set the backward frequency period for Motor 1",
        "s1": "Perform a frequency search to optimize Motor 1",
        "c1": "Request a scan of the current curve for Motor 1",
        "is": "Isolate the device from communication for a specified time",
        "i2": "Get information for Motor 2",
        "f2": "Set the forward frequency period for Motor 2",
        "b2": "Set the backward frequency period for Motor 2",
        "s2": "Perform a frequency search to optimize Motor 2",
        "c2": "Request a scan of the current curve for Motor 2",
        "ho": "Move to the home position",
        "ah": "Set auto-homing behavior on startup (ELL15 Iris only)",
        "ma": "Move to an absolute position",
        "mr": "Move by a relative amount",
        "go": "Get the home offset distance",
        "so": "Set the home offset distance",
        "gj": "Get the jog step size",
        "sj": "Set the jog step size (0 for continuous motion)",
        "fw": "Jog forward by the jog step size",
        "bw": "Jog backward by the jog step size",
        "st": "Stop the current motion",
        "gp": "Get the current absolute position",
        "gv": "Get the velocity setting (% of max)",
        "sv": "Set the velocity setting (% of max)",
        "ga": "Assign a temporary group address for synchronized moves",
        "om": "Perform an extended motor optimization routine",
        "cm": "Start a mechanical cleaning cycle",
        "e1": "Energize Motor 1 at a specified frequency (piezo drivers only)",
        "h1": "Halt (de-energize) Motor 1 (piezo drivers only)",
    }

    # Define the specific settings for this plugin
    params = [
        {
            "title": "Multi-axis settings:",
            "name": "multiaxes",
            "type": "group",
            "visible": True,
            "children": [
                {
                    "title": "Axes names:",
                    "name": "axis_names",
                    "type": "list",
                    "limits": _axis_names,
                },
                {
                    "title": "Selected axis:",
                    "name": "selected_axis",
                    "type": "str",
                    "value": _axis_names[0],
                    "readonly": True,
                },
            ],
        },
        {
            "title": "Elliptec Settings",
            "name": "elliptec_settings",
            "type": "group",
            "children": [
                {
                    "title": "Addresses",
                    "name": "addresses",
                    "type": "group",
                    "children": [
                        # NOTE: The addresses below are defaults. Please verify these against your
                        # actual hardware configuration before connecting.
                        {
                            "title": f"{name} Address:",
                            "name": f"address_{name}",
                            "type": "str",
                            "value": addr,
                        }
                        for name, addr in zip(_axis_names, _default_addresses)
                    ],
                },
                {
                    "title": "Home All on Connect",
                    "name": "home_on_connect",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Optimize Selected Motor",
                    "name": "optimize_motor",
                    "type": "action",
                },
            ],
        },
    ]

    # Add common parameters if the function returns a list
    common_params = comon_parameters_fun(is_multiaxes=True, axes_names=_axis_names)
    if isinstance(common_params, list):
        params.extend(common_params)

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controller: serial.Serial = None
        self.pulses_per_deg = {}  # Dictionary to store calibration for each axis

    def get_axis_address(self, axis_name=None):
        """Gets the address for a given axis name from the settings."""
        if axis_name is None:
            axis_name = self.settings.child("multiaxes", "selected_axis").value()
        return self.settings.child(
            "elliptec_settings", "addresses", f"address_{axis_name}"
        ).value()

    def commit_settings(self, param: Parameter):
        """Apply changes made in the GUI settings."""
        if param.name() == "connect" and param.value():
            try:
                self.controller = serial.Serial(
                    self.settings.child("serial", "com_port").value(),
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0,
                )
                self.emit_status(
                    ThreadCommand("status", ["Serial connection opened.", "log"])
                )

                # Query information and set up each axis
                for axis in self._axis_names:
                    self.setup_axis(axis)

                if self.settings.child("elliptec_settings", "home_on_connect").value():
                    self.home_all_axes()

                self.get_actuator_value()  # Update initial position

            except serial.SerialException as e:
                self.emit_status(
                    ThreadCommand("status", [f"Connection failed: {str(e)}", "log"])
                )
                self.settings.child("connect").setValue(False)

        elif param.name() == "connect" and not param.value():
            self.close()

        elif param.name() == "optimize_motor":
            self.run_optimization()

    def setup_axis(self, axis_name: str):
        """Queries an axis for its info and calculates its pulses_per_deg."""
        address = self.get_axis_address(axis_name)
        self.emit_status(
            ThreadCommand(
                "status",
                [
                    f"Querying info for {axis_name} at address {address}...",
                    "log",
                ],
            )
        )

        # Command 'in' gets device information (see manual page 10)
        response = self.send_command(address, "in")

        if response and len(response) == 33 and response[1:3] == "IN":
            try:
                # Response format: <addr>IN<type><sn><year><fw><hw><travel><pulses>
                travel_hex = response[21:25]
                pulses_hex = response[25:33]

                travel = int(travel_hex, 16)  # This is 360 for rotation stages
                pulses_per_rev = int(pulses_hex, 16)

                if travel > 0:
                    self.pulses_per_deg[axis_name] = pulses_per_rev / travel
                    self.emit_status(
                        ThreadCommand(
                            "status",
                            [
                                f"{axis_name} setup complete. Pulses/Deg: {self.pulses_per_deg[axis_name]:.2f}",
                                "log",
                            ],
                        )
                    )
                else:
                    raise ValueError("Travel reported as zero.")

            except (ValueError, IndexError) as e:
                self.emit_status(
                    ThreadCommand(
                        "status",
                        [
                            f"Failed to parse info for {axis_name}. Response: {response}. Error: {e}",
                            "error",
                        ],
                    )
                )
                self.pulses_per_deg[axis_name] = 262144 / 360.0  # Fallback to default
        else:
            self.emit_status(
                ThreadCommand(
                    "status",
                    [
                        f"No/Invalid info from {axis_name} at address {address}. Using default calibration.",
                        "warning",
                    ],
                )
            )
            self.pulses_per_deg[axis_name] = 262144 / 360.0  # Fallback to default

    def home_all_axes(self):
        """Sends the home command to all configured axes."""
        self.emit_status(ThreadCommand("status", ["Homing all axes...", "log"]))
        for axis in self._axis_names:
            address = self.get_axis_address(axis)
            self.send_command(address, "ho", "1")  # Home CCW
            self._wait_for_action_completion(address)
            self.emit_status(ThreadCommand("status", [f"{axis} homed.", "log"]))
        self.emit_status(ThreadCommand("status", ["Homing complete.", "log"]))

    def close(self):
        """Cleanly close the serial connection."""
        if self.controller is not None and self.controller.is_open:
            self.controller.close()
        self.emit_status(ThreadCommand("status", ["Serial connection closed.", "log"]))

    def send_command(self, address: str, command: str, data: str = ""):
        """Constructs and sends a command, returning the response."""
        if self.controller is None or not self.controller.is_open:
            return None
        try:
            full_command = f"{address}{command}{data}\r".encode()
            self.controller.reset_input_buffer()
            self.controller.write(full_command)
            time.sleep(0.05)  # Short pause for device to process
            response = self.controller.readline().decode().strip()
            return response
        except serial.SerialException as e:
            self.emit_status(
                ThreadCommand("status", [f"Command failed: {str(e)}", "error"])
            )
            return None

    def _check_status(self, address: str):
        """Sends 'gs' to get status and logs any errors."""
        status_response = self.send_command(address, "gs")
        if status_response and len(status_response) >= 5:
            status_code = status_response[3:5].upper()
            if status_code != "00" and status_code != "09":  # Ignore OK and Busy
                error_msg = self._error_codes.get(
                    status_code, f"Unknown error code: {status_code}"
                )
                self.emit_status(
                    ThreadCommand(
                        "status",
                        [f"Error from address {address}: {error_msg}", "error"],
                    )
                )
            return status_code
        self.emit_status(
            ThreadCommand(
                "status",
                [f"No status response from address {address}", "warning"],
            )
        )
        return None

    def _wait_for_action_completion(self, address: str):
        """Polls the device status until it is no longer busy."""
        while True:
            status_code = self._check_status(address)
            if status_code is None or status_code != "09":  # '09' means Busy
                break
            time.sleep(0.2)  # Polling interval

    def run_optimization(self):
        """Runs the 'om' motor optimization routine on the selected axis."""
        axis = self.settings.child("multiaxes", "selected_axis").value()
        address = self.get_axis_address(axis)

        self.emit_status(
            ThreadCommand(
                "status",
                [
                    f"Starting motor optimization for {axis}. This will take several minutes...",
                    "log",
                ],
            )
        )

        # This is a blocking call as requested. The GUI may be unresponsive.
        self.send_command(address, "om")
        self._wait_for_action_completion(address)

        # Final status check
        final_status = self._check_status(address)
        if final_status == "00":
            self.emit_status(
                ThreadCommand(
                    "status",
                    [f"Optimization for {axis} completed successfully.", "log"],
                )
            )
        else:
            self.emit_status(
                ThreadCommand("status", [f"Optimization for {axis} failed.", "error"])
            )

    def move_abs(self, position: float):
        """Move the selected actuator to an absolute position in degrees."""
        axis = self.settings.child("multiaxes", "selected_axis").value()
        address = self.get_axis_address(axis)

        conversion_factor = self.pulses_per_deg.get(axis, 262144 / 360.0)
        pos_in_pulses = int(position * conversion_factor)

        hex_pos = f"{pos_in_pulses & 0xFFFFFFFF:08X}"

        self.send_command(address, "ma", hex_pos)
        self._wait_for_action_completion(address)

        self.emit_status(ThreadCommand("move_abs_done", [position]))

    def get_actuator_value(self):
        """Get the current value of the selected actuator in degrees."""
        axis = self.settings.child("multiaxes", "selected_axis").value()
        address = self.get_axis_address(axis)

        if self.controller is None:
            return 0.0

        response = self.send_command(address, "gp")  # gp = get position
        if response and len(response) == 11 and response[1:3] == "PO":
            hex_pos = response[3:]
            try:
                pulses = int(hex_pos, 16)
                if pulses > 0x7FFFFFFF:
                    pulses -= 0x100000000

                conversion_factor = self.pulses_per_deg.get(axis, 262144 / 360.0)
                current_pos_deg = pulses / conversion_factor
                self.current_position = current_pos_deg
                return current_pos_deg
            except (ValueError, ZeroDivisionError) as e:
                self.emit_status(
                    ThreadCommand(
                        "status",
                        [
                            f"Invalid position response or setup for {axis}: {e}",
                            "error",
                        ],
                    )
                )
                return 0.0
        return self.current_position

    def stop_motion(self):
        """Stop the current motion of the selected actuator."""
        address = self.get_axis_address()
        self.send_command(address, "st")  # st = stop
        self.emit_status(ThreadCommand("move_abs_done", [self.current_position]))


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
