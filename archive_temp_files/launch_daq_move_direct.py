#!/usr/bin/env python3
"""
Direct DAQ_Move Launcher for URASHG Plugin Verification
Launches DAQ_Move interface directly to test URASHG plugins
"""

import os
import sys

def setup_x11_environment():
    """Set up X11-compatible environment"""
    os.environ["QT_X11_NO_MITSHM"] = "1"
    os.environ["QT_GRAPHICSSYSTEM"] = "native"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_OPENGL"] = "software"

def launch_daq_move():
    """Launch DAQ_Move interface for URASHG plugin testing"""
    
    setup_x11_environment()
    
    try:
        print("="*60)
        print("PyMoDAQ DAQ_Move - URASHG Plugin Verification")
        print("="*60)
        print("Launching DAQ_Move interface to test URASHG move plugins")
        print()
        
        from qtpy import QtWidgets
        from pymodaq.control_modules.daq_move import DAQ_Move
        
        print("Creating Qt application...")
        app = QtWidgets.QApplication(sys.argv)
        
        print("Creating DAQ_Move interface...")
        daq_move = DAQ_Move('URASHG_Plugin_Test')
        
        print("✅ DAQ_Move interface created successfully!")
        print()
        print("🚀 DAQ_Move window launching...")
        print()
        print("📋 VERIFICATION CHECKLIST:")
        print("   1. ✓ Check plugin dropdown for URASHG plugins:")
        print("      - DAQ_Move_Elliptec (Thorlabs rotation mounts)")
        print("      - DAQ_Move_MaiTai (MaiTai laser control)")
        print("      - DAQ_Move_ESP300 (Newport motion controller)")
        print()
        print("   2. ✓ Select a plugin and verify settings appear")
        print("   3. ✓ Enable 'Mock Mode' for safe testing")
        print("   4. ✓ Click 'Init' to initialize the plugin")
        print("   5. ✓ Test movement commands work")
        print()
        print("🔧 Plugin Details:")
        print("   • Elliptec: Controls 3 rotation mounts (HWP, QWP, Analyzer)")
        print("   • MaiTai: Laser wavelength control (700-900nm)")
        print("   • ESP300: Multi-axis motion controller")
        print()
        print("⚠️  Use Mock Mode for initial testing!")
        print("💡 Press Ctrl+C in terminal to close when done")
        print()
        
        # Show the DAQ_Move window
        daq_move.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n👋 DAQ_Move verification completed")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error launching DAQ_Move: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to provide helpful debugging info
        print(f"\n🔍 Debugging Information:")
        print(f"   Python version: {sys.version}")
        print(f"   Working directory: {os.getcwd()}")
        
        # Check if PyMoDAQ is properly installed
        try:
            import pymodaq
            print(f"   PyMoDAQ version: {pymodaq.__version__}")
        except:
            print("   ❌ PyMoDAQ import failed")
            
        # Check if our plugins are available
        try:
            import importlib.metadata
            plugins = list(importlib.metadata.entry_points().select(group='pymodaq.move_plugins'))
            urashg_plugins = [p.name for p in plugins if 'urashg' in p.value.lower()]
            print(f"   URASHG plugins found: {urashg_plugins}")
        except:
            print("   ❌ Plugin discovery failed")
        
        sys.exit(1)

if __name__ == "__main__":
    launch_daq_move()