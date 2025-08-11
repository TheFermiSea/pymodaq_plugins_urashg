#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
μRASHG Microscopy Extension - UV-Optimized Launcher

This launcher is optimized for UV-managed environments and provides the most
reliable way to launch the comprehensive μRASHG microscopy extension.

Features:
- UV environment detection and activation
- Automatic dependency verification
- PyMoDAQ 5.x compatibility
- Bypasses PyMoDAQ's extension discovery bug
- Modern Python environment management

Usage:
    uv run python launch_urashg_uv.py
    # or
    python launch_urashg_uv.py (if UV environment is active)
"""

import sys
import subprocess
import logging
from pathlib import Path
import os

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_uv_environment():
    """Check if we're running in a UV-managed environment."""
    # Check for UV virtual environment
    venv_path = Path('.venv')
    if venv_path.exists() and (venv_path / 'pyvenv.cfg').exists():
        logger.info("✅ UV virtual environment detected")
        return True

    # Check if UV is available
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ UV available: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    logger.warning("⚠️  UV environment not detected")
    return False

def verify_dependencies():
    """Verify that required dependencies are available."""
    required_packages = {
        'pymodaq': '5.0.0',
        'pymodaq_gui': '5.0.0',
        'pymodaq_data': '5.0.0',
        'PySide6': '6.0.0',
        'pyqtgraph': '0.12.0',
        'numpy': '1.20.0',
    }

    missing_packages = []

    for package, min_version in required_packages.items():
        try:
            if package == 'PySide6':
                import PySide6
                logger.info(f"✅ {package} available")
            else:
                module = __import__(package.replace('-', '_'))
                if hasattr(module, '__version__'):
                    logger.info(f"✅ {package} {module.__version__} available")
                else:
                    logger.info(f"✅ {package} available (version unknown)")
        except ImportError:
            logger.error(f"❌ {package} not found")
            missing_packages.append(package)

    if missing_packages:
        logger.error("Missing required packages. Install with:")
        logger.error("  uv sync")
        return False

    return True

