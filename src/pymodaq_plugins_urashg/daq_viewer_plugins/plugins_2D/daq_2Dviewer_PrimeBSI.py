import numpy as np
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter



# Removed unused imports: get_param_path, iter_children
from pymodaq.utils.data import Axis, DataToExport, DataWithAxes
from pymodaq_data import DataSource

# Try to import PyVCAM and handle the case where it's not installed
try:
    import pyvcam
    from pyvcam import pvc
    from pyvcam.camera import Camera
    from pyvcam.constants import CLEAR_NEVER, CLEAR_PRE_SEQUENCE, EXT_TRIG_INTERNAL

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

    params = [
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
        try:
            # Ensure clean PVCAM state
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

            self.update_camera_params()
            self.populate_advanced_params()
            self.populate_post_processing_params()

            self.status.update(
                msg=f"Camera {self.camera.name} Initialized.", busy=False
            )
            self.initialized = True
            return self.status

        except Exception as e:
            error_msg = f"Camera Initialization Failed: {str(e)}"
            self.status.update(msg=error_msg, busy=False)
            self.initialized = False
            return self.status

    def update_camera_params(self):
        """
        Queries the connected camera for its primary capabilities and updates the main settings panel.
        """
        self.settings.child("camera_settings", "camera_name").setValue(self.camera.name)
        sensor_size = f"{self.camera.sensor_size[0]} x {self.camera.sensor_size[1]}"
        self.settings.child("camera_settings", "sensor_size").setValue(sensor_size)

        self.settings.child("camera_settings", "readout_port").setLimits(
            self.camera.readout_ports
        )
        # Get available speeds from current port
        current_port = self.camera.readout_port
        port_name = list(self.camera.readout_ports.keys())[
            list(self.camera.readout_ports.values()).index(current_port)
        ]
        port_info = self.camera.port_speed_gain_table[port_name]
        speed_names = [k for k in port_info.keys() if k.startswith("Speed_")]
        self.settings.child("camera_settings", "speed_index").setLimits(speed_names)
        # Get available gains for current speed
        current_speed_name = f"Speed_{self.camera.speed}"
        if current_speed_name in port_info:
            speed_info = port_info[current_speed_name]
            gain_names = [
                k
                for k in speed_info.keys()
                if k not in ["speed_index", "pixel_time", "bit_depth", "gain_range"]
            ]
            self.settings.child("camera_settings", "gain").setLimits(gain_names)
        self.settings.child("camera_settings", "trigger_mode").setLimits(
            list(self.camera.exp_modes.keys())
        )
        self.settings.child("camera_settings", "clear_mode").setLimits(
            list(self.camera.clear_modes.keys())
        )

        self.settings.child("camera_settings", "readout_port").setValue(
            self.camera.readout_port
        )
        self.settings.child("camera_settings", "speed_index").setValue(
            f"Speed_{self.camera.speed}"
        )
        self.settings.child("camera_settings", "gain").setValue(self.camera.gain_name)
        self.settings.child("camera_settings", "trigger_mode").setValue(
            list(self.camera.exp_modes.keys())[
                list(self.camera.exp_modes.values()).index(self.camera.exp_mode)
            ]
        )
        self.settings.child("camera_settings", "clear_mode").setValue(
            list(self.camera.clear_modes.keys())[
                list(self.camera.clear_modes.values()).index(self.camera.clear_mode)
            ]
        )
        self.settings.child("camera_settings", "temperature_setpoint").setValue(
            self.camera.temp_setpoint
        )

        self.x_axis = self.get_xaxis()
        self.y_axis = self.get_yaxis()

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
        if self.camera is not None and self.camera.is_open:
            self.camera.close()
        pvc.uninit_pvcam()

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
            self.settings.child("camera_settings", "temperature").setValue(
                self.camera.temp
            )

            frame = self.camera.get_frame(
                exp_time=self.settings.child("camera_settings", "exposure").value()
            ).reshape(self.camera.rois[0].shape)

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
