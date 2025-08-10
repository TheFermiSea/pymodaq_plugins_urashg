# -*- coding: utf-8 -*-
"""
Device Manager for μRASHG Extension

This module provides centralized device management and coordination for the
μRASHG microscopy extension. It handles discovery, validation, and coordinated
control of all hardware devices through PyMoDAQ's dashboard framework.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from qtpy.QtCore import QObject, Signal, QTimer
import numpy as np

from pymodaq.utils.data import DataWithAxes, Axis
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class DeviceStatus(Enum):
    """Device status enumeration."""
    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    BUSY = "busy"


class DeviceInfo:
    """Information about a device."""
    
    def __init__(self, name: str, device_type: str, module_name: str = None):
        self.name = name
        self.device_type = device_type  # 'move' or 'viewer'
        self.module_name = module_name
        self.status = DeviceStatus.UNKNOWN
        self.last_error = None
        self.last_update = time.time()
        self.capabilities = {}
        
    def update_status(self, status: DeviceStatus, error_msg: str = None):
        """Update device status and error information."""
        self.status = status
        self.last_error = error_msg
        self.last_update = time.time()


class URASHGDeviceManager(QObject):
    """
    Centralized device management for μRASHG Extension.
    
    Handles discovery, validation, and coordinated control of all hardware
    devices required for μRASHG measurements through PyMoDAQ's dashboard.
    """
    
    # Signals for device status updates
    device_status_changed = Signal(str, str)  # device_name, status
    device_error = Signal(str, str)  # device_name, error_message
    all_devices_ready = Signal(bool)  # ready_status
    
    # Required devices configuration
    REQUIRED_DEVICES = {
        'camera': {
            'type': 'viewer',
            'name_patterns': ['PrimeBSI', 'Camera'],
            'description': 'Primary camera for SHG detection',
            'required': True,
        },
        'power_meter': {
            'type': 'viewer', 
            'name_patterns': ['Newport1830C', 'PowerMeter', 'Newport'],
            'description': 'Power meter for laser monitoring',
            'required': True,
        },
        'elliptec': {
            'type': 'move',
            'name_patterns': ['Elliptec'],
            'description': '3-axis rotation mounts for polarization control',
            'required': True,
        },
        'laser': {
            'type': 'move',
            'name_patterns': ['MaiTai', 'Laser'],
            'description': 'MaiTai laser with wavelength control',
            'required': False,  # Optional for basic measurements
        },
        'pid_control': {
            'type': 'move',
            'name_patterns': ['PyRPL_PID', 'PID'],
            'description': 'PyRPL PID controller for stabilization',
            'required': False,  # Optional
        },
    }
    
    def __init__(self, dashboard):
        """
        Initialize the device manager.
        
        Args:
            dashboard: PyMoDAQ dashboard instance
        """
        super().__init__()
        
        self.dashboard = dashboard
        self.modules_manager = dashboard.modules_manager if dashboard else None
        
        # Device tracking
        self.devices: Dict[str, DeviceInfo] = {}
        self.available_modules = {}
        self.missing_devices = []
        
        # Status monitoring
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_all_device_status)
        self.status_timer.setInterval(5000)  # Check every 5 seconds
        
        # Initialize device discovery
        self.discover_devices()
        
        logger.info("URASHGDeviceManager initialized")
    
    def discover_devices(self) -> Tuple[Dict[str, DeviceInfo], List[str]]:
        """
        Discover and validate all required devices.
        
        Returns:
            Tuple of (available_devices, missing_devices)
        """
        if not self.modules_manager:
            logger.warning("No modules manager available for device discovery")
            return {}, list(self.REQUIRED_DEVICES.keys())
        
        logger.info("Starting device discovery...")
        
        # Get available modules from dashboard
        try:
            move_modules = getattr(self.modules_manager, 'move_modules', {})
            viewer_modules = getattr(self.modules_manager, 'viewer_modules', {})
            
            self.available_modules = {
                'move': move_modules,
                'viewer': viewer_modules,
            }
            
            logger.info(f"Available move modules: {list(move_modules.keys())}")
            logger.info(f"Available viewer modules: {list(viewer_modules.keys())}")
            
        except Exception as e:
            logger.error(f"Error accessing dashboard modules: {e}")
            self.available_modules = {'move': {}, 'viewer': {}}
        
        # Match required devices with available modules
        found_devices = {}
        missing_devices = []
        
        for device_key, device_config in self.REQUIRED_DEVICES.items():
            device_info = self._find_device_module(device_key, device_config)
            
            if device_info:
                found_devices[device_key] = device_info
                self.devices[device_key] = device_info
                logger.info(f"Found device '{device_key}': {device_info.module_name}")
            else:
                if device_config.get('required', True):
                    missing_devices.append(device_key)
                    logger.warning(f"Required device '{device_key}' not found")
                else:
                    logger.info(f"Optional device '{device_key}' not found")
        
        self.missing_devices = missing_devices
        
        # Emit status signals
        self.device_status_changed.emit('discovery', 'completed')
        self.all_devices_ready.emit(len(missing_devices) == 0)
        
        logger.info(f"Device discovery completed. Found: {len(found_devices)}, Missing: {len(missing_devices)}")
        
        return found_devices, missing_devices
    
    def _find_device_module(self, device_key: str, device_config: dict) -> Optional[DeviceInfo]:
        """
        Find a device module matching the configuration.
        
        Args:
            device_key: Device identifier key
            device_config: Device configuration dictionary
            
        Returns:
            DeviceInfo object if found, None otherwise
        """
        device_type = device_config['type']
        name_patterns = device_config['name_patterns']
        
        # Get modules of the correct type
        modules = self.available_modules.get(device_type, {})
        
        # Search for matching module names
        for module_name in modules.keys():
            for pattern in name_patterns:
                if pattern.lower() in module_name.lower():
                    # Create device info
                    device_info = DeviceInfo(
                        name=device_key,
                        device_type=device_type,
                        module_name=module_name
                    )
                    device_info.update_status(DeviceStatus.CONNECTED)
                    return device_info
        
        return None
    
    def get_device_module(self, device_key: str):
        """
        Get the actual PyMoDAQ module for a device.
        
        Args:
            device_key: Device identifier key
            
        Returns:
            PyMoDAQ module object or None
        """
        if device_key not in self.devices:
            logger.warning(f"Device '{device_key}' not found in device registry")
            return None
        
        device_info = self.devices[device_key]
        module_name = device_info.module_name
        device_type = device_info.device_type
        
        try:
            if device_type == 'move':
                return self.available_modules['move'].get(module_name)
            elif device_type == 'viewer':
                return self.available_modules['viewer'].get(module_name)
        except Exception as e:
            logger.error(f"Error accessing device module '{device_key}': {e}")
            return None
        
        return None
    
    def check_device_status(self, device_key: str) -> DeviceStatus:
        """
        Check the current status of a specific device.
        
        Args:
            device_key: Device identifier key
            
        Returns:
            Device status
        """
        if device_key not in self.devices:
            return DeviceStatus.UNKNOWN
        
        device_info = self.devices[device_key]
        module = self.get_device_module(device_key)
        
        if not module:
            device_info.update_status(DeviceStatus.DISCONNECTED)
            return DeviceStatus.DISCONNECTED
        
        try:
            # Check if module is initialized and connected
            if hasattr(module, 'controller') and module.controller:
                if hasattr(module.controller, 'connected'):
                    status = DeviceStatus.CONNECTED if module.controller.connected else DeviceStatus.DISCONNECTED
                else:
                    status = DeviceStatus.CONNECTED  # Assume connected if no explicit status
            else:
                status = DeviceStatus.DISCONNECTED
            
            device_info.update_status(status)
            return status
            
        except Exception as e:
            logger.error(f"Error checking device status for '{device_key}': {e}")
            device_info.update_status(DeviceStatus.ERROR, str(e))
            return DeviceStatus.ERROR
    
    def update_all_device_status(self):
        """Update status for all registered devices."""
        for device_key in self.devices.keys():
            old_status = self.devices[device_key].status
            new_status = self.check_device_status(device_key)
            
            if old_status != new_status:
                logger.debug(f"Device '{device_key}' status changed: {old_status.value} -> {new_status.value}")
                self.device_status_changed.emit(device_key, new_status.value)
    
    def start_monitoring(self):
        """Start periodic device status monitoring."""
        self.status_timer.start()
        logger.info("Started device status monitoring")
    
    def stop_monitoring(self):
        """Stop periodic device status monitoring."""
        self.status_timer.stop()
        logger.info("Stopped device status monitoring")
    
    def get_device_info(self, device_key: str) -> Optional[DeviceInfo]:
        """Get device information."""
        return self.devices.get(device_key)
    
    def get_all_device_info(self) -> Dict[str, DeviceInfo]:
        """Get information for all registered devices."""
        return self.devices.copy()
    
    def is_all_devices_ready(self) -> bool:
        """Check if all required devices are ready."""
        for device_key, device_config in self.REQUIRED_DEVICES.items():
            if device_config.get('required', True):
                if device_key not in self.devices:
                    return False
                if self.devices[device_key].status != DeviceStatus.CONNECTED:
                    return False
        return True
    
    def get_missing_devices(self) -> List[str]:
        """Get list of missing required devices."""
        return self.missing_devices.copy()
    
    # Convenience methods for specific device access
    
    def get_camera(self):
        """Get the camera module."""
        return self.get_device_module('camera')
    
    def get_power_meter(self):
        """Get the power meter module."""
        return self.get_device_module('power_meter')
    
    def get_elliptec(self):
        """Get the Elliptec rotation mounts module."""
        return self.get_device_module('elliptec')
    
    def get_laser(self):
        """Get the laser module."""
        return self.get_device_module('laser')
    
    def get_pid_control(self):
        """Get the PID control module."""
        return self.get_device_module('pid_control')
    
    # Coordinated device operations
    
    def initialize_all_devices(self) -> bool:
        """
        Initialize all available devices.
        
        Returns:
            True if all required devices initialized successfully
        """
        logger.info("Initializing all devices...")
        
        success = True
        for device_key in self.devices.keys():
            try:
                module = self.get_device_module(device_key)
                if module and hasattr(module, 'ini_stage'):
                    result = module.ini_stage()
                    if not result[1]:  # Check success flag
                        success = False
                        logger.error(f"Failed to initialize device '{device_key}': {result[0]}")
                    else:
                        logger.info(f"Successfully initialized device '{device_key}'")
            except Exception as e:
                success = False
                logger.error(f"Error initializing device '{device_key}': {e}")
                self.device_error.emit(device_key, str(e))
        
        return success
    
    def emergency_stop_all_devices(self):
        """Emergency stop for all devices."""
        logger.warning("Emergency stop activated for all devices")
        
        for device_key in self.devices.keys():
            try:
                module = self.get_device_module(device_key)
                if module:
                    # Stop any ongoing operations
                    if hasattr(module, 'stop_motion'):
                        module.stop_motion()
                    if hasattr(module, 'stop_acquisition'):
                        module.stop_acquisition()
                    
                    logger.info(f"Emergency stop applied to device '{device_key}'")
            except Exception as e:
                logger.error(f"Error during emergency stop for device '{device_key}': {e}")
    
    def cleanup(self):
        """Clean up device manager resources."""
        self.stop_monitoring()
        
        # Close all device connections
        for device_key in self.devices.keys():
            try:
                module = self.get_device_module(device_key)
                if module and hasattr(module, 'close'):
                    module.close()
                    logger.info(f"Closed device '{device_key}'")
            except Exception as e:
                logger.error(f"Error closing device '{device_key}': {e}")
        
        logger.info("Device manager cleanup completed")


# Export for extension use
__all__ = ['URASHGDeviceManager', 'DeviceStatus', 'DeviceInfo']