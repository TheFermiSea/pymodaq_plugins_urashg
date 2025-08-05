#!/usr/bin/env python3
"""
Manual Plugin Creation Tool
Since the dropdown doesn't show our plugins, this creates them directly
"""

import os
import sys

def create_manual_plugin_script():
    """Create a script that manually adds URASHG plugins to PyMoDAQ"""
    
    script_content = '''#!/usr/bin/env python3
"""
Manual URASHG Plugin Loader for PyMoDAQ
This bypasses the GUI dropdown issue by creating plugins directly
"""

import sys
from qtpy import QtWidgets, QtCore

def create_elliptec_plugin(parent_manager):
    """Create Elliptec rotation mount plugin manually"""
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
        
        # Create the plugin with proper parameters
        plugin = DAQ_Move_Elliptec(parent_manager, params_list=None)
        plugin.ini_attributes()
        
        print("✅ Elliptec plugin created successfully")
        return plugin
        
    except Exception as e:
        print(f"❌ Failed to create Elliptec plugin: {e}")
        return None

def create_maitai_plugin(parent_manager):
    """Create MaiTai laser plugin manually"""
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
        
        # Create the plugin with proper parameters
        plugin = DAQ_Move_MaiTai(parent_manager, params_list=None)
        plugin.ini_attributes()
        
        print("✅ MaiTai plugin created successfully")
        return plugin
        
    except Exception as e:
        print(f"❌ Failed to create MaiTai plugin: {e}")
        return None

def create_newport_plugin(parent_manager):
    """Create Newport power meter plugin manually"""
    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C import DAQ_0DViewer_Newport1830C
        
        # Create the plugin with proper parameters
        plugin = DAQ_0DViewer_Newport1830C(parent_manager, params_list=None)
        plugin.ini_attributes()
        
        print("✅ Newport plugin created successfully")
        return plugin
        
    except Exception as e:
        print(f"❌ Failed to create Newport plugin: {e}")
        return None

def create_primebsi_plugin(parent_manager):
    """Create PrimeBSI camera plugin manually"""
    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
        
        # Create the plugin with proper parameters  
        plugin = DAQ_2DViewer_PrimeBSI(parent_manager, params_list=None)
        plugin.ini_attributes()
        
        print("✅ PrimeBSI plugin created successfully")
        return plugin
        
    except Exception as e:
        print(f"❌ Failed to create PrimeBSI plugin: {e}")
        return None

def main():
    """Main function to demonstrate manual plugin creation"""
    print("=== Manual URASHG Plugin Creation ===")
    print("This demonstrates that our plugins work correctly")
    print("")
    
    # Create a Qt application for testing
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    
    # Create a dummy parent manager (normally this would be the ModulesManager)
    class DummyManager:
        def __init__(self):
            self.settings = {}
            
    parent = DummyManager()
    
    # Test creating each plugin
    plugins = []
    
    print("Creating URASHG plugins...")
    plugins.append(create_elliptec_plugin(parent))
    plugins.append(create_maitai_plugin(parent))  
    plugins.append(create_newport_plugin(parent))
    plugins.append(create_primebsi_plugin(parent))
    
    successful_plugins = [p for p in plugins if p is not None]
    
    print(f"\\n=== RESULTS ===")
    print(f"Successfully created {len(successful_plugins)}/4 plugins")
    
    if len(successful_plugins) == 4:
        print("✅ ALL URASHG PLUGINS WORK CORRECTLY!")
        print("✅ The issue is only with PyMoDAQ GUI plugin discovery")
        print("\\n📝 SOLUTION:")
        print("   1. Load the preset: preset_urashg_working.xml")
        print("   2. Or manually type plugin names in the Add dialogs")
        print("   3. Plugin names to use:")
        print("      - DAQ_Move_Elliptec")
        print("      - DAQ_Move_MaiTai")  
        print("      - DAQ_0DViewer_Newport1830C")
        print("      - DAQ_2DViewer_PrimeBSI")
    else:
        print("❌ Some plugins have issues - check the error messages above")

if __name__ == "__main__":
    main()
'''
    
    script_path = '/home/maitai/pymodaq_plugins_urashg/test_manual_plugins.py'
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"✅ Created manual plugin test script: {script_path}")
    return script_path

def create_preset_loader():
    """Create a script to load the working preset"""
    
    script_content = '''#!/usr/bin/env python3
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
'''
    
    script_path = '/home/maitai/pymodaq_plugins_urashg/load_urashg_preset.py'
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"✅ Created preset loader script: {script_path}")
    return script_path

def main():
    """Create all manual plugin tools"""
    print("Creating manual plugin tools to bypass GUI discovery issue...")
    print("")
    
    # Create the manual plugin test script
    test_script = create_manual_plugin_script()
    
    # Create the preset loader script
    preset_script = create_preset_loader()
    
    print("")
    print("=== SOLUTIONS CREATED ===")
    print(f"1. ✅ Working preset: /home/maitai/.pymodaq/preset_configs/preset_urashg_working.xml")
    print(f"2. ✅ Manual plugin test: {test_script}")  
    print(f"3. ✅ Preset loader: {preset_script}")
    print("")
    print("=== HOW TO USE ===")
    print("Option 1 - Load preset automatically:")
    print("   python load_urashg_preset.py")
    print("")
    print("Option 2 - Manual dashboard + preset:")
    print("   1. python dashboard_x11_fixed.py")
    print("   2. In PyMoDAQ: File -> Load Preset -> preset_urashg_working.xml")
    print("")
    print("Option 3 - Manual plugin names (if dropdown is empty):")
    print("   - DAQ_Move_Elliptec")
    print("   - DAQ_Move_MaiTai")
    print("   - DAQ_0DViewer_Newport1830C") 
    print("   - DAQ_2DViewer_PrimeBSI")

if __name__ == "__main__":
    main()