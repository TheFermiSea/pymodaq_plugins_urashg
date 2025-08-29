from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal

class MaiTaiUI(QObject):
    """
    User interface for the MaiTai laser plugin.
    
    Provides dedicated buttons for shutter control and status display.
    """
    
    # Signals to connect to plugin methods
    open_shutter_signal = Signal()
    close_shutter_signal = Signal()

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self.parent_widget = parent_widget
        self.setup_ui()

    def setup_ui(self):
        """Create and arrange the UI elements."""
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        
        # Shutter control group
        shutter_group = QtWidgets.QGroupBox("Shutter Control")
        shutter_layout = QtWidgets.QHBoxLayout()
        
        # Shutter status
        self.shutter_status_label = QtWidgets.QLabel("Status: Unknown")
        
        # Shutter buttons
        self.open_button = QtWidgets.QPushButton("Open")
        self.close_button = QtWidgets.QPushButton("Close")
        
        # Add widgets to shutter layout
        shutter_layout.addWidget(self.shutter_status_label)
        shutter_layout.addStretch()
        shutter_layout.addWidget(self.open_button)
        shutter_layout.addWidget(self.close_button)
        
        shutter_group.setLayout(shutter_layout)
        
        # Add group to main layout
        layout.addWidget(shutter_group)
        layout.addStretch()
        
        self.parent_widget.setLayout(layout)
        
        # Connect button signals
        self.open_button.clicked.connect(self.open_shutter_signal.emit)
        self.close_button.clicked.connect(self.close_shutter_signal.emit)

    def update_shutter_status(self, status: str):
        """Update the shutter status label."""
        self.shutter_status_label.setText(f"Status: {status}")
