"""
MaiTai Laser Controller - Stub Implementation for Testing

This is a placeholder implementation for testing purposes.
The full implementation would provide MaiTai laser control.
"""


class MaiTaiError(Exception):
    """MaiTai specific exception"""

    pass


class MaiTaiController:
    """Stub implementation of MaiTai controller"""

    def __init__(self):
        self.connected = False
        self.power_mw = 0.0

    def connect(self):
        """Mock connection"""
        self.connected = True
        return True

    def disconnect(self):
        """Mock disconnection"""
        self.connected = False

    def set_power_setpoint(self, power_mw):
        """Mock power setting"""
        if not self.connected:
            raise MaiTaiError("Not connected")
        self.power_mw = power_mw
        return True

    def get_current_power(self):
        """Mock current power reading"""
        if not self.connected:
            raise MaiTaiError("Not connected")
        return self.power_mw
