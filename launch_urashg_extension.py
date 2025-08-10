#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone launcher for the μRASHG Microscopy Extension

This script provides a workaround for PyMoDAQ 5.1.0a0's broken extension discovery
mechanism, allowing direct launch of the comprehensive μRASHG extension.

Usage:
    python launch_urashg_extension.py

Features:
- Bypasses PyMoDAQ's extension discovery bug
- Provides full extension functionality
- Compatible with PyMoDAQ 5.x framework
- Auto-detects correct Python interpreter
"""

import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_pymodaq_python():
    """Find Python interpreter with PyMoDAQ installed."""
    # Try common Python locations
    python_candidates = [
        "/home/maitai/miniforge3/bin/python",
        "/home/maitai/miniconda3/bin/python",
        "/home/maitai/anaconda3/bin/python",
        sys.executable,
        "python3",
        "python"
    ]

    for python_path in python_candidates:
        try:
            result = subprocess.run([python_path, "-c", "import pymodaq; print('OK')"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Found PyMoDAQ in Python: {python_path}")
                return python_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return None

def relaunch_with_correct_python():
    """Relaunch script with correct Python interpreter."""
    correct_python = find_pymodaq_python()
    if not correct_python:
        logger.error("Could not find Python with PyMoDAQ installed")
        logger.error("Please install PyMoDAQ or check your Python environment")
        return False

    if correct_python != sys.executable:
        logger.info(f"Relaunching with correct Python: {correct_python}")
        # Relaunch this script with the correct Python
        result = subprocess.run([correct_python, __file__, "--direct"])
        return result.returncode == 0

    return True

def main():
    """Launch the μRASHG Microscopy Extension directly."""
    # Check if we need to relaunch with correct Python
    if "--direct" not in sys.argv:
        try:
            import pymodaq
            logger.info("PyMoDAQ found in current environment")
        except ImportError:
            logger.warning("PyMoDAQ not found in current Python environment")
            logger.info("Attempting to find correct Python interpreter...")
            if relaunch_with_correct_python():
                return 0
            else:
                return 1

    try:
        # Import PyMoDAQ components with correct paths
        from pymodaq.dashboard import DashBoard, DockArea
        from PySide6.QtWidgets import QApplication  # Use PySide6 (available in environment)

        logger.info("Starting μRASHG Microscopy Extension Launcher")

        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            logger.info("Created new QApplication")

        # Import our extension
        from src.pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        logger.info("Successfully imported URASHGMicroscopyExtension")

        # Create a minimal dock area for the dashboard
        dock_area = DockArea()
        logger.info("Created DockArea")

        # Create dashboard with the dock area
        dashboard = DashBoard(dock_area)
        logger.info("Created PyMoDAQ Dashboard")

        # Create and launch our extension
        extension = URASHGMicroscopyExtension(dashboard)
        logger.info("Created μRASHG extension instance")

        # Show the dashboard
        dashboard.show()
        logger.info("Displayed dashboard")

        # Start the extension
        extension.start_extension()
        logger.info("Started μRASHG extension")

        # Show main window
        if hasattr(extension, 'main_widget') and extension.main_widget:
            extension.main_widget.show()
            logger.info("Displayed extension main widget")

        # Run the application
        logger.info("Launching application - press Ctrl+C to exit")
        return app.exec()

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure PyMoDAQ and pymodaq-plugins-urashg are installed:")
        logger.error("  pip install -e .")
        return 1

    except Exception as e:
        logger.error(f"Launch error: {e}")
        logger.exception("Full traceback:")
        return 1

if __name__ == '__main__':
    print("=" * 80)
    print("μRASHG Microscopy Extension - Standalone Launcher")
    print("=" * 80)
    print("This launcher bypasses PyMoDAQ's extension discovery bug")
    print("and launches the comprehensive μRASHG extension directly.")
    print("=" * 80)
    print()

    exit_code = main()
    sys.exit(exit_code)
