# Codebase Structure

## Root Directory Structure
```
pymodaq_plugins_urashg/
├── src/pymodaq_plugins_urashg/          # Main source code
├── tests/                               # Test suite
├── docs/                                # Documentation
├── examples/                            # Usage examples
├── pyproject.toml                       # Modern Python project config
├── plugin_info.toml                     # PyMoDAQ plugin metadata
├── requirements.txt                     # Development dependencies
└── CLAUDE.md                           # AI assistant instructions
```

## Source Code Organization
```
src/pymodaq_plugins_urashg/
├── __init__.py                          # Package initialization
├── daq_move_plugins/                    # Move/actuator plugins
│   ├── DAQ_Move_Elliptec.py            # Thorlabs ELL14 rotation mounts
│   └── DAQ_Move_MaiTai.py              # MaiTai laser control
├── daq_viewer_plugins/plugins_2D/       # 2D detector plugins
│   └── DAQ_Viewer_PrimeBSI.py          # Photometrics camera
└── hardware/urashg/                     # Hardware abstraction layer
    ├── constants.py                     # Hardware constants/settings
    ├── redpitaya_control.py            # FPGA control
    ├── elliptec_wrapper.py             # Rotation mount wrapper
    ├── camera_utils.py                 # Camera utilities
    ├── maitai_control.py               # Laser control
    ├── system_control.py               # System orchestration
    └── utils.py                        # General utilities
```

## Test Structure
```
tests/
├── unit/                               # Fast isolated tests
├── integration/                        # Hardware integration tests
├── mock/                              # Mock device tests
├── mock_modules/                      # Mock hardware modules
│   ├── mock_pyvcam.py                # Camera mocking
│   └── mock_serial.py                # Serial communication mocking
├── test_*.py                          # Individual plugin tests
├── run_all_tests.py                   # Test runner script
└── setup_test_environment.py         # Test environment setup
```

## Key Plugin Entry Points
- **Move Plugins**: Registered in `pyproject.toml` under `pymodaq.move_plugins`
- **Viewer Plugins**: Registered under `pymodaq.viewer_plugins`
- **Hardware Modules**: Importable from `hardware.urashg` namespace