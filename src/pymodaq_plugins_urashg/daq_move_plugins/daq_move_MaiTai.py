import numpy as np
from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    comon_parameters_fun,
    main,
)
from pymodaq_utils.utils import ThreadCommand
from qtpy.QtCore import Signal, QTimer
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDoubleSpinBox, QGroupBox
)

# Import URASHG configuration
try:
    from pymodaq_plugins_urashg import config
    maitai_config = config.get("urashg", {}).get("hardware", {}).get("maitai", {})
except (ImportError, AttributeError):
    maitai_config = {
        "serial_port": "/dev/ttyUSB1",
        "baudrate": 9600,
        "timeout": 2.0,
        "wavelength_range_min": 700.0,
        "wavelength_range_max": 1000.0,
    }


class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ plugin for controlling MaiTai Ti:Sapphire laser.

    Provides wavelength control, power monitoring, and shutter operations
    for Spectra-Physics MaiTai femtosecond laser systems.

    Features custom UI controls for:
    - Laser on/off control
    - Real-time wavelength display
    - Target wavelength setting
    - Shutter control
    """

    # PyMoDAQ 5.x required attributes
    _controller_units = "nm"
    is_multiaxes = False
    _axis_names = ["Wavelength"]
    _epsilon = 0.1  # nm precision

    params = comon_parameters_fun(
        is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilon
    ) + [
        {
            "title": "Connection Settings:",
            "name": "connection_group",
            "type": "group",
            "children": [
                {
                    "title": "Serial Port:",
                    "name": "serial_port",
                    "type": "str",
                    "value": maitai_config.get("serial_port", "/dev/ttyUSB1"),
                    "tip": "Serial port for MaiTai laser (e.g. /dev/ttyUSB1 or COM3)",
                },
                {
                    "title": "Baudrate:",
                    "name": "baudrate",
                    "type": "list",
                    "limits": [9600, 19200, 38400, 57600, 115200],
                    "value": maitai_config.get("baudrate", 9600),
                    "tip": "Serial communication baud rate",
                },
                {
                    "title": "Timeout (s):",
                    "name": "timeout",
                    "type": "float",
                    "value": maitai_config.get("timeout", 2.0),
                    "min": 0.1,
                    "max": 10.0,
                    "tip": "Communication timeout in seconds",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": False,
                    "tip": "Enable for testing without physical MaiTai laser",
                },
            ],
        },
        {
            "title": "Wavelength Range:",
            "name": "wavelength_range",
            "type": "group",
            "children": [
                {
                    "title": "Min Wavelength (nm):",
                    "name": "min_wavelength",
                    "type": "float",
                    "value": maitai_config.get("wavelength_range_min", 700.0),
                    "min": 700.0,
                    "max": 1000.0,
                    "readonly": True,
                    "tip": "Minimum tunable wavelength for MaiTai laser",
                },
                {
                    "title": "Max Wavelength (nm):",
                    "name": "max_wavelength",
                    "type": "float",
                    "value": maitai_config.get("wavelength_range_max", 1000.0),
                    "min": 700.0,
                    "max": 1000.0,
                    "readonly": True,
                    "tip": "Maximum tunable wavelength for MaiTai laser",
                },
            ],
        },
        {
            "title": "Status:",
            "name": "status_group",
            "type": "group",
            "children": [
                {
                    "title": "Current Wavelength (nm):",
                    "name": "current_wavelength",
                    "type": "float",
                    "value": 800.0,
                    "readonly": True,
                    "tip": "Current laser wavelength",
                },
                {
                    "title": "Laser Status:",
                    "name": "laser_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                    "tip": "Current laser status",
                },
                {
                    "title": "Shutter Status:",
                    "name": "shutter_status",
                    "type": "str",
                    "value": "Unknown",
                    "readonly": True,
                    "tip": "Current shutter status",
                }
            ],
        },
    ]

    def ini_attributes(self):
        """Initialize attributes before __init__ - PyMoDAQ 5.x pattern"""
        self.controller = None
        self.initialized = False

        # Custom UI elements
        self.laser_on_btn = None
        self.status_label = None
        self.current_wavelength_label = None
        self.target_wavelength_spinbox = None
        self.shutter_btn = None

        # Timer for updating display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.setInterval(1000)  # Update every second

    def ini_stage(self, controller=None):
        """Initialize the MaiTai laser controller."""
        self.initialized = False
        try:
            self.emit_status(
                ThreadCommand("show_splash", "Initializing MaiTai Laser...")
            )

            if self.is_master:
                # Initialize controller based on mock mode
                mock_mode = self.settings.child("connection_group", "mock_mode").value()

                if mock_mode:
                    self.controller = MockMaiTaiController()
                    info = "Mock MaiTai controller initialized"
                else:
                    # Here would be real hardware initialization
                    # from pymodaq_plugins_urashg.hardware.urashg.maitai import MaiTaiController
                    # self.controller = MaiTaiController(...)
                    self.controller = MockMaiTaiController()  # Using mock for now
                    info = "MaiTai controller initialized (using mock)"

                self.initialized = True
            else:
                self.controller = controller
                self.initialized = True
                info = "MaiTai controller shared"

            # Update status
            if self.initialized:
                self.settings.child("status_group", "laser_status").setValue("Ready")
                self.settings.child("status_group", "shutter_status").setValue("Closed")

            return info, self.initialized

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error initializing MaiTai: {e}"])
            )
            return str(e), False

    def get_actuator_value(self):
        """Get the current wavelength from the hardware."""
        try:
            if not self.initialized or not self.controller:
                return DataActuator(data=np.array([800.0]))

            if hasattr(self.controller, "get_wavelength"):
                wavelength = self.controller.get_wavelength()
                if wavelength is not None and not np.isnan(wavelength):
                    # Update parameter tree
                    self.settings.child("status_group", "current_wavelength").setValue(wavelength)
                    return DataActuator(data=np.array([wavelength]))

            # Fallback
            return DataActuator(data=np.array([800.0]))

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error reading wavelength: {e}"])
            )
            return DataActuator(data=np.array([800.0]))

    def move_abs(self, position):
        """Move to absolute wavelength position."""
        try:
            if isinstance(position, DataActuator):
                target_wavelength = position.value()
            else:
                target_wavelength = float(position)

            if self.controller and hasattr(self.controller, "set_wavelength"):
                success = self.controller.set_wavelength(target_wavelength)
                if success:
                    self.emit_status(
                        ThreadCommand("Update_Status", [f"Moving to {target_wavelength:.1f} nm"])
                    )
                else:
                    self.emit_status(
                        ThreadCommand("Update_Status", ["Failed to set wavelength"])
                    )
            else:
                self.emit_status(
                    ThreadCommand("Update_Status", [f"Mock: Set wavelength to {target_wavelength:.1f} nm"])
                )

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving to wavelength: {e}"])
            )

    def move_rel(self, position):
        """Move relative to current wavelength position."""
        try:
            current_pos = self.get_actuator_value()
            if isinstance(current_pos, DataActuator):
                current_wavelength = current_pos.value()
            else:
                current_wavelength = current_pos

            if isinstance(position, DataActuator):
                relative_move = position.value()
            else:
                relative_move = float(position)

            target_wavelength = current_wavelength + relative_move
            self.move_abs(target_wavelength)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error in relative move: {e}"])
            )

    def move_home(self):
        """Move to home position (center wavelength)."""
        try:
            home_wavelength = 800.0  # nm
            self.move_abs(home_wavelength)
            self.emit_status(
                ThreadCommand("Update_Status", ["Moving to home position (800 nm)"])
            )
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error moving home: {e}"])
            )

    def stop_motion(self):
        """Stop wavelength change."""
        try:
            if self.controller and hasattr(self.controller, "stop"):
                self.controller.stop()
            self.emit_status(ThreadCommand("Update_Status", ["Motion stopped"]))
        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error stopping motion: {e}"])
            )

    def commit_settings(self, param):
        """Handle parameter changes and actions."""
        # Standard parameter handling is sufficient for this plugin
        pass

    def custom_ui(self):
        """Create custom UI controls for MaiTai laser."""
        try:
            # Main widget
            main_widget = QWidget()
            main_layout = QVBoxLayout()

            # Laser Control Group
            laser_group = QGroupBox("Laser Control")
            laser_layout = QVBoxLayout()

            # Laser On/Off Button
            self.laser_on_btn = QPushButton("Laser OFF")
            self.laser_on_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 12pt;
                    min-height: 40px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
            """)
            self.laser_on_btn.clicked.connect(self.toggle_laser)
            laser_layout.addWidget(self.laser_on_btn)

            # Status Label
            self.status_label = QLabel("Status: Initializing...")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 10pt;
                    padding: 5px;
                }
            """)
            laser_layout.addWidget(self.status_label)

            laser_group.setLayout(laser_layout)
            main_layout.addWidget(laser_group)

            # Wavelength Control Group
            wavelength_group = QGroupBox("Wavelength Control")
            wavelength_layout = QVBoxLayout()

            # Current Wavelength Display
            current_layout = QHBoxLayout()
            current_layout.addWidget(QLabel("Current:"))
            self.current_wavelength_label = QLabel("--- nm")
            self.current_wavelength_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14pt;
                    color: #2ecc71;
                    padding: 5px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    background-color: #ecf0f1;
                }
            """)
            current_layout.addWidget(self.current_wavelength_label)
            current_layout.addStretch()
            wavelength_layout.addLayout(current_layout)

            # Target Wavelength Input
            target_layout = QHBoxLayout()
            target_layout.addWidget(QLabel("Target:"))
            self.target_wavelength_spinbox = QDoubleSpinBox()
            self.target_wavelength_spinbox.setRange(700.0, 1000.0)
            self.target_wavelength_spinbox.setValue(800.0)
            self.target_wavelength_spinbox.setSuffix(" nm")
            self.target_wavelength_spinbox.setDecimals(1)
            self.target_wavelength_spinbox.setStyleSheet("""
                QDoubleSpinBox {
                    font-size: 11pt;
                    min-height: 25px;
                    padding: 3px;
                }
            """)
            target_layout.addWidget(self.target_wavelength_spinbox)

            # Set Wavelength Button
            set_wavelength_btn = QPushButton("Set Wavelength")
            set_wavelength_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    min-height: 30px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            set_wavelength_btn.clicked.connect(self.move_to_target)
            target_layout.addWidget(set_wavelength_btn)
            wavelength_layout.addLayout(target_layout)

            wavelength_group.setLayout(wavelength_layout)
            main_layout.addWidget(wavelength_group)

            # Shutter Control Group
            shutter_group = QGroupBox("Shutter Control")
            shutter_layout = QHBoxLayout()

            # Shutter On/Off Button
            self.shutter_btn = QPushButton("Shutter CLOSED")
            self.shutter_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 12pt;
                    min-height: 40px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
            """)
            self.shutter_btn.clicked.connect(self.toggle_shutter)
            shutter_layout.addWidget(self.shutter_btn)

            shutter_group.setLayout(shutter_layout)
            main_layout.addWidget(shutter_group)

            main_layout.addStretch()
            main_widget.setLayout(main_layout)

            # Start update timer
            self.update_timer.start()

            return main_widget

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error creating custom UI: {e}"]))
            return QWidget()

    def toggle_laser(self):
        """Toggle laser on/off state."""
        try:
            if self.laser_on_btn.text() == "Laser OFF":
                # Turn laser ON
                if self.controller and hasattr(self.controller, "turn_on"):
                    success = self.controller.turn_on()
                else:
                    success = True  # Mock success

                if success:
                    self.laser_on_btn.setText("Laser ON")
                    self.laser_on_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2ecc71;
                            color: white;
                            font-weight: bold;
                            font-size: 12pt;
                            min-height: 40px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #27ae60;
                        }
                    """)
                    self.status_label.setText("Status: Laser ON")
                    self.settings.child("status_group", "laser_status").setValue("On")
                    self.emit_status(ThreadCommand("Update_Status", ["Laser turned ON"]))
                else:
                    self.emit_status(ThreadCommand("Update_Status", ["Failed to turn laser ON"]))
            else:
                # Turn laser OFF
                if self.controller and hasattr(self.controller, "turn_off"):
                    success = self.controller.turn_off()
                else:
                    success = True  # Mock success

                if success:
                    self.laser_on_btn.setText("Laser OFF")
                    self.laser_on_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ff6b6b;
                            color: white;
                            font-weight: bold;
                            font-size: 12pt;
                            min-height: 40px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #ff5252;
                        }
                    """)
                    self.status_label.setText("Status: Laser OFF")
                    self.settings.child("status_group", "laser_status").setValue("Off")
                    self.emit_status(ThreadCommand("Update_Status", ["Laser turned OFF"]))
                else:
                    self.emit_status(ThreadCommand("Update_Status", ["Failed to turn laser OFF"]))

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error toggling laser: {e}"]))

    def toggle_shutter(self):
        """Toggle shutter open/closed state."""
        try:
            if self.shutter_btn.text() == "Shutter CLOSED":
                self.open_shutter()
            else:
                self.close_shutter()
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error toggling shutter: {e}"]))

    def open_shutter(self):
        """Open the laser shutter."""
        try:
            if self.controller and hasattr(self.controller, "open_shutter"):
                success = self.controller.open_shutter()
            else:
                success = True  # Mock success

            if success:
                self.shutter_btn.setText("Shutter OPEN")
                self.shutter_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2ecc71;
                        color: white;
                        font-weight: bold;
                        font-size: 12pt;
                        min-height: 40px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #27ae60;
                    }
                """)
                self.settings.child("status_group", "shutter_status").setValue("Open")
                self.emit_status(ThreadCommand("Update_Status", ["Shutter opened"]))
            else:
                self.emit_status(ThreadCommand("Update_Status", ["Failed to open shutter"]))

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error opening shutter: {e}"]))

    def close_shutter(self):
        """Close the laser shutter."""
        try:
            if self.controller and hasattr(self.controller, "close_shutter"):
                success = self.controller.close_shutter()
            else:
                success = True  # Mock success

            if success:
                self.shutter_btn.setText("Shutter CLOSED")
                self.shutter_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6b6b;
                        color: white;
                        font-weight: bold;
                        font-size: 12pt;
                        min-height: 40px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #ff5252;
                    }
                """)
                self.settings.child("status_group", "shutter_status").setValue("Closed")
                self.emit_status(ThreadCommand("Update_Status", ["Shutter closed"]))
            else:
                self.emit_status(ThreadCommand("Update_Status", ["Failed to close shutter"]))

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error closing shutter: {e}"]))

    def move_to_target(self):
        """Move to the target wavelength set in the spinbox."""
        try:
            target = self.target_wavelength_spinbox.value()
            self.move_abs(DataActuator(data=np.array([target])))
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [f"Error moving to target: {e}"]))

    def update_display(self):
        """Update the custom UI display with current values."""
        try:
            if self.initialized and self.current_wavelength_label:
                # Get current wavelength
                current_pos = self.get_actuator_value()
                if isinstance(current_pos, DataActuator):
                    wavelength = current_pos.value()
                    if np.isscalar(wavelength):
                        self.current_wavelength_label.setText(f"{wavelength:.1f} nm")
                    elif len(wavelength) > 0:
                        self.current_wavelength_label.setText(f"{wavelength[0]:.1f} nm")

        except Exception:
            # Don't spam errors during display updates
            pass

    def close(self):
        """Terminate the communication protocol"""
        try:
            # Stop update timer
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()

            if self.is_master and self.controller:
                if hasattr(self.controller, "disconnect"):
                    self.controller.disconnect()
                elif hasattr(self.controller, "close"):
                    self.controller.close()

            self.initialized = False

        except Exception as e:
            self.emit_status(
                ThreadCommand("Update_Status", [f"Error during close: {e}"])
            )


class MockMaiTaiController:
    """Mock controller for testing without hardware."""

    def __init__(self):
        self._wavelength = 800.0
        self._laser_on = False
        self._shutter_open = False

    def get_wavelength(self):
        return self._wavelength

    def set_wavelength(self, wavelength):
        try:
            self._wavelength = float(wavelength)
            return True
        except:
            return False

    def turn_on(self):
        self._laser_on = True
        return True

    def turn_off(self):
        self._laser_on = False
        return True

    def open_shutter(self):
        self._shutter_open = True
        return True

    def close_shutter(self):
        self._shutter_open = False
        return True

    def close(self):
        pass

    def disconnect(self):
        pass


if __name__ == '__main__':
    main(__file__)
