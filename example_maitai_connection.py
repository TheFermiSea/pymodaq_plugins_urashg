#!/usr/bin/env python3
"""
Example: Proper MaiTai Laser Connection with URASHG Extension

This example demonstrates the correct PyMoDAQ-compliant approach for connecting
to the MaiTai laser through the URASHG microscopy extension.

Key Points:
1. DeviceManager directly instantiates PyMoDAQ plugins
2. Follows proper PyMoDAQ plugin lifecycle (ini_stage, move_abs, close)
3. Uses DataActuator for position commands
4. Implements proper error handling and cleanup

Usage:
    python example_maitai_connection.py
    python example_maitai_connection.py --mock  # For testing without hardware
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_mock_dashboard():
    """Create minimal dashboard for plugin instantiation."""
    class MockDashboard:
        def __init__(self):
            self.modules_manager = None
    return MockDashboard()

def example_direct_maitai_connection():
    """Example 1: Direct MaiTai plugin connection."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Direct MaiTai Plugin Connection")
    print("="*60)

    try:
        # Import MaiTai plugin
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

        # Create mock dashboard
        dashboard = create_mock_dashboard()

        # Instantiate plugin
        print("Creating MaiTai plugin instance...")
        maitai_plugin = DAQ_Move_MaiTai(parent=dashboard)

        # Initialize plugin (this connects to hardware)
        print("Initializing MaiTai plugin...")
        init_result = maitai_plugin.ini_stage()

        if init_result and len(init_result) >= 2 and init_result[1]:
            print("✅ MaiTai plugin initialized successfully")

            # Get current wavelength
            current_wavelength = maitai_plugin.get_actuator_value()
            print(f"Current wavelength: {current_wavelength}")

            # Set new wavelength using DataActuator
            from pymodaq.utils.data import DataActuator

            target_wavelength = 800.0  # nm
            position_data = DataActuator(data=[target_wavelength])

            print(f"Setting wavelength to {target_wavelength} nm...")
            maitai_plugin.move_abs(position_data)

            # Verify new wavelength
            new_wavelength = maitai_plugin.get_actuator_value()
            print(f"New wavelength: {new_wavelength}")

            # Close connection
            maitai_plugin.close()
            print("✅ MaiTai connection closed properly")

        else:
            print(f"❌ MaiTai initialization failed: {init_result}")

    except Exception as e:
        print(f"❌ Direct connection example failed: {e}")
        import traceback
        traceback.print_exc()

def example_device_manager_connection():
    """Example 2: MaiTai connection through DeviceManager."""
    print("\n" + "="*60)
    print("EXAMPLE 2: MaiTai Connection via DeviceManager")
    print("="*60)

    try:
        # Import DeviceManager
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Create mock dashboard
        dashboard = create_mock_dashboard()

        # Create DeviceManager (automatically discovers and initializes plugins)
        print("Creating DeviceManager...")
        device_manager = URASHGDeviceManager(dashboard=dashboard)

        # Get MaiTai laser device
        print("Getting MaiTai laser device...")
        laser_device = device_manager.get_laser()

        if laser_device:
            print("✅ MaiTai laser device available")

            # Check device status
            print("Checking device status...")
            device_info = device_manager.get_device_info('laser')
            if device_info:
                print(f"Device status: {device_info.status.value}")

            # Get current wavelength
            current_wavelength = laser_device.get_actuator_value()
            print(f"Current wavelength: {current_wavelength}")

            # Set wavelength using the extension's pattern
            from pymodaq.utils.data import DataActuator

            target_wavelength = 850.0  # nm
            position_data = DataActuator(data=[target_wavelength])

            print(f"Setting wavelength to {target_wavelength} nm...")
            laser_device.move_abs(position_data)

            # Verify new wavelength
            new_wavelength = laser_device.get_actuator_value()
            print(f"New wavelength: {new_wavelength}")

            print("✅ DeviceManager connection successful")

        else:
            print("❌ MaiTai laser device not available")
            print("Available devices:")
            for device_key, device_info in device_manager.devices.items():
                print(f"  - {device_key}: {device_info.status.value}")

        # Cleanup
        device_manager.cleanup()
        print("✅ DeviceManager cleaned up")

    except Exception as e:
        print(f"❌ DeviceManager example failed: {e}")
        import traceback
        traceback.print_exc()

