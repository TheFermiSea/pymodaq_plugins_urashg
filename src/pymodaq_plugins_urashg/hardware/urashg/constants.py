"""
Hardware Constants for URASHG System

This module defines hardware-specific constants used throughout the system.
"""

# Red Pitaya FPGA Memory Map
REDPITAYA_BASE_ADDRESS = 0x40300000

# PID Register Offsets (relative to base address)
PID_REGISTER_OFFSETS = {
    "kp": 0x00,
    "ki": 0x04,
    "kd": 0x08,
    "setpoint": 0x0C,
    "error": 0x10,
    "output": 0x14,
}

# Elliptec Communication Settings
ELLIPTEC_BAUD_RATE = 9600

# Camera Default Settings
CAMERA_DEFAULT_SETTINGS = {
    "exposure_ms": 100.0,
    "gain": 1,
    "roi": (0, 0, 2048, 2048),
    "trigger_mode": "internal",
}

# MaiTai Communication Settings
MAITAI_COMMUNICATION_SETTINGS = {
    "baud_rate": 9600,
    "timeout": 1.0,
    "terminator": "\r\n",
}
