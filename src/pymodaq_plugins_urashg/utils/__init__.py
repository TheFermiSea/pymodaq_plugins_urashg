# -*- coding: utf-8 -*-
"""
Utilities for URASHG plugins.
"""

from pathlib import Path

# Handle missing PyMoDAQ dependencies gracefully
try:
    from pymodaq_utils.config import USER, BaseConfig
    from pymodaq_utils.logger import get_module_name, set_logger

    class Config(BaseConfig):
        """Main class to deal with configuration values for this plugin"""

        config_template_path = Path(__file__).parent.parent.joinpath(
            "resources/config_template.toml"
        )
        config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"

except ImportError:
    # Fallback for environments without PyMoDAQ
    import logging

    USER = "user"

    class Config:
        """Minimal config fallback for testing environments"""
        config_template_path = Path(__file__).parent.parent.joinpath(
            "resources/config_template.toml"
        )
        config_name = "config_urashg"

    def get_module_name(name):
        return name.split('.')[-1] if '.' in name else name

    def set_logger(name, level=logging.INFO, add_to_console=True, **kwargs):
        return logging.getLogger(name)


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
except ImportError as e:
    # PyRPL not available - provide mock classes for development
    import logging
    from enum import Enum

    logger = logging.getLogger(__name__)
    logger.info(f"PyRPL wrapper not available ({e}), using mock classes for development")

    PYRPL_WRAPPER_AVAILABLE = False

    # Create proper mock enum classes to prevent NameError
    class MockPIDChannel(Enum):
        PID0 = "pid0"
        PID1 = "pid1"
        PID2 = "pid2"

    class MockInputChannel(Enum):
        IN1 = "in1"
        IN2 = "in2"

    class MockOutputChannel(Enum):
        OUT1 = "out1"
        OUT2 = "out2"

    class MockConnectionState(Enum):
        CONNECTED = "connected"
        DISCONNECTED = "disconnected"
        ERROR = "error"

    class MockASGChannel(Enum):
        ASG0 = "asg0"
        ASG1 = "asg1"

    class MockASGWaveform(Enum):
        SIN = "sin"
        COS = "cos"
        SQUARE = "square"

    class MockASGTriggerSource(Enum):
        IMMEDIATELY = "immediately"
        EXT_POSITIVE_EDGE = "ext_positive_edge"

    class MockIQChannel(Enum):
        IQ0 = "iq0"
        IQ1 = "iq1"
        IQ2 = "iq2"

    class MockIQOutputDirect(Enum):
        OFF = "off"
        OUT1 = "out1"
        OUT2 = "out2"

    class MockScopeTriggerSource(Enum):
        IMMEDIATELY = "immediately"
        CH1_POSITIVE_EDGE = "ch1_positive_edge"

    class MockScopeDecimation(Enum):
        DEC_1 = 1
        DEC_64 = 64
        DEC_1024 = 1024

    # Mock configuration classes
    class MockConfiguration:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    # Assign mock classes
    PyRPLManager = None
    PyRPLConnection = None
    PIDChannel = MockPIDChannel
    InputChannel = MockInputChannel
    OutputChannel = MockOutputChannel
    PIDConfiguration = MockConfiguration
    ASGConfiguration = MockConfiguration
    IQConfiguration = MockConfiguration
    ScopeConfiguration = MockConfiguration
    ConnectionState = MockConnectionState
    ASGChannel = MockASGChannel
    ASGWaveform = MockASGWaveform
    ASGTriggerSource = MockASGTriggerSource
    IQChannel = MockIQChannel
    IQOutputDirect = MockIQOutputDirect
    ScopeTriggerSource = MockScopeTriggerSource
    ScopeDecimation = MockScopeDecimation
    get_pyrpl_manager = lambda: None
    connect_redpitaya = lambda *args, **kwargs: None
    disconnect_redpitaya = lambda *args, **kwargs: None

__all__ = [
    "set_logger",
    "get_module_name",
    "Config",
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
