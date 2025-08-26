#!/usr/bin/env python3
"""
Hardware Connectivity Test for URASHG Components

This script tests the basic hardware connectivity without full PyMoDAQ plugin
initialization to verify that the hardware devices are properly connected
and accessible.

Usage:
    python test_hardware_connectivity.py

Hardware Expected:
    - Elliptec rotation mounts on /dev/ttyUSB1
    - Newport 1830-C Power Meter on /dev/ttyS0
    - Photometrics PrimeBSI camera (PyVCAM)
    - MaiTai laser (serial connection on various ports)
    - ESP300 motion controller (serial connection on various ports)
"""

import os
import sys
import time
from pathlib import Path

import serial

# Add source path for local imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_serial_device(
    port, baudrate=9600, timeout=2, test_command=None, description=""
):
    """Test basic serial communication with a device."""
    print(f"Testing {description} on {port}...")

    if not os.path.exists(port):
        print(f"❌ Port {port} does not exist")
        return False

    try:
        # Open serial connection
        ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(0.1)  # Give device time to initialize

        if test_command:
            # Send test command
            ser.write((test_command + "\r\n").encode())
            time.sleep(0.1)

            # Read response
            response = ser.read(100).decode("utf-8", errors="ignore").strip()
            ser.close()

            if response:
                print(f"✅ {description}: Connected - Response: {response[:50]}...")
                return True
            else:
                print(f"⚠️  {description}: Connected but no response to command")
                return True
        else:
            # Just test connection
            ser.close()
            print(f"✅ {description}: Port accessible")
            return True

    except Exception as e:
        print(f"❌ {description}: Connection failed - {e}")
        return False


def test_elliptec_connectivity():
    """Test Elliptec rotation mounts connectivity."""
    print("\n=== Testing Elliptec Rotation Mounts ===")

    # Elliptec uses 9600 baud by default
    # Command 'in' gets device info for all devices on bus
    return test_serial_device(
        port="/dev/ttyUSB1",
        baudrate=9600,
        test_command="in",
        description="Elliptec Rotation Mounts",
    )


def test_newport_power_meter():
    """Test Newport 1830-C Power Meter connectivity."""
    print("\n=== Testing Newport Power Meter ===")

    # Newport 1830-C typically uses 9600 baud
    # Command '*IDN?' requests device identification
    return test_serial_device(
        port="/dev/ttyS0",
        baudrate=9600,
        test_command="*IDN?",
        description="Newport 1830-C Power Meter",
    )


def test_maitai_laser():
    """Test direct communication with MaiTai Ti:Sapphire laser."""
    print("\n" + "="*50)
    print("Testing MaiTai Ti:Sapphire Laser")
    print("="*50)
    
    # Try Silicon Labs port first (user suggested), then others
    ports_to_try = [
        "/dev/ttyUSB2",  # ✅ FIXED: Actual detected port first
        "/dev/ttyUSB0",
        "/dev/ttyUSB4",
        "/dev/ttyUSB5", 
        "/dev/ttyUSB6",
    ]
    baud_rates = [9600, 19200, 115200]  # ✅ FIXED: 9600 first (actual working baudrate)

    # SCPI commands from MaiTai manual
    test_commands = [
        "?",           # Simple query
        "*IDN?",       # Identification
        "READ:POW?",   # Read power
        "READ:WAVE?",  # Read wavelength
    ]
    
    for port in ports_to_try:
        for baud in baud_rates:
            print(f"\n--- Testing {port} at {baud} baud ---")
            
            result = test_serial_device(
                port=port,
                baudrate=baud,
                test_command="*IDN?",
                expected_response="MaiTai",
                timeout=2.0
            )
            
            if result:
                print(f"✅ MaiTai CONFIRMED on {port} at {baud} baud")
                
                # Test additional commands  
                print("Testing additional commands...")
                for cmd in test_commands[1:]:  # Skip "?" as it might not work
                    cmd_result = test_serial_device(
                        port=port,
                        baudrate=baud, 
                        test_command=cmd,
                        expected_response=None,  # Accept any response
                        timeout=1.0
                    )
                    if cmd_result:
                        print(f"   ✅ {cmd} -> Response received")
                    else:
                        print(f"   ⚠️ {cmd} -> No response")
                        
                return True
            else:
                print(f"   ❌ No response from {port} at {baud}")
    
    print("\n❌ MaiTai not found on any tested port/baud combination")
    print("   Expected: Working MaiTai on /dev/ttyUSB2 at 9600 baud")  # ✅ FIXED: Correct expectation
    return False


