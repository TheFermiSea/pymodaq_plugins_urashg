import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from qtpy.QtWidgets import QApplication
from pymodaq.dashboard import DashBoard
from pymodaq.utils.conftests import qtbotsleep

# Import the extension class
from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension

@pytest.fixture
def dashboard_app(qtbot):
    """Fixture to create a full Dashboard application."""
    app = QApplication.instance() or QApplication([])
    win = MagicMock() # Mock the main window
    dashboard = DashBoard(win)
    yield dashboard
    # Teardown
    dashboard.quit_fun()
    qtbotsleep(100)

def test_extension_loading_and_preset(dashboard_app, qtbot, tmp_path):
    """
    Test that the extension can be loaded and can load a preset.
    """
    dashboard = dashboard_app
    
    # 1. Load the extension
    extension = URASHGMicroscopyExtension(parent=dashboard.dock_area, dashboard=dashboard)
    assert extension.name == "μRASHG Microscopy System"

    # 2. Create a mock preset file
    preset_content = """
    <preset name="test_preset">
        <actuators>
            <actuator name="Elliptec">
                <module>DAQ_Move_Elliptec</module>
                <settings>
                    <param name="connection_group">
                        <param name="mock_mode" type="bool">True</param>
                    </param>
                </settings>
            </actuator>
        </actuators>
        <detectors>
            <detector name="PrimeBSI">
                <module>DAQ_2DViewer_PrimeBSI</module>
                <settings>
                    <param name="camera_settings">
                        <param name="mock_mode" type="bool">True</param>
                    </param>
                </settings>
            </detector>
        </detectors>
    </preset>
    """
    preset_path = tmp_path / "test_preset.xml"
    preset_path.write_text(preset_content)

    # 3. Simulate user selecting the preset and clicking "Load"
    extension.settings.child('preset_file').setValue(str(preset_path))
    
    # Mock the preset loaded signal to check our update function
    mock_status_update = MagicMock()
    dashboard.preset_manager.preset_loaded.connect(mock_status_update)

    extension.load_preset()
    qtbotsleep(500) # Allow time for modules to load

    # 4. Verify results
    # Check that the modules are now in the ModuleManager
    assert 'Elliptec' in dashboard.modules_manager.actuators
    assert 'PrimeBSI' in dashboard.modules_manager.detectors
    
    # Check that the status update function was called
    mock_status_update.assert_called()

@patch('pymodaq_plugins_urashg.extensions.urashg_microscopy_extension.MeasurementWorker')
def test_start_measurement(MockWorker, dashboard_app, qtbot, tmp_path):
    """
    Test the start_measurement logic.
    """
    dashboard = dashboard_app
    extension = URASHGMicroscopyExtension(parent=dashboard.dock_area, dashboard=dashboard)

    # Mock the loaded modules in the manager
    mock_elliptec = MagicMock()
    mock_camera = MagicMock()
    dashboard.modules_manager.actuators['Elliptec'] = mock_elliptec
    dashboard.modules_manager.detectors['PrimeBSI'] = mock_camera
    
    # Configure the extension settings for the measurement
    extension.settings.child('experiment', 'measurement_type').setValue('Basic RASHG')
    extension.settings.child('experiment', 'pol_steps').setValue(10)
    
    # Call the start measurement method
    extension.start_measurement()
    qtbotsleep(100)
    
    # Verify the MeasurementWorker was instantiated correctly
    MockWorker.assert_called_once()
    
    # Check the arguments passed to the worker's constructor
    args, kwargs = MockWorker.call_args
    devices_arg = args[0]
    params_arg = args[1]
    
    assert devices_arg['elliptec'] == mock_elliptec
    assert devices_arg['camera'] == mock_camera
    assert params_arg['pol_steps'] == 10
    
    # Check that the worker's start method was called
    worker_instance = MockWorker.return_value
    worker_instance.start.assert_called_once()
