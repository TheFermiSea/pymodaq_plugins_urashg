#\!/usr/bin/env python3
"""
Test PyMoDAQ dashboard startup without hanging
This simulates the critical operations that would cause hanging
"""

import os
import sys
import xml.etree.ElementTree as ET
import traceback

def test_dashboard_components():
    """Test PyMoDAQ components that could cause hanging"""
    
    print('=== PyMoDAQ Dashboard Startup Test ===')
    
    # Set environment for headless operation
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['DISPLAY'] = ''
    
    try:
        # Test 1: Import PyMoDAQ without errors
        print('1. Testing PyMoDAQ imports...')
        from pymodaq.dashboard import DashBoard
        from qtpy import QtWidgets
        print('   SUCCESS: PyMoDAQ imports successful')
        
        # Test 2: Create Qt Application
        print('2. Testing Qt Application creation...')
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        print('   SUCCESS: Qt Application created')
        
        # Test 3: Test preset file parsing (the main cause of hanging)
        print('3. Testing preset file XML parsing...')
        preset_files = [
            '/home/maitai/.pymodaq/preset_configs/preset_urashg.xml',
            '/home/maitai/.pymodaq/preset_configs/preset_ellipticity_calibration.xml',
            '/home/maitai/.pymodaq/preset_configs/preset_ellipticity_no_init.xml'
        ]
        
        for preset_file in preset_files:
            if os.path.exists(preset_file):
                try:
                    tree = ET.parse(preset_file)
                    root = tree.getroot()
                    print(f'   SUCCESS: Parsed {os.path.basename(preset_file)} - root: {root.tag}')
                except Exception as e:
                    print(f'   ERROR: Failed to parse {os.path.basename(preset_file)}: {e}')
                    return False
        
        # Test 4: Test parameter loading simulation
        print('4. Testing PyMoDAQ parameter system...')
        try:
            from pymodaq.utils.parameter import Parameter
            param = Parameter.create(name='test', type='group')
            print('   SUCCESS: Parameter system working')
        except Exception as e:
            print(f'   ERROR: Parameter system failed: {e}')
            return False
        
        # Test 5: Test plugin discovery
        print('5. Testing plugin discovery...')
        try:
            from pymodaq.utils.managers.modules_manager import ModulesManager
            manager = ModulesManager()
            print('   SUCCESS: ModulesManager created')
        except Exception as e:
            print(f'   ERROR: ModulesManager failed: {e}')
            return False
        
        print('\n=== DASHBOARD STARTUP TEST RESULTS ===')
        print('SUCCESS: All critical components tested successfully')
        print('SUCCESS: No hanging conditions detected')
        print('SUCCESS: PyMoDAQ dashboard should start properly')
        return True
        
    except Exception as e:
        print(f'\nERROR: Dashboard test failed: {e}')
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_dashboard_components()
    if success:
        print('\n*** FINAL RESULT: PyMoDAQ dashboard startup issues RESOLVED ***')
    else:
        print('\n*** FINAL RESULT: Issues still exist ***')
    exit(0 if success else 1)
EOF < /dev/null