# Code Style and Conventions

## Formatting Tools
- **Black**: Code formatter with 88-character line length
- **isort**: Import statement organizer with profile "black"
- **flake8**: Linting tool for style enforcement

## Code Style Guidelines
- **Line Length**: 88 characters (Black default)
- **Import Organization**: 
  - First-party packages: `pymodaq_plugins_urashg`
  - Third-party packages: `pymodaq`, `pyvcam`, `elliptec`, `numpy`, `pytest`
- **Type Hints**: Use where appropriate for public APIs
- **Docstrings**: Follow PyMoDAQ plugin documentation patterns

## Error Handling Patterns
- **Defensive Programming**: Import error handling for optional hardware libraries
- **Graceful Degradation**: Code works even when hardware is unavailable
- **Comprehensive Error Mapping**: See `DAQ_Move_Elliptec._error_codes` for examples

## Plugin Architecture Conventions
- **Move Plugins**: Located in `daq_move_plugins/`, inherit from PyMoDAQ base classes
- **Viewer Plugins**: Located in `daq_viewer_plugins/plugins_2D/`
- **Hardware Abstraction**: Separate low-level control in `hardware/urashg/`
- **Entry Points**: Defined in `pyproject.toml` under appropriate plugin categories

## Testing Conventions
- **Pytest Markers**: 
  - `unit`: Fast isolated tests
  - `integration`: Hardware-dependent tests  
  - `hardware`: Tests requiring physical hardware
  - `slow`: Long-running tests
- **Mock Strategy**: Comprehensive mocking for hardware dependencies
- **Coverage**: Excludes test files, examples, and documentation