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
    BaseConfig = dict


class Config(dict):
    """
    Configuration manager for URASHG plugins.

    Provides configuration management compatible with PyMoDAQ patterns.
    """

    def __init__(self, config_name: str = "urashg_plugins_config"):
        """
        Initialize URASHG plugin configuration.

        Args:
            config_name: Name of the configuration file
        """
        super().__init__()
        self.config_name = config_name

        # Plugin-specific configuration sections
        self._default_config = {
            "hardware": {
                "elliptec": {
                    "default_port": "/dev/ttyUSB1",
                    "baudrate": 9600,
                    "timeout": 2.0,
                    "mount_addresses": "2,3,8",
                    "home_on_connect": False,
                    "position_tolerance": 0.1,  # degrees
                },
                "maitai": {
                    "default_port": "/dev/ttyUSB0",
                    "baudrate": 115200,
                    "timeout": 2.0,
                    "wavelength_min": 700,
                    "wavelength_max": 900,
                    "stabilization_time": 2.0,  # seconds
                },
                "primebsi": {
                    "default_camera": "pvcamUSB_0",
                    "default_exposure": 10.0,  # ms
                    "default_roi": {"x": 0, "y": 0, "width": 2048, "height": 2048},
                    "cooling_enabled": True,
                    "target_temperature": -20.0,  # °C
                },
                "newport1830c": {
                    "default_port": "/dev/ttyS0",
                    "baudrate": 9600,
                    "timeout": 2.0,
                    "default_wavelength": 780.0,  # nm
                    "default_units": "W",
                    "averaging_count": 3,
                },
                "esp300": {
                    "default_host": "192.168.1.100",
                    "default_port": 5001,
                    "timeout": 5.0,
                    "axis_count": 1,
                    "position_tolerance": 0.01,  # mm
                },
            },
            "measurement": {
                "default_type": "Basic RASHG",
                "polarization_steps": 36,
                "integration_time": 100.0,  # ms
                "stabilization_time": 0.5,  # seconds
                "safety": {
                    "max_laser_power": 50.0,  # %
                    "movement_timeout": 10.0,  # seconds
                    "camera_timeout": 5.0,  # seconds
                },
            },
            "data": {
                "auto_save": True,
                "save_format": "HDF5",
                "save_raw_images": False,
                "default_path": str(Path.home() / "rashg_data"),
                "file_prefix": "urashg_measurement",
            },
            "analysis": {
                "auto_fit": True,
                "fit_function": "I = A + B*cos(4θ + φ)",
                "r_squared_threshold": 0.9,
                "contrast_threshold": 0.1,
            },
            "presets": {
                "default_preset": "urashg_microscopy_system",
                "preset_for_urashgmicroscopyextension": "urashg_microscopy_system",
                "auto_load_preset": True,
            },
            "ui": {
                "update_interval": 5.0,  # seconds
                "plot_update_rate": 2.0,  # Hz
                "status_display_lines": 100,
                "theme": "default",
            },
        }

        # Initialize with default configuration
        self._initialize_config()

    def _initialize_config(self):
        """Initialize configuration with default values."""
        for section, section_config in self._default_config.items():
            if section not in self:
                self[section] = {}

            self._update_section_recursive(self[section], section_config)

    def _update_section_recursive(self, target: Dict, source: Dict):
        """Recursively update configuration section with defaults."""
        for key, value in source.items():
            if key not in target:
                if isinstance(value, dict):
                    target[key] = {}
                    self._update_section_recursive(target[key], value)
                else:
                    target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._update_section_recursive(target[key], value)

    def get_hardware_config(self, device: str) -> Dict[str, Any]:
        """
        Get hardware configuration for a specific device.

        Args:
            device: Device name (elliptec, maitai, primebsi, etc.)

        Returns:
            Dictionary with device configuration
        """
        return self.get("hardware", {}).get(device, {})

    def get_measurement_config(self) -> Dict[str, Any]:
        """Get measurement configuration."""
        return self.get("measurement", {})

    def get_data_config(self) -> Dict[str, Any]:
        """Get data management configuration."""
        return self.get("data", {})

    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration."""
        return self.get("analysis", {})

    def get_preset_config(self) -> Dict[str, Any]:
        """Get preset configuration."""
        return self.get("presets", {})

    def set_hardware_parameter(self, device: str, parameter: str, value: Any):
        """
        Set a hardware parameter for a specific device.

        Args:
            device: Device name
            parameter: Parameter name
            value: Parameter value
        """
        if "hardware" not in self:
            self["hardware"] = {}
        if device not in self["hardware"]:
            self["hardware"][device] = {}

        self["hardware"][device][parameter] = value
        self.save_config()

    def get_hardware_parameter(
        self, device: str, parameter: str, default: Any = None
    ) -> Any:
        """
        Get a hardware parameter for a specific device.

        Args:
            device: Device name
            parameter: Parameter name
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        device_config = self.get_hardware_config(device)
        return device_config.get(parameter, default)

    def get_default_preset_path(self) -> Path:
        """Get the default preset file path."""
        preset_name = self.get_preset_config().get(
            "default_preset", "urashg_microscopy_system"
        )

        # Look in plugin presets directory
        plugin_root = Path(__file__).parent.parent.parent.parent
        preset_path = plugin_root / "presets" / f"{preset_name}.xml"

        return preset_path

    def get_data_save_path(self) -> Path:
        """Get the data save path."""
        data_config = self.get_data_config()
        save_path = data_config.get("default_path", str(Path.home() / "rashg_data"))
        return Path(save_path)

    def create_measurement_config(self, measurement_type: str = None) -> Dict[str, Any]:
        """
        Create a measurement configuration dictionary.

        Args:
            measurement_type: Type of measurement to configure

        Returns:
            Dictionary with measurement configuration
        """
        base_config = self.get_measurement_config().copy()

        if measurement_type:
            base_config["measurement_type"] = measurement_type

        # Add current hardware configurations
        base_config["hardware"] = {}
        for device in ["elliptec", "maitai", "primebsi", "newport1830c"]:
            base_config["hardware"][device] = self.get_hardware_config(device)

        return base_config

    def validate_configuration(self) -> Dict[str, List[str]]:
        """
        Validate the current configuration.

        Returns:
            Dictionary with validation results (errors and warnings)
        """
        errors = []
        warnings = []

        # Check hardware configurations
        hardware_config = self.get("hardware", {})

        # Validate Elliptec configuration
        elliptec_config = hardware_config.get("elliptec", {})
        if not elliptec_config.get("default_port"):
            errors.append("Elliptec default port not configured")

        mount_addresses = elliptec_config.get("mount_addresses", "")
        if not mount_addresses or not isinstance(mount_addresses, str):
            errors.append("Elliptec mount addresses not properly configured")

        # Validate MaiTai configuration
        maitai_config = hardware_config.get("maitai", {})
        wl_min = maitai_config.get("wavelength_min", 0)
        wl_max = maitai_config.get("wavelength_max", 0)
        if wl_min >= wl_max or wl_min <= 0:
            errors.append("MaiTai wavelength range invalid")

        # Validate data configuration
        data_config = self.get_data_config()
        save_path = data_config.get("default_path")
        if save_path:
            try:
                Path(save_path).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                warnings.append(f"Cannot create data save path: {save_path}")

        # Validate measurement configuration
        measurement_config = self.get_measurement_config()
        pol_steps = measurement_config.get("polarization_steps", 0)
        if pol_steps < 4:
            warnings.append(
                "Polarization steps should be at least 4 for meaningful analysis"
            )

        integration_time = measurement_config.get("integration_time", 0)
        if integration_time <= 0:
            errors.append("Integration time must be positive")

        return {"errors": errors, "warnings": warnings}

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.clear()
        self._initialize_config()
        self.save_config()

    def export_config(self, file_path: Union[str, Path]) -> bool:
        """
        Export configuration to a file.

        Args:
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            import json

            export_data = {
                "config_type": "urashg_plugin_config",
                "version": "1.0.0",
                "config": dict(self),
            }

            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting configuration: {e}")
            return False

    def import_config(self, file_path: Union[str, Path]) -> bool:
        """
        Import configuration from a file.

        Args:
            file_path: Path to import file

        Returns:
            True if successful, False otherwise
        """
        try:
            import json

            with open(file_path, "r") as f:
                import_data = json.load(f)

            if import_data.get("config_type") != "urashg_plugin_config":
                print("Invalid configuration file type")
                return False

            imported_config = import_data.get("config", {})

            # Merge with existing configuration
            for section, section_config in imported_config.items():
                self[section] = section_config

            self.save_config()
            return True

        except Exception as e:
            print(f"Error importing configuration: {e}")
            return False


# Global configuration instance
try:
    config = Config()
except Exception:
    # Fallback for environments where config cannot be initialized
    config = {}
