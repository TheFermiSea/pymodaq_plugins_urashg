"""Mock PyVCAM module for camera testing"""

import numpy as np


class MockCamera:
    """Mock camera for testing"""

    def __init__(self):
        self.name = "Prime BSI Mock Camera"
        self.is_open = False
        self.sensor_size = (2048, 2048)
        self.roi = (0, 0, 2048, 2048)
        self.readout_ports = ["Port 1", "Port 2"]
        self.speed_table_size = 3
        self.gains = [1, 2, 4]
        self.readout_port = "Port 1"
        self.speed_table_index = 1
        self.gain = 1
        self.temp = -10.0
        self.temp_setpoint = -10
        self.trigger_mode = TriggerMode.INTERNAL
        self.clear_mode = ClearMode.PRE_SEQUENCE
        self.params = {}
        self.post_processing_features = []

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def get_frame(self, exp_time=100):
        """Generate mock frame data"""
        size = self.roi[2] * self.roi[3]
        # Generate realistic camera noise pattern
        frame = np.random.poisson(100, size) + np.random.normal(10, 5, size)
        return np.clip(frame, 0, 65535).astype(np.uint16)

    def get_param(self, param_id):
        """Get parameter value"""
        return self.params.get(param_id, 0)

    def set_param(self, param_id, value):
        """Set parameter value"""
        self.params[param_id] = value

    def get_pp_param(self, param_id):
        """Get post-processing parameter"""
        return 0

    def set_pp_param(self, param_id, value):
        """Set post-processing parameter"""
        pass


class Camera:
    """Mock Camera class"""

    @staticmethod
    def detect_camera():
        """Detect mock cameras"""
        yield MockCamera()


class TriggerMode:
    INTERNAL = "Internal"
    EXTERNAL = "External"


class ClearMode:
    PRE_SEQUENCE = "Pre-Sequence"
    POST_SEQUENCE = "Post-Sequence"


class Param:
    EXP_TIME = "exp_time"
    READOUT_PORT = "readout_port"
    PIX_TIME = "pix_time"
    GAIN_INDEX = "gain_index"
    TEMP_SETPOINT = "temp_setpoint"


class pvc:
    @staticmethod
    def init_pvcam():
        """Initialize mock PVCAM"""
        pass

    @staticmethod
    def uninit_pvcam():
        """Uninitialize mock PVCAM"""
        pass
