# -*- coding: utf-8 -*-
"""
PyRPL Wrapper Utilities for PyMoDAQ URASHG Plugin Suite

This module provides centralized PyRPL connection management, preventing conflicts
between multiple plugins and providing a clean abstraction layer for Red Pitaya
hardware control within the URASHG polarimetry measurement system.

Classes:
    PyRPLConnection: Manages individual Red Pitaya device connections
    PyRPLManager: Singleton connection pool manager
"""

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Set up logger early to avoid NameError in exception handlers
logger = logging.getLogger(__name__)

try:
    # Python 3.10+ compatibility fix for collections.Mapping
    import collections
    import collections.abc

    if not hasattr(collections, "Mapping"):
        collections.Mapping = collections.abc.Mapping
        collections.MutableMapping = collections.abc.MutableMapping
        collections.MutableSet = collections.abc.MutableSet
        collections.Set = collections.abc.Set
        collections.MutableSequence = collections.abc.MutableSequence
        collections.Sequence = collections.abc.Sequence
        collections.Iterable = collections.abc.Iterable
        collections.Iterator = collections.abc.Iterator
        collections.Container = collections.abc.Container
        collections.Sized = collections.abc.Sized
        collections.Callable = collections.abc.Callable
        collections.Hashable = collections.abc.Hashable

    # NumPy 1.20+ compatibility fix for np.complex
    if not hasattr(np, "complex"):
        np.complex = complex
        np.complex_ = complex

    # Qt timer compatibility fix - patch before importing pyrpl
    try:
        from qtpy.QtCore import QTimer

        original_setInterval = QTimer.setInterval

        def setInterval_patched(self, msec):
            """Patched setInterval to handle float inputs properly."""
            return original_setInterval(self, int(msec))

        QTimer.setInterval = setInterval_patched
    except ImportError:
        pass  # Qt not available, skip timer patch

    import pyrpl

    PYRPL_AVAILABLE = True
    PYRPL_MOCK = False
    from pyrpl.hardware_modules.pid import Pid as PidModule

    logger.info("PyRPL library imported successfully")
except (ImportError, TypeError, AttributeError) as e:
    # Handle PyRPL import issues (e.g., Qt compatibility problems)
    logger.warning(f"PyRPL import failed: {e}")
    logger.info("Attempting to load mock PyRPL implementation...")

    try:
        # Import our mock PyRPL implementation
        import pymodaq_plugins_urashg.utils.pyrpl_mock as pyrpl

        from .pyrpl_mock import MockPID, MockPyrpl

        PYRPL_AVAILABLE = True  # Mock is available for development
        PYRPL_MOCK = True
        PidModule = MockPID
        logger.info("Mock PyRPL implementation loaded successfully")
    except ImportError as mock_err:
        logger.error(f"Failed to load mock PyRPL: {mock_err}")
        PYRPL_AVAILABLE = False
        PYRPL_MOCK = False
        pyrpl = None
        PidModule = object  # Final fallback

        # Create a basic mock Pyrpl class for type hints
        class _MockPyrpl:
            pass

        pyrpl = type("MockPyrplModule", (), {"Pyrpl": _MockPyrpl})()

from pymodaq.utils.daq_utils import ThreadCommand


