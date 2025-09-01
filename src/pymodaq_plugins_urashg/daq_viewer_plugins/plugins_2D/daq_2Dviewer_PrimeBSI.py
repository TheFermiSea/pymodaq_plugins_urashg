import numpy as np
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq_data.data import Axis, DataSource, DataToExport, DataWithAxes
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_urashg.hardware.camera_wrapper import CameraWrapper, MockCameraWrapper, HardwareError

class DAQ_2DViewer_PrimeBSI(DAQ_Viewer_base):
    """PyMoDAQ Plugin for Photometrics Prime BSI cameras with dynamic parameter discovery."""
    params = comon_parameters + [
        {"title": "Mock Mode", "name": "mock_mode", "type": "bool", "value": False},
        {"title": "Exposure (ms):", "name": "exposure", "type": "float", "value": 50.0},
        {"title": "Camera Info", "name": "camera_info", "type": "group", "children": [
            {"title": "Camera Name:", "name": "camera_name", "type": "str", "value": "", "readonly": True},
            {"title": "Sensor Size:", "name": "sensor_size", "type": "str", "value": "", "readonly": True},
        ]},
        {"title": "Advanced Settings", "name": "advanced_settings", "type": "group", "children": []},
        {"title": "Post-Processing", "name": "post_processing", "type": "group", "children": []},
    ]

    def ini_attributes(self):
        self.controller: CameraWrapper = None
        self.x_axis: Axis = None
        self.y_axis: Axis = None

    def ini_detector(self, controller=None):
        self.initialized = False
        try:
            ControllerClass = MockCameraWrapper if self.settings.child("mock_mode").value() else CameraWrapper
            self.controller = controller or ControllerClass()
            self.controller.connect()

            self.update_camera_info()
            self.populate_dynamic_params()
            self.initialized = True
            return f"Camera {self.settings.child('camera_info', 'camera_name').value()} Initialized.", True
        except (HardwareError, ImportError) as e:
            self.status.update(msg=f"Camera Initialization Failed: {e}", busy=False)
            return f"Camera Initialization Failed: {e}", False

    def update_camera_info(self):
        """Update GUI with camera properties and set up axes."""
        props = self.controller.get_camera_properties()
        self.settings.child('camera_info', 'camera_name').setValue(props["name"])
        self.settings.child('camera_info', 'sensor_size').setValue(f"{props['sensor_size'][0]} x {props['sensor_size'][1]}")
        
        height, width = props["sensor_size"]
        self.x_axis = Axis(data=np.arange(width), label="X", units="px")
        self.y_axis = Axis(data=np.arange(height), label="Y", units="px")

    def populate_dynamic_params(self):
        """Dynamically discover and create GUI controls for camera features."""
        params_dict = self.controller.discover_params()
        
        adv_group = self.settings.child("advanced_settings")
        for param_data in params_dict["advanced"]:
            adv_group.addChild(Parameter.create(**param_data))

        pp_group = self.settings.child("post_processing")
        for param_data in params_dict["post_processing"]:
            pp_group.addChild(Parameter.create(**param_data))

    def close(self):
        """Disconnect from the camera."""
        if self.controller:
            self.controller.disconnect()

    def commit_settings(self, param: Parameter):
        """Apply a changed setting to the camera hardware."""
        try:
            if 'pvc_enum' in param.opts:
                self.controller.set_param(param.opts['pvc_enum'], param.value())
            elif 'pvc_id' in param.opts:
                self.controller.set_pp_param(param.opts['pvc_id'], param.value())
        except HardwareError as e:
            self.emit_status(ThreadCommand("Update Error", [f"Failed to set {param.name()}: {e}", "error"]))

    def grab_data(self, Naverage=1, **kwargs):
        """Acquire a frame from the camera and emit the data."""
        try:
            exposure_ms = self.settings.child("exposure").value()
            frame = self.controller.get_frame(int(exposure_ms))
            
            dwa = DataWithAxes("PrimeBSI", DataSource.raw, [frame], axes=[self.y_axis, self.x_axis])
            self.dte_signal.emit(DataToExport("PrimeBSI_Data", data=[dwa]))
        except HardwareError as e:
            self.emit_status(ThreadCommand("Acquisition Error", [f"Failed to grab data: {e}", "error"]))

    def stop(self):
        return ""
