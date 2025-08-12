#!/usr/bin/env python3
"""
Mock PyMoDAQ classes for testing plugins without full PyMoDAQ installation.
"""

import numpy as np
from unittest.mock import Mock, MagicMock


class MockThreadCommand:
    """Mock thread command for PyMoDAQ communication."""

    def __init__(self, command, data=None):
        self.command = command
        self.data = data if data is not None else []


class MockAxis:
    """Mock axis for data structure."""

    def __init__(self, data=None, label="", units="", **kwargs):
        self.data = data if data is not None else np.arange(100)
        self.label = label
        self.units = units

    def get_data(self):
        return self.data


class MockDataWithAxes:
    """Mock DataWithAxes for PyMoDAQ 5.x."""

    def __init__(
        self,
        name="",
        data=None,
        axes=None,
        labels=None,
        units=None,
        source=None,
        **kwargs,
    ):
        self.name = name
        self.data = data if data is not None else []
        self.axes = axes if axes is not None else []
        self.labels = labels if labels is not None else []
        self.units = units if units is not None else []
        self.source = source


class MockDataToExport:
    """Mock DataToExport for PyMoDAQ 5.x."""

    def __init__(self, name="", data=None, **kwargs):
        self.name = name
        self.data = data if data is not None else []


class MockParameter:
    """Mock parameter class for PyMoDAQ settings."""

    def __init__(self, name="", value=None, **kwargs):
        self._name = name
        self._value = value
        self._children = {}
        self._parent = None
        self._readonly = kwargs.get("readonly", False)
        self._limits = kwargs.get("limits", [])
        self._type = kwargs.get("type", "str")
        self.opts = kwargs.get("opts", {})

    def name(self):
        return self._name

    def value(self):
        return self._value

    def setValue(self, value):
        if not self._readonly:
            self._value = value

    def setLimits(self, limits):
        self._limits = limits

    def type(self):
        return self._type

    def child(self, *path):
        """Navigate to child parameter"""
        current = self
        for step in path:
            if step not in current._children:
                current._children[step] = MockParameter(step)
                current._children[step]._parent = current
            current = current._children[step]
        return current

    def children(self):
        """Return list of child parameters"""
        return list(self._children.values())

    def remove(self):
        """Remove this parameter"""
        if self._parent and self._name in self._parent._children:
            del self._parent._children[self._name]

    def addChild(self, child):
        """Add child parameter"""
        self._children[child.name()] = child
        child._parent = self

    @staticmethod
    def create(**kwargs):
        """Create parameter from kwargs"""
        return MockParameter(**kwargs)


class MockStatus:
    """Mock status object."""

    def __init__(self):
        self.busy = False
        self.message = ""

    def update(self, msg="", busy=False):
        self.message = msg
        self.busy = busy


class MockSignal:
    """Mock signal for data emission."""

    def __init__(self):
        self._callbacks = []

    def emit(self, data):
        for callback in self._callbacks:
            callback(data)

    def connect(self, callback):
        self._callbacks.append(callback)


class MockDAQViewerBase:
    """Mock base class for DAQ_Viewer plugins"""

    def __init__(self, parent=None, params_state=None):
        self.parent = parent
        self.params_state = params_state
        self.settings = self._create_settings_tree()
        self.initialized = False
        self.status = MockStatus()
        self.dte_signal = MockSignal()
        self._status_callbacks = []

    def _create_settings_tree(self):
        """Create mock settings tree with camera parameters"""
        settings = MockParameter("root")

        # Create camera settings
        settings.child("camera_settings", "camera_name").setValue("")
        settings.child("camera_settings", "sensor_size").setValue("")
        settings.child("camera_settings", "exposure").setValue(100.0)
        settings.child("camera_settings", "readout_port").setValue("Port 1")
        settings.child("camera_settings", "speed_index").setValue(1)
        settings.child("camera_settings", "gain").setValue(1)
        settings.child("camera_settings", "trigger_mode").setValue("Internal")
        settings.child("camera_settings", "clear_mode").setValue("Pre-Sequence")
        settings.child("camera_settings", "temperature").setValue(-10.0)
        settings.child("camera_settings", "temperature_setpoint").setValue(-10)

        # Create ROI settings
        settings.child("roi_settings", "roi_integration").setValue(True)

        return settings

    def emit_status(self, command):
        """Mock status emission"""
        for callback in self._status_callbacks:
            callback(command)

    def add_status_callback(self, callback):
        """Add status callback for testing"""
        self._status_callbacks.append(callback)
