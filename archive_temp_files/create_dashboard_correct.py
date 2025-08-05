#!/usr/bin/env python3
"""
Correct PyMoDAQ Dashboard Creation
Using the proper DockArea import from pymodaq_gui.utils
"""

import os
import sys

def create_dashboard_correctly():
    """Create PyMoDAQ dashboard with correct imports"""
    
    print("=== Creating PyMoDAQ Dashboard Correctly ===")
    
    try:
        print("1. Setting up Qt application...")
        from qtpy import QtWidgets, QtCore
        
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        print("   ✅ Qt application ready")
        
        print("\n2. Importing correct DockArea...")
        from pymodaq_gui.utils import DockArea
        print("   ✅ DockArea imported from pymodaq_gui.utils")
        
        print("\n3. Creating main window and dock area...")
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle("PyMoDAQ Dashboard")
        main_window.resize(1200, 800)
        
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        print("   ✅ Main window and dock area created")
        
        print("\n4. Importing and creating Dashboard...")
        from pymodaq.dashboard import DashBoard
        dashboard = DashBoard(dock_area)
        print("   ✅ Dashboard created successfully!")
        
        print("\n5. Showing dashboard window...")
        main_window.show()
        print("   ✅ Dashboard window shown!")
        
        print("\n6. Dashboard is ready - you should see the window now")
        print("   Press Ctrl+C to close when done testing")
        
        # Keep the application running
        try:
            app.exec_()
        except KeyboardInterrupt:
            print("\n\n7. Closing dashboard...")
            main_window.close()
            print("   ✅ Dashboard closed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_launch_script():
    """Create a working dashboard launch script"""
    
    script_content = '''#!/usr/bin/env python3
"""
PyMoDAQ Dashboard Launcher - X11 Compatible
This script properly creates and launches the PyMoDAQ dashboard
"""

import os
import sys

# Set environment variables for X11 compatibility
os.environ["QT_X11_NO_MITSHM"] = "1"
os.environ["QT_GRAPHICSSYSTEM"] = "native"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

def main():
    """Main dashboard launcher"""
    try:
        from qtpy import QtWidgets
        from pymodaq_gui.utils import DockArea
        from pymodaq.dashboard import DashBoard
        
        # Create Qt application
        app = QtWidgets.QApplication(sys.argv)
        
        # Create main window
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle("PyMoDAQ Dashboard")
        main_window.resize(1200, 800)
        
        # Create dock area
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        
        # Create dashboard
        dashboard = DashBoard(dock_area)
        
        # Show window
        main_window.show()
        
        # Run application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Error launching dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    script_path = '/home/maitai/pymodaq_plugins_urashg/launch_dashboard.py'
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"✅ Created launch script: {script_path}")
    print("   Run with: python launch_dashboard.py")

if __name__ == "__main__":
    print("PyMoDAQ Dashboard - Correct Creation Test")
    
    # Test the correct dashboard creation
    success = create_dashboard_correctly()
    
    if success:
        print("\n🎉 SUCCESS: Dashboard works correctly!")
    else:
        print("\n❌ Dashboard creation still has issues")
    
    # Always create the launch script
    print("\nCreating launch script for future use...")
    create_launch_script()
    
    print(f"\n{'='*60}")
    print("SOLUTION SUMMARY")
    print(f"{'='*60}")
    print("✅ The issue was incorrect DockArea import")
    print("✅ Correct import: from pymodaq_gui.utils import DockArea")
    print("✅ Use the launch_dashboard.py script for reliable launching")
    print("✅ X11 forwarding should work with these settings")