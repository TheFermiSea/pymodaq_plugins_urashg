"""
PyTest configuration for URASHG Plugin Tests.

This file sets up the test environment with proper QApplication initialization
for PyQt6 testing and provides common fixtures for all tests.
"""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Set up Qt environment before any Qt imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_DEBUG_PLUGINS", "0")

# Import Qt after setting environment
try:
    from qtpy.QtWidgets import QApplication

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication instance for GUI tests."""
    if not QT_AVAILABLE:
        pytest.skip("Qt not available")

    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        # Create new QApplication
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

    yield app

    # Cleanup
    if app is not None:
        app.quit()


@pytest.fixture(scope="function")
def qtbot():
    """Provide qtbot fixture for Qt testing."""
    if not QT_AVAILABLE:
        pytest.skip("Qt not available")

    try:
        from qtpy import QtTest

        return QtTest.QTest
    except ImportError:
        pytest.skip("QtTest not available")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set PyMoDAQ test mode
    os.environ["PYMODAQ_TEST_MODE"] = "mock"
    os.environ["CI"] = "true"

    # Ensure proper path setup
    project_root = Path(__file__).parent.parent
    if str(project_root / "src") not in sys.path:
        sys.path.insert(0, str(project_root / "src"))

    yield

    # Cleanup
    os.environ.pop("PYMODAQ_TEST_MODE", None)


@pytest.fixture
def mock_dashboard():
    """Create mock PyMoDAQ dashboard for testing."""
    dashboard = Mock()
    dashboard.modules_manager = Mock()
    dashboard.modules_manager.actuators = {}
    dashboard.modules_manager.detectors_0D = {}
    dashboard.modules_manager.detectors_1D = {}
    dashboard.modules_manager.detectors_2D = {}
    return dashboard


@pytest.fixture
def mock_plugin_settings():
    """Create mock plugin settings structure."""
    from pymodaq.utils.parameter import Parameter

    settings = Parameter.create(
        name="Settings",
        type="group",
        children=[
            {"name": "controller_status", "type": "str", "value": "Disconnected"},
            {"name": "controller_ID", "type": "str", "value": ""},
            {
                "name": "connection_group",
                "type": "group",
                "children": [
                    {"name": "mock_mode", "type": "bool", "value": True},
                    {"name": "com_port", "type": "str", "value": "COM1"},
                    {"name": "baudrate", "type": "int", "value": 115200},
                    {"name": "timeout", "type": "float", "value": 1.0},
                ],
            },
        ],
    )
    return settings


@pytest.fixture
def suppress_qt_warnings():
    """Suppress Qt warnings during testing."""
    # Suppress specific Qt warnings that appear in CI
    logging.getLogger("qt").setLevel(logging.ERROR)
    logging.getLogger("PyQt6").setLevel(logging.ERROR)

    yield


# Configure logging for tests
def pytest_configure(config):
    """Configure pytest with custom markers and logging."""
    # Suppress noisy loggers
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("h5py").setLevel(logging.WARNING)

    # Set up test logging
    logging.basicConfig(
        level=logging.WARNING, format="%(name)s - %(levelname)s - %(message)s"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip conditions."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to tests in integration/ directory
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Skip hardware tests in CI unless explicitly requested
        if item.get_closest_marker("hardware") and os.environ.get("CI"):
            if not config.getoption("-m") or "hardware" not in config.getoption("-m"):
                item.add_marker(pytest.mark.skip(reason="Hardware tests skipped in CI"))


# Handle missing Qt gracefully
def pytest_runtest_setup(item):
    """Setup function run before each test."""
    # Skip Qt-dependent tests if Qt not available
    if not QT_AVAILABLE:
        if any(
            marker.name in ["qt", "gui", "extension"] for marker in item.iter_markers()
        ):
            pytest.skip("Qt not available - skipping GUI test")
