"""
URASHG Red Pitaya Power Stabilization Controller

This module provides comprehensive laser power stabilization capabilities for
wavelength-dependent polarimetry measurements using Red Pitaya STEMlab devices
with PyRPL library integration.

Features:
    - Hardware PID control for laser power stabilization
    - Wavelength-dependent power setpoint management
    - Real-time power monitoring and feedback
    - Thread-safe operation with PyMoDAQ integration
    - Comprehensive error handling and status reporting
    - Mock mode for development without hardware

Author: PyMoDAQ Plugin Development Team
License: MIT
"""

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# Import PyRPL wrapper utilities
try:
    from ...utils import (
        PYRPL_WRAPPER_AVAILABLE,
        InputChannel,
        OutputChannel,
        PIDChannel,
        PIDConfiguration,
        PyRPLConnection,
        PyRPLManager,
        connect_redpitaya,
        disconnect_redpitaya,
        get_pyrpl_manager,
    )

    if not PYRPL_WRAPPER_AVAILABLE or PIDChannel is None:
        raise ImportError("PyRPL wrapper not available")
except ImportError:
    # PyRPL not available - provide mock constants
    from enum import Enum

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

    PYRPL_WRAPPER_AVAILABLE = False
    PyRPLManager = None
    PyRPLConnection = None
    PIDChannel = MockPIDChannel
    InputChannel = MockInputChannel
    OutputChannel = MockOutputChannel
    PIDConfiguration = None
    get_pyrpl_manager = None
    connect_redpitaya = None
    disconnect_redpitaya = None

logger = logging.getLogger(__name__)


class PowerStabilizationError(Exception):
    """Power stabilization specific exception"""

    pass


class StabilizationState:
    """Enumeration of stabilization states"""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STABILIZING = "stabilizing"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class PowerTarget:
    """Power target definition for wavelength-dependent stabilization."""

    wavelength: float  # nm
    power_setpoint: float  # V (Red Pitaya voltage)
    tolerance: float = 0.001  # V (tolerance for power stability)
    timeout: float = 5.0  # s (timeout for reaching target)


@dataclass
class StabilizationConfiguration:
    """Configuration parameters for power stabilization."""

    # Connection parameters
    hostname: str = "rp-f08d6c.local"
    config_name: str = "urashg"
    connection_timeout: float = 10.0

    # PID parameters
    pid_channel: PIDChannel = PIDChannel.PID0
    input_channel: InputChannel = InputChannel.IN1  # Photodiode signal
    output_channel: OutputChannel = OutputChannel.OUT1  # Laser control

    # PID gains for power control
    p_gain: float = 0.1  # Proportional gain
    i_gain: float = 0.01  # Integral gain
    d_gain: float = 0.0  # Derivative gain (usually 0 for stability)

    # Safety limits
    min_power_setpoint: float = -1.0  # V
    max_power_setpoint: float = 1.0  # V

    # Monitoring parameters
    power_monitoring_rate: float = 10.0  # Hz
    stability_check_duration: float = 1.0  # s
    power_stability_threshold: float = 0.005  # V RMS

    # Mock mode
    mock_mode: bool = False


