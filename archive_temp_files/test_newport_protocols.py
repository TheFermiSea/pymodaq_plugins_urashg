#!/usr/bin/env python3
"""
Test different Newport 1830-C communication protocols.

The device might use binary protocol or different command formats.
"""

import serial
import time
import struct

print("🔬 Newport 1830-C Protocol Detection")
print("=" * 45)

def test_ascii_protocol():
    """Test ASCII command protocol."""
    print("\n1️⃣ Testing ASCII Protocol...")
    
    try:
        ser = serial.Serial('/dev/ttyUSB2', 9600, timeout=2.0)
        print("   ✅ Serial port opened")
        
        # Try different ASCII command formats
        ascii_commands = [
            b'*IDN?\r\n',     # Standard SCPI
            b'*IDN?\n',       # LF only
            b'*IDN?\r',       # CR only
            b'W?\r\n',        # Wavelength query
            b'D?\r\n',        # Data query
            b'U?\r\n',        # Units query
            b'POWER?\r\n',    # Power query
            b'READ?\r\n',     # Read measurement
        ]
        
        for cmd in ascii_commands:
            print(f"   Testing: {cmd}")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            ser.write(cmd)
            ser.flush()
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   ✅ Response: {response}")
                return True
            else:
                print(f"   ❌ No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   ❌ ASCII test error: {e}")
        return False

def test_binary_protocol():
    """Test binary command protocol."""
    print("\n2️⃣ Testing Binary Protocol...")
    
    try:
        ser = serial.Serial('/dev/ttyUSB2', 9600, timeout=2.0)
        print("   ✅ Serial port opened")
        
        # Try binary commands (Newport often uses specific binary formats)
        binary_commands = [
            b'\x02P?\x03',      # STX P? ETX
            b'\x02W?\x03',      # STX W? ETX  
            b'\x02D?\x03',      # STX D? ETX
            b'\x02U?\x03',      # STX U? ETX
            b'\x50\x00',        # P + null
            b'\x57\x00',        # W + null
            b'\x44\x00',        # D + null
        ]
        
        for cmd in binary_commands:
            print(f"   Testing: {cmd.hex()}")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            ser.write(cmd)
            ser.flush()
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   ✅ Response: {response.hex()} ({response})")
                return True
            else:
                print(f"   ❌ No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"   ❌ Binary test error: {e}")
        return False

def test_different_bauds():
    """Test different baud rates."""
    print("\n3️⃣ Testing Different Baud Rates...")
    
    baud_rates = [9600, 19200, 38400, 57600, 115200]
    
    for baud in baud_rates:
        try:
            print(f"   Testing {baud} baud...")
            ser = serial.Serial('/dev/ttyUSB2', baud, timeout=1.0)
            
            # Try simple command
            ser.write(b'*IDN?\r\n')
            ser.flush()
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   ✅ {baud} baud works: {response}")
                ser.close()
                return baud
            
            ser.close()
            
        except Exception as e:
            print(f"   ❌ {baud} baud failed: {e}")
    
    return None

def check_device_state():
    """Check if device responds to basic probes."""
    print("\n4️⃣ Checking Device State...")
    
    try:
        ser = serial.Serial('/dev/ttyUSB2', 9600, timeout=1.0)
        print("   ✅ Serial port accessible")
        
        # Check if data is already coming from device
        print("   🔍 Listening for spontaneous data...")
        time.sleep(2.0)
        
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"   📊 Spontaneous data: {data.hex()} ({data})")
        else:
            print("   💤 No spontaneous data")
        
        # Try to wake up device
        wake_commands = [
            b'\r\n',          # Just newlines
            b'\x0D\x0A',      # CR LF
            b'\x1B',          # ESC
            b'\x03',          # ETX
            b'\x04',          # EOT
            b'',              # Empty
        ]
        
        for cmd in wake_commands:
            print(f"   Trying wake command: {cmd.hex()}")
            ser.write(cmd)
            ser.flush()
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   ✅ Wake response: {response}")
                break
        
        ser.close()
        
    except Exception as e:
        print(f"   ❌ Device state check error: {e}")

def main():
    print("Starting comprehensive Newport 1830-C protocol detection...")
    
    # Run all tests
    ascii_works = test_ascii_protocol()
    binary_works = test_binary_protocol()
    working_baud = test_different_bauds()
    check_device_state()
    
    print(f"\n📊 Results Summary:")
    print(f"   ASCII Protocol: {'✅ Working' if ascii_works else '❌ Failed'}")
    print(f"   Binary Protocol: {'✅ Working' if binary_works else '❌ Failed'}")
    print(f"   Working Baud Rate: {working_baud if working_baud else '❌ None found'}")
    
    if not ascii_works and not binary_works:
        print(f"\n🚨 No communication protocols working!")
        print(f"   Possible issues:")
        print(f"   - Device not powered on")
        print(f"   - Calibration module not connected") 
        print(f"   - Different communication interface needed")
        print(f"   - Device in different mode")
        print(f"   - Hardware fault")
    else:
        print(f"\n🎉 Found working communication protocol!")

if __name__ == '__main__':
    main()