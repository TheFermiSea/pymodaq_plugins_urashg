# -*- coding: utf-8 -*-
"""
Utilities for URASHG plugins.
"""

from pymodaq_utils.logger import get_module_name, set_logger

# Configuration management
try:
    from .config import Config

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    Config = None

# PyRPL wrapper utilities for hardware integration
try:
    from .pyrpl_wrapper import (
        ASGChannel,
        ASGConfiguration,
        ASGTriggerSource,
        ASGWaveform,
        ConnectionState,
        InputChannel,
        IQChannel,
        IQConfiguration,
        IQOutputDirect,
        OutputChannel,
        PIDChannel,
        PIDConfiguration,
        PyRPLConnection,
        PyRPLManager,
        ScopeConfiguration,
        ScopeDecimation,
        ScopeTriggerSource,
        connect_redpitaya,
        disconnect_redpitaya,
        get_pyrpl_manager,
    )

    PYRPL_WRAPPER_AVAILABLE = True
except ImportError:
    # PyRPL not available - provide mock classes for development
    PYRPL_WRAPPER_AVAILABLE = False
    PyRPLManager = None
    PyRPLConnection = None

__all__ = [
    "set_logger",
    "get_module_name",
    "Config",
    "CONFIG_AVAILABLE",
    "PyRPLManager",
    "PyRPLConnection",
    "PIDChannel",
    "InputChannel",
    "OutputChannel",
    "PIDConfiguration",
    "ASGConfiguration",
    "IQConfiguration",
    "ScopeConfiguration",
    "ConnectionState",
    "ASGChannel",
    "ASGWaveform",
    "ASGTriggerSource",
    "IQChannel",
    "IQOutputDirect",
    "ScopeTriggerSource",
    "ScopeDecimation",
    "get_pyrpl_manager",
    "connect_redpitaya",
    "disconnect_redpitaya",
    "PYRPL_WRAPPER_AVAILABLE",
]
