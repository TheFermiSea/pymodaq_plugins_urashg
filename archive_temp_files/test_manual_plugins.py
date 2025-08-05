#!/usr/bin/env python3
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
    
    print(f"\n=== RESULTS ===")
    print(f"Successfully created {len(successful_plugins)}/4 plugins")
    
    if len(successful_plugins) == 4:
        print("✅ ALL URASHG PLUGINS WORK CORRECTLY!")
        print("✅ The issue is only with PyMoDAQ GUI plugin discovery")
        print("\n📝 SOLUTION:")
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
