#!/usr/bin/env python3
"""
PyMoDAQ URASHG Plugin GUI Test Launcher

This script creates a minimal environment to test the URASHG plugins
in the PyMoDAQ Dashboard without requiring the full PyMoDAQ framework.
"""

import sys
import os
from pathlib import Path

# Add the plugin source to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_plugin_imports():
    """Test that all plugins can be imported successfully"""
    print("Testing plugin imports...")
    
    try:
        # Test individual plugin imports
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        print("✓ Elliptec plugin imported successfully")
        
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        print("✓ MaiTai plugin imported successfully")
        
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        print("✓ Prime BSI camera plugin imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Plugin import failed: {e}")
        return False

def launch_individual_plugin_test(plugin_name):
    """Launch individual plugin for testing"""
    print(f"\nLaunching {plugin_name} plugin test...")
    
    if plugin_name == "elliptec":
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        
        # Create a mock testing environment
        try:
            import qtpy.QtWidgets as QtWidgets
            from qtpy.QtCore import QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            # Create a minimal test window
            window = QtWidgets.QMainWindow()
            window.setWindowTitle("PyMoDAQ URASHG - Elliptec Plugin Test")
            window.resize(800, 600)
            
            # Create a simple widget to display plugin info
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            
            # Plugin information
            info_label = QtWidgets.QLabel(f"""
<h2>Elliptec Plugin Test</h2>
<p><b>Plugin Class:</b> DAQ_Move_Elliptec</p>
<p><b>Axes:</b> {', '.join(DAQ_Move_Elliptec._axis_names)}</p>
<p><b>Default Addresses:</b> {', '.join(DAQ_Move_Elliptec._default_addresses)}</p>
<p><b>Commands:</b> {len(DAQ_Move_Elliptec._command_reference)} defined</p>
<p><b>Error Codes:</b> {len(DAQ_Move_Elliptec._error_codes)} defined</p>
<br>
<p><i>This plugin is ready for hardware integration.</i></p>
<p><i>In actual PyMoDAQ Dashboard, this would show parameter controls.</i></p>
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Add close button
            close_btn = QtWidgets.QPushButton("Close")
            close_btn.clicked.connect(window.close)
            layout.addWidget(close_btn)
            
            widget.setLayout(layout)
            window.setCentralWidget(widget)
            
            print("✓ Plugin test window created successfully")
            window.show()
            return app
            
        except Exception as e:
            print(f"❌ GUI launch failed: {e}")
            return None
    
    elif plugin_name == "maitai":
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        
        try:
            import qtpy.QtWidgets as QtWidgets
            from qtpy.QtCore import QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            window = QtWidgets.QMainWindow()
            window.setWindowTitle("PyMoDAQ URASHG - MaiTai Plugin Test")
            window.resize(800, 600)
            
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            
            info_label = QtWidgets.QLabel(f"""
<h2>MaiTai Laser Plugin Test</h2>
<p><b>Plugin Class:</b> DAQ_Move_MaiTai</p>
<p><b>Axes:</b> Wavelength, Shutter</p>
<p><b>Commands:</b> {len(DAQ_Move_MaiTai._command_reference)} defined</p>
<p><b>Features:</b> Background monitoring, Threading safety</p>
<br>
<p><i>This plugin is ready for hardware integration.</i></p>
<p><i>In actual PyMoDAQ Dashboard, this would show laser controls and status.</i></p>
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            close_btn = QtWidgets.QPushButton("Close")
            close_btn.clicked.connect(window.close)
            layout.addWidget(close_btn)
            
            widget.setLayout(layout)
            window.setCentralWidget(widget)
            
            print("✓ Plugin test window created successfully")
            window.show()
            return app
            
        except Exception as e:
            print(f"❌ GUI launch failed: {e}")
            return None
    
    elif plugin_name == "camera":
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        
        try:
            import qtpy.QtWidgets as QtWidgets
            from qtpy.QtCore import QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            window = QtWidgets.QMainWindow()
            window.setWindowTitle("PyMoDAQ URASHG - Prime BSI Camera Plugin Test")
            window.resize(800, 600)
            
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            
            info_label = QtWidgets.QLabel(f"""
<h2>Prime BSI Camera Plugin Test</h2>
<p><b>Plugin Class:</b> DAQ_2DViewer_PrimeBSI</p>
<p><b>Interface:</b> PyVCAM (with graceful fallback)</p>
<p><b>Features:</b> ROI integration, Dynamic parameter discovery</p>
<p><b>Data Output:</b> 2D frames + 0D integrated signal</p>
<br>
<p><i>This plugin is ready for hardware integration.</i></p>
<p><i>In actual PyMoDAQ Dashboard, this would show camera controls and live imaging.</i></p>
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            close_btn = QtWidgets.QPushButton("Close")
            close_btn.clicked.connect(window.close)
            layout.addWidget(close_btn)
            
            widget.setLayout(layout)
            window.setCentralWidget(widget)
            
            print("✓ Plugin test window created successfully")
            window.show()
            return app
            
        except Exception as e:
            print(f"❌ GUI launch failed: {e}")
            return None

def main():
    """Main test function"""
    print("=" * 80)
    print(" PyMoDAQ URASHG Plugin GUI Test")
    print("=" * 80)
    
    # Test plugin imports first
    if not test_plugin_imports():
        print("\n❌ Plugin import test failed. Cannot proceed with GUI test.")
        return 1
    
    print("\n" + "=" * 80)
    print(" GUI Integration Test Options")
    print("=" * 80)
    print("1. Test Elliptec Plugin")
    print("2. Test MaiTai Plugin") 
    print("3. Test Prime BSI Camera Plugin")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                app = launch_individual_plugin_test("elliptec")
                if app:
                    print("\nGUI launched! Close the window to return to menu.")
                    app.exec_()
                    
            elif choice == "2":
                app = launch_individual_plugin_test("maitai")
                if app:
                    print("\nGUI launched! Close the window to return to menu.")
                    app.exec_()
                    
            elif choice == "3":
                app = launch_individual_plugin_test("camera")
                if app:
                    print("\nGUI launched! Close the window to return to menu.")
                    app.exec_()
                    
            elif choice == "4":
                print("\nExiting...")
                break
                
            else:
                print("Invalid choice. Please select 1-4.")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())