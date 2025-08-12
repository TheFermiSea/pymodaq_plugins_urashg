"""
Comprehensive Mock Modules for URASHG Extension Testing

This module provides mock implementations of all hardware devices and PyMoDAQ
components needed for comprehensive testing of the URASHG extension without
requiring actual hardware.

Mock Components:
- MockMovePlugin: Mock PyMoDAQ move actuator plugins
- MockViewerPlugin: Mock PyMoDAQ viewer detector plugins
- MockDeviceManager: Mock device manager for extension testing
- MockDeviceStatus: Mock device status enumeration
- MockDeviceInfo: Mock device information structure
- Mock hardware controllers for all URASHG devices

These mocks provide realistic behavior for testing while ensuring tests
can run in any environment without hardware dependencies.
"""

import numpy as np
import time
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Mock PyMoDAQ imports (in case they're not available)
try:
    from pymodaq.utils.data import DataWithAxes, Axis, DataSource
    from pymodaq.utils.parameter import Parameter
    from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
    from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
    from pymodaq.utils.logger import set_logger, get_module_name

    PYMODAQ_AVAILABLE = True
except ImportError:
    # Create mock classes if PyMoDAQ not available
    class DataWithAxes:
        def __init__(self, name, data=None, axes=None, units=None, source=None):
            self.name = name
            self.data = data or []
            self.axes = axes or []
            self.units = units
            self.source = source

    class Axis:
        def __init__(self, name, data=None, units=None):
            self.name = name
            self.data = data
            self.units = units

    class DataSource:
        raw = "raw"

    class Parameter:
        @staticmethod
        def create(*args, **kwargs):
            return Mock()

    class DAQ_Move_base:
        pass

    class DAQ_Viewer_base:
        pass

    def set_logger(name):
        import logging

        return logging.getLogger(name)

    def get_module_name(file_path):
        return "mock_logger"

    PYMODAQ_AVAILABLE = False

# Mock Qt imports
try:
    from qtpy.QtCore import QObject, Signal

    QT_AVAILABLE = True
except ImportError:

    class QObject:
        pass

    class Signal:
        def __init__(self, *args):
            self.signal = f"mock_signal({','.join(str(arg) for arg in args)})"

        def emit(self, *args):
            pass

        def connect(self, slot):
            pass

    QT_AVAILABLE = False


# Mock device status enumeration
class MockDeviceStatus(Enum):
    """Mock device status enumeration for testing."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


# Use real enum if available, otherwise use mock
try:
    from pymodaq_plugins_urashg.extensions.device_manager import DeviceStatus
except ImportError:
    DeviceStatus = MockDeviceStatus


class MockDeviceInfo:
    """Mock device information structure."""

    def __init__(self, name: str, device_type: str, description: str = ""):
        self.name = name
        self.type = device_type
        self.description = description
        self.connected = False
        self.status = MockDeviceStatus.DISCONNECTED


class MockMovePlugin(DAQ_Move_base):
    """
    Mock PyMoDAQ move plugin for testing.

    Provides realistic behavior for move actuator plugins without
    requiring actual hardware.
    """

    # Mock PyMoDAQ plugin attributes
    params = [
        {
            "title": "Mock Settings",
            "name": "mock_settings",
            "type": "group",
            "children": [
                {
                    "title": "Device ID:",
                    "name": "device_id",
                    "type": "str",
                    "value": "mock_device",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Timeout (ms):",
                    "name": "timeout",
                    "type": "int",
                    "value": 1000,
                },
                {
                    "title": "Position (deg):",
                    "name": "position",
                    "type": "float",
                    "value": 0.0,
                    "min": -180,
                    "max": 180,
                },
            ],
        },
    ]

    _controller_units = "deg"

    def __init__(self, name: str = "MockMove"):
        super().__init__()
        self.name = name
        self.controller = None
        self.settings = {}
        self.initialized = False
        self.connected = False
        self.closed = False
        self.current_position = 0.0
        self.is_moving = False
        self.simulate_error = False

        # Mock signals
        self.status_sig = Signal(str)
        self.settings_tree = Mock()

    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.initialized = True
        self.controller = MockHardwareController(self.name)

    def get_actuator_value(self) -> float:
        """Get current actuator position."""
        if self.simulate_error:
            raise RuntimeError(f"Simulated error in {self.name}")

        return self.current_position

    def close(self):
        """Close plugin and cleanup resources."""
        self.closed = True
        self.connected = False
        if self.controller:
            self.controller.disconnect()
            self.controller = None

    def commit_settings(self, param_dict: Dict[str, Any]):
        """Apply parameter changes."""
        self.settings.update(param_dict)

        # Handle mock mode parameter
        if "mock_mode" in param_dict:
            self.mock_mode = param_dict["mock_mode"]

    def ini_stage(self, controller=None):
        """Initialize stage/actuator."""
        if controller is not None:
            self.controller = controller

        if self.controller:
            self.controller.connect()
            self.connected = True

        return "Mock stage initialized"

    def move_abs(self, position: Union[float, List[float]]):
        """Move to absolute position."""
        if self.simulate_error:
            raise RuntimeError(f"Move error in {self.name}")

        if isinstance(position, (list, np.ndarray)):
            position = position[0] if len(position) > 0 else 0.0

        self.is_moving = True
        self.current_position = float(position)

        # Simulate movement time
        time.sleep(0.01)
        self.is_moving = False

    def move_home(self, value=None):
        """Move to home position."""
        self.move_abs(0.0)

    def move_rel(self, position: Union[float, List[float]]):
        """Move relative to current position."""
        if isinstance(position, (list, np.ndarray)):
            position = position[0] if len(position) > 0 else 0.0

        new_position = self.current_position + float(position)
        self.move_abs(new_position)

    def stop_motion(self):
        """Stop current motion."""
        self.is_moving = False

    def get_settings(self) -> Dict[str, Any]:
        """Get current plugin settings."""
        return {
            "device_id": getattr(self, "device_id", "mock_device"),
            "mock_mode": getattr(self, "mock_mode", True),
            "timeout": getattr(self, "timeout", 1000),
            "position": self.current_position,
        }


class MockViewerPlugin(DAQ_Viewer_base):
    """
    Mock PyMoDAQ viewer plugin for testing.

    Provides realistic behavior for detector/viewer plugins without
    requiring actual hardware.
    """

    # Mock PyMoDAQ plugin attributes
    params = [
        {
            "title": "Mock Detector Settings",
            "name": "detector_settings",
            "type": "group",
            "children": [
                {
                    "title": "Device ID:",
                    "name": "device_id",
                    "type": "str",
                    "value": "mock_detector",
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": True,
                },
                {
                    "title": "Integration Time (ms):",
                    "name": "integration_time",
                    "type": "int",
                    "value": 100,
                },
                {
                    "title": "Gain:",
                    "name": "gain",
                    "type": "float",
                    "value": 1.0,
                    "min": 0.1,
                    "max": 10.0,
                },
            ],
        },
    ]

    _controller_units = "counts"

    def __init__(self, name: str = "MockViewer"):
        super().__init__()
        self.name = name
        self.controller = None
        self.settings = {}
        self.initialized = False
        self.connected = False
        self.closed = False
        self.simulate_error = False

        # Mock signals
        self.status_sig = Signal(str)
        self.settings_tree = Mock()

        # Data generation parameters
        self.data_shape = (
            (100, 100)
            if "2D" in name or "Camera" in name or "Prime" in name
            else (100,)
        )
        self.data_type = (
            np.uint16 if "Camera" in name or "Prime" in name else np.float64
        )

    def ini_attributes(self):
        """Initialize plugin attributes."""
        self.initialized = True
        self.controller = MockDetectorController(self.name)

    def grab_data(self) -> List[DataWithAxes]:
        """Acquire data from detector."""
        if self.simulate_error:
            raise RuntimeError(f"Acquisition error in {self.name}")

        # Generate mock data based on detector type
        if len(self.data_shape) == 2:
            # 2D detector (camera)
            data = np.random.randint(0, 4096, self.data_shape, dtype=self.data_type)
            axes = [
                Axis("x", data=np.arange(self.data_shape[1]), units="pixel"),
                Axis("y", data=np.arange(self.data_shape[0]), units="pixel"),
            ]
        else:
            # 1D or 0D detector
            if "Power" in self.name or "Newport" in self.name:
                # Power meter - single value
                data = np.array([np.random.exponential(1.0) * 1e-3])  # mW
                axes = []
            else:
                # Generic 1D detector
                data = np.random.normal(1000, 100, self.data_shape).astype(
                    self.data_type
                )
                axes = [Axis("x", data=np.arange(self.data_shape[0]), units="index")]

        data_with_axes = DataWithAxes(
            self.name,
            data=[data],
            axes=axes,
            units=self._controller_units,
            source=DataSource.raw,
        )

        return [data_with_axes]

    def close(self):
        """Close plugin and cleanup resources."""
        self.closed = True
        self.connected = False
        if self.controller:
            self.controller.disconnect()
            self.controller = None

    def commit_settings(self, param_dict: Dict[str, Any]):
        """Apply parameter changes."""
        self.settings.update(param_dict)

        # Handle specific parameters
        if "integration_time" in param_dict:
            self.integration_time = param_dict["integration_time"]
        if "gain" in param_dict:
            self.gain = param_dict["gain"]

    def ini_detector(self, controller=None):
        """Initialize detector."""
        if controller is not None:
            self.controller = controller

        if self.controller:
            self.controller.connect()
            self.connected = True

        return "Mock detector initialized"

    def get_settings(self) -> Dict[str, Any]:
        """Get current plugin settings."""
        return {
            "device_id": getattr(self, "device_id", "mock_detector"),
            "mock_mode": getattr(self, "mock_mode", True),
            "integration_time": getattr(self, "integration_time", 100),
            "gain": getattr(self, "gain", 1.0),
        }


class MockHardwareController:
    """Mock hardware controller for move devices."""

    def __init__(self, name: str):
        self.name = name
        self.connected = False
        self.position = 0.0

    def connect(self):
        """Connect to hardware."""
        self.connected = True

    def disconnect(self):
        """Disconnect from hardware."""
        self.connected = False

    def move_absolute(self, position: float):
        """Move to absolute position."""
        if not self.connected:
            raise RuntimeError("Not connected")
        self.position = position

    def get_position(self) -> float:
        """Get current position."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return self.position


class MockDetectorController:
    """Mock detector controller for viewer devices."""

    def __init__(self, name: str):
        self.name = name
        self.connected = False
        self.integration_time = 100
        self.gain = 1.0

    def connect(self):
        """Connect to detector."""
        self.connected = True

    def disconnect(self):
        """Disconnect from detector."""
        self.connected = False

    def acquire_data(self) -> np.ndarray:
        """Acquire data from detector."""
        if not self.connected:
            raise RuntimeError("Not connected")

        # Generate mock data
        if "Camera" in self.name or "Prime" in self.name:
            return np.random.randint(0, 4096, (512, 512), dtype=np.uint16)
        else:
            return np.array([np.random.exponential(1.0)])


class MockDeviceManager(QObject):
    """
    Mock device manager for extension testing.

    Provides realistic device coordination without requiring actual hardware.
    """

    # Mock signals
    device_status_changed = Signal(str, str)
    device_error_occurred = Signal(str, str)
    all_devices_ready = Signal()
    device_data_updated = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.devices = {}
        self.device_status = {}
        self.device_info = {}

        # Initialize mock devices
        self._initialize_mock_devices()

    def _initialize_mock_devices(self):
        """Initialize mock devices for testing."""
        # Mock move devices
        self.devices["MaiTai"] = MockMovePlugin("MaiTai")
        self.devices["Elliptec"] = MockMovePlugin("Elliptec")
        self.devices["ESP300"] = MockMovePlugin("ESP300")

        # Mock viewer devices
        self.devices["PrimeBSI"] = MockViewerPlugin("PrimeBSI")
        self.devices["Newport1830C"] = MockViewerPlugin("Newport1830C")

        # Initialize status
        for device_name in self.devices:
            self.device_status[device_name] = MockDeviceStatus.DISCONNECTED
            self.device_info[device_name] = MockDeviceInfo(
                device_name,
                "Move" if device_name in ["MaiTai", "Elliptec", "ESP300"] else "Viewer",
                f"Mock {device_name} device for testing",
            )

    def register_device(self, name: str, device):
        """Register a device with the manager."""
        self.devices[name] = device
        self.device_status[name] = MockDeviceStatus.DISCONNECTED

    def unregister_device(self, name: str):
        """Unregister a device from the manager."""
        if name in self.devices:
            del self.devices[name]
        if name in self.device_status:
            del self.device_status[name]

    def get_device(self, name: str):
        """Get device by name."""
        return self.devices.get(name)

    def update_device_status(self, device_name: str, status: str):
        """Update device status."""
        if device_name in self.device_status:
            self.device_status[device_name] = status
            self.device_status_changed.emit(device_name, status)

    def get_device_status(self, device_name: str):
        """Get device status."""
        return self.device_status.get(device_name, MockDeviceStatus.DISCONNECTED)

    def get_all_device_status(self) -> Dict[str, str]:
        """Get all device statuses."""
        return {name: str(status.value) for name, status in self.device_status.items()}

    def are_all_devices_ready(self) -> bool:
        """Check if all devices are ready."""
        return all(
            status == MockDeviceStatus.READY for status in self.device_status.values()
        )

    def is_device_ready(self, device_name: str) -> bool:
        """Check if specific device is ready."""
        return self.device_status.get(device_name) == MockDeviceStatus.READY

    def emergency_stop_all(self):
        """Emergency stop all devices."""
        for device in self.devices.values():
            if hasattr(device, "stop_motion"):
                device.stop_motion()

    def initialize_plugins(self):
        """Initialize all plugins."""
        for device_name, device in self.devices.items():
            try:
                device.ini_attributes()
                if hasattr(device, "ini_stage"):
                    device.ini_stage()
                elif hasattr(device, "ini_detector"):
                    device.ini_detector()

                self.update_device_status(device_name, MockDeviceStatus.READY.value)
            except Exception as e:
                self.update_device_status(device_name, MockDeviceStatus.ERROR.value)
                self.device_error_occurred.emit(device_name, str(e))

    def cleanup_plugins(self):
        """Cleanup all plugins."""
        for device in self.devices.values():
            try:
                device.close()
            except Exception:
                pass

    def coordinate_devices(self, operations: Dict[str, Any]):
        """Coordinate multiple device operations."""
        for device_name, operation in operations.items():
            if device_name in self.devices:
                device = self.devices[device_name]
                # Execute operation on device
                if "move" in operation and hasattr(device, "move_abs"):
                    device.move_abs(operation["move"])
                elif "acquire" in operation and hasattr(device, "grab_data"):
                    device.grab_data()

    def get_plugin_data(self, device_name: str):
        """Get data from a plugin."""
        device = self.devices.get(device_name)
        if device and hasattr(device, "grab_data"):
            return device.grab_data()
        elif device and hasattr(device, "get_actuator_value"):
            return device.get_actuator_value()
        return None

    def set_plugin_parameters(self, device_name: str, parameters: Dict[str, Any]):
        """Set plugin parameters."""
        device = self.devices.get(device_name)
        if device and hasattr(device, "commit_settings"):
            device.commit_settings(parameters)


# Specific mock devices for URASHG system
class MockMaiTaiLaser(MockMovePlugin):
    """Mock MaiTai laser controller."""

    def __init__(self):
        super().__init__("MaiTai")
        self._controller_units = "nm"
        self.wavelength = 800.0
        self.shutter_open = False

    def move_abs(self, wavelength: float):
        """Set laser wavelength."""
        if 700 <= wavelength <= 1000:
            self.wavelength = wavelength
            self.current_position = wavelength
        else:
            raise ValueError("Wavelength out of range")

    def get_actuator_value(self) -> float:
        """Get current wavelength."""
        return self.wavelength

    def open_shutter(self):
        """Open laser shutter."""
        self.shutter_open = True

    def close_shutter(self):
        """Close laser shutter."""
        self.shutter_open = False


class MockElliptecRotator(MockMovePlugin):
    """Mock Elliptec rotation mount."""

    def __init__(self, address: int = 0):
        super().__init__(f"Elliptec_{address}")
        self.address = address
        self._controller_units = "deg"
        self.angle = 0.0

    def move_abs(self, angle: float):
        """Rotate to absolute angle."""
        self.angle = angle % 360
        self.current_position = self.angle

    def get_actuator_value(self) -> float:
        """Get current angle."""
        return self.angle


class MockPrimeBSICamera(MockViewerPlugin):
    """Mock Photometrics Prime BSI camera."""

    def __init__(self):
        super().__init__("PrimeBSI")
        self._controller_units = "counts"
        self.exposure_time = 100  # ms
        self.gain = 1
        self.roi = (0, 0, 2048, 2048)

    def grab_data(self) -> List[DataWithAxes]:
        """Acquire camera image."""
        width, height = self.roi[2] - self.roi[0], self.roi[3] - self.roi[1]

        # Generate realistic SHG-like image
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        center_x, center_y = width // 2, height // 2

        # Gaussian beam profile with some noise
        beam_profile = np.exp(
            -((x - center_x) ** 2 + (y - center_y) ** 2) / (2 * (width / 8) ** 2)
        )
        noise = np.random.poisson(10, (height, width))
        image = (beam_profile * 1000 + noise).astype(np.uint16)

        data_with_axes = DataWithAxes(
            "PrimeBSI",
            data=[image],
            axes=[
                Axis("x", data=np.arange(width), units="pixel"),
                Axis("y", data=np.arange(height), units="pixel"),
            ],
            units="counts",
            source=DataSource.raw,
        )

        return [data_with_axes]


class MockNewportPowerMeter(MockViewerPlugin):
    """Mock Newport 1830-C power meter."""

    def __init__(self):
        super().__init__("Newport1830C")
        self._controller_units = "W"
        self.wavelength = 800.0
        self.power_level = 1e-3  # 1 mW

    def grab_data(self) -> List[DataWithAxes]:
        """Read power measurement."""
        # Simulate power measurement with noise
        power = self.power_level * (1 + np.random.normal(0, 0.05))
        power = max(0, power)  # No negative power

        data_with_axes = DataWithAxes(
            "Newport1830C",
            data=[np.array([power])],
            axes=[],
            units="W",
            source=DataSource.raw,
        )

        return [data_with_axes]

    def set_wavelength(self, wavelength: float):
        """Set wavelength for power meter calibration."""
        self.wavelength = wavelength


# Export all mock classes
__all__ = [
    "MockDeviceStatus",
    "MockDeviceInfo",
    "MockMovePlugin",
    "MockViewerPlugin",
    "MockDeviceManager",
    "MockHardwareController",
    "MockDetectorController",
    "MockMaiTaiLaser",
    "MockElliptecRotator",
    "MockPrimeBSICamera",
    "MockNewportPowerMeter",
]
