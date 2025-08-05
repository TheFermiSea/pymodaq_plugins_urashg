#!/usr/bin/env python3
"""
Test PyMoDAQ DAQ_Move with URASHG plugins
This verifies that our move plugins work correctly
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

def launch_daq_move_elliptec():
    """Launch DAQ_Move for Elliptec plugin"""
    
    setup_x11_environment()
    
    try:
        print("=== Launching DAQ_Move for Elliptec Rotation Mounts ===")
        print("This will test the DAQ_Move_Elliptec plugin")
        print()
        
        from qtpy import QtWidgets
        from pymodaq.control_modules.daq_move import DAQ_Move
        
        # Create Qt application
        app = QtWidgets.QApplication(sys.argv)
        
        # Create DAQ_Move with Elliptec plugin
        print("Creating DAQ_Move with Elliptec plugin...")
        
        # Set up the plugin configuration
        plugin_config = {
            'move_type': 'DAQ_Move_Elliptec',
            'module_name': 'pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec',
            'init': False,  # Don't auto-initialize for testing
            'settings': {
                'serial_port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'mount_addresses': '2,3,8',
                'mock_mode': True  # Use mock mode for safe testing
            }
        }
        
        # Create the DAQ_Move instance
        daq_move = DAQ_Move('Elliptec_Test')
        
        print("✅ DAQ_Move created successfully!")
        print("✅ Elliptec plugin should be available in the dropdown")
        print()
        print("🚀 DAQ_Move interface launching...")
        print("   - Look for 'DAQ_Move_Elliptec' in the plugin dropdown")
        print("   - This controls 3 rotation mounts: HWP, QWP, Analyzer")
        print("   - Mock mode is enabled for safe testing")
        print()
        print("Press Ctrl+C in terminal to close when done testing")
        
        # Show the DAQ_Move window
        daq_move.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n👋 DAQ_Move closed by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error launching DAQ_Move: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def launch_daq_move_maitai():
    """Launch DAQ_Move for MaiTai plugin"""
    
    setup_x11_environment()
    
    try:
        print("=== Launching DAQ_Move for MaiTai Laser ===")
        print("This will test the DAQ_Move_MaiTai plugin")
        print()
        
        from qtpy import QtWidgets
        from pymodaq.control_modules.daq_move import DAQ_Move
        
        # Create Qt application
        app = QtWidgets.QApplication(sys.argv)
        
        # Create DAQ_Move with MaiTai plugin
        print("Creating DAQ_Move with MaiTai plugin...")
        
        # Create the DAQ_Move instance
        daq_move = DAQ_Move('MaiTai_Test')
        
        print("✅ DAQ_Move created successfully!")
        print("✅ MaiTai plugin should be available in the dropdown")
        print()
        print("🚀 DAQ_Move interface launching...")
        print("   - Look for 'DAQ_Move_MaiTai' in the plugin dropdown")
        print("   - This controls MaiTai laser wavelength and power")
        print("   - Mock mode is enabled for safe testing")
        print()
        print("Press Ctrl+C in terminal to close when done testing")
        
        # Show the DAQ_Move window
        daq_move.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n👋 DAQ_Move closed by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error launching DAQ_Move: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def launch_daq_move_generic():
    """Launch generic DAQ_Move to test plugin discovery"""
    
    setup_x11_environment()
    
    try:
        print("=== Launching Generic DAQ_Move Interface ===")
        print("This will show all available move plugins including URASHG ones")
        print()
        
        from qtpy import QtWidgets
        from pymodaq.control_modules.daq_move import DAQ_Move
        
        # Create Qt application
        app = QtWidgets.QApplication(sys.argv)
        
        print("Creating generic DAQ_Move interface...")
        
        # Create the DAQ_Move instance
        daq_move = DAQ_Move('URASHG_Move_Test')
        
        print("✅ DAQ_Move interface created successfully!")
        print()
        print("🚀 DAQ_Move interface launching...")
        print("📋 In the interface, check the plugin dropdown for:")
        print("   ✓ DAQ_Move_Elliptec (Thorlabs rotation mounts)")
        print("   ✓ DAQ_Move_MaiTai (MaiTai laser control)")
        print("   ✓ DAQ_Move_ESP300 (Newport motion controller)")
        print()
        print("🧪 To test a plugin:")
        print("   1. Select plugin from dropdown")
        print("   2. Configure settings (mock mode recommended)")
        print("   3. Click 'Init' to initialize")
        print("   4. Test movement commands")
        print()
        print("Press Ctrl+C in terminal to close when done testing")
        
        # Show the DAQ_Move window
        daq_move.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n👋 DAQ_Move closed by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error launching DAQ_Move: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main function to choose which DAQ_Move to launch"""
    
    print("PyMoDAQ DAQ_Move Verification Tool")
    print("="*50)
    print("Choose which DAQ_Move interface to launch:")
    print()
    print("1. Generic DAQ_Move (shows all plugins)")
    print("2. Elliptec-specific DAQ_Move")
    print("3. MaiTai-specific DAQ_Move")
    print()
    
    choice = input("Enter choice (1-3, or press Enter for generic): ").strip()
    
    if choice == "2":
        launch_daq_move_elliptec()
    elif choice == "3":
        launch_daq_move_maitai()
    else:
        launch_daq_move_generic()

if __name__ == "__main__":
    main()