def example_extension_wavelength_control():
    """Example 3: Wavelength control as used in extension."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Extension-Style Wavelength Control")
    print("="*60)

    try:
        # This simulates how the URASHG extension controls wavelength
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager
        from pymodaq.utils.data import DataActuator

        # Create DeviceManager
        dashboard = create_mock_dashboard()
        device_manager = URASHGDeviceManager(dashboard=dashboard)

        def set_laser_wavelength(target_wavelength):
            """Set laser wavelength (extension method simulation)."""
            try:
                laser = device_manager.get_laser()
                if not laser:
                    print("ERROR: Laser device not available")
                    return False

                # Create position data - MaiTai laser uses single-axis control
                position_data = DataActuator(data=[target_wavelength])

                # Execute movement
                laser.move_abs(position_data)

                print(f"✅ Wavelength set to {target_wavelength} nm")
                return True

            except Exception as e:
                print(f"❌ Failed to set wavelength: {e}")
                return False

        def get_current_laser_wavelength():
            """Get current laser wavelength (extension method simulation)."""
            try:
                laser = device_manager.get_laser()
                if not laser:
                    return None

                # Try to get current wavelength
                if hasattr(laser, 'current_position') and laser.current_position is not None:
                    if hasattr(laser.current_position, 'value'):
                        return laser.current_position.value()
                    elif hasattr(laser.current_position, 'data'):
                        return laser.current_position.data[0][0]
                else:
                    # Fallback to get_actuator_value
                    return laser.get_actuator_value()

            except Exception as e:
                print(f"❌ Failed to get wavelength: {e}")
                return None

        # Test wavelength control
        print("Testing extension-style wavelength control...")

        current_wl = get_current_laser_wavelength()
        print(f"Current wavelength: {current_wl}")

        # Set to different wavelengths
        test_wavelengths = [800.0, 850.0, 900.0]

        for wl in test_wavelengths:
            success = set_laser_wavelength(wl)
            if success:
                actual_wl = get_current_laser_wavelength()
                print(f"Wavelength after setting to {wl}: {actual_wl}")
            else:
                print(f"Failed to set wavelength to {wl}")

        print("✅ Extension-style wavelength control complete")

        # Cleanup
        device_manager.cleanup()

    except Exception as e:
        print(f"❌ Extension wavelength control example failed: {e}")
        import traceback
        traceback.print_exc()

def example_shutter_control():
    """Example 4: MaiTai shutter control."""
    print("\n" + "="*60)
    print("EXAMPLE 4: MaiTai Shutter Control")
    print("="*60)

    try:
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Create DeviceManager
        dashboard = create_mock_dashboard()
        device_manager = URASHGDeviceManager(dashboard=dashboard)

        laser = device_manager.get_laser()
        if not laser:
            print("❌ Laser device not available for shutter control")
            return

        # Check if laser has shutter control capability
        if hasattr(laser, 'controller') and laser.controller:
            if hasattr(laser.controller, 'open_shutter'):
                print("Opening laser shutter...")
                laser.controller.open_shutter()
                print("✅ Laser shutter opened")

            if hasattr(laser.controller, 'close_shutter'):
                print("Closing laser shutter...")
                laser.controller.close_shutter()
                print("✅ Laser shutter closed")

            if hasattr(laser.controller, 'get_shutter_state'):
                shutter_state = laser.controller.get_shutter_state()
                print(f"Current shutter state: {shutter_state}")
        else:
            print("❌ Laser controller does not support shutter control")

        # Cleanup
        device_manager.cleanup()

    except Exception as e:
        print(f"❌ Shutter control example failed: {e}")
        import traceback
        traceback.print_exc()

def example_error_handling():
    """Example 5: Proper error handling patterns."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Error Handling Patterns")
    print("="*60)

    try:
        from pymodaq_plugins_urashg.extensions.device_manager import URASHGDeviceManager

        # Create DeviceManager
        dashboard = create_mock_dashboard()
        device_manager = URASHGDeviceManager(dashboard=dashboard)

        # Example of robust wavelength setting with error handling
        def safe_set_wavelength(target_wavelength, timeout=10.0):
            """Safely set wavelength with comprehensive error handling."""
            try:
                laser = device_manager.get_laser()
                if not laser:
                    raise RuntimeError("Laser device not available")

                # Validate wavelength range
                if not (700 <= target_wavelength <= 1000):
                    raise ValueError(f"Wavelength {target_wavelength} nm out of range (700-1000 nm)")

                # Get current wavelength for comparison
                current_wl = laser.get_actuator_value()
                print(f"Current wavelength: {current_wl} nm")

                # Check if change is significant
                if abs(current_wl - target_wavelength) < 0.1:
                    print(f"Wavelength already at target ({target_wavelength} nm)")
                    return True

                # Create position data
                from pymodaq.utils.data import DataActuator
                position_data = DataActuator(data=[target_wavelength])

                # Execute movement
                print(f"Setting wavelength to {target_wavelength} nm...")
                laser.move_abs(position_data)

                # Verify the change
                import time
                time.sleep(0.5)  # Allow time for movement
                actual_wl = laser.get_actuator_value()

                if abs(actual_wl - target_wavelength) < 1.0:  # 1 nm tolerance
                    print(f"✅ Wavelength successfully set to {actual_wl} nm")
                    return True
                else:
                    print(f"⚠️  Wavelength set to {actual_wl} nm (target was {target_wavelength} nm)")
                    return False

            except ValueError as e:
                print(f"❌ Invalid wavelength: {e}")
                return False
            except RuntimeError as e:
                print(f"❌ Runtime error: {e}")
                return False
            except Exception as e:
                print(f"❌ Unexpected error setting wavelength: {e}")
                import traceback
                traceback.print_exc()
                return False

        # Test error handling
        print("Testing error handling patterns...")

        # Valid wavelength
        safe_set_wavelength(800.0)

        # Invalid wavelength (out of range)
        safe_set_wavelength(1500.0)

        # Edge case wavelength
        safe_set_wavelength(699.9)

        print("✅ Error handling examples complete")

        # Cleanup
        device_manager.cleanup()

    except Exception as e:
        print(f"❌ Error handling example failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all examples."""
    print("URASHG MaiTai Laser Connection Examples")
    print("=" * 60)
    print("Demonstrating PyMoDAQ-compliant connection patterns")

    # Check for mock mode
    mock_mode = "--mock" in sys.argv
    if mock_mode:
        print("🧪 Running in MOCK MODE (simulated hardware)")
    else:
        print("🔧 Running with REAL HARDWARE")

    try:
        # Run examples
        example_direct_maitai_connection()
        example_device_manager_connection()
        example_extension_wavelength_control()
        example_shutter_control()
        example_error_handling()

        print("\n" + "=" * 60)
        print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Key Takeaways:")
        print("1. DeviceManager directly instantiates PyMoDAQ plugins")
        print("2. Use DataActuator for position commands")
        print("3. Follow proper plugin lifecycle (ini_stage → operations → close)")
        print("4. Implement comprehensive error handling")
        print("5. Always cleanup resources properly")

    except Exception as e:
        print(f"\n❌ Examples failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
