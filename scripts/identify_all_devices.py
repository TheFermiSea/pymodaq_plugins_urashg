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
                if "Mai Tai" in response or "Spectra-Physics" in response:
                    print(
                        f"Success! MaiTai found on {port} at {baudrate} baud with terminator {term!r}"
                    )
                    return True
        except serial.SerialException:
            pass
        except Exception as e:
            print(f"An error occurred on {port} at {baudrate} baud: {e}")
    return False


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
            response = ser.readline().decode().strip()
            if response.startswith("2GS"):
                print(f"Elliptec found on {port}")
                return True
    except serial.SerialException:
        pass
    return False


if __name__ == "__main__":
    # Mock ports for testing
    ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"]
    baudrates = [9600, 19200, 38400, 57600, 115200]

    maitai_found = False
    newport_found = False
    elliptec_found = False

    for port in ports:
        if not maitai_found:
            for baud in baudrates:
                if identify_maitai(port, baud):
                    maitai_found = True
                    break
        if not newport_found:
            if identify_newport(port):
                newport_found = True
        if not elliptec_found:
            if identify_elliptec(port):
                elliptec_found = True

    if not maitai_found:
        print("MaiTai laser not found on any port/baud combination.")
    if not newport_found:
        print("Newport power meter not found on any port.")
    if not elliptec_found:
        print("Elliptec controller not found on any port.")
