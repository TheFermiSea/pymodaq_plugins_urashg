#!/usr/bin/env python3
"""
URASHG Preset Loader
Automatically loads the working URASHG preset in PyMoDAQ
"""

import os
import sys

def load_urashg_preset():
    """Load the URASHG working preset"""
    
    preset_path = '/home/maitai/.pymodaq/preset_configs/preset_urashg_working.xml'
    
    if not os.path.exists(preset_path):
        print(f"❌ Preset file not found: {preset_path}")
        return False
    
    try:
        # Set environment for X11 compatibility
        os.environ["QT_X11_NO_MITSHM"] = "1"
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
        os.environ["QT_OPENGL"] = "software"
        
        from qtpy import QtWidgets
        from pymodaq_gui.utils import DockArea
        from pymodaq.dashboard import DashBoard
        
        # Create Qt application
        app = QtWidgets.QApplication(sys.argv)
        
        # Create main window
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle("PyMoDAQ Dashboard - URASHG")
        main_window.resize(1200, 800)
        
        # Create dock area and dashboard
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        dashboard = DashBoard(dock_area)
        
        # Load the preset
        print(f"Loading URASHG preset: {preset_path}")
        dashboard.preset_manager.load_preset(preset_path)
        print("✅ URASHG preset loaded successfully!")
        
        # Show the window
        main_window.show()
        
        print("🚀 PyMoDAQ Dashboard with URASHG plugins is ready!")
        print("All plugins should now be visible and configured.")
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error loading preset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== URASHG PyMoDAQ Preset Loader ===")
    print("Loading PyMoDAQ with pre-configured URASHG plugins")
    print("")
    
    load_urashg_preset()
