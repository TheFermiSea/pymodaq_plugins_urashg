"""
Custom hardware-specific exceptions for the URASHG plugin.
"""

class HardwareError(Exception):
    """Base exception for hardware-related errors."""
    pass

class ESP300Error(HardwareError):
    """Custom exception for ESP300 motion controller errors."""
    pass

class MaiTaiError(HardwareError):
    """Custom exception for MaiTai laser errors."""
    pass

class Newport1830CError(HardwareError):
    """Custom exception for Newport 1830C power meter errors."""
    pass

class ElliptecError(HardwareError):
    """Custom exception for Elliptec rotation mount errors."""
    pass
