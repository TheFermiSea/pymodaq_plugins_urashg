#!/usr/bin/env python3
"""
Test script for MaiTai laser plugin custom UI.

This script demonstrates the custom UI controls for the MaiTai laser plugin
including laser on/off, wavelength control, and shutter control.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from qtpy.QtCore import QTimer
import numpy as np

# Import the MaiTai plugin
from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai


class MaiTaiUITest(QMainWindow):
    """Test window for MaiTai custom UI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MaiTai Laser Control - UI Test")
        self.setGeometry(100, 100, 400, 500)

        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Add title
        title = QLabel("MaiTai Laser Control Test")
        title.setStyleSheet("QLabel { font-size: 16pt; font-weight: bold; margin: 10px; }")
        layout.addWidget(title)

        # Initialize MaiTai plugin
        try:
            self.maitai_plugin = DAQ_Move_MaiTai()

            # Initialize plugin attributes
            self.maitai_plugin.ini_attributes()

            # Mock settings for testing
            self.create_mock_settings()

            # Get the custom UI
            custom_ui = self.maitai_plugin.custom_ui()
            if custom_ui:
                layout.addWidget(custom_ui)

                # Set up timer to update display
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self.update_display)
                self.update_timer.start(1000)  # Update every second
            else:
                error_label = QLabel("Failed to create custom UI")
                error_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                layout.addWidget(error_label)

        except Exception as e:
            error_label = QLabel(f"Error initializing plugin: {e}")
            error_label.setStyleSheet("QLabel { color: red; }")
            layout.addWidget(error_label)

    def create_mock_settings(self):
        """Create mock settings for the plugin."""
        # This is a simplified mock - in real PyMoDAQ, settings come from Parameter objects
        class MockSettings:
            def __init__(self):
                self.values = {
                    ("connection_group", "mock_mode"): True,
                    ("status_group", "current_wavelength"): 800.0,
                    ("status_group", "laser_status"): "Ready",
                    ("status_group", "shutter_status"): "Closed",
                    ("wavelength_range", "min_wavelength"): 700.0,
                    ("wavelength_range", "max_wavelength"): 1000.0,
                }

            def child(self, *path):
                return MockParameter(self.values.get(tuple(path), None))

        class MockParameter:
            def __init__(self, value):
                self._value = value

            def value(self):
                return self._value

            def setValue(self, value):
                self._value = value

        self.maitai_plugin.settings = MockSettings()

        # Initialize the plugin
        self.maitai_plugin.ini_stage(None)

    def update_display(self):
        """Update the display periodically."""
        if hasattr(self.maitai_plugin, 'update_display'):
            self.maitai_plugin.update_display()


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)

    # Create and show the test window
    window = MaiTaiUITest()
    window.show()

    print("MaiTai UI Test started")
    print("Features to test:")
    print("- Laser ON/OFF button (red/green)")
    print("- Current wavelength display")
    print("- Target wavelength input (700-1000 nm)")
    print("- Set Wavelength button")
    print("- Shutter OPEN/CLOSED button (red/green)")
    print("\nNote: This is using mock hardware, so all controls are simulated.")

    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
