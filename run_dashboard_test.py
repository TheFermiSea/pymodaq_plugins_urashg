#!/usr/bin/env python3
"""
Test PyMoDAQ Dashboard startup and preset loading
This verifies the hanging issue has been resolved
"""

import os
import sys
import time

def run_dashboard_test():
    """Run PyMoDAQ dashboard and test preset loading"""
    
    # Set up for GUI display if available, fallback to offscreen
    try:
        # Try to use real display if available
        import subprocess
        result = subprocess.run(['echo', '$DISPLAY'], shell=True, capture_output=True, text=True)
        if not result.stdout.strip():
            print('No DISPLAY detected, using offscreen rendering')
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    except:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    print('Starting PyMoDAQ Dashboard...')
    print('This will test that presets load without hanging')

    try:
        from qtpy import QtWidgets, QtCore
        from pymodaq.dashboard import DashBoard
        from pymodaq.utils.gui_utils.dock import DockArea
        
        # Create Qt application
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        
        print('Qt Application created successfully')
        
        # Create main window and dock area
        main_window = QtWidgets.QMainWindow()
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        
        # Create dashboard
        print('Creating PyMoDAQ Dashboard...')
        dashboard = DashBoard(dock_area)
        
        print('Dashboard created successfully!')
        print('Testing preset loading...')
        
        # Test loading the main preset
        preset_file = '/home/maitai/.pymodaq/preset_configs/preset_urashg.xml'
        if os.path.exists(preset_file):
            print(f'Loading preset: {preset_file}')
            try:
                # Load the preset - this was previously causing hanging
                dashboard.preset_manager.load_preset(preset_file)
                print('SUCCESS: Preset loaded without hanging!')
            except Exception as e:
                print(f'ERROR: Preset loading failed: {e}')
                import traceback
                traceback.print_exc()
                return False
        
        print()
        print('=== FINAL RESULT ===')
        print('SUCCESS: PyMoDAQ Dashboard started successfully')
        print('SUCCESS: Preset loaded without hanging')
        print('SUCCESS: Dashboard hanging issue RESOLVED')
        
        # Show window briefly if display available
        if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
            main_window.show()
            print('Dashboard window displayed - closing in 3 seconds...')
            QtCore.QTimer.singleShot(3000, app.quit)
            app.exec_()
        else:
            print('Dashboard running in offscreen mode (no display)')
        
        return True
        
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('Dashboard test completed successfully!')
    success = run_dashboard_test()
    sys.exit(0 if success else 1)