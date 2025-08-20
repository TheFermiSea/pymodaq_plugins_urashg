"""Mock serial module for testing PyMoDAQ plugins without hardware"""


class SerialException(Exception):
    """Mock serial exception"""

    pass


EIGHTBITS = 8
PARITY_NONE = "N"
STOPBITS_ONE = 1


class Serial:
    """Mock serial port for testing"""

    def __init__(self, port, baudrate=9600, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._buffer = b""
        self._write_history = []

    def write(self, data):
        """Mock write operation"""
        self._write_history.append(data)
        return len(data)

    def readline(self):
        """Mock readline - returns test responses"""
        if self._write_history:
            last_cmd = self._write_history[-1].decode("utf-8", errors="ignore").lower()

            # Elliptec device responses
            if "in" in last_cmd:
                return b"2IN0F14290000602019050105016800000004000\n"
            elif "gp" in last_cmd:
                return b"2PO00000000\n"
            elif "gs" in last_cmd:
                return b"2GS00\n"
            elif "ma" in last_cmd:
                return b"2MA\n"
            elif "ho" in last_cmd:
                return b"2HO1\n"

            # MaiTai responses
            elif "wavelength" in last_cmd:
                return b"800.0\n"
            elif "power" in last_cmd:
                return b"1.5\n"
            elif "stb" in last_cmd:
                return b"66\n"  # Status byte with modelocking

        return b"\n"

    def reset_input_buffer(self):
        """Mock buffer reset"""
        self._buffer = b""

    def close(self):
        """Mock close operation"""
        self.is_open = False