class ConnectionState(Enum):
    """Connection states for PyRPL devices."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class PIDChannel(Enum):
    """Available PID channels on Red Pitaya."""

    PID0 = "pid0"
    PID1 = "pid1"
    PID2 = "pid2"


class InputChannel(Enum):
    """Available input channels on Red Pitaya."""

    IN1 = "in1"
    IN2 = "in2"


class OutputChannel(Enum):
    """Available output channels on Red Pitaya."""

    OUT1 = "out1"
    OUT2 = "out2"


class ASGChannel(Enum):
    """Available ASG (Arbitrary Signal Generator) channels on Red Pitaya."""

    ASG0 = "asg0"
    ASG1 = "asg1"


class ASGWaveform(Enum):
    """Available waveforms for ASG."""

    SIN = "sin"
    COS = "cos"
    RAMP = "ramp"
    HALFRAMP = "halframp"
    SQUARE = "square"
    NOISE = "noise"
    DC = "dc"
    CUSTOM = "custom"


class ASGTriggerSource(Enum):
    """Available trigger sources for ASG."""

    OFF = "off"
    IMMEDIATELY = "immediately"
    EXT_POSITIVE_EDGE = "ext_positive_edge"
    EXT_NEGATIVE_EDGE = "ext_negative_edge"
    EXT_POSITIVE_LEVEL = "ext_positive_level"
    EXT_NEGATIVE_LEVEL = "ext_negative_level"


class IQChannel(Enum):
    """Available IQ (Lock-in Amplifier) channels on Red Pitaya."""

    IQ0 = "iq0"
    IQ1 = "iq1"
    IQ2 = "iq2"


class IQOutputDirect(Enum):
    """Available output routing for IQ modules."""

    OFF = "off"
    OUT1 = "out1"
    OUT2 = "out2"


class ScopeTriggerSource(Enum):
    """Available trigger sources for Scope."""

    IMMEDIATELY = "immediately"
    CH1_POSITIVE_EDGE = "ch1_positive_edge"
    CH1_NEGATIVE_EDGE = "ch1_negative_edge"
    CH2_POSITIVE_EDGE = "ch2_positive_edge"
    CH2_NEGATIVE_EDGE = "ch2_negative_edge"
    EXT_POSITIVE_EDGE = "ext_positive_edge"
    EXT_NEGATIVE_EDGE = "ext_negative_edge"


class ScopeDecimation(Enum):
    """Available decimation values for Scope."""

    DEC_1 = 1
    DEC_8 = 8
    DEC_64 = 64
    DEC_1024 = 1024
    DEC_8192 = 8192
    DEC_65536 = 65536


@dataclass
class PIDConfiguration:
    """Configuration for a PID controller."""

    setpoint: float = 0.0
    p_gain: float = 0.1
    i_gain: float = 0.0
    d_gain: float = 0.0
    input_channel: InputChannel = InputChannel.IN1
    output_channel: OutputChannel = OutputChannel.OUT1
    voltage_limit_min: float = -1.0
    voltage_limit_max: float = 1.0
    enabled: bool = False


@dataclass
class ASGConfiguration:
    """Configuration for an Arbitrary Signal Generator."""

    frequency: float = 1000.0  # Hz
    amplitude: float = 0.1  # V
    offset: float = 0.0  # V
    phase: float = 0.0  # degrees
    waveform: ASGWaveform = ASGWaveform.SIN
    trigger_source: ASGTriggerSource = ASGTriggerSource.IMMEDIATELY
    output_enable: bool = True
    frequency_min: float = 0.0
    frequency_max: float = 62.5e6  # 62.5 MHz max frequency for Red Pitaya
    amplitude_min: float = -1.0
    amplitude_max: float = 1.0
    offset_min: float = -1.0
    offset_max: float = 1.0


@dataclass
class IQConfiguration:
    """Configuration for IQ (Lock-in Amplifier) module."""

    frequency: float = 1000.0  # Hz
    bandwidth: float = 100.0  # Hz
    acbandwidth: float = 10000.0  # Hz, AC bandwidth/inputfilter
    phase: float = 0.0  # degrees
    gain: float = 1.0  # amplification factor
    quadrature_factor: float = 1.0  # quadrature signal factor
    amplitude: float = 0.0  # V, output amplitude
    input_channel: InputChannel = InputChannel.IN1
    output_direct: IQOutputDirect = IQOutputDirect.OFF
    frequency_min: float = 0.1
    frequency_max: float = 62.5e6  # 62.5 MHz max frequency for Red Pitaya
    bandwidth_min: float = 0.01
    bandwidth_max: float = 62.5e6
    acbandwidth_max: float = 62.5e6
    phase_min: float = -180.0
    phase_max: float = 180.0
    gain_min: float = 0.001
    gain_max: float = 1000.0
    quadrature_factor_min: float = -10.0
    quadrature_factor_max: float = 10.0
    amplitude_min: float = -1.0
    amplitude_max: float = 1.0


@dataclass
class ScopeConfiguration:
    """Configuration for Scope module."""

    input_channel: InputChannel = InputChannel.IN1
    decimation: ScopeDecimation = ScopeDecimation.DEC_64
    trigger_source: ScopeTriggerSource = ScopeTriggerSource.IMMEDIATELY
    trigger_delay: int = 0  # 0 to 16383 samples
    trigger_level: float = 0.0  # -1.0 to 1.0 V
    average: int = 1  # 1 to 1000 averages
    rolling_mode: bool = False
    timeout: float = 5.0  # acquisition timeout in seconds
    data_length: int = 16384  # 2^14 samples fixed for Red Pitaya


@dataclass
class ConnectionInfo:
    """Information about a Red Pitaya connection."""

    hostname: str
    config_name: str = "urashg"
    port: int = 2222
    connection_timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


class PyRPLConnection:
    """
    Manages a single Red Pitaya connection with thread-safe operations.

    This class handles the connection lifecycle, PID module management,
    and provides safe access to hardware resources for URASHG polarimetry
    measurements with laser power stabilization.

    Attributes:
        hostname (str): Red Pitaya hostname or IP address
        config_name (str): PyRPL configuration name
        state (ConnectionState): Current connection state
        last_error (Optional[str]): Last error message if any
    """

    def __init__(self, connection_info: ConnectionInfo):
        self.hostname = connection_info.hostname
        self.config_name = connection_info.config_name
        self.port = connection_info.port
        self.connection_timeout = connection_info.connection_timeout
        self.retry_attempts = connection_info.retry_attempts
        self.retry_delay = connection_info.retry_delay

        self.state = ConnectionState.DISCONNECTED
        self.last_error: Optional[str] = None
        self.connected_at: Optional[float] = None

        # PyRPL objects
        self._pyrpl: Optional[pyrpl.Pyrpl] = None
        self._redpitaya: Optional[Any] = None

        # Thread safety
        self._lock = threading.RLock()
        self._connection_lock = threading.Lock()

        # PID modules tracking
        self._active_pids: Dict[PIDChannel, PidModule] = {}
        self._pid_configs: Dict[PIDChannel, PIDConfiguration] = {}

        # ASG modules tracking
        self._active_asgs: Dict[ASGChannel, Any] = {}
        self._asg_configs: Dict[ASGChannel, ASGConfiguration] = {}

        # IQ modules tracking
        self._active_iqs: Dict[IQChannel, Any] = {}
        self._iq_configs: Dict[IQChannel, IQConfiguration] = {}

        # Scope module tracking
        self._scope_module: Optional[Any] = None
        self._scope_config: Optional[ScopeConfiguration] = None

        # Reference counting for proper cleanup
        self._ref_count = 0

    @property
    def is_connected(self) -> bool:
        """Check if the connection is active and healthy."""
        with self._lock:
            return (
                self.state == ConnectionState.CONNECTED
                and self._pyrpl is not None
                and self._redpitaya is not None
            )

    @property
    def pyrpl(self) -> Optional[pyrpl.Pyrpl]:
        """Get the PyRPL instance (thread-safe)."""
        with self._lock:
            return self._pyrpl

    @property
    def redpitaya(self) -> Optional[Any]:
        """Get the Red Pitaya instance (thread-safe)."""
        with self._lock:
            return self._redpitaya

    def connect(self, status_callback: Optional[callable] = None) -> bool:
        """
        Establish connection to Red Pitaya.

        Args:
            status_callback: Optional callback for status updates

        Returns:
            bool: True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self.is_connected:
                logger.debug(f"Already connected to {self.hostname}")
                return True

            self.state = ConnectionState.CONNECTING
            self.last_error = None

            if status_callback:
                status_callback(
                    ThreadCommand(
                        "Update_Status",
                        [f"Connecting to Red Pitaya at {self.hostname}", "log"],
                    )
                )

            for attempt in range(self.retry_attempts):
                try:
                    logger.info(
                        f"Connection attempt {attempt + 1}/{self.retry_attempts} to {self.hostname}"
                    )

                    # Create PyRPL connection
                    self._pyrpl = pyrpl.Pyrpl(
                        config=self.config_name,
                        hostname=self.hostname,
                        port=self.port,
                        timeout=self.connection_timeout,
                    )

                    self._redpitaya = self._pyrpl.rp

                    # Connection is successful if we reach this point
                    # Skip version check due to PyRPL compatibility issues
                    logger.debug(f"PyRPL connection established to {self.hostname}")

                    self.state = ConnectionState.CONNECTED
                    self.connected_at = time.time()
                    self.last_error = None

                    logger.info(f"Successfully connected to Red Pitaya {self.hostname}")

                    if status_callback:
                        status_callback(
                            ThreadCommand(
                                "Update_Status",
                                [f"Red Pitaya {self.hostname} connected", "log"],
                            )
                        )

                    return True

                except ZeroDivisionError as e:
                    # PyRPL sometimes has division by zero errors during module loading
                    # but the connection itself is successful, so ignore these
                    logger.debug(f"Ignoring PyRPL ZeroDivisionError: {e}")
                    if self._pyrpl and self._redpitaya:
                        logger.info(
                            f"PyRPL connection successful despite ZeroDivisionError"
                        )
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True
                    # If no connection objects, treat as real error
                    error_msg = f"Connection attempt {attempt + 1} failed: {str(e)}"
                    logger.warning(error_msg)
                    self.last_error = str(e)

                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

                except Exception as e:
                    # Check if this is a PyRPL-related error that we can ignore
                    error_str = str(e)
                    if (
                        "float division by zero" in error_str
                        and self._pyrpl
                        and self._redpitaya
                    ):
                        logger.info(
                            f"PyRPL connection successful despite error: {error_str}"
                        )
                        self.state = ConnectionState.CONNECTED
                        self.connected_at = time.time()
                        self.last_error = None
                        return True

                    error_msg = f"Connection attempt {attempt + 1} failed: {error_str}"
                    logger.warning(error_msg)
                    self.last_error = error_str

                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)

            # All attempts failed
            self.state = ConnectionState.ERROR
            error_msg = f"Failed to connect to {self.hostname} after {self.retry_attempts} attempts"
            logger.error(error_msg)

            if status_callback:
                status_callback(ThreadCommand("Update_Status", [error_msg, "log"]))

            return False

    def disconnect(self, status_callback: Optional[callable] = None) -> None:
        """
        Safely disconnect from Red Pitaya.

        Args:
            status_callback: Optional callback for status updates
        """
        with self._connection_lock:
            if not self.is_connected:
                return

            try:
                if status_callback:
                    status_callback(
                        ThreadCommand(
                            "Update_Status",
                            [f"Disconnecting from {self.hostname}", "log"],
                        )
                    )

                # Safely disable all active PIDs, ASGs, IQs, and Scope
                self._disable_all_pids()
                self._disable_all_asgs()
                self._disable_all_iqs()
                self._disable_scope()

                # Close PyRPL connection
                if self._pyrpl is not None:
                    self._pyrpl.close()

                self._pyrpl = None
                self._redpitaya = None
                self._active_pids.clear()
                self._pid_configs.clear()
                self._active_asgs.clear()
                self._asg_configs.clear()
                self._active_iqs.clear()
                self._iq_configs.clear()
                self._scope_module = None
                self._scope_config = None

                self.state = ConnectionState.DISCONNECTED
                self.connected_at = None

                logger.info(f"Disconnected from Red Pitaya {self.hostname}")

                if status_callback:
                    status_callback(
                        ThreadCommand(
                            "Update_Status",
                            [f"Disconnected from {self.hostname}", "log"],
                        )
                    )

            except Exception as e:
                error_msg = f"Error during disconnect from {self.hostname}: {str(e)}"
                logger.error(error_msg)
                self.last_error = str(e)
                self.state = ConnectionState.ERROR

    def _disable_all_pids(self) -> None:
        """Safely disable all active PID controllers."""
        for pid_channel, pid_module in self._active_pids.items():
            try:
                pid_module.output_direct = "off"
                pid_module.input = "off"
                logger.debug(f"Disabled PID {pid_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable PID {pid_channel.value}: {e}")

    def _disable_all_asgs(self) -> None:
        """Safely disable all active ASG modules."""
        for asg_channel, asg_module in self._active_asgs.items():
            try:
                asg_module.output_direct = "off"
                asg_module.trigger_source = "off"
                logger.debug(f"Disabled ASG {asg_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable ASG {asg_channel.value}: {e}")

    def _disable_all_iqs(self) -> None:
        """Safely disable all active IQ modules."""
        for iq_channel, iq_module in self._active_iqs.items():
            try:
                iq_module.output_direct = "off"
                iq_module.input = "off"
                logger.debug(f"Disabled IQ {iq_channel.value}")
            except Exception as e:
                logger.warning(f"Failed to disable IQ {iq_channel.value}: {e}")

    def _disable_scope(self) -> None:
        """Safely disable scope module."""
        if self._scope_module is not None:
            try:
                # Stop any ongoing acquisition
                self._scope_module.trigger_source = "off"
                logger.debug("Disabled scope module")
            except Exception as e:
                logger.warning(f"Failed to disable scope: {e}")

    def get_pid_module(self, channel: PIDChannel) -> Optional[PidModule]:
        """
        Get a PID module for the specified channel.

        Args:
            channel: PID channel to retrieve

        Returns:
            PidModule or None if not available
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                if channel not in self._active_pids:
                    pid_module = getattr(self._redpitaya, channel.value)
                    self._active_pids[channel] = pid_module

                return self._active_pids[channel]

            except Exception as e:
                logger.error(f"Failed to get PID module {channel.value}: {e}")
                return None

    def configure_pid(self, channel: PIDChannel, config: PIDConfiguration) -> bool:
        """
        Configure a PID controller with the specified parameters.

        Args:
            channel: PID channel to configure
            config: PID configuration parameters

        Returns:
            bool: True if configuration successful
        """
        with self._lock:
            if not self.is_connected:
                logger.error(f"Cannot configure PID {channel.value}: not connected")
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                # Store configuration
                self._pid_configs[channel] = config

                # Configure PID parameters
                pid_module.setpoint = config.setpoint
                pid_module.p = config.p_gain
                pid_module.i = config.i_gain
                pid_module.d = config.d_gain

                # Configure input/output routing
                pid_module.input = config.input_channel.value
                if config.enabled:
                    pid_module.output_direct = config.output_channel.value
                else:
                    pid_module.output_direct = "off"

                # Set voltage limits
                pid_module.max_voltage = config.voltage_limit_max
                pid_module.min_voltage = config.voltage_limit_min

                logger.debug(
                    f"Configured PID {channel.value} with setpoint {config.setpoint}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to configure PID {channel.value}: {e}")
                return False

    def set_pid_setpoint(self, channel: PIDChannel, setpoint: float) -> bool:
        """
        Set the setpoint for a PID controller.

        Args:
            channel: PID channel
            setpoint: New setpoint value

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                pid_module.setpoint = setpoint

                # Update stored configuration
                if channel in self._pid_configs:
                    self._pid_configs[channel].setpoint = setpoint

                return True

            except Exception as e:
                logger.error(f"Failed to set setpoint for PID {channel.value}: {e}")
                return False

    def get_pid_setpoint(self, channel: PIDChannel) -> Optional[float]:
        """
        Get the current setpoint for a PID controller.

        Args:
            channel: PID channel

        Returns:
            Current setpoint or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return None

                return pid_module.setpoint

            except Exception as e:
                logger.error(f"Failed to get setpoint for PID {channel.value}: {e}")
                return None

    def enable_pid(self, channel: PIDChannel) -> bool:
        """
        Enable a PID controller.

        Args:
            channel: PID channel to enable

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None or channel not in self._pid_configs:
                    return False

                config = self._pid_configs[channel]
                pid_module.output_direct = config.output_channel.value
                config.enabled = True

                logger.debug(f"Enabled PID {channel.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to enable PID {channel.value}: {e}")
                return False

    def disable_pid(self, channel: PIDChannel) -> bool:
        """
        Disable a PID controller.

        Args:
            channel: PID channel to disable

        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.is_connected:
                return False

            try:
                pid_module = self.get_pid_module(channel)
                if pid_module is None:
                    return False

                pid_module.output_direct = "off"

                if channel in self._pid_configs:
                    self._pid_configs[channel].enabled = False

                logger.debug(f"Disabled PID {channel.value}")
                return True

            except Exception as e:
                logger.error(f"Failed to disable PID {channel.value}: {e}")
                return False

    def read_voltage(self, channel: InputChannel) -> Optional[float]:
        """
        Read voltage from an input channel.

        Args:
            channel: Input channel to read

        Returns:
            Voltage value or None if error
        """
        with self._lock:
            if not self.is_connected:
                return None

            try:
                # Use scope for fast voltage reading
                if hasattr(self._redpitaya, "scope"):
                    scope = self._redpitaya.scope
                    if channel == InputChannel.IN1:
                        return scope.voltage_in1
                    elif channel == InputChannel.IN2:
                        return scope.voltage_in2

                # Fallback to sampler if scope not available
                if hasattr(self._redpitaya, "sampler"):
                    sampler = self._redpitaya.sampler
                    return getattr(sampler, channel.value)

                logger.warning(
                    "Neither scope nor sampler available for voltage reading"
                )
                return None

            except Exception as e:
                logger.error(f"Failed to read voltage from {channel.value}: {e}")
                return None

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get detailed connection information.

        Returns:
            Dictionary with connection details
        """
        with self._lock:
            return {
                "hostname": self.hostname,
                "config_name": self.config_name,
                "state": self.state.value,
                "connected_at": self.connected_at,
                "last_error": self.last_error,
                "active_pids": list(self._active_pids.keys()),
                "active_asgs": list(self._active_asgs.keys()),
                "active_iqs": list(self._active_iqs.keys()),
                "scope_configured": self._scope_config is not None,
                "ref_count": self._ref_count,
            }

    @contextmanager
    def acquire_reference(self):
        """
        Context manager for reference counting.

        Usage:
            with connection.acquire_reference():
                # Use connection safely
                pass
        """
        with self._lock:
            self._ref_count += 1
        try:
            yield self
        finally:
            with self._lock:
                self._ref_count -= 1

    def __enter__(self):
        """Context manager entry."""
        return self.acquire_reference().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # This is handled by acquire_reference context manager
        pass


