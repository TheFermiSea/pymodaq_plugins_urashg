"""
Camera Controller Utils for URASHG Microscopy

Provides camera control interface for Photometrics PrimeBSI camera
with support for both real hardware and mock operation.
"""

import time
from typing import Optional, Tuple

import numpy as np


class CameraError(Exception):
    """Camera specific exception"""

    pass


class CameraController:
    """Legacy stub implementation of Camera controller"""

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


class CameraManager:
    """
    Advanced camera manager for URASHG CustomApp.

    Provides unified interface for Photometrics PrimeBSI camera control
    with support for real hardware and mock operation.
    """

    def __init__(self, mock_mode: bool = False):
        """
        Initialize camera manager.

        Args:
            mock_mode: If True, use mock camera for testing
        """
        self.mock_mode = mock_mode
        self.camera = None
        self.initialized = False
        self.live_view_active = False
        self.sensor_size = (2048, 2048)
        self.temperature = -20.0

        # Try to import PyVCAM for real hardware
        self.pyvcam_available = False
        if not mock_mode:
            try:
                from pyvcam import pvc
                from pyvcam.camera import Camera

                self.pyvcam_available = True
                self.pvc = pvc
                self.Camera = Camera
            except ImportError:
                print("Warning: PyVCAM not available, using mock mode")
                self.mock_mode = True

    def initialize(self) -> bool:
        """
        Initialize the camera.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self.mock_mode:
                # Mock camera initialization
                from unittest.mock import Mock

                self.camera = Mock()
                self.camera.name = "pvcamUSB_0"
                self.camera.sensor_size = self.sensor_size
                self.camera.temp = self.temperature
                self.camera.is_open = True
                self.initialized = True
                return True
            else:
                # Real hardware initialization
                if not self.pyvcam_available:
                    return False

                # Initialize PVCAM
                self.pvc.init_pvcam()

                # Detect cameras
                cameras = list(self.Camera.detect_camera())
                if len(cameras) == 0:
                    raise CameraError("No cameras detected")

                self.camera = cameras[0]
                self.camera.open()
                self.sensor_size = self.camera.sensor_size
                self.initialized = True
                return True

        except Exception as e:
            print(f"Camera initialization error: {e}")
            self.initialized = False
            return False

    def disconnect(self):
        """Disconnect from the camera."""
        try:
            if self.camera and not self.mock_mode:
                if hasattr(self.camera, "is_open") and self.camera.is_open:
                    self.camera.close()

            if not self.mock_mode and self.pyvcam_available:
                self.pvc.uninit_pvcam()

        except Exception as e:
            print(f"Warning: Error disconnecting camera: {e}")
        finally:
            self.camera = None
            self.initialized = False
            self.live_view_active = False

    def capture_image(self, exposure_ms: float = 100.0) -> Optional[np.ndarray]:
        """
        Capture a single image.

        Args:
            exposure_ms: Exposure time in milliseconds

        Returns:
            Image data as numpy array, or None if failed
        """
        if not self.initialized:
            raise CameraError("Camera not initialized")

        try:
            if self.mock_mode:
                # Generate mock image data
                height, width = self.sensor_size

                # Create realistic SHG-like image with some structure
                x = np.linspace(-1, 1, width)
                y = np.linspace(-1, 1, height)
                X, Y = np.meshgrid(x, y)

                # Gaussian beam profile with noise
                beam_profile = 1000 * np.exp(-(X**2 + Y**2) / 0.3)
                noise = np.random.poisson(
                    beam_profile + 50
                )  # Poisson noise + background

                # Add some periodic structure (like interference fringes)
                fringes = 100 * np.sin(10 * X) * np.exp(-(X**2 + Y**2) / 0.5)

                image = (noise + fringes).astype(np.uint16)

                # Simulate exposure time delay
                time.sleep(exposure_ms / 1000.0)

                return image
            else:
                # Real camera capture
                if hasattr(self.camera, "exp_time"):
                    self.camera.exp_time = int(exposure_ms)

                frame = self.camera.get_frame()

                # Reshape to 2D if needed
                if hasattr(frame, "reshape"):
                    if hasattr(self.camera, "rois") and self.camera.rois:
                        roi = self.camera.rois[0]
                        frame = frame.reshape(roi.shape)
                    else:
                        frame = frame.reshape(self.sensor_size)

                return frame

        except Exception as e:
            raise CameraError(f"Image capture failed: {e}")

    def start_live_view(self):
        """Start live view mode."""
        if not self.initialized:
            raise CameraError("Camera not initialized")

        self.live_view_active = True
        # Implementation would start continuous acquisition thread
        print("Live view started (mock implementation)")

    def stop_live_view(self):
        """Stop live view mode."""
        self.live_view_active = False
        print("Live view stopped")

    def get_temperature(self) -> Optional[float]:
        """
        Get current sensor temperature.

        Returns:
            Temperature in Celsius, or None if not available
        """
        if not self.initialized:
            return None

        try:
            if self.mock_mode:
                # Simulate temperature drift
                base_temp = -20.0
                drift = np.sin(time.time() / 30) * 0.5  # ±0.5°C drift over 1 minute
                self.temperature = base_temp + drift
                return self.temperature
            else:
                # Real hardware temperature reading
                if hasattr(self.camera, "temp"):
                    return float(self.camera.temp)
                else:
                    return None

        except Exception as e:
            print(f"Warning: Error reading temperature: {e}")
            return None

    def set_exposure(self, exposure_ms: float):
        """
        Set camera exposure time.

        Args:
            exposure_ms: Exposure time in milliseconds
        """
        if not self.initialized:
            raise CameraError("Camera not initialized")

        try:
            if not self.mock_mode and hasattr(self.camera, "exp_time"):
                self.camera.exp_time = int(exposure_ms)
        except Exception as e:
            raise CameraError(f"Failed to set exposure: {e}")

    def set_roi(self, x: int, y: int, width: int, height: int):
        """
        Set region of interest.

        Args:
            x, y: Top-left corner coordinates
            width, height: ROI dimensions
        """
        if not self.initialized:
            raise CameraError("Camera not initialized")

        try:
            if not self.mock_mode:
                # Real hardware ROI setting
                # Implementation would depend on camera API
                pass

            print(f"ROI set to ({x}, {y}, {width}, {height})")

        except Exception as e:
            raise CameraError(f"Failed to set ROI: {e}")

    def is_connected(self) -> bool:
        """Check if camera is connected and initialized."""
        return self.initialized and self.camera is not None
