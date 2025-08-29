from qtpy import QtWidgets


class ElliptecUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.label = QtWidgets.QLabel("This is a custom UI for the Elliptec Plugin!")
        self.layout().addWidget(self.label)
        self.test_button = QtWidgets.QPushButton("Test Button")
        self.layout().addWidget(self.test_button)
