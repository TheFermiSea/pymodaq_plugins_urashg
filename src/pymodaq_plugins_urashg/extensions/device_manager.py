# This file has been removed as it was causing conflicts with PyMoDAQ's plugin architecture.
#
# The original device_manager.py was attempting to directly instantiate and manage PyMoDAQ
# plugins outside of PyMoDAQ's framework, which violates PyMoDAQ's design principles and
# causes integration issues.
#
# Extensions should use PyMoDAQ's existing plugin management through the dashboard's
# modules_manager instead of creating parallel device management systems.
#
# For device coordination in extensions, use:
# - dashboard.modules_manager to access existing plugins
# - PyMoDAQ's standard plugin interfaces and signals
# - Proper PyMoDAQ extension patterns
#
# This removal should resolve plugin discovery and integration issues.
