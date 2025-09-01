"""
Hardware Utility Functions for URASHG System

This module provides utility functions for hardware configuration validation,
unit conversions, and system calculations.
"""

import numpy as np


def validate_hardware_configuration(config):
    """
    Validate hardware configuration parameters.

    Args:
        config (dict): Hardware configuration dictionary

    Returns:
        bool: True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ["laser_power_mw", "camera_exposure_ms"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    return True


def convert_physical_to_fpga_units(physical_value, unit_type="voltage"):
    """
    Convert physical units to FPGA register values.

    Args:
        physical_value (float): Value in physical units
        unit_type (str): Type of unit conversion

    Returns:
        int: FPGA register value
    """
    if unit_type == "voltage":
        # Convert voltage (V) to 14-bit signed integer
        return int((physical_value / 1.0) * 8192)
    elif unit_type == "power":
        # Convert power (mW) to control signal
        return int((physical_value / 1000.0) * 8192)
    else:
        return int(physical_value)


def convert_fpga_to_physical_units(fpga_value, unit_type="voltage"):
    """
    Convert FPGA register values to physical units.

    Args:
        fpga_value (int): FPGA register value
        unit_type (str): Type of unit conversion

    Returns:
        float: Value in physical units
    """
    if unit_type == "voltage":
        # Convert 14-bit signed integer to voltage (V)
        return (fpga_value / 8192.0) * 1.0
    elif unit_type == "power":
        # Convert control signal to power (mW)
        return (fpga_value / 8192.0) * 1000.0
    else:
        return float(fpga_value)


def calculate_polarization_matrix(angles_deg):
    """
    Calculate polarization transformation matrix for given angles.

    Args:
        angles_deg (tuple): Angles in degrees (qwp, hwp_inc, hwp_ana)

    Returns:
        np.ndarray: 2x2 polarization matrix
    """
    qwp, hwp_inc, hwp_ana = angles_deg

    # Convert to radians
    qwp_rad = np.radians(qwp)
    hwp_inc_rad = np.radians(hwp_inc)
    hwp_ana_rad = np.radians(hwp_ana)

    # Simplified polarization matrix calculation
    matrix = np.array(
        [
            [
                np.cos(qwp_rad) * np.cos(hwp_inc_rad),
                -np.sin(qwp_rad) * np.sin(hwp_inc_rad),
            ],
            [
                np.sin(qwp_rad) * np.cos(hwp_ana_rad),
                np.cos(qwp_rad) * np.sin(hwp_ana_rad),
            ],
        ]
    )

    return matrix


def estimate_measurement_time(config):
    """
    Estimate total measurement time based on configuration.

    Args:
        config (dict): Measurement configuration

    Returns:
        float: Estimated time in seconds
    """
    exposure_ms = config.get("camera_exposure_ms", 100.0)
    averaging_frames = config.get("averaging_frames", 1)
    angle_steps = config.get("angle_steps", 36)

    # Add overhead for polarization adjustment and data transfer
    overhead_per_step = 500  # ms

    total_time_ms = (exposure_ms + overhead_per_step) * averaging_frames * angle_steps

    return total_time_ms / 1000.0  # Convert to seconds