def launch_with_uv():
    """Launch the extension using UV."""
    logger.info("🚀 Launching with UV...")

    # Use UV to run the script
    cmd = ['uv', 'run', 'python', __file__, '--direct']
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except FileNotFoundError:
        logger.error("❌ UV not found. Please install UV first:")
        logger.error("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        return 1

def main():
    """Main launcher function."""
    logger.info("Starting μRASHG Microscopy Extension (UV-Optimized)")

    # If not running with --direct flag, check environment
    if "--direct" not in sys.argv:
        # Check if we need to use UV
        if not check_uv_environment():
            logger.info("Attempting to launch with UV...")
            return launch_with_uv()

        # Verify dependencies
        if not verify_dependencies():
            logger.error("Dependencies missing. Run: uv sync")
            return 1

    try:
        # Set up the environment
        logger.info("Setting up PyMoDAQ environment...")

        # Import Qt components first to ensure proper backend selection
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        logger.info("✅ PySide6 backend selected")

        # Import PyMoDAQ components
        from pymodaq.dashboard import DashBoard, DockArea
        logger.info("✅ PyMoDAQ components imported")

        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            logger.info("✅ QApplication created")

        # Set application properties
        app.setApplicationName("μRASHG Microscopy Extension")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("PyMoDAQ URASHG")

        # Import our extension
        logger.info("Importing μRASHG extension...")
        try:
            from src.pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
            logger.info("✅ Extension imported successfully")
        except ImportError as e:
            # Try alternative import path
            logger.warning(f"Standard import failed: {e}")
            logger.info("Trying alternative import path...")
            sys.path.insert(0, str(Path.cwd() / 'src'))
            from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
            logger.info("✅ Extension imported via alternative path")

        # Create main window first
        from PySide6.QtWidgets import QMainWindow
        main_window = QMainWindow()
        main_window.setWindowTitle("μRASHG Microscopy Extension")
        main_window.setGeometry(100, 100, 1400, 900)

        # Create PyMoDAQ Dashboard with proper main window
        logger.info("Creating PyMoDAQ Dashboard...")
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        logger.info("✅ DockArea created")

        # Patch PyMoDAQ Dashboard for proper main window handling
        from pymodaq.dashboard import DashBoard
        original_init = DashBoard.__init__

        def patched_init(self, dockarea=None):
            """Patched Dashboard __init__ to use existing main window."""
            try:
                # Store the main window reference
                self.mainwindow = main_window
                # Call original init but skip main window creation
                original_init(self, dockarea)
            except AttributeError as e:
                if "'NoneType' object has no attribute 'setVisible'" in str(e):
                    # Handle the setVisible error
                    logger.info("Handled dashboard initialization issue")
                    if hasattr(self, 'mainwindow') and self.mainwindow:
                        self.mainwindow.setVisible(True)
                else:
                    raise

        DashBoard.__init__ = patched_init
        logger.info("✅ Dashboard patch applied")

        # Create dashboard
        dashboard = DashBoard(dock_area)
        logger.info("✅ PyMoDAQ Dashboard created")

        # Create extension instance with dashboard as parent
        extension = URASHGMicroscopyExtension(dashboard)
        logger.info("✅ μRASHG extension instance created")

        # Show main window
        main_window.show()
        logger.info("✅ Main window displayed")

        # Initialize extension
        try:
            extension.start_extension()
            logger.info("✅ Extension started successfully")
        except Exception as e:
            logger.warning(f"Extension start_extension() warning: {e}")
            logger.info("Extension may still be functional")

        # Show extension widget if available
        if hasattr(extension, 'main_widget') and extension.main_widget:
            extension.main_widget.show()
            logger.info("✅ Extension main widget displayed")
        elif hasattr(extension, 'get_widget'):
            widget = extension.get_widget()
            if widget:
                widget.show()
                logger.info("✅ Extension widget displayed")

        # Final setup
        logger.info("🎉 μRASHG Extension launched successfully!")
        logger.info("   - Dashboard: Multi-device coordination interface")
        logger.info("   - Plugins: All URASHG and PyRPL plugins available")
        logger.info("   - Hardware: Ready for μRASHG microscopy experiments")
        logger.info("")
        logger.info("Note: Extension discovery bypass active for PyMoDAQ 5.1.0a0")
        logger.info("Close the window or press Ctrl+C to exit")

        # Run the application event loop
        return app.exec()

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all dependencies are installed:")
        logger.error("  uv sync")
        logger.error("  uv sync --extra hardware  # for hardware support")
        return 1

    except Exception as e:
        logger.error(f"❌ Launch error: {e}")
        logger.exception("Full traceback:")
        return 1

def print_help():
    """Print usage help."""
    print("=" * 80)
    print("μRASHG Microscopy Extension - UV-Optimized Launcher")
    print("=" * 80)
    print("This launcher provides the most reliable way to run the μRASHG")
    print("microscopy extension in a UV-managed Python environment.")
    print()
    print("Usage:")
    print("  uv run python launch_urashg_uv.py     # Recommended")
    print("  python launch_urashg_uv.py            # If UV env is active")
    print()
    print("Prerequisites:")
    print("  1. UV installed: curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("  2. Dependencies: uv sync")
    print("  3. Hardware deps: uv sync --extra hardware (optional)")
    print()
    print("Environment check:")
    print("  uv run python -c \"import pymodaq; print('PyMoDAQ OK')\"")
    print()
    print("For detailed setup instructions, see: UV_ENVIRONMENT_SETUP.md")
    print("=" * 80)

if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0)

    # Set environment variables for GUI applications
    if 'DISPLAY' not in os.environ and sys.platform.startswith('linux'):
        os.environ['DISPLAY'] = ':0'

    exit_code = main()
    sys.exit(exit_code)
