# -*- coding: utf-8 -*-
"""
Utilities for URASHG plugins.
"""

from pathlib import Path
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import BaseConfig, USER


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.joinpath('resources/config_template.toml')
    config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"

# PyRPL wrapper utilities for hardware integration
try:
    from .pyrpl_wrapper import (
        PyRPLManager, PyRPLConnection, PIDChannel, InputChannel, OutputChannel,
        PIDConfiguration, ASGConfiguration, IQConfiguration, ScopeConfiguration,
        ConnectionState, ASGChannel, ASGWaveform, ASGTriggerSource,
        IQChannel, IQOutputDirect, ScopeTriggerSource, ScopeDecimation,
        get_pyrpl_manager, connect_redpitaya, disconnect_redpitaya
    )
    PYRPL_WRAPPER_AVAILABLE = True
except ImportError as e:
    # PyRPL not available - provide mock classes for development
    PYRPL_WRAPPER_AVAILABLE = False
    PyRPLManager = None
    PyRPLConnection = None
    PIDChannel = None
    InputChannel = None
    OutputChannel = None
    PIDConfiguration = None
    ASGConfiguration = None
    IQConfiguration = None
    ScopeConfiguration = None
    ConnectionState = None
    ASGChannel = None
    ASGWaveform = None
    ASGTriggerSource = None
    IQChannel = None
    IQOutputDirect = None
    ScopeTriggerSource = None
    ScopeDecimation = None
    get_pyrpl_manager = None
    connect_redpitaya = None
    disconnect_redpitaya = None

__all__ = [
    'set_logger', 'get_module_name', 'Config',
    'PyRPLManager', 'PyRPLConnection', 'PIDChannel', 'InputChannel', 'OutputChannel',
    'PIDConfiguration', 'ASGConfiguration', 'IQConfiguration', 'ScopeConfiguration',
    'ConnectionState', 'ASGChannel', 'ASGWaveform', 'ASGTriggerSource',
    'IQChannel', 'IQOutputDirect', 'ScopeTriggerSource', 'ScopeDecimation',
    'get_pyrpl_manager', 'connect_redpitaya', 'disconnect_redpitaya',
    'PYRPL_WRAPPER_AVAILABLE'
]
