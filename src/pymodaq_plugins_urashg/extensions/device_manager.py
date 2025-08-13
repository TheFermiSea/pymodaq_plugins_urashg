# -*- coding: utf-8 -*-
"""
Minimal Device Manager Stub for Test Compatibility

This file provides a minimal stub implementation to maintain compatibility with
existing tests while using PyMoDAQ's extension-based architecture.

The original device_manager.py was removed as it was causing conflicts with
PyMoDAQ's plugin architecture. This stub provides the minimal interface
required by tests while encouraging migration to the extension-based approach.

For production use, device coordination should be handled through:
- pymodaq_plugins_urashg.extensions.urashg_microscopy_extension
- PyMoDAQ's dashboard.modules_manager
- Standard PyMoDAQ plugin interfaces
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from qtpy.QtCore import QObject, Signal, QMetaObject, Qt

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """Device status enumeration for compatibility."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class URASHGDeviceManager(QObject):
    """
    Minimal device manager stub for test compatibility.

    This is a compatibility layer only. For production use, migrate to
    URASHGMicroscopyExtension which follows PyMoDAQ standards.
    """

    # Required signals for test compatibility
    device_status_changed = Signal(str, str)
    device_error_occurred = Signal(str, str)
    all_devices_ready = Signal()
    device_data_updated = Signal(str, object)

    def __init__(self, dashboard=None):
        super().__init__()
        logger.warning(
            "URASHGDeviceManager is a compatibility stub only. "
            "Use URASHGMicroscopyExtension for production applications."
        )

        # Store dashboard reference
        self.dashboard = dashboard

        # Basic attributes for test compatibility
        self.devices: Dict[str, Any] = {}
        self.device_status: Dict[str, DeviceStatus] = {}
        self.supported_devices: List[str] = [
            "MaiTai",
            "Elliptec",
            "ESP300",
            "PrimeBSI",
            "Newport1830C",
        ]

        # Initialize all devices as disconnected
        for device in self.supported_devices:
            self.device_status[device] = DeviceStatus.DISCONNECTED

    def register_device(self, device_name: str, device_instance: Any) -> bool:
        """Register a device (compatibility method)."""
        if device_name in self.supported_devices:
            self.devices[device_name] = device_instance
            self.device_status[device_name] = DeviceStatus.CONNECTED
            self.device_status_changed.emit(device_name, "connected")
            return True
        return False

    def unregister_device(self, device_name: str) -> bool:
        """Unregister a device (compatibility method)."""
        if device_name in self.devices:
            del self.devices[device_name]
            self.device_status[device_name] = DeviceStatus.DISCONNECTED
            self.device_status_changed.emit(device_name, "disconnected")
            return True
        return False

    def update_device_status(self, device_name: str, status: str) -> None:
        """Update device status (compatibility method)."""
        if device_name in self.supported_devices:
            try:
                new_status = DeviceStatus(status.lower())
                old_status = self.device_status.get(device_name)
                if old_status != new_status:
                    self.device_status[device_name] = new_status
                    self.device_status_changed.emit(device_name, status)
            except ValueError:
                logger.warning(f"Invalid status '{status}' for device '{device_name}'")

    def get_device_status(self, device_name: str) -> Optional[DeviceStatus]:
        """Get device status (compatibility method)."""
        return self.device_status.get(device_name)

    def get_all_device_status(self) -> Dict[str, str]:
        """Get all device statuses (compatibility method)."""
        return {name: status.value for name, status in self.device_status.items()}

    def is_device_ready(self, device_name: str) -> bool:
        """Check if device is ready (compatibility method)."""
        status = self.get_device_status(device_name)
        return status == DeviceStatus.READY if status else False

    def are_all_devices_ready(self) -> bool:
        """Check if all devices are ready (compatibility method)."""
        return all(
            status == DeviceStatus.READY for status in self.device_status.values()
        )

    def initialize_devices(self) -> bool:
        """Initialize devices (compatibility stub)."""
        logger.info("Device initialization is handled by URASHGMicroscopyExtension")
        return True

    def cleanup_devices(self) -> None:
        """Cleanup devices (compatibility stub)."""
        logger.info("Device cleanup is handled by URASHGMicroscopyExtension")
        for device_name in self.supported_devices:
            self.device_status[device_name] = DeviceStatus.DISCONNECTED

    def initialize_plugins(self) -> bool:
        """Initialize plugins (compatibility stub)."""
        logger.info("Plugin initialization is handled by URASHGMicroscopyExtension")
        return True

    def cleanup_plugins(self) -> None:
        """Cleanup plugins (compatibility stub)."""
        logger.info("Plugin cleanup is handled by URASHGMicroscopyExtension")
        for device_name in self.supported_devices:
            self.device_status[device_name] = DeviceStatus.DISCONNECTED

    def handle_device_error(self, device_name: str, error_message: str) -> None:
        """Handle device error with proper signal emission."""
        logger.error(f"Device error - {device_name}: {error_message}")

        # Update device status to error
        self.device_status[device_name] = DeviceStatus.ERROR

        # Emit error signals following PyMoDAQ standards
        self.device_error_occurred.emit(device_name, error_message)
        self.device_status_changed.emit(device_name, "error")

    def emit_error(self, device_name: str, error_message: str) -> None:
        """Emit error signal (for test compatibility)."""
        self.handle_device_error(device_name, error_message)

    def safe_emit_signal(self, signal, *args):
        """Thread-safe signal emission."""
        QMetaObject.invokeMethod(
            self, lambda: signal.emit(*args), Qt.ConnectionType.QueuedConnection
        )
