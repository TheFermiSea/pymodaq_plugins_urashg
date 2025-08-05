#!/usr/bin/env python3
"""
WORKING PyMoDAQ Dashboard for X11 Forwarding
This version fixes the X11/OpenGL issues and works over SSH
"""

import os
import sys

def setup_x11_environment():
    """Set up environment variables for X11 compatibility"""
    print("Setting up X11-compatible environment...")
    
    # Disable problematic Qt features for X11 forwarding
    os.environ["QT_X11_NO_MITSHM"] = "1"
    os.environ["QT_GRAPHICSSYSTEM"] = "native" 
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    
    # Force software rendering to avoid OpenGL issues
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_OPENGL"] = "software"
    
    print("✅ Environment configured for X11 forwarding")

def launch_dashboard():
    """Launch PyMoDAQ dashboard with X11 compatibility"""
    
    setup_x11_environment()
    
    try:
        print("Importing PyMoDAQ components...")
        from qtpy import QtWidgets
        from pymodaq_gui.utils import DockArea
        from pymodaq.dashboard import DashBoard
        
        print("Creating Qt application...")
        app = QtWidgets.QApplication(sys.argv)
        
        print("Creating main window...")
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle("PyMoDAQ Dashboard - URASHG")
        main_window.resize(1200, 800)
        
        print("Creating dock area...")
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        
        print("Creating PyMoDAQ dashboard...")
        dashboard = DashBoard(dock_area)
        
        print("Showing dashboard window...")
        main_window.show()
        
        print("🚀 PyMoDAQ Dashboard launched successfully!")
        print("The dashboard should now be visible in your X11 session.")
        print("Press Ctrl+C in the terminal to close the dashboard.")
        
        # Run the application
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard closed by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("="*60)
    print("PyMoDAQ Dashboard - X11 Forwarding Compatible")
    print("="*60)
    print("This version works with SSH X11 forwarding and XQuartz")
    print()
    
    launch_dashboard()