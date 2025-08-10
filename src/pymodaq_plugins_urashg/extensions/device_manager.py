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

import time
from typing import Optional
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

    
    def move_polarization_elements(self, positions: dict, timeout: float = 10.0) -> bool:
        """
        Coordinated movement of polarization elements.
        
        Args:
            positions: Dictionary with axis positions {'axis_0': angle0, 'axis_1': angle1, 'axis_2': angle2}
            timeout: Movement timeout in seconds
            
        Returns:
            True if movement successful, False otherwise
        """
        logger.info(f"Moving polarization elements: {positions}")
        
        try:
            elliptec = self.get_elliptec()
            if not elliptec:
                logger.error("Elliptec device not available for coordinated movement")
                return False
            
            # Prepare position data for multi-axis movement
            from pymodaq.utils.data import DataActuator
            
            # Convert positions dict to list format expected by Elliptec
            position_list = [0.0, 0.0, 0.0]  # Initialize all axes
            
            for axis_key, angle in positions.items():
                if axis_key == 'axis_0' or axis_key == 'qwp':
                    position_list[0] = float(angle)
                elif axis_key == 'axis_1' or axis_key == 'hwp_incident':
                    position_list[1] = float(angle)
                elif axis_key == 'axis_2' or axis_key == 'hwp_analyzer':
                    position_list[2] = float(angle)
            
            # Create DataActuator for multi-axis movement
            position_data = DataActuator(data=[position_list])
            
            # Execute movement
            if hasattr(elliptec, 'move_abs'):
                elliptec.move_abs(position_data)
                logger.debug(f"Coordinated movement initiated: {position_list}")
                
                # Wait for completion with timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # For now, assume movement completes after reasonable time
                    # Real implementation would check device status
                    time.sleep(0.1)
                    if time.time() - start_time > 3.0:  # Minimum movement time
                        break
                
                logger.info("Coordinated polarization movement completed")
                return True
            else:
                logger.error("Elliptec device does not support absolute movement")
                return False
                
        except Exception as e:
            logger.error(f"Error in coordinated polarization movement: {e}")
            return False
    
    def acquire_synchronized_data(self, integration_time: float = 100.0, averages: int = 1) -> Optional[dict]:
        """
        Acquire synchronized data from camera and power meter.
        
        Args:
            integration_time: Integration time in milliseconds
            averages: Number of averages
            
        Returns:
            Dictionary with synchronized data or None on failure
        """
        try:
            camera = self.get_camera()
            power_meter = self.get_power_meter()
            
            if not camera:
                logger.error("Camera not available for synchronized acquisition")
                return None
            
            # Acquire multiple images for averaging
            images = []
            power_readings = []
            
            for avg in range(averages):
                # Acquire camera image
                camera_data = camera.grab_data()
                if camera_data and len(camera_data) > 0:
                    data_item = camera_data[0]
                    if hasattr(data_item, 'data') and len(data_item.data) > 0:
                        images.append(data_item.data[0])
                
                # Acquire power reading if available
                if power_meter:
                    try:
                        power_data = power_meter.grab_data()
                        if power_data and len(power_data) > 0:
                            power_value = float(power_data[0].data[0]) if hasattr(power_data[0], 'data') else None
                            if power_value is not None:
                                power_readings.append(power_value)
                    except Exception as e:
                        logger.debug(f"Could not acquire power reading {avg + 1}: {e}")
                
                # Small delay between averages
                if avg < averages - 1:
                    time.sleep(0.01)
            
            if not images:
                logger.error("No camera images acquired")
                return None
            
            # Average the data
            import numpy as np
            
            averaged_image = np.mean(images, axis=0) if len(images) > 1 else images[0]
            averaged_power = np.mean(power_readings) if power_readings else None
            
            # Calculate total intensity
            total_intensity = float(np.sum(averaged_image))
            
            return {
                'image': averaged_image,
                'intensity': total_intensity,
                'power': averaged_power,
                'n_averages': len(images),
                'n_power_readings': len(power_readings)
            }
            
        except Exception as e:
            logger.error(f"Error in synchronized data acquisition: {e}")
            return None
    
    def configure_camera_for_measurement(self, roi_settings: dict, integration_time: float) -> bool:
        """
        Configure camera settings for μRASHG measurement.
        
        Args:
            roi_settings: ROI configuration dictionary
            integration_time: Integration time in milliseconds
            
        Returns:
            True if configuration successful
        """
        try:
            camera = self.get_camera()
            if not camera:
                logger.error("Camera not available for configuration")
                return False
            
            # Configure camera settings if accessible
            if hasattr(camera, 'settings') and camera.settings:
                try:
                    # Set ROI if camera supports it
                    detector_settings = camera.settings.child('detector_settings')
                    if detector_settings and detector_settings.child('ROIselect'):
                        roi_select = detector_settings.child('ROIselect')
                        if roi_select.child('x0'):
                            roi_select.child('x0').setValue(roi_settings.get('x_start', 0))
                        if roi_select.child('y0'):
                            roi_select.child('y0').setValue(roi_settings.get('y_start', 0))
                        if roi_select.child('width'):
                            roi_select.child('width').setValue(roi_settings.get('width', 2048))
                        if roi_select.child('height'):
                            roi_select.child('height').setValue(roi_settings.get('height', 2048))
                        
                        logger.info(f"Camera ROI configured: {roi_settings}")
                    
                    # Set integration time if supported
                    main_settings = camera.settings.child('main_settings')
                    if main_settings and main_settings.child('exposure'):
                        main_settings.child('exposure').setValue(integration_time)
                        logger.info(f"Camera exposure set to {integration_time} ms")
                        
                    return True
                    
                except Exception as e:
                    logger.warning(f"Could not configure camera settings: {e}")
                    return False
            else:
                logger.warning("Camera settings not accessible")
                return False
                
        except Exception as e:
            logger.error(f"Error configuring camera: {e}")
            return False
    
    def check_safety_limits(self, settings) -> list:
        """
        Check all safety limits and return any violations.
        
        Args:
            settings: Extension settings object
            
        Returns:
            List of safety violation messages (empty if all OK)
        """
        violations = []
        
        try:
            # Check power limits
            max_power = settings.child('hardware', 'safety', 'max_power').value()
            if max_power > 90.0:
                violations.append(f"Power limit too high: {max_power}% (max recommended: 90%)")
            
            # Check timeout settings
            movement_timeout = settings.child('hardware', 'safety', 'movement_timeout').value()
            if movement_timeout > 60.0:
                violations.append(f"Movement timeout too long: {movement_timeout}s (max recommended: 60s)")
            
            camera_timeout = settings.child('hardware', 'safety', 'camera_timeout').value()
            if camera_timeout > 30.0:
                violations.append(f"Camera timeout too long: {camera_timeout}s (max recommended: 30s)")
            
            # Check measurement parameters
            pol_steps = settings.child('experiment', 'pol_steps').value()
            if pol_steps > 360:
                violations.append(f"Too many polarization steps: {pol_steps} (max recommended: 360)")
            
            integration_time = settings.child('experiment', 'integration_time').value()
            if integration_time > 10000:
                violations.append(f"Integration time too long: {integration_time}ms (max recommended: 10s)")
            
            # Check ROI settings
            roi_width = settings.child('hardware', 'camera', 'roi', 'width').value()
            roi_height = settings.child('hardware', 'camera', 'roi', 'height').value()
            
            if roi_width * roi_height > 2048 * 2048:
                violations.append(f"ROI too large: {roi_width}x{roi_height} (may cause memory issues)")
            
            if violations:
                logger.warning(f"Safety violations detected: {violations}")
            else:
                logger.debug("All safety checks passed")
            
            return violations
            
        except Exception as e:
            logger.error(f"Error checking safety limits: {e}")
            return [f"Error checking safety limits: {str(e)}"]
    
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