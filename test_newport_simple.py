#!/usr/bin/env python3
"""
Simple Newport 1830-C connection test.
"""

import serial
import time

print("🔬 Simple Newport 1830-C Connection Test")
print("=" * 45)

try:
    # Test if we can open the serial port
    print("📡 Testing serial port /dev/ttyUSB2...")
    
    ser = serial.Serial(
        port='/dev/ttyUSB2',
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=2.0
    )
    
    print("✅ Serial port opened successfully!")
    print(f"   Port: {ser.port}")
    print(f"   Baudrate: {ser.baudrate}")
    print(f"   Is open: {ser.is_open}")
    
    # Try basic commands
    print("\n🔄 Testing basic communication...")
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    test_commands = ['*IDN?\n', 'W?\n', 'U?\n', 'D?\n']
    
    for cmd in test_commands:
        print(f"\n   Sending: {cmd.strip()}")
        
        # Send command
        ser.write(cmd.encode('ascii'))
        ser.flush()
        
        # Wait and read response
        time.sleep(1.0)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            print(f"   Response: '{response.strip()}'")
        else:
            print("   No response")
    
    ser.close()
    print("\n✅ Serial test completed")
    
except serial.SerialException as e:
    print(f"❌ Serial error: {e}")
    print("   This could be a permissions issue")
    print("   Try: sudo usermod -a -G dialout $USER")
    print("   Then log out and back in")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("\n🔍 Checking device permissions...")
import os
import stat

try:
    stat_info = os.stat('/dev/ttyUSB2')
    print(f"   Device permissions: {stat.filemode(stat_info.st_mode)}")
    print(f"   Owner: {stat_info.st_uid}")
    print(f"   Group: {stat_info.st_gid}")
    
    # Check current user groups
    import grp
    import pwd
    
    user = pwd.getpwuid(os.getuid()).pw_name
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
    primary_group = grp.getgrgid(pwd.getpwuid(os.getuid()).pw_gid).gr_name
    all_groups = [primary_group] + groups
    
    print(f"   Current user: {user}")
    print(f"   User groups: {all_groups}")
    
    if 'dialout' in all_groups or 'uucp' in all_groups:
        print("   ✅ User has serial port access")
    else:
        print("   ❌ User lacks serial port access")
        print("   Run: sudo usermod -a -G dialout $USER")
        
except Exception as e:
    print(f"   Error checking permissions: {e}")