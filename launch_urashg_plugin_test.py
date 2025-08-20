#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Individual Plugin Test Launcher for μRASHG

This script tests individual plugins with mock mode enabled,
bypassing the complex extension framework for direct plugin testing.

Features:
- Tests individual PyMoDAQ plugins directly
- Full mock mode for hardware simulation
- Direct plugin GUI testing
- Debug logging to files

Usage:
    python launch_urashg_plugin_test.py
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Create logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"urashg_plugin_test_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def test_individual_plugins():
    """Test individual URASHG plugins in mock mode."""

    print("🧪 μRASHG Plugin Individual Testing")
    print("=" * 50)

    try:
        # Import Qt
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import (
            QApplication,
            QLabel,
            QMainWindow,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )

        # Create Qt Application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            app.setStyle("Fusion")

        # Create main test window
        main_window = QMainWindow()
        main_window.setWindowTitle("μRASHG Plugin Testing - Mock Mode")
        main_window.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Add header
        header = QLabel("🧪 URASHG PLUGIN TESTING - MOCK MODE 🧪")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(
            """
            QLabel {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                margin: 10px;
            }
        """
        )
        layout.addWidget(header)

        # Test results area
        results_label = QLabel("Test Results:\n\n")
        results_label.setWordWrap(True)
        results_label.setStyleSheet(
            """
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 4px;
                font-family: monospace;
            }
        """
        )
        layout.addWidget(results_label)

        # Test plugins
        test_results = []

        # Test 1: Elliptec Plugin
        logger.info("Testing Elliptec plugin...")
        try:
            from src.pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import (
                DAQ_Move_Elliptec,
            )

            test_results.append("✅ DAQ_Move_Elliptec: Import successful")

            # Try to create plugin instance with mock settings
            plugin = DAQ_Move_Elliptec(None, None)
            # Set mock mode in parameter tree
            plugin.settings.child("connection_group", "mock_mode").setValue(True)
            plugin.settings.child("connection_group", "mount_addresses").setValue(
                "2,3,8"
            )
            test_results.append("✅ DAQ_Move_Elliptec: Instance created successfully")

        except Exception as e:
            test_results.append(f"❌ DAQ_Move_Elliptec: {str(e)}")
            logger.error(f"Elliptec plugin test failed: {e}")

        # Test 2: MaiTai Plugin
        logger.info("Testing MaiTai plugin...")
        try:
            from src.pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import (
                DAQ_Move_MaiTai,
            )

            test_results.append("✅ DAQ_Move_MaiTai: Import successful")

            # Try to create plugin instance
            plugin = DAQ_Move_MaiTai(None, None)
            plugin.settings.child("connection_group", "mock_mode").setValue(True)
            test_results.append("✅ DAQ_Move_MaiTai: Instance created successfully")

        except Exception as e:
            test_results.append(f"❌ DAQ_Move_MaiTai: {str(e)}")
            logger.error(f"MaiTai plugin test failed: {e}")

        # Test 3: PrimeBSI Camera Plugin
        logger.info("Testing PrimeBSI camera plugin...")
        try:
            from src.pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import (
                DAQ_2DViewer_PrimeBSI,
            )

            test_results.append("✅ DAQ_2DViewer_PrimeBSI: Import successful")

            # Note: Camera plugin might need more complex initialization
            test_results.append(
                "ℹ️  DAQ_2DViewer_PrimeBSI: Requires PyVCAM for full testing"
            )

        except Exception as e:
            test_results.append(f"❌ DAQ_2DViewer_PrimeBSI: {str(e)}")
            logger.error(f"PrimeBSI plugin test failed: {e}")

        # Test 4: Newport Power Meter Plugin
        logger.info("Testing Newport power meter plugin...")
        try:
            from src.pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import (
                DAQ_0DViewer_Newport1830C,
            )

            test_results.append("✅ DAQ_0DViewer_Newport1830C: Import successful")

            plugin = DAQ_0DViewer_Newport1830C(None, None)
            plugin.settings.child("connection_group", "mock_mode").setValue(True)
            test_results.append(
                "✅ DAQ_0DViewer_Newport1830C: Instance created successfully"
            )

        except Exception as e:
            test_results.append(f"❌ DAQ_0DViewer_Newport1830C: {str(e)}")
            logger.error(f"Newport plugin test failed: {e}")

        # Test 5: Hardware Controllers
        logger.info("Testing hardware controllers...")
        try:
            from src.pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import (
                ElliptecController,
            )

            controller = ElliptecController("/dev/ttyUSB1", mock_mode=True)
            test_results.append("✅ ElliptecController: Mock mode working")

            from src.pymodaq_plugins_urashg.hardware.urashg.maitai_control import (
                MaiTaiController,
            )

            # Mock port for testing
            laser = MaiTaiController("/dev/ttyUSB2", mock_mode=True)
            test_results.append("✅ MaiTaiController: Mock mode working")

        except Exception as e:
            test_results.append(f"❌ Hardware controllers: {str(e)}")
            logger.error(f"Hardware controller test failed: {e}")

        # Update results display
        results_text = "Test Results:\\n\\n" + "\\n".join(test_results)
        results_label.setText(results_text)

        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(main_window.close)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """
        )
        layout.addWidget(close_btn)

        main_window.setCentralWidget(central_widget)

        # Show window
        main_window.show()

        # Print summary
        print("\\n" + "=" * 50)
        print("🎉 PLUGIN TESTING COMPLETE")
        print("=" * 50)
        for result in test_results:
            print(result)
        print(f"📋 Full log: {log_file}")
        print("=" * 50)

        # Run application
        return app.exec()

    except Exception as e:
        logger.error(f"Critical testing error: {e}")
        logger.exception("Full traceback:")
        return 1


def main():
    """Main entry point."""
    logger.info("Starting URASHG plugin testing...")
    exit_code = test_individual_plugins()
    logger.info(f"Testing completed with exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
