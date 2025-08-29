"""
Shared Elliptec Controller Manager for URASHG System

This module provides a singleton pattern for managing a shared Elliptec controller
connection, preventing multiple serial port conflicts when using separate single-axis
plugins for HWP_Incident, QWP, and HWP_Analyzer.
"""

import logging
import threading
from typing import Dict, Optional, Set
from contextlib import contextmanager

from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController


class ElliptecSharedController:
    """
    Singleton shared controller manager for Elliptec rotation mounts.

    Ensures only one serial connection is used by all Elliptec plugins,
    preventing port conflicts and communication overhead.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ElliptecSharedController, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._controller: Optional[ElliptecController] = None
        self._clients: Set[str] = set()  # Track which plugins are using the controller
        self._connection_params = {}
        self._connected = False
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self._initialized = True

    def register_client(
        self,
        client_id: str,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        timeout: float = 2.0,
        mock_mode: bool = False,
    ) -> bool:
        """
        Register a plugin client and initialize shared controller if needed.

        Args:
            client_id: Unique identifier for the plugin (e.g., "HWP_Incident")
            port: Serial port for communication
            baudrate: Communication baud rate
            timeout: Communication timeout
            mock_mode: Enable mock mode for testing

        Returns:
            True if registration successful and controller connected
        """
        with self._lock:
            self.logger.info(f"Registering client: {client_id}")

            # Store connection parameters from first client
            if not self._connection_params:
                self._connection_params = {
                    "port": port,
                    "baudrate": baudrate,
                    "timeout": timeout,
                    "mock_mode": mock_mode,
                }
            else:
                # Verify consistent parameters
                if (
                    port != self._connection_params["port"]
                    or baudrate != self._connection_params["baudrate"]
                ):
                    self.logger.warning(
                        f"Client {client_id} has different connection params. "
                        f"Using existing: {self._connection_params}"
                    )

            # Add client to set
            self._clients.add(client_id)

            # Initialize controller if this is the first client
            if self._controller is None:
                try:
                    self.logger.info("Creating shared Elliptec controller...")
                    self._controller = ElliptecController(
                        port=self._connection_params["port"],
                        baudrate=self._connection_params["baudrate"],
                        timeout=self._connection_params["timeout"],
                        mount_addresses=["2", "3", "8"],  # All three mounts
                        mock_mode=self._connection_params["mock_mode"],
                    )

                    # Connect to hardware
                    if self._controller.connect():
                        self._connected = True
                        self.logger.info(
                            f"Shared controller connected successfully on {port}"
                        )
                        self.logger.info(f"Active clients: {self._clients}")
                        return True
                    else:
                        self.logger.error("Failed to connect shared controller")
                        self._controller = None
                        self._clients.remove(client_id)
                        return False

                except Exception as e:
                    self.logger.error(f"Error creating shared controller: {e}")
                    self._controller = None
                    self._clients.remove(client_id)
                    return False

            # Controller already exists and connected
            if self._connected:
                self.logger.info(
                    f"Client {client_id} registered with existing controller"
                )
                self.logger.info(f"Active clients: {self._clients}")
                return True
            else:
                self.logger.error("Shared controller exists but not connected")
                self._clients.remove(client_id)
                return False

    def unregister_client(self, client_id: str):
        """
        Unregister a plugin client and cleanup controller if no clients remain.

        Args:
            client_id: Unique identifier for the plugin
        """
        with self._lock:
            self.logger.info(f"Unregistering client: {client_id}")

            if client_id in self._clients:
                self._clients.remove(client_id)
                self.logger.info(f"Remaining clients: {self._clients}")

                # If no more clients, disconnect controller
                if not self._clients and self._controller is not None:
                    self.logger.info(
                        "No more clients - disconnecting shared controller"
                    )
                    try:
                        self._controller.disconnect()
                    except Exception as e:
                        self.logger.error(f"Error disconnecting controller: {e}")
                    finally:
                        self._controller = None
                        self._connected = False
                        self._connection_params = {}
                        self.logger.info("Shared controller cleanup complete")
            else:
                self.logger.warning(f"Client {client_id} was not registered")

    def get_controller(self) -> Optional[ElliptecController]:
        """
        Get the shared controller instance.

        Returns:
            ElliptecController instance if connected, None otherwise
        """
        with self._lock:
            if self._connected and self._controller is not None:
                return self._controller
            return None

    def is_connected(self) -> bool:
        """Check if shared controller is connected."""
        with self._lock:
            return self._connected and self._controller is not None

    def get_client_count(self) -> int:
        """Get number of registered clients."""
        with self._lock:
            return len(self._clients)

    def get_clients(self) -> Set[str]:
        """Get set of registered client IDs."""
        with self._lock:
            return self._clients.copy()

    @contextmanager
    def exclusive_access(self, client_id: str):
        """
        Context manager for exclusive access to controller operations.

        Args:
            client_id: Client requesting exclusive access

        Usage:
            with shared_controller.exclusive_access("HWP_Incident"):
                position = controller.get_position("2")
        """
        if client_id not in self._clients:
            raise ValueError(f"Client {client_id} not registered")

        with self._lock:
            try:
                yield self._controller
            except Exception as e:
                self.logger.error(f"Error during exclusive access for {client_id}: {e}")
                raise

    def reset_connection(self):
        """
        Force reset of the shared controller connection.
        Should only be used in error recovery scenarios.
        """
        with self._lock:
            self.logger.warning("Force resetting shared controller connection")

            if self._controller is not None:
                try:
                    self._controller.disconnect()
                except Exception as e:
                    self.logger.error(f"Error during force disconnect: {e}")

                self._controller = None
                self._connected = False

            # Keep clients registered but clear connection state
            self.logger.info(
                f"Connection reset. Clients still registered: {self._clients}"
            )

    def get_status(self) -> Dict:
        """
        Get status information about the shared controller.

        Returns:
            Dictionary with controller status information
        """
        with self._lock:
            return {
                "connected": self._connected,
                "controller_exists": self._controller is not None,
                "client_count": len(self._clients),
                "clients": list(self._clients),
                "connection_params": (
                    self._connection_params.copy() if self._connection_params else {}
                ),
                "controller_status": (
                    self._controller.is_connected() if self._controller else False
                ),
            }


# Global instance for easy access
_shared_controller = ElliptecSharedController()


def get_shared_controller() -> ElliptecSharedController:
    """
    Get the global shared controller instance.

    Returns:
        ElliptecSharedController singleton instance
    """
    return _shared_controller


def register_elliptec_client(client_id: str, **connection_params) -> bool:
    """
    Convenience function to register a client with the shared controller.

    Args:
        client_id: Unique identifier for the plugin
        **connection_params: Connection parameters (port, baudrate, timeout, mock_mode)

    Returns:
        True if registration successful
    """
    return get_shared_controller().register_client(client_id, **connection_params)


def unregister_elliptec_client(client_id: str):
    """
    Convenience function to unregister a client from the shared controller.

    Args:
        client_id: Unique identifier for the plugin
    """
    get_shared_controller().unregister_client(client_id)


def get_elliptec_controller() -> Optional[ElliptecController]:
    """
    Convenience function to get the shared controller.

    Returns:
        ElliptecController instance if available
    """
    return get_shared_controller().get_controller()
