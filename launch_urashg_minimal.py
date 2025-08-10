#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minimal launcher for the μRASHG Microscopy Extension

This launcher creates a minimal Qt application with a DockArea container
that satisfies CustomApp requirements without triggering PyMoDAQ's broken
initialization in version 5.1.0a0.

Usage:
    python launch_urashg_minimal.py
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Launch the μRASHG Extension with minimal Qt container."""
    try:
        # Import Qt components
        from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
        from PyQt5.QtCore import Qt
        
        logger.info("Starting Minimal μRASHG Extension Launcher")
        
        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            logger.info("Created QApplication")
        
        # Import pyqtgraph DockArea directly (what CustomApp actually needs)
        try:
            from pyqtgraph.dockarea import DockArea
            logger.info("Imported pyqtgraph DockArea")
        except ImportError:
            logger.error("pyqtgraph not available - required for DockArea")
            return 1
        
        # Create main window  
        main_window = QMainWindow()
        main_window.setWindowTitle("μRASHG Microscopy Extension")
        main_window.setGeometry(100, 100, 1400, 900)
        
        # Define HybridDashboard class first
        from PyQt5.QtCore import pyqtSignal
        class HybridDashboard(QWidget):
            """Hybrid dashboard that provides PyMoDAQ-compatible parent interface."""
            # PyMoDAQ plugin parent signals (class level)
            status_sig = pyqtSignal(object)
            
            def __init__(self):
                super().__init__()
                # Create layout for Qt compatibility
                from PyQt5.QtWidgets import QVBoxLayout
                self.main_layout = QVBoxLayout()
                self.setLayout(self.main_layout)
                
                # Create embedded DockArea for extension
                self.dockarea = DockArea()
                self.main_layout.addWidget(self.dockarea)
                
                # Required dashboard attributes - modules_manager will be set after creation
                self.modules_manager = None  # Will be set after initialization  
                self.mainwindow = main_window
                self.docks = {}  # Dictionary to store individual docks
                
                # Required PyMoDAQ plugin parent attributes
                self.title = "μRASHG Dashboard"
                
            def __getattr__(self, name):
                # First try to get from dockarea for CustomApp compatibility
                if hasattr(self.dockarea, name):
                    return getattr(self.dockarea, name)
                # Fallback for any missing attributes
                logger.warning(f"Dashboard accessed missing attribute: {name}")
                return None
        
        # Create a real modules manager with PyMoDAQ plugins
        class RealModulesManager:
            """Real modules manager that instantiates PyMoDAQ plugins for hardware connectivity."""
            def __init__(self, dashboard):
                self.dashboard = dashboard
                self.move_modules = {}
                self.viewer_modules = {}
                self._initialize_real_plugins()
                
            def _initialize_real_plugins(self):
                """Initialize real PyMoDAQ plugin instances for hardware connectivity."""
                try:
                    # Import PyMoDAQ plugin classes
                    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
                    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai
                    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C
                    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
                    from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import DAQ_Move_PyRPL_PID
                    
                    # Create plugin instances directly (bypassing container complexity)
                    try:
                        elliptec_plugin = DAQ_Move_Elliptec(parent=self.dashboard)
                        self.move_modules['Elliptec'] = elliptec_plugin
                        logger.info("Created REAL Elliptec plugin instance directly")
                    except Exception as e:
                        logger.error(f"Could not create Elliptec plugin: {e}")
                        
                    try:
                        maitai_plugin = DAQ_Move_MaiTai(parent=self.dashboard)
                        self.move_modules['MaiTai'] = maitai_plugin
                        logger.info("Created REAL MaiTai plugin instance directly")
                    except Exception as e:
                        logger.error(f"Could not create MaiTai plugin: {e}")
                        
                    try:
                        # PyRPL plugin often has initialization issues - allow failure
                        pyrpl_plugin = DAQ_Move_PyRPL_PID(parent=self.dashboard)
                        self.move_modules['PyRPL_PID'] = pyrpl_plugin
                        logger.info("Created REAL PyRPL_PID plugin instance directly")
                    except Exception as e:
                        logger.warning(f"PyRPL_PID plugin failed to initialize (will run without PID control): {e}")
                    
                    # Create viewer plugin instances directly
                    try:
                        newport_plugin = DAQ_0DViewer_Newport1830C(parent=self.dashboard)
                        self.viewer_modules['Newport1830C'] = newport_plugin
                        logger.info("Created REAL Newport1830C plugin instance directly")
                    except Exception as e:
                        logger.error(f"Could not create Newport1830C plugin: {e}")
                        
                    try:
                        camera_plugin = DAQ_2DViewer_PrimeBSI(parent=self.dashboard)
                        self.viewer_modules['PrimeBSI'] = camera_plugin
                        logger.info("Created REAL PrimeBSI plugin instance directly")
                    except Exception as e:
                        logger.error(f"Could not create PrimeBSI plugin: {e}")
                        
                    logger.info(f"RealModulesManager initialized with {len(self.move_modules)} move modules and {len(self.viewer_modules)} viewer modules")
                    
                except ImportError as e:
                    logger.error(f"Could not import PyMoDAQ plugin classes: {e}")
                except Exception as e:
                    logger.error(f"Error initializing RealModulesManager: {e}")
        
        # Create hybrid dashboard and set as central widget
        hybrid_dashboard = HybridDashboard()
        main_window.setCentralWidget(hybrid_dashboard)
        
        # Now create the modules manager with the dashboard reference  
        hybrid_dashboard.modules_manager = RealModulesManager(hybrid_dashboard)
        
        # dockarea and docks already initialized in HybridDashboard __init__
        
        logger.info("Created main window with hybrid dashboard (DockArea + dashboard interfaces)")
        
        # Import our extension
        from src.pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        logger.info("Successfully imported URASHGMicroscopyExtension")
        
        # Create extension with hybrid dashboard (has modules_manager for device discovery)
        # The extension will use hybrid_dashboard.dockarea for its UI
        extension = URASHGMicroscopyExtension(hybrid_dashboard)
        logger.info("Created μRASHG extension instance")
        
        # Show the window
        main_window.show()
        logger.info("Displayed main window")
        
        # Try to start the extension
        try:
            extension.start_extension()
            logger.info("Started μRASHG extension")
        except Exception as e:
            logger.warning(f"Extension start_extension() failed: {e}")
            logger.info("Extension GUI should still be accessible")
        
        # Run the application
        logger.info("Application launched - close window to exit")
        return app.exec_()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Missing dependencies - ensure PyMoDAQ and pyqtgraph are installed")
        return 1
        
    except Exception as e:
        logger.error(f"Launch error: {e}")
        logger.exception("Full traceback:")
        return 1

if __name__ == '__main__':
    print("=" * 80)
    print("μRASHG Microscopy Extension - Minimal Launcher")
    print("=" * 80)
    print("Bypasses PyMoDAQ 5.1.0a0 initialization issues")
    print("Creates minimal Qt container with DockArea support")
    print("=" * 80)
    print()
    
    exit_code = main()
    sys.exit(exit_code)