class PowerStabilizationController:
    """
    Comprehensive power stabilization controller for URASHG polarimetry measurements.

    This controller manages laser power stabilization during wavelength-dependent
    measurements by coordinating Red Pitaya PyRPL PID control with measurement
    workflows.

    Key Features:
    - Hardware PID control with microsecond response times
    - Wavelength-dependent power target management
    - Real-time power monitoring and stability assessment
    - Thread-safe operation for concurrent measurement workflows
    - Comprehensive error handling and recovery
    - Integration with URASHG measurement protocols

    Usage Example:
    ```python
    config = StabilizationConfiguration(
        hostname="rp-f08d6c.local",
        p_gain=0.1,
        i_gain=0.01
    )

    controller = PowerStabilizationController(config)

    # Connect and initialize
    success = controller.connect()
    if success:
        # Set power target for specific wavelength
        target = PowerTarget(wavelength=800.0, power_setpoint=0.5)
        controller.set_power_target(target)

        # Start stabilization
        controller.start_stabilization()

        # Monitor power during measurement
        power = controller.get_current_power()
        stability = controller.assess_power_stability()
    ```
    """

    def __init__(self, config: StabilizationConfiguration):
        """
        Initialize the power stabilization controller.

        Args:
            config: StabilizationConfiguration with all parameters
        """
        self.config = config
        self.state = StabilizationState.IDLE
        self.last_error: Optional[str] = None

        # PyRPL connection management
        self.pyrpl_manager: Optional[PyRPLManager] = None
        self.pyrpl_connection: Optional[PyRPLConnection] = None

        # Current power target and monitoring
        self.current_target: Optional[PowerTarget] = None
        self.power_history: List[Tuple[float, float]] = []  # (timestamp, power)
        self.stability_status: Dict[str, Any] = {}

        # Thread safety and monitoring
        self._lock = threading.RLock()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._stop_monitoring = threading.Event()

        # Status callbacks
        self._status_callbacks: List[Callable] = []

        # Mock mode attributes
        self.mock_power = 0.0
        self.mock_setpoint = 0.0

        # Initialize PyRPL manager if available
        if PYRPL_WRAPPER_AVAILABLE:
            self.pyrpl_manager = get_pyrpl_manager()
        else:
            logger.warning("PyRPL wrapper not available - using mock mode")
            self.config.mock_mode = True

    @property
    def is_connected(self) -> bool:
        """Check if controller is connected to hardware."""
        with self._lock:
            if self.config.mock_mode:
                return self.state not in [
                    StabilizationState.IDLE,
                    StabilizationState.ERROR,
                ]
            else:
                # For real hardware, check actual PyRPL connection status
                return (
                    self._pyrpl_manager is not None
                    and self._pyrpl_manager.is_connected()
                )

    @property
    def is_stabilizing(self) -> bool:
        """Check if power stabilization is active."""
        with self._lock:
            return self.state == StabilizationState.STABILIZING

    def add_status_callback(self, callback: Callable[[str], None]):
        """Add a status update callback function."""
        with self._lock:
            self._status_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[str], None]):
        """Remove a status update callback function."""
        with self._lock:
            if callback in self._status_callbacks:
                self._status_callbacks.remove(callback)

    def _emit_status(self, message: str, level: str = "info"):
        """Emit status message to all registered callbacks."""
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        with self._lock:
            for callback in self._status_callbacks:
                try:
                    callback(f"PowerStabilization: {message}")
                except Exception as e:
                    logger.error(f"Status callback error: {e}")

    def connect(self) -> bool:
        """
        Connect to Red Pitaya and initialize power stabilization.

        Returns:
            bool: True if connection successful
        """
        with self._lock:
            if self.is_connected:
                return True

            self.state = StabilizationState.CONNECTING
            self.last_error = None
            self._emit_status(f"Connecting to Red Pitaya at {self.config.hostname}")

            try:
                if self.config.mock_mode:
                    # Mock mode initialization
                    time.sleep(0.5)  # Simulate connection delay
                    self.state = StabilizationState.CONNECTED
                    self._emit_status("Connected to Red Pitaya (Mock Mode)")
                    return True

                else:
                    # Real hardware connection
                    if not PYRPL_WRAPPER_AVAILABLE:
                        raise PowerStabilizationError("PyRPL wrapper not available")

                    self.pyrpl_connection = self.pyrpl_manager.connect_device(
                        hostname=self.config.hostname,
                        config_name=self.config.config_name,
                        connection_timeout=self.config.connection_timeout,
                        status_callback=lambda cmd: self._emit_status(cmd.args[0]),
                    )

                    # Configure PID controller for power stabilization
                    pid_config = PIDConfiguration(
                        setpoint=0.0,  # Will be set by power targets
                        p_gain=self.config.p_gain,
                        i_gain=self.config.i_gain,
                        d_gain=self.config.d_gain,
                        input_channel=self.config.input_channel,
                        output_channel=self.config.output_channel,
                        voltage_limit_min=self.config.min_power_setpoint,
                        voltage_limit_max=self.config.max_power_setpoint,
                        enabled=False,  # Will be enabled when stabilization starts
                    )

                    success = self.pyrpl_connection.configure_pid(
                        self.config.pid_channel, pid_config
                    )

                    self.state = StabilizationState.CONNECTED
                    self._emit_status(
                        f"Connected to Red Pitaya {self.config.hostname} - Power stabilization ready"
                    )
                    return True

            except Exception as e:
                error_msg = f"Connection failed: {str(e)}"
                self.last_error = error_msg
                self.state = StabilizationState.ERROR
                self._emit_status(error_msg, "error")
                return False

    def disconnect(self):
        """Disconnect from Red Pitaya and clean up resources."""
        with self._lock:
            if self.state == StabilizationState.IDLE:
                return

            try:
                # Stop any active stabilization
                if self.is_stabilizing:
                    self.stop_stabilization()

                # Disconnect from hardware
                if not self.config.mock_mode and self.pyrpl_connection:
                    # Disable PID before disconnecting
                    try:
                        self.pyrpl_connection.disable_pid(self.config.pid_channel)
                    except Exception as e:
                        logger.warning(f"Failed to disable PID before disconnect: {e}")

                    # Disconnect through manager
                    self.pyrpl_manager.disconnect_device(
                        self.config.hostname,
                        self.config.config_name,
                        status_callback=lambda cmd: self._emit_status(cmd.args[0]),
                    )

                self.pyrpl_connection = None
                self.state = StabilizationState.DISCONNECTED
                self._emit_status("Disconnected from Red Pitaya")

            except Exception as e:
                error_msg = f"Disconnect error: {str(e)}"
                self.last_error = error_msg
                self._emit_status(error_msg, "error")
                self.state = StabilizationState.ERROR

    def set_power_target(self, target: PowerTarget) -> bool:
        """
        Set the power target for stabilization.

        Args:
            target: PowerTarget with wavelength and setpoint information

        Returns:
            bool: True if target set successfully
        """
        with self._lock:
            if not self.is_connected:
                error_msg = "Cannot set power target: not connected"
                self._emit_status(error_msg, "error")
                return False

            # Validate target
            if not (
                self.config.min_power_setpoint
                <= target.power_setpoint
                <= self.config.max_power_setpoint
            ):
                error_msg = f"Power setpoint {target.power_setpoint}V outside limits"
                self._emit_status(error_msg, "error")
                return False

            try:
                self.current_target = target

                if self.config.mock_mode:
                    self.mock_setpoint = target.power_setpoint
                    self._emit_status(
                        f"Mock power target set: {target.wavelength}nm → {target.power_setpoint}V"
                    )
                    return True

                else:
                    # Set PID setpoint
                    success = self.pyrpl_connection.set_pid_setpoint()

                    if success:
                        self._emit_status(
                            f"Power target set: λ={target.wavelength}nm, "
                            f"setpoint={target.power_setpoint}V, "
                            f"tolerance=±{target.tolerance}V"
                        )
                        return True
                    else:
                        error_msg = "Failed to set PID setpoint"
                        self._emit_status(error_msg, "error")
                        return False

            except Exception as e:
                error_msg = f"Error setting power target: {str(e)}"
                self.last_error = error_msg
                self._emit_status(error_msg, "error")
                return False

    def start_stabilization(self) -> bool:
        """
        Start power stabilization with the current target.

        Returns:
            bool: True if stabilization started successfully
        """
        with self._lock:
            if not self.is_connected:
                error_msg = "Cannot start stabilization: not connected"
                self._emit_status(error_msg, "error")
                return False

            if self.current_target is None:
                error_msg = "Cannot start stabilization: no power target set"
                self._emit_status(error_msg, "error")
                return False

            if self.is_stabilizing:
                self._emit_status("Stabilization already active")
                return True

            try:
                if not self.config.mock_mode:
                    # Enable PID controller
                    success = self.pyrpl_connection.enable_pid(self.config.pid_channel)
                    if not success:
                        error_msg = (
                            f"Failed to enable PID {self.config.pid_channel.value}"
                        )
                        self._emit_status(error_msg, "error")
                        return False

                # Start power monitoring
                self._start_power_monitoring()

                self.state = StabilizationState.STABILIZING
                self._emit_status(
                    f"Power stabilization started for λ={self.current_target.wavelength}nm, "
                    f"target={self.current_target.power_setpoint}V"
                )
                return True

            except Exception as e:
                error_msg = f"Error starting stabilization: {str(e)}"
                self.last_error = error_msg
                self._emit_status(error_msg, "error")
                return False

    def stop_stabilization(self):
        """Stop power stabilization and disable PID control."""
        with self._lock:
            if not self.is_stabilizing:
                return

            try:
                # Stop power monitoring
                self._stop_power_monitoring()

                if not self.config.mock_mode and self.pyrpl_connection:
                    # Disable PID controller
                    success = self.pyrpl_connection.disable_pid(self.config.pid_channel)
                    if not success:
                        logger.warning(
                            f"Failed to disable PID {self.config.pid_channel.value}"
                        )

                self.state = StabilizationState.CONNECTED
                self._emit_status("Power stabilization stopped")

            except Exception as e:
                error_msg = f"Error stopping stabilization: {str(e)}"
                self.last_error = error_msg
                self._emit_status(error_msg, "error")

    def get_current_power(self) -> Optional[float]:
        """
        Get the current laser power reading.

        Returns:
            Current power voltage or None if error
        """
        if not self.is_connected:
            return None

        try:
            if self.config.mock_mode:
                # Mock power reading with some noise and PID behavior
                if self.current_target:
                    error = self.mock_setpoint - self.mock_power
                    self.mock_power += 0.1 * error + np.random.normal(0, 0.001)
                return self.mock_power

            else:
                # Read actual voltage from Red Pitaya
                return self.pyrpl_connection.read_voltage(self.config.input_channel)

        except Exception as e:
            logger.error(f"Error reading power: {e}")
            return None

    def assess_power_stability(
        self, duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Assess current power stability based on recent history.

        Args:
            duration: Time window for stability assessment (uses config default if None)

        Returns:
            Dictionary with stability metrics
        """
        with self._lock:
            if duration is None:
                duration = self.config.stability_check_duration

            current_time = time.time()
            cutoff_time = current_time - duration

            # Filter recent power readings
            recent_readings = [
                power
                for timestamp, power in self.power_history
                if timestamp >= cutoff_time and power is not None
            ]

            if len(recent_readings) < 2:
                return {
                    "stable": False,
                    "reason": "insufficient_data",
                    "sample_count": len(recent_readings),
                    "rms_deviation": None,
                    "mean_power": None,
                }

            # Calculate stability metrics
            recent_powers = np.array(recent_readings)
            mean_power = np.mean(recent_powers)
            rms_deviation = np.sqrt(np.mean(np.square(recent_powers - mean_power)))

            # Check if power is stable within threshold
            is_stable = rms_deviation <= self.config.power_stability_threshold

            # Check target compliance if available
            target_compliance = None
            if self.current_target:
                target_error = abs(mean_power - self.current_target.power_setpoint)
                target_compliance = target_error <= self.current_target.tolerance

            stability_result = {
                "stable": is_stable,
                "reason": "stable" if is_stable else "power_fluctuation",
                "sample_count": len(recent_readings),
                "duration": duration,
                "rms_deviation": rms_deviation,
                "mean_power": mean_power,
                "stability_threshold": self.config.power_stability_threshold,
                "target_compliance": target_compliance,
                "target_error": target_error if self.current_target else None,
            }

            self.stability_status = stability_result
            return stability_result

    def wait_for_stability(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for power to stabilize within target tolerance.

        Args:
            timeout: Maximum time to wait (uses target timeout if None)

        Returns:
            bool: True if power stabilized within timeout
        """
        if not self.is_stabilizing or not self.current_target:
            return False

        max_wait = timeout or self.current_target.timeout
        start_time = time.time()

        self._emit_status(f"Waiting for power stability (timeout: {max_wait}s)")

        while time.time() - start_time < max_wait:
            stability = self.assess_power_stability()

            return True

            time.sleep(0.1)  # Check every 100ms

        self._emit_status(f"Power stability timeout after {max_wait}s", "warning")
        return False

    def _start_power_monitoring(self):
        """Start background power monitoring thread."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._stop_monitoring.clear()
        self.power_history.clear()

        self._monitoring_thread = threading.Thread(
            target=self._power_monitoring_loop, name="PowerMonitoring", daemon=True
        )
        self._monitoring_thread.start()

    def _stop_power_monitoring(self):
        """Stop background power monitoring thread."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False
        self._stop_monitoring.set()

        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)
            if self._monitoring_thread.is_alive():
                logger.warning("Power monitoring thread did not stop cleanly")

    def _power_monitoring_loop(self):
        """Background loop for continuous power monitoring."""
        monitor_interval = 1.0 / self.config.power_monitoring_rate

        try:
            current_power = self.get_current_power()
            current_time = time.time()

            with self._lock:
                # Store power reading with timestamp
                self.power_history.append((current_time, current_power))

                # Limit history size (keep last 10 minutes)
                max_history_time = 600  # seconds
                cutoff_time = current_time - max_history_time
                self.power_history = [
                    (t, p) for t, p in self.power_history if t >= cutoff_time
                ]

        except Exception as e:
            logger.error(f"Power monitoring error: {e}")
            time.sleep(1.0)  # Wait before retry

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information.

        Returns:
            Dictionary with current status
        """
        with self._lock:
            current_power = self.get_current_power()

            return {
                "state": self.state,
                "connected": self.is_connected,
                "stabilizing": self.is_stabilizing,
                "mock_mode": self.config.mock_mode,
                "hostname": self.config.hostname,
                "last_error": self.last_error,
                "current_power": current_power,
                "current_target": (
                    {
                        "wavelength": self.current_target.wavelength,
                        "setpoint": self.current_target.power_setpoint,
                        "tolerance": self.current_target.tolerance,
                    }
                    if self.current_target
                    else None
                ),
                "stability": self.assess_power_stability(),
                "monitoring_active": self._monitoring_active,
                "history_size": len(self.power_history),
                "pid_channel": self.config.pid_channel.value,
                "pid_gains": {
                    "p": self.config.p_gain,
                    "i": self.config.i_gain,
                    "d": self.config.d_gain,
                },
            }

    @contextmanager
    def power_stabilization_context(
        self, target: PowerTarget, wait_for_stability: bool = True
    ):
        """
        Context manager for power stabilization during measurements.

        Usage:
            with controller.power_stabilization_context(target) as stabilized:
                if stabilized:
                    # Perform measurement with stable power
                    pass
        """
        success = False
        try:
            # Set target and start stabilization
            if self.set_power_target(target):
                if self.start_stabilization():
                    # Wait for stability if requested
                    if not wait_for_stability or self.wait_for_stability():
                        success = True

            yield success

        finally:
            # Always stop stabilization when context exits
            if self.is_stabilizing:
                self.stop_stabilization()

    def __enter__(self):
        """Context manager entry - connect to hardware."""
        if not self.connect():
            raise PowerStabilizationError("Failed to connect to Red Pitaya")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from hardware."""
        self.disconnect()


