#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMoDAQ-compliant launcher for URASHG Microscopy Extension

This launcher properly integrates with PyMoDAQ's extension framework
and follows PyMoDAQ 5.x standards for extension loading and initialization.
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main launcher function following PyMoDAQ extension patterns.

    This function:
    1. Creates PyMoDAQ application
    2. Loads dashboard with URASHG preset
    3. Initializes extension through PyMoDAQ framework
    """
    try:
        from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset
        from pymodaq.utils.gui_utils.utils import mkQApp
        from pymodaq.utils.messenger import messagebox
        from pymodaq_utils.config import ConfigError

        # Import extension metadata
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            CLASS_NAME,
            EXTENSION_NAME,
        )
        from pymodaq_plugins_urashg.utils.config import Config as PluginConfig

        logger.info(f"Starting {EXTENSION_NAME} launcher...")

        # Create PyMoDAQ application
        app = mkQApp(EXTENSION_NAME)

        try:
            # Initialize plugin configuration
            plugin_config = PluginConfig()

            # Get preset configuration
            preset_file_name = plugin_config.get_preset_config().get(
                f"preset_for_{CLASS_NAME.lower()}", "urashg_microscopy_system"
            )

            logger.info(f"Loading dashboard with preset: {preset_file_name}")

            # Load dashboard with preset - this is the PyMoDAQ standard way
            load_dashboard_with_preset(preset_file_name, EXTENSION_NAME)

            logger.info(f"Dashboard loaded successfully with {EXTENSION_NAME}")

            # Start application event loop
            app.exec()

        except ConfigError as e:
            error_msg = (
                f"Configuration error for {EXTENSION_NAME}:\n\n"
                f'No entry with name "preset_for_{CLASS_NAME.lower()}" has been configured '
                f"in the plugin config file.\n\n"
                f"The config entry should be:\n"
                f"[presets]\n"
                f'preset_for_{CLASS_NAME.lower()} = "urashg_microscopy_system"\n\n'
                f"Please check your plugin configuration or create the preset file."
            )

            logger.error(f"Configuration error: {e}")
            messagebox(error_msg)

        except Exception as e:
            error_msg = f"Error loading {EXTENSION_NAME}: {str(e)}"
            logger.error(error_msg)
            messagebox(f"Failed to load extension:\n\n{error_msg}")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"Error: Cannot import required PyMoDAQ modules: {e}")
        print("Please ensure PyMoDAQ 5.x is properly installed.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error occurred: {e}")
        sys.exit(1)


def launch_standalone():
    """
    Launch extension in standalone mode for development/testing.

    This creates a minimal dashboard environment for extension testing
    without requiring full PyMoDAQ preset configuration.
    """
    try:
        from pymodaq.dashboard import DashBoard
        from pymodaq.utils.gui_utils.utils import mkQApp
        from pyqtgraph.dockarea import DockArea
        from qtpy.QtWidgets import QMainWindow

        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
            EXTENSION_NAME,
            URASHGMicroscopyExtension,
        )

        logger.info(f"Starting {EXTENSION_NAME} in standalone mode...")

        # Create application
        app = mkQApp(f"{EXTENSION_NAME} - Standalone")

        # Create main window and dashboard
        main_window = QMainWindow()
        main_window.setWindowTitle(f"{EXTENSION_NAME} - Development Mode")
        main_window.setGeometry(100, 100, 1400, 900)

        # Create dock area for extension
        dockarea = DockArea()
        main_window.setCentralWidget(dockarea)

        # Create minimal dashboard for extension
        dashboard = DashBoard(dockarea)

        # Initialize extension directly
        URASHGMicroscopyExtension(dockarea, dashboard)

        # Show main window
        main_window.show()

        logger.info("Extension launched in standalone mode successfully")

        # Start application
        app.exec()

    except Exception as e:
        logger.error(f"Error in standalone mode: {e}")
        print(f"Error launching standalone mode: {e}")
        sys.exit(1)


def check_dependencies():
    """Check if all required dependencies are available."""
    required_modules = [
        "pymodaq",
        "pymodaq_gui",
        "pymodaq_data",
        "pymodaq_utils",
        "numpy",
        "pyqtgraph",
        "qtpy",
    ]

    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print("Missing required dependencies:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nPlease install missing dependencies before running the extension.")
        return False

    return True


def print_help():
    """Print help information."""
    help_text = f"""
PyMoDAQ URASHG Extension Launcher

Usage:
    python {Path(__file__).name} [OPTIONS]

Options:
    --standalone    Launch in standalone development mode
    --check-deps    Check required dependencies
    --help, -h      Show this help message

Examples:
    python {Path(__file__).name}              # Normal launch with PyMoDAQ
    python {Path(__file__).name} --standalone # Development mode
    python {Path(__file__).name} --check-deps # Check dependencies

For more information, see the documentation at:
https://github.com/TheFermiSea/pymodaq_plugins_urashg
"""
    print(help_text)


if __name__ == "__main__":
    # Parse command line arguments
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_help()
        sys.exit(0)

    if "--check-deps" in args:
        if check_dependencies():
            print("All required dependencies are available.")
            sys.exit(0)
        else:
            sys.exit(1)

    if "--standalone" in args:
        if not check_dependencies():
            sys.exit(1)
        launch_standalone()
    else:
        if not check_dependencies():
            sys.exit(1)
        main()
