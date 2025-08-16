import numpy as np
from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base,
    comon_parameters,
)
from pymodaq.utils.daq_utils import ThreadCommand

# Removed unused imports: get_param_path, iter_children
from pymodaq.utils.data import Axis, DataToExport, DataWithAxes
from pymodaq.utils.logger import get_module_name, set_logger
from pymodaq.utils.parameter import Parameter
from pymodaq_data import DataSource

logger = set_logger(get_module_name(__file__))

# Try to import PyVCAM and handle the case where it's not installed
try:
    from pyvcam import pvc
    from pyvcam.camera import Camera

    PYVCAM_AVAILABLE = True
except ImportError as e:
    print(f"PyVCAM import error: {e}")
    PYVCAM_AVAILABLE = False

    # Define dummy classes to avoid crashing on import if pyvcam is missing
    class Camera:
        @staticmethod
        def detect_camera():
            return iter([])

    class TriggerMode:
        INTERNAL = "Internal"

    class ClearMode:
        PRE_SEQUENCE = "Pre-Sequence"

    class Param:
        EXP_TIME = None
        READOUT_PORT = None
        PIX_TIME = None
        GAIN_INDEX = None
        TEMP_SETPOINT = None


class DAQ_2DViewer_PrimeBSI(DAQ_Viewer_base):
    """
    PyMoDAQ Plugin for Photometrics Prime BSI and other PVCAM-compatible cameras.
    This plugin interfaces with the camera using the official PyVCAM library.
    It supports:
    - Live acquisition and single-shot captures.
    - Dynamic querying of camera features, including post-processing and advanced parameters.
    - Control over exposure, gain, readout speed, and triggering.
    - Dynamic ROI selection and on-the-fly intensity integration for 0D data export.
    """

    params = comon_parameters + [
        # Settings group with multiaxes (required by PyMoDAQ)
        {
            "title": "Settings",
            "name": "Settings",
            "type": "group",
            "children": [
                {
                    "title": "Multi-axes",
                    "name": "multiaxes",
                    "type": "group",
                    "children": [
                        {
                            "title": "Is Multi-axes:",
                            "name": "is_multiaxes",
                            "type": "bool",
                            "value": False,
                            "readonly": True,
                        },
                        {
                            "title": "Status:",
                            "name": "multi_status",
                            "type": "list",
                            "value": "Single",
                            "values": ["Single"],
                            "readonly": True,
                        },
                    ],
                },
                {
                    "title": "Mock Mode:",
                    "name": "mock_mode",
                    "type": "bool",
                    "value": True,
                },
            ],
        },
        {
            "title": "Camera Settings",
            "name": "camera_settings",
            "type": "group",
            "children": [
                {
                    "title": "Camera Name:",
                    "name": "camera_name",
                    "type": "str",
                    "value": "",
                    "readonly": True,
                },
                {
                    "title": "Sensor Size:",
                    "name": "sensor_size",
                    "type": "str",
                    "value": "",
                    "readonly": True,
                },
                {
                    "title": "Exposure (ms):",
                    "name": "exposure",
                    "type": "float",
                    "value": 10.0,
                    "min": 0.01,
                },
                {
                    "title": "Readout Port:",
                    "name": "readout_port",
                    "type": "list",
                    "limits": [],
                },
                {
                    "title": "Speed Index:",
                    "name": "speed_index",
                    "type": "list",
                    "limits": [],
                },
                {
                    "title": "Gain:",
                    "name": "gain",
                    "type": "list",
                    "limits": [],
                },
                {
                    "title": "Trigger Mode:",
                    "name": "trigger_mode",
                    "type": "list",
                    "limits": [],
                },
                {
                    "title": "Clear Mode:",
                    "name": "clear_mode",
                    "type": "list",
                    "limits": [],
                },
                {
                    "title": "Temperature (°C):",
                    "name": "temperature",
                    "type": "float",
                    "readonly": True,
                },
                {
                    "title": "Temp. Setpoint (°C):",
                    "name": "temperature_setpoint",
                    "type": "int",
                    "value": -20,
                },
            ],
        },
        {
            "title": "Advanced Settings",
            "name": "advanced_settings",
            "type": "group",
            "children": [],
        },
        {
            "title": "Post-Processing",
            "name": "post_processing",
            "type": "group",
            "children": [],
        },
        {
            "title": "ROI Settings",
            "name": "roi_settings",
            "type": "group",
            "children": [
                {
                    "title": "Enable ROI Integration",
                    "name": "roi_integration",
                    "type": "bool",
                    "value": True,
                },
            ],
        },
    ]

    # PyMoDAQ 5 handles common parameters differently
    # Common parameters are automatically added by the base class
    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.camera: Camera = None
        self.x_axis = None
        self.y_axis = None

    def ini_detector(self, controller=None):
        """
        Initializes the camera connection and populates the GUI with all camera-specific parameters.
        """
        self.status.update(msg="Initializing Camera...", busy=True)
        # Check if mock mode is enabled
        mock_mode = self.settings.child("Settings", "mock_mode").value()
        try:
            if mock_mode:
                # Initialize mock camera
                self.camera = self._create_mock_camera()
                self.status.update(msg="Mock Camera Initialized.", busy=False)
                # Update camera parameters for mock mode
                self.update_camera_params()
                self.initialized = True
                return self.status
            else:
                # Ensure clean PVCAM state - safely uninitialize if needed
                try:
                    if pvc.get_cam_total() >= 0:  # Check if already initialized
                        pvc.uninit_pvcam()
                except:
                    pass  # PVCAM not initialized or other state issues
                # Fresh initialization
                pvc.init_pvcam()
                # Check camera availability
                total_cams = pvc.get_cam_total()
                if total_cams == 0:
                    raise RuntimeError("No cameras found by PVCAM")
                cameras = list(Camera.detect_camera())
                if len(cameras) == 0:
                    raise RuntimeError(
                        "No cameras detected by PyVCAM Camera.detect_camera()"
                    )

                self.camera = cameras[0]  # Use first camera
                self.camera.open()
                self.status.update(
                    msg=f"Camera {self.camera.name} Initialized.", busy=False
                )

            self.update_camera_params()

            # Only populate advanced params if not in mock mode or if camera has the necessary attributes
            try:
                if not mock_mode:
                    self.populate_advanced_params()
                    self.populate_post_processing_params()
            except Exception as e:
                logger.warning(f"Could not populate advanced parameters: {e}")

            self.initialized = True
            return self.status

        except Exception as e:
            error_msg = f"Camera Initialization Failed: {str(e)}"
            self.status.update(msg=error_msg, busy=False)
            self.initialized = False
            return self.status

    def _create_mock_camera(self):
        """Create a mock camera for testing purposes."""

        class MockROI:
            def __init__(self):
                self.s1 = 0
                self.s2 = 2047
                self.p1 = 0
                self.p2 = 2047
                self.shape = (2048, 2048)

        class MockCamera:
            def __init__(self):
                self.name = "Mock Prime BSI Camera"
                self.sensor_size = (2048, 2048)
                self.is_open = True
                self.temp = -20.0
                self.temp_setpoint = -20

                # PyVCAM-compatible attributes
                self.readout_ports = {"Port 1": 0, "Port 2": 1}
                self.readout_port = 0
                self.speed = 0
                self.gain = 1
                self.gain_name = "Full well"

                # Exposure and trigger modes
                self.exp_mode = 1792
                self.exp_modes = {"Internal": 1792, "External": 2304}
                self.clear_mode = 0
                self.clear_modes = {"Auto": 0, "Never": 1}

                # Port speed gain table structure
                self.port_speed_gain_table = {
                    "Port 1": {
                        "Speed_0": {
                            "speed_index": 0,
                            "pixel_time": 5,
                            "bit_depth": 11,
                            "Full well": {"gain_index": 1},
                            "Balanced": {"gain_index": 2},
                        }
                    }
                }

                # ROI structure
                self.rois = [MockROI()]
                self.exp_time = 100

            def open(self):
                self.is_open = True

            def close(self):
                self.is_open = False

            def get_frame(self, exp_time=100, clear_mode=None, trigger_mode=None):
                import numpy as np

                if exp_time:
                    self.exp_time = exp_time
                # Return mock image data that matches the ROI shape
                return np.random.randint(
                    0, 4096, self.sensor_size[0] * self.sensor_size[1], dtype=np.uint16
                )

            def start_live(self, exp_time=100):
                pass

            def stop_live(self):
                pass

            def poll_frame(self):
                return {"pixel_data": self.get_frame()}

        return MockCamera()

    def update_camera_params(self):
        """
        Queries the connected camera for its primary capabilities and updates the main settings panel.
        """
        if self.camera is None:
            return

        try:
            self.settings.child("camera_settings", "camera_name").setValue(
                self.camera.name
            )
            sensor_size = f"{self.camera.sensor_size[0]} x {self.camera.sensor_size[1]}"
            self.settings.child("camera_settings", "sensor_size").setValue(sensor_size)

            # Set readout port limits
            if hasattr(self.camera, "readout_ports") and self.camera.readout_ports:
                readout_port_names = list(self.camera.readout_ports.keys())
                self.settings.child("camera_settings", "readout_port").setLimits(
                    readout_port_names
                )

                # Get available speeds from current port
                current_port = self.camera.readout_port
                port_name = list(self.camera.readout_ports.keys())[
                    list(self.camera.readout_ports.values()).index(current_port)
                ]
                if (
                    hasattr(self.camera, "port_speed_gain_table")
                    and port_name in self.camera.port_speed_gain_table
                ):
                    port_info = self.camera.port_speed_gain_table[port_name]
                    speed_names = [
                        k for k in port_info.keys() if k.startswith("Speed_")
                    ]
                    self.settings.child("camera_settings", "speed_index").setLimits(
                        speed_names
                    )

                    # Get available gains for current speed
                    current_speed_name = f"Speed_{self.camera.speed}"
                    if current_speed_name in port_info:
                        speed_info = port_info[current_speed_name]
                        gain_names = [
                            k
                            for k in speed_info.keys()
                            if k
                            not in [
                                "speed_index",
                                "pixel_time",
                                "bit_depth",
                                "gain_range",
                            ]
                        ]
                        self.settings.child("camera_settings", "gain").setLimits(
                            gain_names
                        )

            # Set trigger and clear mode limits
            if hasattr(self.camera, "exp_modes") and self.camera.exp_modes:
                self.settings.child("camera_settings", "trigger_mode").setLimits(
                    list(self.camera.exp_modes.keys())
                )
            if hasattr(self.camera, "clear_modes") and self.camera.clear_modes:
                self.settings.child("camera_settings", "clear_mode").setLimits(
                    list(self.camera.clear_modes.keys())
                )

            # Set current values
            if hasattr(self.camera, "readout_port"):
                port_name = list(self.camera.readout_ports.keys())[
                    list(self.camera.readout_ports.values()).index(
                        self.camera.readout_port
                    )
                ]
                self.settings.child("camera_settings", "readout_port").setValue(
                    port_name
                )

            if hasattr(self.camera, "speed"):
                self.settings.child("camera_settings", "speed_index").setValue(
                    f"Speed_{self.camera.speed}"
                )

            if hasattr(self.camera, "gain_name"):
                self.settings.child("camera_settings", "gain").setValue(
                    self.camera.gain_name
                )

            if hasattr(self.camera, "exp_mode") and hasattr(self.camera, "exp_modes"):
                for mode_name, mode_value in self.camera.exp_modes.items():
                    if mode_value == self.camera.exp_mode:
                        self.settings.child("camera_settings", "trigger_mode").setValue(
                            mode_name
                        )
                        break

            if hasattr(self.camera, "clear_mode") and hasattr(
                self.camera, "clear_modes"
            ):
                for mode_name, mode_value in self.camera.clear_modes.items():
                    if mode_value == self.camera.clear_mode:
                        self.settings.child("camera_settings", "clear_mode").setValue(
                            mode_name
                        )
                        break

            if hasattr(self.camera, "temp_setpoint"):
                self.settings.child("camera_settings", "temperature_setpoint").setValue(
                    self.camera.temp_setpoint
                )

            self.x_axis = self.get_xaxis()
            self.y_axis = self.get_yaxis()

        except Exception as e:
            logger.error(f"Error updating camera parameters: {e}")
            # Continue with basic initialization even if parameter update fails

    def _create_param_from_feature(self, feature, is_post_processing=False):
        """Helper function to create a PyMoDAQ Parameter from a PyVCAM feature dictionary."""
        param_dict = {
            "title": feature["name"] + ":",
            "name": feature["name"].replace(" ", "_").lower(),
            "readonly": feature["access"] == "Read Only",
        }

        if is_post_processing:
            param_dict["opts"] = {"pvc_id": feature["id"]}
            current_value = self.camera.get_pp_param(feature["id"])
        else:  # Is a general parameter
            param_dict["opts"] = {"pvc_enum": feature["id"]}
            current_value = self.camera.get_param(feature["id"])

        if feature["type"] == "Enum":
            param_dict["type"] = "list"
            param_dict["limits"] = feature["values"]
            param_dict["value"] = feature["values"][
                current_value
            ]  # Enum value is an index
        elif feature["type"] == "Boolean":
            param_dict["type"] = "bool"
            param_dict["value"] = current_value
        elif feature["type"] in [
            "Integer",
            "Long",
            "Unsigned Integer",
            "Unsigned Long",
        ]:
            param_dict["type"] = "int"
            param_dict["value"] = current_value
            param_dict["min"] = feature["min"]
            param_dict["max"] = feature["max"]
        elif feature["type"] == "Float":
            param_dict["type"] = "float"
            param_dict["value"] = current_value
            param_dict["min"] = feature["min"]
            param_dict["max"] = feature["max"]
        else:
            return None  # Skip unsupported types

        return Parameter.create(**param_dict)

    def populate_advanced_params(self):
        """Dynamically discovers and creates GUI controls for general camera features."""
        adv_group = self.settings.child("advanced_settings")
        for child in adv_group.children():
            child.remove()

        # Set of parameters already handled in the main 'Camera Settings' group
        if PYVCAM_AVAILABLE:
            from pyvcam.constants import (
                PARAM_EXP_TIME,
                PARAM_GAIN_INDEX,
                PARAM_PIX_TIME,
                PARAM_READOUT_PORT,
                PARAM_TEMP_SETPOINT,
            )

            handled_params = {
                PARAM_EXP_TIME,
                PARAM_READOUT_PORT,
                PARAM_PIX_TIME,
                PARAM_GAIN_INDEX,
                PARAM_TEMP_SETPOINT,
            }
        else:
            handled_params = set()

        if hasattr(self.camera, "params"):
            for param_enum, param_info in self.camera.params.items():
                if param_enum in handled_params or param_info["access"] in [
                    "Read Only",
                    "Unavailable",
                ]:
                    continue

                # PyVCAM param_info is slightly different from post_processing_features
                feature_dict = {
                    "name": param_info["name"],
                    "access": param_info["access"],
                    "type": param_info["type"].__name__,
                    "id": param_enum,
                    "values": param_info.get("enum_map", {}).keys(),
                    "min": param_info.get("min"),
                    "max": param_info.get("max"),
                }

                new_param = self._create_param_from_feature(
                    feature_dict, is_post_processing=False
                )
                if new_param:
                    adv_group.addChild(new_param)

    def populate_post_processing_params(self):
        """Dynamically discovers and creates GUI controls for post-processing features."""
        post_proc_group = self.settings.child("post_processing")
        for child in post_proc_group.children():
            child.remove()

        if not hasattr(self.camera, "post_processing_features"):
            return

        for feature in self.camera.post_processing_features:
            new_param = self._create_param_from_feature(
                feature, is_post_processing=True
            )
            if new_param:
                post_proc_group.addChild(new_param)

    def close(self):
        """Closes the camera connection and uninitializes the PVCAM library."""
        try:
            if (
                self.camera is not None
                and hasattr(self.camera, "is_open")
                and self.camera.is_open
            ):
                self.camera.close()
        except Exception as e:
            logger.warning(f"Error closing camera: {e}")

        # Only uninitialize PVCAM if it's available and we're not in mock mode
        try:
            mock_mode = self.settings.child("Settings", "mock_mode").value()
            if not mock_mode and PYVCAM_AVAILABLE:
                pvc.uninit_pvcam()
        except Exception as e:
            logger.warning(f"Error uninitializing PVCAM: {e}")

    def commit_settings(self, param: Parameter):
        """Applies a changed setting to the camera hardware."""
        try:
            # Handle standard camera settings
            if param.name() == "exposure":
                self.camera.exp_time = int(param.value())
            elif param.name() == "readout_port":
                self.camera.readout_port = param.value()
                # Update speed limits when port changes
                current_port = param.value()
                port_name = list(self.camera.readout_ports.keys())[
                    list(self.camera.readout_ports.values()).index(current_port)
                ]
                port_info = self.camera.port_speed_gain_table[port_name]
                speed_names = [k for k in port_info.keys() if k.startswith("Speed_")]
                self.settings.child("camera_settings", "speed_index").setLimits(
                    speed_names
                )
            elif param.name() == "speed_index":
                # Extract speed index from Speed_X format
                speed_index = int(param.value().split("_")[1])
                self.camera.speed = speed_index
            elif param.name() == "gain":
                # Find gain_index from gain name
                current_port = self.camera.readout_port
                port_name = list(self.camera.readout_ports.keys())[
                    list(self.camera.readout_ports.values()).index(current_port)
                ]
                port_info = self.camera.port_speed_gain_table[port_name]
                speed_info = port_info[f"Speed_{self.camera.speed}"]
                if param.value() in speed_info:
                    self.camera.gain = speed_info[param.value()]["gain_index"]
            elif param.name() == "trigger_mode":
                self.camera.exp_mode = self.camera.exp_modes[param.value()]
            elif param.name() == "clear_mode":
                self.camera.clear_mode = self.camera.clear_modes[param.value()]
            elif param.name() == "temperature_setpoint":
                self.camera.temp_setpoint = param.value()

            # Handle dynamically generated parameters
            value = param.value()
            if param.type() == "list":
                value = list(param.opts["limits"]).index(value)

            if "pvc_id" in param.opts:  # Post-processing parameter
                self.camera.set_pp_param(param.opts["pvc_id"], value)
            elif "pvc_enum" in param.opts:  # Advanced general parameter
                self.camera.set_param(param.opts["pvc_enum"], value)

        except Exception as e:
            self.emit_status(
                ThreadCommand(
                    "Update Error", [f"Failed to set {param.name()}: {str(e)}"]
                )
            )

    def get_xaxis(self):
        """Get the x_axis from the camera sensor size."""
        if self.camera and self.camera.rois:
            roi = self.camera.rois[0]
            return Axis(data=np.arange(roi.shape[1]), label="Pixels")
        return Axis(data=np.arange(1), label="Pixels")

    def get_yaxis(self):
        """Get the y_axis from the camera sensor size."""
        if self.camera and self.camera.rois:
            roi = self.camera.rois[0]
            return Axis(data=np.arange(roi.shape[0]), label="Pixels")
        return Axis(data=np.arange(1), label="Pixels")

    def get_roi_bounds(self):
        """Get ROI bounds for integration. Returns None if no ROI is set."""
        if self.camera and self.camera.rois:
            roi = self.camera.rois[0]
            # ROI bounds: (start_row, height, start_col, width)
            return (roi.p1, roi.p2 - roi.p1 + 1, roi.s1, roi.s2 - roi.s1 + 1)
        return None

    def grab_data(self, Naverage=1, **kwargs):
        """
        Acquires a single frame from the camera and emits the data.
        Performs ROI integration if enabled.
        """
        try:
            if self.camera is None:
                self.status.update(etat="Error", txt="Camera not initialized")
                return

            self.settings.child("camera_settings", "temperature").setValue(
                self.camera.temp
            )

            frame = self.camera.get_frame(
                exp_time=self.settings.child("camera_settings", "exposure").value()
            )

            # Handle mock camera that doesn't have rois
            if hasattr(self.camera, "rois") and self.camera.rois:
                frame = frame.reshape(self.camera.rois[0].shape)
            else:
                # For mock camera, ensure proper 2D shape
                if len(frame.shape) != 2:
                    frame = frame.reshape(self.camera.sensor_size)

            # PyMoDAQ 5.0+ data structure
            dwa_2d = DataWithAxes(
                name="PrimeBSI",
                source=DataSource.raw,
                data=[frame],
                axes=[self.y_axis, self.x_axis],
            )
            data_to_emit = [dwa_2d]

            if self.settings.child("roi_settings", "roi_integration").value():
                roi_bounds = self.get_roi_bounds()
                if roi_bounds:
                    y, h, x, w = roi_bounds
                    roi_frame = frame[y : y + h, x : x + w]
                    integrated_signal = np.sum(roi_frame, dtype=np.float64)
                    # PyMoDAQ 5.0+ 0D data structure
                    dwa_0d = DataWithAxes(
                        name="SHG Signal",
                        source=DataSource.calculated,
                        data=[integrated_signal],
                    )
                    data_to_emit.append(dwa_0d)

            # PyMoDAQ 5.0+ signal emission
            dte = DataToExport(name="PrimeBSI_Data", data=data_to_emit)
            self.dte_signal.emit(dte)

        except Exception as e:
            self.emit_status(
                ThreadCommand("Acquisition Error", [f"Failed to grab data: {str(e)}"])
            )

    def stop(self):
        """Stops any ongoing acquisition."""
        try:
            pass
        except Exception as e:
            self.emit_status(
                ThreadCommand("Stop Error", [f"Error stopping acquisition: {str(e)}"])
            )
        return ""
