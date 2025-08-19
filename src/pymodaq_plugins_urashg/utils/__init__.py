# -*- coding: utf-8 -*-
"""
Utilities for URASHG plugins.
"""

from pymodaq.utils.logger import set_logger, get_module_name

# PyRPL wrapper utilities for hardware integration
try:
    from .pyrpl_wrapper import (
        PyRPLManager,
        PyRPLConnection,
        PIDChannel,
        InputChannel,
        OutputChannel,
        PIDConfiguration,
        ASGConfiguration,
        IQConfiguration,
        ScopeConfiguration,
        ConnectionState,
        ASGChannel,
        ASGWaveform,
        ASGTriggerSource,
        IQChannel,
        IQOutputDirect,
        ScopeTriggerSource,
        ScopeDecimation,
        get_pyrpl_manager,
        connect_redpitaya,
        disconnect_redpitaya,
    )

    PYRPL_WRAPPER_AVAILABLE = True
except ImportError as e:
    # PyRPL not available - provide mock classes for development
    PYRPL_WRAPPER_AVAILABLE = False
    PyRPLManager = None
    PyRPLConnection = None

__all__ = [
    "set_logger",
    "get_module_name",
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
