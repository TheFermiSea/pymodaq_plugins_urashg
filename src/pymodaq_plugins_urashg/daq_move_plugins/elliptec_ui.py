from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, Slot

class AxisController(QtWidgets.QWidget):
    """A widget for controlling a single rotator axis."""
    move_abs_signal = Signal(int, float)
    move_rel_signal = Signal(int, float)
    home_signal = Signal(int)

    def __init__(self, axis_index: int, axis_name: str, parent=None):
        super().__init__(parent)
        self.axis_index = axis_index
        self.axis_name = axis_name
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.groupbox = QtWidgets.QGroupBox(self.axis_name)
        group_layout = QtWidgets.QGridLayout()
        self.groupbox.setLayout(group_layout)

        self.current_pos_label = QtWidgets.QLabel("Pos: -- °")
        self.target_pos_input = QtWidgets.QDoubleSpinBox()
        self.target_pos_input.setRange(0, 360)
        self.target_pos_input.setSuffix(" °")
        self.set_pos_button = QtWidgets.QPushButton("Set")
        
        self.jog_step_input = QtWidgets.QDoubleSpinBox()
        self.jog_step_input.setValue(1.0)
        self.jog_step_input.setSuffix(" °")
        self.jog_forward_button = QtWidgets.QPushButton("Jog +")
        self.jog_backward_button = QtWidgets.QPushButton("Jog -")
        
        self.home_button = QtWidgets.QPushButton("Home")

        group_layout.addWidget(self.current_pos_label, 0, 0, 1, 3)
        group_layout.addWidget(self.target_pos_input, 1, 0)
        group_layout.addWidget(self.set_pos_button, 1, 1)
        group_layout.addWidget(self.home_button, 1, 2)
        group_layout.addWidget(self.jog_step_input, 2, 0)
        group_layout.addWidget(self.jog_forward_button, 2, 1)
        group_layout.addWidget(self.jog_backward_button, 2, 2)

        layout.addWidget(self.groupbox)

        # Connect signals
        self.set_pos_button.clicked.connect(self._emit_move_abs)
        self.jog_forward_button.clicked.connect(self._emit_jog_forward)
        self.jog_backward_button.clicked.connect(self._emit_jog_backward)
        self.home_button.clicked.connect(lambda: self.home_signal.emit(self.axis_index))

    def _emit_move_abs(self):
        self.move_abs_signal.emit(self.axis_index, self.target_pos_input.value())

    def _emit_jog_forward(self):
        self.move_rel_signal.emit(self.axis_index, self.jog_step_input.value())

    def _emit_jog_backward(self):
        self.move_rel_signal.emit(self.axis_index, -self.jog_step_input.value())
        
    def set_position(self, position: float):
        self.current_pos_label.setText(f"Pos: {position:.2f} °")

class ElliptecUI(QtWidgets.QWidget):
    """Custom multi-axis UI for the Elliptec plugin."""
    status_update_signal = Signal()
    home_all_signal = Signal()
    
    # Forwarded signals from AxisController widgets
    move_abs_signal = Signal(int, float)
    move_rel_signal = Signal(int, float)
    home_signal = Signal(int)

    def __init__(self, axis_names: list, parent=None):
        super().__init__(parent)
        self.axis_names = axis_names
        self.axis_widgets = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        for i, name in enumerate(self.axis_names):
            axis_widget = AxisController(i, name)
            # Forward the signals from the child widget to the main UI signals
            axis_widget.move_abs_signal.connect(self.move_abs_signal)
            axis_widget.move_rel_signal.connect(self.move_rel_signal)
            axis_widget.home_signal.connect(self.home_signal)
            main_layout.addWidget(axis_widget)
            self.axis_widgets.append(axis_widget)
            
        # Global controls
        global_group = QtWidgets.QGroupBox("Global")
        global_layout = QtWidgets.QHBoxLayout()
        self.home_all_button = QtWidgets.QPushButton("Home All")
        global_layout.addWidget(self.home_all_button)
        global_group.setLayout(global_layout)
        main_layout.addWidget(global_group)
        
        main_layout.addStretch()

        self.home_all_button.clicked.connect(self.home_all_signal.emit)

        # Timer for periodic status updates
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(1000)  # Update every second
        self.update_timer.timeout.connect(self.status_update_signal.emit)
        self.update_timer.start()

    @Slot(list)
    def update_positions(self, positions: list):
        """Updates the position display for each axis."""
        for i, pos in enumerate(positions):
            if i < len(self.axis_widgets):
                self.axis_widgets[i].set_position(pos)
