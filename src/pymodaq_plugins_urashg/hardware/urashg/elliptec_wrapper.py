"""
Elliptec Controller Wrapper - Stub Implementation for Testing

This is a placeholder implementation for testing purposes.
The full implementation would provide Thorlabs ELL14 control.
"""


class ElliptecError(Exception):
    """Elliptec specific exception"""

    pass


class ElliptecController:
    """Stub implementation of Elliptec controller"""

    def __init__(self, ports=None):
        self.ports = ports or {}
        self.connected = False

    def connect_all(self):
        """Mock connection to all devices"""
        self.connected = True
        return True

    def disconnect_all(self):
        """Mock disconnection from all devices"""
        self.connected = False

    def set_polarization_state(self, state):
        """Mock polarization state setting"""
        if not self.connected:
            raise ElliptecError("Not connected")
        return True

    def rotate_analyzer(self, angle):
        """Mock analyzer rotation"""
        if not self.connected:
            raise ElliptecError("Not connected")
        return True
