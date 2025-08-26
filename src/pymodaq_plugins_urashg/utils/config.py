# -*- coding: utf-8 -*-
"""
Configuration management for PyMoDAQ URASHG plugins.

This module provides configuration management following PyMoDAQ patterns
and standards for plugin configuration, preset management, and settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from pymodaq_utils.config import BaseConfig

    PYMODAQ_CONFIG_AVAILABLE = True
except ImportError:
    PYMODAQ_CONFIG_AVAILABLE = False

    # Fallback BaseConfig for development
    class BaseConfig:
        def __init__(self):
            self.config_template_path = None
            self.config_name = None


class Config(BaseConfig if PYMODAQ_CONFIG_AVAILABLE else dict):
    """
    Configuration manager for URASHG plugins.

    Provides configuration management compatible with PyMoDAQ patterns.
    """

    # PyMoDAQ configuration attributes
    config_template_path = Path(__file__).parent.parent / 'resources' / 'config_template.toml'
    config_name = "config_urashg"

    def __init__(self):
        """Initialize URASHG plugin configuration."""
        if PYMODAQ_CONFIG_AVAILABLE:
            # Initialize PyMoDAQ BaseConfig properly
            super().__init__()
        else:
            # Initialize dict-based fallback
            super().__init__()
            self._initialize_fallback_config()

    def _initialize_fallback_config(self):
        """Initialize fallback configuration when PyMoDAQ config is not available."""
        # Simple fallback configuration for development
        fallback_config = {
            "urashg": {
                "hardware": {
                    "elliptec": {
                        "serial_port": "/dev/ttyUSB0",
                        "baudrate": 9600,
                        "timeout": 2.0,
                        "mount_addresses": [2, 3, 8],
                        "home_on_startup": False,
                        "position_tolerance": 0.1,
                    },
                    "maitai": {
                        "serial_port": "/dev/ttyUSB2",
                        "baudrate": 9600,
                        "timeout": 5.0,
                        "wavelength_range_min": 700.0,
                        "wavelength_range_max": 1000.0,
                    },
                    "camera": {
                        "exposure_default": 100.0,
                        "gain_default": 1,
                        "cooling_enabled": True,
                        "cooling_temperature": -20,
                        "roi_x": 0,
                        "roi_y": 0,
                        "roi_width": 2048,
                        "roi_height": 2048,
                    },
                },
                "measurement": {
                    "rashg": {
                        "polarization_start": -45.0,
                        "polarization_end": 45.0,
                        "polarization_step": 5.0,
                        "averaging_frames": 3,
                        "laser_power": 100.0,
                        "exposure_time": 100.0,
                    },
                },
            }
        }

        # Copy fallback config to self
        for key, value in fallback_config.items():
            self[key] = value

    def get_hardware_config(self, device: str) -> Dict[str, Any]:
        """
        Get hardware configuration for a specific device.

        Args:
            device: Device name (elliptec, maitai, camera, etc.)

        Returns:
            Dictionary with device configuration
        """
        if PYMODAQ_CONFIG_AVAILABLE:
            # Use PyMoDAQ's BaseConfig _config dict access
            return self._config.get('urashg', {}).get('hardware', {}).get(device, {})
        else:
            return self.get("urashg", {}).get("hardware", {}).get(device, {})

    def get_measurement_config(self) -> Dict[str, Any]:
        """Get measurement configuration."""
        if PYMODAQ_CONFIG_AVAILABLE:
            return self._config.get('urashg', {}).get('measurement', {})
        else:
            return self.get("urashg", {}).get("measurement", {})

    def get_data_config(self) -> Dict[str, Any]:
        """Get data management configuration."""
        if PYMODAQ_CONFIG_AVAILABLE:
            return self._config.get('urashg', {}).get('data', {})
        else:
            return self.get("urashg", {}).get("data", {})

    def get_hardware_parameter(self, device: str, parameter: str, default: Any = None) -> Any:
        """Get a hardware parameter for a specific device."""
        device_config = self.get_hardware_config(device)
        return device_config.get(parameter, default)

    def get_preset_config(self) -> Dict[str, Any]:
        """
        Get preset configuration for PyMoDAQ compliance.

        Returns:
            Dictionary containing preset configuration data
        """
        preset_config = {
            "presets": {
                "urashg_microscopy_system": {
                    "description": "Standard URASHG microscopy configuration",
                    "modules": {
                        "elliptec_hwp_incident": {
                            "plugin": "DAQ_Move_Elliptec",
                            "settings": {
                                "connection_group": {
                                    "serial_port": "/dev/ttyUSB0",
                                    "mount_addresses": "2"
                                }
                            }
                        },
                        "elliptec_qwp": {
                            "plugin": "DAQ_Move_Elliptec",
                            "settings": {
                                "connection_group": {
                                    "serial_port": "/dev/ttyUSB0",
                                    "mount_addresses": "3"
                                }
                            }
                        },
                        "primebsi_camera": {
                            "plugin": "DAQ_2DViewer_PrimeBSI",
                            "settings": {
                                "camera_settings": {
                                    "exposure": 10.0,
                                    "mock_mode": False
                                }
                            }
                        }
                    }
                }
            }
        }

        if PYMODAQ_CONFIG_AVAILABLE:
            return self._config.get('presets', preset_config.get('presets', {}))
        else:
            return preset_config.get('presets', {})


# Lazy configuration instance - removed global initialization to fix PyMoDAQ plugin discovery
# Use get_config() from the main package instead
