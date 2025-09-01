"""
Hardware wrapper for PyVCAM compatible cameras with dynamic feature discovery.
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
import numpy as np

try:
    from pyvcam import pvc
    from pyvcam.camera import Camera
    from pyvcam.constants import (
        PARAM_EXP_TIME, PARAM_GAIN_INDEX, PARAM_PIX_TIME,
        PARAM_READOUT_PORT, PARAM_TEMP_SETPOINT
    )
    PYVCAM_AVAILABLE = True
except ImportError:
    PYVCAM_AVAILABLE = False

from pymodaq_plugins_urashg.hardware.exceptions import HardwareError

logger = logging.getLogger(__name__)


def connection_required(func: Callable):
    """Decorator to ensure the camera is connected before executing a method."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_connected():
            raise HardwareError("Camera is not connected.")
        return func(self, *args, **kwargs)
    return wrapper


class CameraWrapper:
    """A hardware wrapper for PyVCAM compatible cameras with dynamic feature discovery."""

    def __init__(self):
        if not PYVCAM_AVAILABLE:
            raise ImportError("PyVCAM is not installed. Please install it to use the camera.")
        self.camera: Optional[Camera] = None

    def connect(self):
        """Connect to the first available camera."""
        if self.is_connected():
            return
        pvc.init_pvcam()
        cameras = list(Camera.detect_camera())
        if not cameras:
            raise HardwareError("No PyVCAM cameras detected.")
        self.camera = cameras[0]
        self.camera.open()
        logger.info(f"Connected to camera: {self.camera.name}")

    def disconnect(self):
        """Disconnect from the camera."""
        if self.is_connected():
            self.camera.close()
            pvc.uninit_pvcam()
            self.camera = None
            logger.info("Camera disconnected.")

    def is_connected(self) -> bool:
        """Check if the camera is connected."""
        return self.camera is not None and self.camera.is_open

    @connection_required
    def get_frame(self, exposure_time: int) -> np.ndarray:
        """Acquire a frame from the camera."""
        return self.camera.get_frame(exp_time=exposure_time).reshape(self.camera.sensor_size)

    @connection_required
    def discover_params(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover available hardware and post-processing parameters."""
        handled_params = {PARAM_EXP_TIME, PARAM_READOUT_PORT, PARAM_PIX_TIME, PARAM_GAIN_INDEX, PARAM_TEMP_SETPOINT}
        
        advanced_params = []
        for param_enum, param_info in self.camera.params.items():
            if param_enum not in handled_params and param_info["access"] not in ["Read Only", "Unavailable"]:
                advanced_params.append(self._format_param(param_info, param_enum))

        post_processing_params = []
        if hasattr(self.camera, "post_processing_features"):
            for feature in self.camera.post_processing_features:
                post_processing_params.append(self._format_pp_feature(feature))
        
        return {"advanced": advanced_params, "post_processing": post_processing_params}

    def _format_param(self, param_info: Dict[str, Any], param_enum: Any) -> Dict[str, Any]:
        """Format a standard hardware parameter for PyMoDAQ."""
        return {
            "name": param_info["name"].replace(" ", "_").lower(),
            "title": param_info["name"],
            "type": param_info["type"].__name__.lower(),
            "value": self.camera.get_param(param_enum),
            "limits": list(param_info.get("enum_map", {}).keys()),
            "opts": {"pvc_enum": param_enum}
        }

    def _format_pp_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """Format a post-processing feature for PyMoDAQ."""
        return {
            "name": feature["name"].replace(" ", "_").lower(),
            "title": feature["name"],
            "type": feature["type"].lower(),
            "value": self.camera.get_pp_param(feature["id"]),
            "limits": feature["values"],
            "opts": {"pvc_id": feature["id"]}
        }

    @connection_required
    def set_param(self, pvc_enum: Any, value: Any):
        """Set a standard hardware parameter."""
        self.camera.set_param(pvc_enum, value)

    @connection_required
    def set_pp_param(self, pvc_id: Any, value: Any):
        """Set a post-processing parameter."""
        self.camera.set_pp_param(pvc_id, value)


class MockCameraWrapper(CameraWrapper):
    """A mock hardware wrapper for a PyVCAM compatible camera."""

    def __init__(self):
        self.sensor_size = (2048, 2048)

    def connect(self): logger.info("Mock camera connected.")
    def disconnect(self): logger.info("Mock camera disconnected.")
    def is_connected(self) -> bool: return True
    def get_frame(self, exposure_time: int) -> np.ndarray:
        return np.random.randint(0, 2**16, self.sensor_size, dtype=np.uint16)

    def discover_params(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return a predefined set of mock parameters."""
        return {
            "advanced": [{
                "name": "mock_adv_param", "title": "Mock Advanced Param", "type": "list",
                "value": "Option 1", "limits": ["Option 1", "Option 2"], "opts": {"pvc_enum": "mock_enum"}
            }],
            "post_processing": [{
                "name": "mock_pp_feature", "title": "Mock PP Feature", "type": "bool",
                "value": True, "opts": {"pvc_id": "mock_id"}
            }]
        }

    def set_param(self, pvc_enum: Any, value: Any): logger.debug(f"Mock set param {pvc_enum} to {value}")
    def set_pp_param(self, pvc_id: Any, value: Any): logger.debug(f"Mock set pp param {pvc_id} to {value}")