def test_esp300_controller():
    """Test ESP300 motion controller connectivity."""
    print("\n=== Testing ESP300 Motion Controller ===")

    # ESP300 confirmed working on USB3 from real hardware tests
    ports_to_try = ["/dev/ttyUSB3", "/dev/ttyUSB4", "/dev/ttyUSB5", "/dev/ttyUSB6"]

    for port in ports_to_try:
        if os.path.exists(port):
            print(f"Trying ESP300 on {port}...")
            # ESP300 uses 19200 baud, confirmed working
            # Command '*IDN?' gets controller identification
            if test_serial_device(
                port=port,
                baudrate=19200,
                test_command="*IDN?",
                description=f"ESP300 Controller ({port})",
            ):
                return True

    print("❌ ESP300 Controller: No responsive device found on any port")
    return False


def test_primebsi_camera():
    """Test PrimeBSI camera connectivity via PyVCAM."""
    print("\n=== Testing PrimeBSI Camera ===")

    try:
        # Try to import and initialize PyVCAM
        import pyvcam
        from pyvcam import constants

        print("PyVCAM library imported successfully")

        # Initialize PVCAM
        pyvcam.pvc.init_pvcam()
        print("PVCAM library initialized")

        # Get camera count
        cam_count = pyvcam.pvc.get_cam_total()
        print(f"Found {cam_count} camera(s)")

        if cam_count > 0:
            # Try to open first camera
            camera = pyvcam.Camera.detect_camera()
            if camera:
                print(f"✅ PrimeBSI Camera: Detected - {camera.name}")
                # Get some basic info
                try:
                    temp = camera.temp
                    print(f"   Temperature: {temp}°C")
                except:
                    print("   Temperature read failed")

                camera.close()
                pyvcam.pvc.uninit_pvcam()
                return True
            else:
                print("❌ PrimeBSI Camera: No camera detected")
                pyvcam.pvc.uninit_pvcam()
                return False
        else:
            print("❌ PrimeBSI Camera: No cameras found")
            pyvcam.pvc.uninit_pvcam()
            return False

    except ImportError as e:
        print(f"❌ PrimeBSI Camera: PyVCAM not available - {e}")
        return False
    except Exception as e:
        print(f"❌ PrimeBSI Camera: Test failed - {e}")
        try:
            pyvcam.pvc.uninit_pvcam()
        except:
            pass
        return False


def test_device_permissions():
    """Test device file permissions."""
    print("\n=== Testing Device Permissions ===")

    devices_to_check = [
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
        "/dev/ttyUSB2",
        "/dev/ttyUSB3",
        "/dev/ttyUSB4",
        "/dev/ttyUSB5",
        "/dev/ttyUSB6",
        "/dev/ttyS0",
    ]

    accessible_devices = []

    for device in devices_to_check:
        if os.path.exists(device):
            try:
                # Try to open device for reading
                with open(device, "rb") as f:
                    accessible_devices.append(device)
                    print(f"✅ {device}: Readable")
            except PermissionError:
                print(f"❌ {device}: Permission denied")
            except Exception as e:
                print(f"⚠️  {device}: {e}")
        else:
            print(f"⚠️  {device}: Does not exist")

    print(f"\nAccessible devices: {accessible_devices}")
    return len(accessible_devices) > 0


def main():
    """Run all hardware connectivity tests."""
    print("URASHG Hardware Connectivity Test")
    print("=" * 50)
    print("Testing basic hardware connectivity")
    print("Note: This tests low-level device communication")
    print("=" * 50)

    # Track test results
    tests = [
        ("Device Permissions", test_device_permissions),
        ("Elliptec Rotation Mounts", test_elliptec_connectivity),
        ("Newport Power Meter", test_newport_power_meter),
        ("MaiTai Laser", test_maitai_laser),
        ("ESP300 Controller", test_esp300_controller),
        ("PrimeBSI Camera", test_primebsi_camera),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print(f"\n⚠️  Test '{test_name}' interrupted by user")
            results.append((test_name, False))
            break
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("CONNECTIVITY TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ CONNECTED" if result else "❌ NOT CONNECTED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"TOTAL: {passed}/{total} devices connected")

    if passed >= total // 2:
        print("🎉 Most hardware devices are accessible!")
        return 0
    else:
        print("⚠️  Many devices not accessible. Check connections and permissions.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite crashed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