class PyRPLManager:
    """
    Singleton manager for PyRPL connections for URASHG plugin suite.

    Provides centralized connection pooling to prevent conflicts between
    multiple PyMoDAQ plugins accessing the same Red Pitaya devices during
    wavelength-dependent polarimetry measurements.
    """

    _instance: Optional["PyRPLManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "PyRPLManager":
        """Singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager (called only once due to singleton)."""
        if self._initialized:
            return

        self._connections: Dict[str, PyRPLConnection] = {}
        self._manager_lock = threading.RLock()
        self._initialized = True

        logger.info("PyRPL Manager initialized for URASHG")

    def get_connection(
        self, hostname: str, config_name: str = "urashg", **connection_kwargs
    ) -> Optional[PyRPLConnection]:
        """
        Get or create a connection to a Red Pitaya device.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name (defaults to "urashg")
            **connection_kwargs: Additional connection parameters

        Returns:
            PyRPLConnection instance or None if creation failed
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key in self._connections:
                connection = self._connections[connection_key]
                logger.debug(f"Returning existing connection to {hostname}")
                return connection

            # Create new connection
            connection_info = ConnectionInfo(
                hostname=hostname, config_name=config_name, **connection_kwargs
            )

            try:
                connection = PyRPLConnection(connection_info)
                self._connections[connection_key] = connection
                logger.info(f"Created new connection to {hostname}")
                return connection

            except Exception as e:
                logger.error(f"Failed to create connection to {hostname}: {e}")
                return None

    def connect_device(
        self,
        hostname: str,
        config_name: str = "urashg",
        status_callback: Optional[callable] = None,
        **connection_kwargs,
    ) -> Optional[PyRPLConnection]:
        """
        Connect to a Red Pitaya device for URASHG measurements.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name (defaults to "urashg")
            status_callback: Optional callback for status updates
            **connection_kwargs: Additional connection parameters

        Returns:
            Connected PyRPLConnection instance or None if failed
        """
        connection = self.get_connection(hostname, config_name, **connection_kwargs)

        if connection is None:
            return None

        if connection.connect(status_callback):
            return connection
        else:
            return None

    def disconnect_device(
        self,
        hostname: str,
        config_name: str = "urashg",
        status_callback: Optional[callable] = None,
    ) -> bool:
        """
        Disconnect from a Red Pitaya device.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name
            status_callback: Optional callback for status updates

        Returns:
            bool: True if successful
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key not in self._connections:
                return True  # Already disconnected

            connection = self._connections[connection_key]

            # Check if connection is still in use
            if connection._ref_count > 0:
                logger.warning(
                    f"Connection {hostname} still has active references, disconnecting anyway"
                )

            connection.disconnect(status_callback)
            return True

    def remove_connection(self, hostname: str, config_name: str = "urashg") -> bool:
        """
        Remove a connection from the manager.

        Args:
            hostname: Red Pitaya hostname or IP address
            config_name: PyRPL configuration name

        Returns:
            bool: True if removed successfully
        """
        with self._manager_lock:
            connection_key = f"{hostname}:{config_name}"

            if connection_key in self._connections:
                connection = self._connections[connection_key]

                # Ensure connection is disconnected
                if connection.is_connected:
                    connection.disconnect()

                del self._connections[connection_key]
                logger.info(f"Removed connection to {hostname}")
                return True

            return False

    def get_all_connections(self) -> Dict[str, PyRPLConnection]:
        """
        Get all active connections.

        Returns:
            Dictionary mapping connection keys to PyRPLConnection instances
        """
        with self._manager_lock:
            return self._connections.copy()

    def disconnect_all(self, status_callback: Optional[callable] = None) -> None:
        """
        Disconnect all active connections.

        Args:
            status_callback: Optional callback for status updates
        """
        with self._manager_lock:
            for connection_key, connection in list(self._connections.items()):
                try:
                    connection.disconnect(status_callback)
                except Exception as e:
                    logger.error(f"Error disconnecting {connection_key}: {e}")

    def cleanup(self) -> None:
        """
        Clean up all connections and resources.
        """
        logger.info("Cleaning up PyRPL Manager")
        self.disconnect_all()

        with self._manager_lock:
            self._connections.clear()

    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get detailed manager status.

        Returns:
            Dictionary with manager status information
        """
        with self._manager_lock:
            connections_info = {}
            for key, conn in self._connections.items():
                connections_info[key] = conn.get_connection_info()

            return {
                "total_connections": len(self._connections),
                "connections": connections_info,
            }

    @classmethod
    def get_instance(cls) -> "PyRPLManager":
        """Get the singleton instance."""
        return cls()


# Convenience functions for easy access
def get_pyrpl_manager() -> PyRPLManager:
    """Get the global PyRPL manager instance for URASHG."""
    return PyRPLManager.get_instance()


def connect_redpitaya(
    hostname: str,
    config_name: str = "urashg",
    status_callback: Optional[callable] = None,
    **kwargs,
) -> Optional[PyRPLConnection]:
    """
    Convenience function to connect to a Red Pitaya device for URASHG.

    Args:
        hostname: Red Pitaya hostname or IP address
        config_name: PyRPL configuration name (defaults to "urashg")
        status_callback: Optional callback for status updates
        **kwargs: Additional connection parameters

    Returns:
        Connected PyRPLConnection instance or None if failed

    Example:
        >>> connection = connect_redpitaya('rp-f08d6c.local')
        >>> if connection and connection.is_connected:
        ...     voltage = connection.read_voltage(InputChannel.IN1)
        ...     print(f"Input voltage: {voltage}V")
    """
    manager = get_pyrpl_manager()
    return manager.connect_device(hostname, config_name, status_callback, **kwargs)


def disconnect_redpitaya(
    hostname: str,
    config_name: str = "urashg",
    status_callback: Optional[callable] = None,
) -> bool:
    """
    Convenience function to disconnect from a Red Pitaya device.

    Args:
        hostname: Red Pitaya hostname or IP address
        config_name: PyRPL configuration name
        status_callback: Optional callback for status updates

    Returns:
        bool: True if successful
    """
    manager = get_pyrpl_manager()
    return manager.disconnect_device(hostname, config_name, status_callback)


if __name__ == "__main__":
    # Example usage and testing for URASHG
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Usage: python pyrpl_wrapper.py <hostname>")
        sys.exit(1)

    hostname = sys.argv[1]
    print(f"Testing URASHG PyRPL connection to {hostname}")

    # Test connection
    connection = connect_redpitaya(hostname)

    if connection and connection.is_connected:
        print("Connection successful!")

        # Test voltage reading
        voltage = connection.read_voltage(InputChannel.IN1)
        print(f"Input 1 voltage: {voltage}V")

        # Test PID configuration for laser power stabilization
        config = PIDConfiguration(
            setpoint=0.5,
            p_gain=0.1,
            i_gain=0.01,
            input_channel=InputChannel.IN1,
            output_channel=OutputChannel.OUT1,
        )

        success = connection.configure_pid(PIDChannel.PID0, config)
        print(f"PID configuration: {'Success' if success else 'Failed'}")

        # Test cleanup
        disconnect_redpitaya(hostname)
        print("Disconnected successfully")

    else:
        print("Connection failed!")
        if connection:
            print(f"Error: {connection.last_error}")
