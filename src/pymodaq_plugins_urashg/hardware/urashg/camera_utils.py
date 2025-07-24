"""
Camera Controller Utils - Stub Implementation for Testing

This is a placeholder implementation for testing purposes.
The full implementation would provide Photometrics camera utilities.
"""


class CameraError(Exception):
    """Camera specific exception"""

    pass


class CameraController:
    """Stub implementation of Camera controller"""

    def __init__(self):
        self.initialized = False

    def initialize(self):
        """Mock camera initialization"""
        self.initialized = True
        return True

    def set_roi(self, x, y, width, height):
        """Mock ROI setting"""
        if not self.initialized:
            raise CameraError("Not initialized")
        return True

    def acquire_with_roi_integration(self):
        """Mock acquisition with ROI integration"""
        if not self.initialized:
            raise CameraError("Not initialized")
        return None, 0.0
