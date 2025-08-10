#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple launcher for the μRASHG Microscopy Extension

This script launches the extension directly without full dashboard initialization.
Simplified approach for PyMoDAQ 5.1.0a0 compatibility.

Usage:
    python launch_urashg_simple.py
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Launch the μRASHG Extension with simplified approach."""
    try:
        # Import Qt components first
        from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
        from PyQt5.QtCore import Qt
        
        logger.info("Starting Simple μRASHG Extension Launcher")
        
        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            logger.info("Created QApplication")
        
        # Import our extension
        from src.pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        logger.info("Successfully imported URASHGMicroscopyExtension")
        
        # Create a minimal dashboard mock
        class MinimalDashboard:
            """Minimal dashboard mock for extension."""
            def __init__(self):
                self.widget = QMainWindow()
                self.widget.setWindowTitle("PyMoDAQ Dashboard - μRASHG Extension")
                self.widget.setGeometry(100, 100, 1200, 800)
        
        # Create mock dashboard
        dashboard = MinimalDashboard()
        logger.info("Created minimal dashboard")
        
        # Create extension
        extension = URASHGMicroscopyExtension(dashboard)
        logger.info("Created μRASHG extension instance")
        
        # Get extension widget
        extension_widget = extension.get_widget()
        if extension_widget:
            # Set up main window with extension
            main_widget = QWidget()
            layout = QVBoxLayout(main_widget)
            layout.addWidget(extension_widget)
            
            dashboard.widget.setCentralWidget(main_widget)
            logger.info("Set up extension widget in main window")
        
        # Show the window
        dashboard.widget.show()
        logger.info("Displayed main window")
        
        # Start the extension
        try:
            extension.start_extension()
            logger.info("Started μRASHG extension")
        except Exception as e:
            logger.warning(f"Extension start_extension() failed: {e}")
            logger.info("Extension may still be functional")
        
        # Run the application
        logger.info("Application launched successfully - close window to exit")
        return app.exec()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure PyMoDAQ and pymodaq-plugins-urashg are installed")
        return 1
        
    except Exception as e:
        logger.error(f"Launch error: {e}")
        logger.exception("Full traceback:")
        return 1

if __name__ == '__main__':
    print("=" * 80)
    print("μRASHG Microscopy Extension - Simple Launcher")
    print("=" * 80)
    print("Simplified approach for PyMoDAQ 5.1.0a0 compatibility")
    print("Bypasses dashboard initialization complexities")
    print("=" * 80)
    print()
    
    exit_code = main()
    sys.exit(exit_code)