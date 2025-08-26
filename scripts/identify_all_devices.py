import time

import serial


def identify_maitai(port, baudrate):
    terminators = [b"\n", b"\r", b"\r\n"]
    for term in terminators:
        try:
            with serial.Serial(port, baudrate, timeout=1) as ser:
                ser.write(b"*IDN?" + term)
                time.sleep(0.2)
                response = ser.readline().decode(errors="ignore").strip()
                if "MaiTai" in response or "Spectra Physics" in response:
                    print(
                        f"Success! MaiTai found on {port} at {baudrate} baud with terminator {term!r}"
                    )
                    return True, baudrate  # Return the working baudrate
        except serial.SerialException:
            pass
        except Exception as e:
            print(f"An error occurred on {port} at {baudrate} baud: {e}")
    return False, None


def identify_newport(port):
    try:
        with serial.Serial(port, 9600, timeout=1) as ser:
            ser.write(b"*IDN?\n")
            time.sleep(0.1)
            response = ser.readline().decode(errors="ignore").strip()
            if "Newport" in response:
                print(f"Newport found on {port}")
                return True
    except serial.SerialException:
        pass
    return False


def identify_elliptec(port):
    try:
        with serial.Serial(port, 9600, timeout=1) as ser:
            ser.write(b"2gs\n")
            time.sleep(0.1)
            response = ser.readline().decode(errors="ignore").strip()
            if response.startswith("2GS"):
                print(f"Elliptec found on {port}")
                return True
    except serial.SerialException:
        pass
    return False


def identify_esp300(port):
    baudrates = [9600, 19200, 57600, 115200]
    for baud in baudrates:
        try:
            with serial.Serial(port, baud, timeout=2) as ser:
                # ESP300 identification command
                ser.write(b"*IDN?\n")
                time.sleep(0.2)
                response = ser.readline().decode(errors="ignore").strip()
                if "ESP300" in response or "Newport" in response:
                    print(f"ESP300 found on {port} at {baud} baud")
                    return True, baud
        except serial.SerialException:
            pass
        except Exception as e:
            continue
    return False, None


if __name__ == "__main__":
    # Available USB serial ports
    ports = [
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
        "/dev/ttyUSB2",
        "/dev/ttyUSB3",
        "/dev/ttyUSB4",
        "/dev/ttyUSB5",
        "/dev/ttyUSB6",
    ]
    baudrates = [9600, 19200, 38400, 57600, 115200]

    maitai_found = False
    newport_found = False
    elliptec_found = False
    esp300_found = False
    
    # Track found configurations
    found_configs = {}

    print("=== DEVICE IDENTIFICATION SCAN ===")
    
    for port in ports:
        print(f"\nScanning {port}...")
        
        if not maitai_found:
            for baud in baudrates:
                found, working_baud = identify_maitai(port, baud)
                if found:
                    maitai_found = True
                    found_configs['maitai'] = {'port': port, 'baudrate': working_baud}
                    break
        if not newport_found:
            if identify_newport(port):
                newport_found = True
                found_configs['newport'] = {'port': port, 'baudrate': 9600}
        if not elliptec_found:
            if identify_elliptec(port):
                elliptec_found = True
                found_configs['elliptec'] = {'port': port, 'baudrate': 9600}
        if not esp300_found:
            found, baud = identify_esp300(port)
            if found:
                esp300_found = True
                found_configs['esp300'] = {'port': port, 'baudrate': baud}

    print("\n=== FINAL RESULTS ===")
    
    # Display found devices with their configurations
    if maitai_found:
        config = found_configs['maitai']
        print(f"✅ MaiTai: {config['port']} at {config['baudrate']} baud")
    else:
        print("❌ MaiTai laser not found on any port/baud combination.")
        
    if newport_found:
        config = found_configs['newport']
        print(f"✅ Newport: {config['port']} at {config['baudrate']} baud")
    else:
        print("❌ Newport power meter not found on any port.")
        
    if elliptec_found:
        config = found_configs['elliptec']
        print(f"✅ Elliptec: {config['port']} at {config['baudrate']} baud")
    else:
        print("❌ Elliptec controller not found on any port.")
        
    if esp300_found:
        config = found_configs['esp300']
        print(f"✅ ESP300: {config['port']} at {config['baudrate']} baud")
    else:
        print("❌ ESP300 motion controller not found on any port.")
    
    # Summary
    found_devices = sum([maitai_found, newport_found, elliptec_found, esp300_found])
    print(f"\n✅ Found {found_devices}/4 devices")
    
    # Configuration recommendations
    if found_devices > 0:
        print("\n=== CONFIGURATION RECOMMENDATIONS ===")
        for device, config in found_configs.items():
            print(f"{device.upper()}: port={config['port']}, baudrate={config['baudrate']}")
