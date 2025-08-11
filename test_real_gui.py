#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real GUI Test for URASHG Plugin
This actually launches a visible GUI window that stays open
"""

import sys
import logging
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

logger.info("Starting REAL GUI test...")

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                               QHBoxLayout, QWidget, QLabel, QPushButton, 
                               QTextEdit, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class URASHGPluginTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("URASHG Plugin Real Test GUI")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("PyMoDAQ URASHG Plugin Test Interface")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Status display
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(200)
        self.log_display.setReadOnly(True)
        layout.addWidget(QLabel("Plugin Status:"))
        layout.addWidget(self.log_display)
        
        # Test buttons
        button_layout = QHBoxLayout()
        
        self.test_plugins_btn = QPushButton("Test Plugin Discovery")
        self.test_plugins_btn.clicked.connect(self.test_plugin_discovery)
        button_layout.addWidget(self.test_plugins_btn)
        
        self.test_hardware_btn = QPushButton("Test Hardware Controllers")
        self.test_hardware_btn.clicked.connect(self.test_hardware_controllers)
        button_layout.addWidget(self.test_hardware_btn)
        
        self.test_pymodaq_btn = QPushButton("Test PyMoDAQ Integration")
        self.test_pymodaq_btn.clicked.connect(self.test_pymodaq_integration)
        button_layout.addWidget(self.test_pymodaq_btn)
        
        layout.addLayout(button_layout)
        
        # Plugin status
        self.plugin_status = QGroupBox("Plugin Status")
        plugin_layout = QVBoxLayout(self.plugin_status)
        self.plugin_labels = {}
        
        plugins = ["Elliptec", "MaiTai", "ESP300", "PrimeBSI", "Newport1830C"]
        for plugin in plugins:
            label = QLabel(f"{plugin}: Not tested")
            self.plugin_labels[plugin] = label
            plugin_layout.addWidget(label)
            
        layout.addWidget(self.plugin_status)
        
        # Start initial test
        self.log("GUI Loaded - Click buttons to test functionality")
        QTimer.singleShot(1000, self.initial_test)
        
    def log(self, message):
        self.log_display.append(message)
        logger.info(message)
        
    def initial_test(self):
        self.log("Running initial plugin import test...")
        self.test_plugin_discovery()
        
    def test_plugin_discovery(self):
        self.log("Testing plugin discovery...")
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
            self.plugin_labels["Elliptec"].setText("Elliptec: ✅ IMPORTED")
            self.log("✅ Elliptec plugin imported")
        except Exception as e:
            self.plugin_labels["Elliptec"].setText("Elliptec: ❌ FAILED")
            self.log(f"❌ Elliptec: {e}")
            
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
            self.plugin_labels["MaiTai"].setText("MaiTai: ✅ IMPORTED")
            self.log("✅ MaiTai plugin imported")
        except Exception as e:
            self.plugin_labels["MaiTai"].setText("MaiTai: ❌ FAILED")
            self.log(f"❌ MaiTai: {e}")
            
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300
            self.plugin_labels["ESP300"].setText("ESP300: ✅ IMPORTED")
            self.log("✅ ESP300 plugin imported")
        except Exception as e:
            self.plugin_labels["ESP300"].setText("ESP300: ❌ FAILED")
            self.log(f"❌ ESP300: {e}")
            
        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
            self.plugin_labels["PrimeBSI"].setText("PrimeBSI: ✅ IMPORTED")
            self.log("✅ PrimeBSI plugin imported")
        except Exception as e:
            self.plugin_labels["PrimeBSI"].setText("PrimeBSI: ❌ FAILED")
            self.log(f"❌ PrimeBSI: {e}")
            
        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C
            self.plugin_labels["Newport1830C"].setText("Newport1830C: ✅ IMPORTED")
            self.log("✅ Newport1830C plugin imported")
        except Exception as e:
            self.plugin_labels["Newport1830C"].setText("Newport1830C: ❌ FAILED")
            self.log(f"❌ Newport1830C: {e}")
            
    def test_hardware_controllers(self):
        self.log("Testing hardware controllers...")
        try:
            from pymodaq_plugins_urashg.utils.pyrpl_wrapper import PYRPL_AVAILABLE, PYRPL_MOCK
            self.log(f"PyRPL: Available={PYRPL_AVAILABLE}, Mock={PYRPL_MOCK}")
        except Exception as e:
            self.log(f"❌ PyRPL wrapper error: {e}")
            
        try:
            from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller
            controller = ESP300Controller("test_port")
            self.log("✅ ESP300Controller instantiated")
        except Exception as e:
            self.log(f"❌ ESP300Controller error: {e}")
            
    def test_pymodaq_integration(self):
        self.log("Testing PyMoDAQ integration...")
        try:
            import pymodaq
            self.log(f"✅ PyMoDAQ {pymodaq.__version__} available")
            
            # Test extension
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
            self.log("✅ Extension class imported")
            
        except Exception as e:
            self.log(f"❌ PyMoDAQ integration error: {e}")

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create and show the GUI
    gui = URASHGPluginTestGUI()
    gui.show()
    
    logger.info("GUI should now be visible - check your desktop")
    
    # Run the event loop
    return app.exec()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)