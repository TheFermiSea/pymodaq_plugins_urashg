#!/usr/bin/env python3
"""
Test PyMoDAQ Dashboard creation step by step
Since basic Qt works, let's test the specific dashboard creation
"""

import os
import sys
import traceback

def test_dashboard_components():
    """Test dashboard components individually"""
    
    print("=== Testing PyMoDAQ Dashboard Creation ===")
    
    try:
        print("1. Setting up Qt application...")
        from qtpy import QtWidgets, QtCore
        
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        print("   ✅ Qt application ready")
        
        print("\n2. Testing DockArea import...")
        try:
            from pymodaq.utils.gui_utils.dock import DockArea
            print("   ✅ DockArea imported successfully")
        except ImportError:
            print("   ❌ DockArea not found in pymodaq.utils.gui_utils.dock")
            print("   Trying alternative imports...")
            
            # Try different possible locations
            alternatives = [
                "pyqdockwidget.dock",
                "pymodaq_gui.dock", 
                "pymodaq.utils.dock",
                "pymodaq.dock"
            ]
            
            dock_area_class = None
            for alt in alternatives:
                try:
                    module = __import__(alt, fromlist=['DockArea'])
                    if hasattr(module, 'DockArea'):
                        DockArea = module.DockArea
                        dock_area_class = DockArea
                        print(f"   ✅ Found DockArea in {alt}")
                        break
                except ImportError:
                    continue
            
            if dock_area_class is None:
                print("   ❌ Could not find DockArea anywhere")
                print("   Let's try creating a simple widget as dockarea...")
                DockArea = QtWidgets.QWidget  # Fallback
        
        print("\n3. Creating main window and dock area...")
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle("PyMoDAQ Dashboard Test")
        
        dock_area = DockArea()
        main_window.setCentralWidget(dock_area)
        print("   ✅ Main window and dock area created")
        
        print("\n4. Importing Dashboard...")
        from pymodaq.dashboard import DashBoard
        print("   ✅ Dashboard imported")
        
        print("\n5. Creating Dashboard...")
        dashboard = DashBoard(dock_area)
        print("   ✅ Dashboard created successfully!")
        
        print("\n6. Testing dashboard show...")
        main_window.show()
        print("   ✅ Dashboard window shown")
        
        # Process events briefly
        for i in range(10):
            app.processEvents()
            QtCore.QThread.msleep(100)
        
        print("\n7. Closing dashboard...")
        main_window.close()
        print("   ✅ Dashboard closed successfully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during dashboard creation: {e}")
        traceback.print_exc()
        return False

def test_command_line_dashboard():
    """Test running dashboard command directly with environment setup"""
    
    print("\n=== Testing Command Line Dashboard ===")
    
    # Test different environment configurations
    configs = [
        {
            "name": "Default Environment",
            "env": {}
        },
        {
            "name": "Software Rendering", 
            "env": {
                "QT_QUICK_BACKEND": "software",
                "QT_XCB_GL_INTEGRATION": "none",
                "LIBGL_ALWAYS_SOFTWARE": "1", 
                "QT_OPENGL": "software",
                "QT_X11_NO_MITSHM": "1"
            }
        },
        {
            "name": "Offscreen Platform",
            "env": {
                "QT_QPA_PLATFORM": "offscreen"
            }
        }
    ]
    
    for config in configs:
        print(f"\n--- Testing {config['name']} ---")
        
        # Create test script
        test_script = f"""
import os
import sys

# Set environment
{chr(10).join([f'os.environ["{k}"] = "{v}"' for k, v in config['env'].items()])}

try:
    print("Importing PyMoDAQ...")
    from qtpy import QtWidgets
    from pymodaq.dashboard import DashBoard
    
    print("Creating application...")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    
    print("Creating main window...")
    main_window = QtWidgets.QMainWindow()
    
    # Try to create dock area
    try:
        from pymodaq.utils.gui_utils.dock import DockArea
        dock_area = DockArea()
    except ImportError:
        print("Using QWidget as dock area fallback")
        dock_area = QtWidgets.QWidget()
    
    main_window.setCentralWidget(dock_area)
    
    print("Creating dashboard...")
    dashboard = DashBoard(dock_area)
    
    print("Showing window...")
    main_window.show()
    
    # Process events briefly then close
    for i in range(5):
        app.processEvents()
        
    main_window.close()
    print("SUCCESS: Dashboard created and shown successfully")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    import traceback
    traceback.print_exc()
"""
        
        with open('/tmp/test_dashboard.py', 'w') as f:
            f.write(test_script)
        
        import subprocess
        try:
            result = subprocess.run([sys.executable, '/tmp/test_dashboard.py'], 
                                  capture_output=True, text=True, timeout=30)
            
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            if result.stderr:
                print(f"Error: {result.stderr}")
                
            if result.returncode == 0:
                print(f"✅ {config['name']} works!")
                return config  # Return working configuration
            else:
                print(f"❌ {config['name']} failed")
                
        except subprocess.TimeoutExpired:
            print(f"❌ {config['name']} timed out")
        except Exception as e:
            print(f"❌ {config['name']} error: {e}")
    
    return None

def main():
    """Main test function"""
    print("PyMoDAQ Dashboard Creation Debugging")
    print("Since basic Qt works, let's test dashboard specifically")
    
    # Test 1: Direct dashboard creation
    success1 = test_dashboard_components()
    
    # Test 2: Command line dashboard
    working_config = test_command_line_dashboard()
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    
    if success1:
        print("✅ Direct dashboard creation works")
        print("✅ The issue might be with the 'dashboard' command specifically")
        print("\nTry creating a custom dashboard script:")
        print("   python -c \"from pymodaq.dashboard import main; main()\"")
    else:
        print("❌ Dashboard creation has issues")
    
    if working_config:
        print(f"✅ Working configuration found: {working_config['name']}")
        print("Environment variables to set:")
        for k, v in working_config['env'].items():
            print(f"   export {k}={v}")
    
    print("\nNext: Try the custom dashboard launch script below")

if __name__ == "__main__":
    main()