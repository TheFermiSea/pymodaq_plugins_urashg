from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, Slot

class StatusIndicator(QtWidgets.QLabel):
    """A QLabel that changes color based on status."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("color: white; background-color: grey; border-radius: 5px; padding: 2px;")
        self.set_status(False)

    def set_status(self, active):
        if active:
            self.setStyleSheet("color: white; background-color: green; border-radius: 5px; padding: 2px;")
        else:
            self.setStyleSheet("color: white; background-color: red; border-radius: 5px; padding: 2px;")

class MaiTaiUI(QtWidgets.QWidget):
    """
    Custom user interface for the MaiTai laser plugin.
    Provides controls for wavelength, shutter, and displays key laser status parameters.
    """
    # Signals to connect to the main plugin logic
    open_shutter_signal = Signal()
    close_shutter_signal = Signal()
    set_wavelength_signal = Signal(float)
    status_update_signal = Signal()  # Signal to request a status update from the hardware
    check_errors_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Create and arrange the UI elements."""
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # --- Wavelength Control ---
        wl_group = QtWidgets.QGroupBox("Wavelength Control")
        wl_layout = QtWidgets.QGridLayout()
        
        self.current_wl_label = QtWidgets.QLabel("Current: -- nm")
        self.target_wl_input = QtWidgets.QDoubleSpinBox()
        self.target_wl_input.setRange(700.0, 1000.0)
        self.target_wl_input.setSuffix(" nm")
        self.set_wl_button = QtWidgets.QPushButton("Set Wavelength")

        wl_layout.addWidget(self.current_wl_label, 0, 0)
        wl_layout.addWidget(QtWidgets.QLabel("Target:"), 1, 0)
        wl_layout.addWidget(self.target_wl_input, 1, 1)
        wl_layout.addWidget(self.set_wl_button, 1, 2)
        wl_group.setLayout(wl_layout)
        main_layout.addWidget(wl_group)

        # --- Shutter & Power ---
        shutter_power_group = QtWidgets.QGroupBox("Shutter & Power")
        sp_layout = QtWidgets.QGridLayout()

        self.shutter_status_label = QtWidgets.QLabel("Shutter: Unknown")
        self.open_shutter_button = QtWidgets.QPushButton("Open Shutter")
        self.close_shutter_button = QtWidgets.QPushButton("Close Shutter")
        self.power_label = QtWidgets.QLabel("Power: -- W")

        sp_layout.addWidget(self.shutter_status_label, 0, 0, 1, 2)
        sp_layout.addWidget(self.open_shutter_button, 1, 0)
        sp_layout.addWidget(self.close_shutter_button, 1, 1)
        sp_layout.addWidget(self.power_label, 2, 0, 1, 2)
        shutter_power_group.setLayout(sp_layout)
        main_layout.addWidget(shutter_power_group)

        # --- Laser Status ---
        status_group = QtWidgets.QGroupBox("Laser Status")
        status_layout = QtWidgets.QHBoxLayout()

        self.modelocked_indicator = StatusIndicator("Modelocked")
        self.emission_indicator = StatusIndicator("Emission")
        
        status_layout.addWidget(self.modelocked_indicator)
        status_layout.addWidget(self.emission_indicator)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # --- System & Errors ---
        system_group = QtWidgets.QGroupBox("System")
        system_layout = QtWidgets.QHBoxLayout()
        self.check_errors_button = QtWidgets.QPushButton("Check For Errors")
        system_layout.addWidget(self.check_errors_button)
        system_group.setLayout(system_layout)
        main_layout.addWidget(system_group)
        
        main_layout.addStretch()

        # --- Connect Signals ---
        self.open_shutter_button.clicked.connect(self.open_shutter_signal.emit)
        self.close_shutter_button.clicked.connect(self.close_shutter_signal.emit)
        self.set_wl_button.clicked.connect(self._emit_set_wavelength)
        self.check_errors_button.clicked.connect(self.check_errors_signal.emit)

        # --- Timer for periodic status updates ---
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(2000)  # Update every 2 seconds
        self.update_timer.timeout.connect(self.status_update_signal.emit)
        self.update_timer.start()

    def _emit_set_wavelength(self):
        """Emits the signal to set the wavelength with the current input value."""
        self.set_wavelength_signal.emit(self.target_wl_input.value())

    @Slot(dict)
    def update_status(self, status: dict):
        """Receives a dictionary of status info and updates the UI."""
        self.current_wl_label.setText(f"Current: {status.get('wavelength', '--'):.2f} nm")
        self.power_label.setText(f"Power: {status.get('power', '--'):.3f} W")
        self.shutter_status_label.setText(f"Shutter: {'Open' if status.get('shutter_open') else 'Closed'}")
        self.modelocked_indicator.set_status(status.get('modelocked', False))
        self.emission_indicator.set_status(status.get('emission_possible', False))
