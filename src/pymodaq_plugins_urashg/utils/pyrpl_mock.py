# -*- coding: utf-8 -*-
"""
Mock PyRPL Implementation for Development

This module provides a mock implementation of PyRPL functionality
to enable development and testing when the real PyRPL library
cannot be installed due to dependency conflicts.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MockPyrpl:
    """Mock PyRPL main class for development."""

    def __init__(
        self, hostname: str = "192.168.1.100", config_file: Optional[str] = None
    ):
        self.hostname = hostname
        self.config_file = config_file
        self._connected = False
        logger.info(f"MockPyrpl initialized for {hostname}")

    def __enter__(self):
        self._connected = True
        logger.info("MockPyrpl connection established")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connected = False
        logger.info("MockPyrpl connection closed")

    @property
    def rp(self):
        """Mock Red Pitaya interface."""
        return MockRedPitaya()


class MockRedPitaya:
    """Mock Red Pitaya interface."""

    def __init__(self):
        self.pid0 = MockPID("PID0")
        self.pid1 = MockPID("PID1")
        self.pid2 = MockPID("PID2")


class MockPID:
    """Mock PID controller."""

    def __init__(self, name: str):
        self.name = name
        self._setpoint = 0.0
        self._p = 1.0
        self._i = 0.0
        self._d = 0.0
        self._enabled = False

    @property
    def setpoint(self) -> float:
        return self._setpoint

    @setpoint.setter
    def setpoint(self, value: float):
        self._setpoint = float(value)
        logger.debug(f"{self.name} setpoint set to {value}")

    @property
    def p(self) -> float:
        return self._p

    @p.setter
    def p(self, value: float):
        self._p = float(value)

    @property
    def i(self) -> float:
        return self._i

    @i.setter
    def i(self, value: float):
        self._i = float(value)

    @property
    def d(self) -> float:
        return self._d

    @d.setter
    def d(self, value: float):
        self._d = float(value)

    def setup(self, **kwargs):
        """Setup PID parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        logger.info(f"{self.name} configured with {kwargs}")


# Mock module-level functions that PyRPL provides
def Pyrpl(*args, **kwargs):
    """Mock Pyrpl constructor function."""
    return MockPyrpl(*args, **kwargs)


# Version information
__version__ = "0.9.3.mock"
