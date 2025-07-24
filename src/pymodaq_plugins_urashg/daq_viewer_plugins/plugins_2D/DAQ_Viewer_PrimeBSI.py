import numpy as np
from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base,
    comon_parameters,
    main,
)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import Axis, DataFromPlugins
from pymodaq.utils.parameter import Parameter

# Try to import PyVCAM and handle the case where it's not installed
try:
    import pyvcam
    from pyvcam.camera import Camera
    from pyvcam.enums import ClearMode, Param, TriggerMode
except ImportError:
    print("PyVCAM library is not installed. This plugin will not be usable.")

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
                    "value": -10,
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

    # Add common parameters if available
    if hasattr(comon_parameters, "__iter__") and not isinstance(comon_parameters, str):
        params.extend(comon_parameters)

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
            pyvcam.pvc.init_pvcam()
            self.camera = next(Camera.detect_camera())
            self.camera.open()

            self.update_camera_params()
            self.populate_advanced_params()
            self.populate_post_processing_params()

            self.status.update(
                msg=f"Camera {self.camera.name} Initialized.", busy=False
            )
            self.initialized = True
            return self.status

        except (StopIteration, Exception) as e:
            self.status.update(
                msg=f"Camera Initialization Failed: {str(e)}", busy=False
            )
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
        self.settings.child("camera_settings", "speed_index").setLimits(
            list(range(self.camera.speed_table_size))
        )
        self.settings.child("camera_settings", "gain").setLimits(self.camera.gains)
        self.settings.child("camera_settings", "trigger_mode").setLimits(
            [e.name for e in TriggerMode]
        )
        self.settings.child("camera_settings", "clear_mode").setLimits(
            [e.name for e in ClearMode]
        )

        self.settings.child("camera_settings", "readout_port").setValue(
            self.camera.readout_port
        )
        self.settings.child("camera_settings", "speed_index").setValue(
            self.camera.speed_table_index
        )
        self.settings.child("camera_settings", "gain").setValue(self.camera.gain)
        self.settings.child("camera_settings", "trigger_mode").setValue(
            self.camera.trigger_mode.name
        )
        self.settings.child("camera_settings", "clear_mode").setValue(
            self.camera.clear_mode.name
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
        handled_params = {
            Param.EXP_TIME,
            Param.READOUT_PORT,
            Param.PIX_TIME,
            Param.GAIN_INDEX,
            Param.TEMP_SETPOINT,
        }

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
        pyvcam.pvc.uninit_pvcam()

    def commit_settings(self, param: Parameter):
        """Applies a changed setting to the camera hardware."""
        try:
            # Handle standard camera settings
            if param.name() == "exposure":
                self.camera.exp_time = int(param.value())
            elif param.name() == "readout_port":
                self.camera.readout_port = param.value()
                self.settings.child("camera_settings", "speed_index").setLimits(
                    list(range(self.camera.speed_table_size))
                )
            elif param.name() == "speed_index":
                self.camera.speed_table_index = param.value()
            elif param.name() == "gain":
                self.camera.gain = param.value()
            elif param.name() == "trigger_mode":
                self.camera.trigger_mode = TriggerMode[param.value()]
            elif param.name() == "clear_mode":
                self.camera.clear_mode = ClearMode[param.value()]
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
        if self.camera:
            return Axis(data=np.arange(self.camera.roi[2]), label="Pixels")
        return Axis(data=np.arange(1), label="Pixels")

    def get_yaxis(self):
        """Get the y_axis from the camera sensor size."""
        if self.camera:
            return Axis(data=np.arange(self.camera.roi[3]), label="Pixels")
        return Axis(data=np.arange(1), label="Pixels")

    def get_roi_bounds(self):
        """Get ROI bounds for integration. Returns None if no ROI is set."""
        if self.camera and hasattr(self.camera, "roi"):
            # camera.roi format is typically (x, y, width, height)
            x, y, width, height = self.camera.roi
            return (y, height, x, width)
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
            ).reshape((self.camera.roi[3], self.camera.roi[2]))

            data_to_emit = [
                DataFromPlugins(
                    name="PrimeBSI",
                    data=[frame],
                    dim="Data2D",
                    axes=[self.y_axis, self.x_axis],
                )
            ]

            if self.settings.child("roi_settings", "roi_integration").value():
                roi_bounds = self.get_roi_bounds()
                if roi_bounds:
                    y, h, x, w = roi_bounds
                    roi_frame = frame[y : y + h, x : x + w]
                    integrated_signal = np.sum(roi_frame, dtype=np.float64)
                    data_to_emit.append(
                        DataFromPlugins(
                            name="SHG Signal",
                            data=[integrated_signal],
                            dim="Data0D",
                        )
                    )

            self.data_grabed_signal.emit(data_to_emit)

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


if __name__ == "__main__":
    main(__file__)