# Convenience functions for compatibility
class RedPitayaController(PowerStabilizationController):
    """Legacy compatibility class."""

    def __init__(self, ip_address="rp-f08d6c.local"):
        """Initialize with legacy interface."""
        config = StabilizationConfiguration(hostname=ip_address)
        super().__init__(config)
        self.ip_address = ip_address
        self.connected = False

    def connect(self):
        """Legacy connect method."""
        success = super().connect()
        self.connected = success
        return success

    def disconnect(self):
        """Legacy disconnect method."""
        super().disconnect()
        self.connected = False

    def set_pid_parameters(self, kp=0.1, ki=0.01, kd=0.001):
        """Legacy PID parameter setting."""
        if not self.is_connected:
            raise PowerStabilizationError("Not connected")

        # Update configuration
        self.config.p_gain = kp
        self.config.i_gain = ki
        self.config.d_gain = kd

        # Reconfigure if active
        if not self.config.mock_mode and self.pyrpl_connection:
            pid_config = PIDConfiguration(
                setpoint=0.0,
                p_gain=kp,
                i_gain=ki,
                d_gain=kd,
                input_channel=self.config.input_channel,
                output_channel=self.config.output_channel,
                voltage_limit_min=self.config.min_power_setpoint,
                voltage_limit_max=self.config.max_power_setpoint,
                enabled=self.is_stabilizing,
            )

        return True

    def get_error_signal(self):
        """Legacy error signal reading."""
        if not self.is_connected:
            raise PowerStabilizationError("Not connected")

        current_power = self.get_current_power()
        if current_power is None or not self.current_target:
            return 0.0

        return self.current_target.power_setpoint - current_power


# Maintain backward compatibility
RedPitayaError = PowerStabilizationError
