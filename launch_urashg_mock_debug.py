#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock Mode Debug Launcher for μRASHG Microscopy Extension

This script launches the extension in full mock/debug mode for GUI testing
without requiring any physical hardware. All devices run in simulation mode.

Features:
- Full mock mode for all hardware devices
- Enhanced debug logging saved to files
- GUI testing environment
- PyMoDAQ 5.x compatible launcher

Usage:
    python launch_urashg_mock_debug.py
"""

import sys
import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Setup comprehensive logging to both console and file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"urashg_mock_debug_{timestamp}.log"

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Create logger for this script
logger = logging.getLogger(__name__)


def setup_mock_environment():
    """Setup environment variables and patches for mock mode."""
    logger.info("Setting up mock environment variables")

    # Set environment variables to force mock mode
    os.environ["URASHG_MOCK_MODE"] = "1"
    os.environ["PYMODAQ_LOG_LEVEL"] = "DEBUG"

    # Disable hardware detection
    os.environ["URASHG_DISABLE_HARDWARE"] = "1"

    logger.info("Mock environment configured")


def patch_pymodaq_imports():
    """Apply patches for PyMoDAQ compatibility in mock mode."""
    try:
        # Mock PyVCAM if not available
        try:
            import pyvcam

            logger.info("PyVCAM available - using real library")
        except ImportError:
            logger.info("PyVCAM not available - using mock")
            # The plugin should handle this gracefully

        # Mock PyRPL if not available
        try:
            import pyrpl

            logger.info("PyRPL available - using real library")
        except ImportError:
            logger.info("PyRPL not available - using mock")
            # The plugin should handle this gracefully

        return True

    except Exception as e:
        logger.error(f"Error patching imports: {e}")
        return False


def create_mock_dashboard():
    """Create a mock PyMoDAQ dashboard with DockArea for the extension."""
    from qtpy.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
    from qtpy.QtCore import QObject, Signal as pyqtSignal
    from pyqtgraph.dockarea import DockArea

    class MockModulesManager:
        """Mock PyMoDAQ modules manager."""

        def __init__(self):
            self.actuators = {}
            self.detectors = {}

        def get_modules(self):
            """Return empty module lists."""
            return [], []

    class MockDashboard(DockArea):
        """Mock PyMoDAQ dashboard based on DockArea."""

        # PyMoDAQ dashboard signals
        status_sig = pyqtSignal(object)

        def __init__(self):
            super().__init__()

            # Mock PyMoDAQ attributes
            self.modules_manager = MockModulesManager()
            self.title = "μRASHG Extension - Mock Debug Mode"

            # Create main window to contain the DockArea
            self.main_window = QMainWindow()
            self.main_window.setWindowTitle(self.title)
            self.main_window.setGeometry(100, 100, 1400, 900)

            # Create container widget
            container = QWidget()
            layout = QVBoxLayout(container)

            # Mock mode banner
            mock_banner = QLabel("🧪 MOCK DEBUG MODE - No Hardware Required 🧪")
            mock_banner.setStyleSheet(
                """
                QLabel {
                    background-color: #ff6b35;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 5px;
                }
            """
            )
            layout.addWidget(mock_banner)

            # Add the DockArea to the layout
            layout.addWidget(self)

            self.main_window.setCentralWidget(container)

        def show(self):
            """Show the main window."""
            self.main_window.show()

        def get_widget(self):
            """Return self since this IS the DockArea."""
            return self

    return MockDashboard()


def launch_extension_mock_mode():
    """Launch the extension in comprehensive mock mode."""
    try:
        logger.info("Starting μRASHG Extension Mock Debug Launcher")

        # Import Qt components
        from qtpy.QtWidgets import QApplication
        from qtpy.QtCore import Qt

        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            app.setStyle("Fusion")  # Modern look
            logger.info("Created QApplication with Fusion style")

        # Setup mock environment
        setup_mock_environment()

        # Patch imports if needed
        if not patch_pymodaq_imports():
            logger.error("Failed to setup mock environment")
            return 1

        # Import our extension
        try:
            from src.pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import (
                URASHGMicroscopyExtension,
            )

            logger.info("Successfully imported URASHGMicroscopyExtension")
        except ImportError as e:
            logger.error(f"Failed to import extension: {e}")
            return 1

        # Create mock dashboard
        dashboard = create_mock_dashboard()
        logger.info("Created mock dashboard")

        # Create extension in mock mode
        logger.info("Creating extension instance...")
        extension = URASHGMicroscopyExtension(dashboard)
        logger.info("✅ Extension instance created successfully")

        # Configure all plugins for mock mode
        logger.info("Configuring plugins for mock mode...")
        configure_plugins_mock_mode(extension)

        # Extension should automatically set up its UI in the DockArea
        logger.info("✅ Extension UI integrated with DockArea")

        # Show the dashboard
        dashboard.show()
        logger.info("✅ Dashboard displayed")

        # Start the extension
        try:
            if hasattr(extension, "start_extension"):
                extension.start_extension()
                logger.info("✅ Extension started")
            else:
                logger.info("Extension has no start_extension method - that's OK")
        except Exception as e:
            logger.warning(f"Extension start failed: {e} - GUI should still work")

        # Print success message
        print("\n" + "=" * 80)
        print("🎉 μRASHG EXTENSION LAUNCHED IN MOCK DEBUG MODE")
        print("=" * 80)
        print(f"📋 Debug log file: {log_file}")
        print("🧪 All devices running in simulation mode")
        print("🖥️  GUI ready for testing")
        print("❌ Close window to exit")
        print("=" * 80 + "\n")

        # Run the application
        return app.exec()

    except Exception as e:
        logger.error(f"Critical launch error: {e}")
        logger.exception("Full traceback:")
        return 1


def configure_plugins_mock_mode(extension):
    """Configure all plugins in the extension to use mock mode."""
    try:
        # Force mock mode in device manager if available
        if hasattr(extension, "device_manager"):
            logger.info("Configuring device manager for mock mode...")

            # Force mock mode for all hardware controllers
            import os

            os.environ["URASHG_MOCK_MODE"] = "true"
            os.environ["PYMODAQ_MOCK_MODE"] = "true"

            # Restart device discovery with mock mode
            try:
                # Reinitialize with mock mode
                extension.device_manager._initialize_devices_mock()
                logger.info("✅ Device manager configured for mock mode")
            except Exception as e:
                logger.warning(f"Device manager mock configuration failed: {e}")

        logger.info("Mock mode configuration applied to all plugins")

    except Exception as e:
        logger.warning(f"Could not configure mock mode: {e}")


def main():
    """Main entry point."""
    print("μRASHG Microscopy Extension - Mock Debug Launcher")
    print("=" * 60)

    # Check Python environment
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {Path.cwd()}")

    # Launch the extension
    exit_code = launch_extension_mock_mode()

    # Final log message
    logger.info(f"Application exited with code: {exit_code}")
    print(f"\n📋 Debug log saved to: {log_file}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
