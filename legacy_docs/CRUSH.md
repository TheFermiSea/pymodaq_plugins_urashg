# CRUSH.md

Quick reference for agentic coding in this repo (PyMoDAQ 5.x plugins for URASHG).

- Setup
  - python -m pip install -e .[dev]
  - Optional: python -m pip install -e ".[hardware,pyrpl]"

- Build/format/lint/typecheck
  - black src/ && isort src/
  - flake8 src/
  - mypy src/  # if installed; type hints are encouraged but not enforced

- Tests
  - Run all: python scripts/run_all_tests.py
  - Pytest defaults (from pyproject): -ra -q --strict-markers --cov=pymodaq_plugins_urashg --cov-report=term-missing
  - Single file: pytest tests/unit/test_plugin_discovery.py -q
  - Single test: pytest tests/unit/test_plugin_discovery.py::test_entry_points -q
  - Markers: unit/integration/hardware/slow/camera (e.g., pytest -m "not hardware")

- Common tasks
  - Build docs: sphinx-build docs/ docs/_build/
  - Serve docs: python -m http.server 8000 --directory docs/_build/

- Code style
  - Imports: isort profile=black; order stdlib, third-party, first-party (pymodaq_plugins_urashg)
  - Formatting: black line-length=88; keep functions small and explicit
  - Types: use typing for public interfaces; DataActuator/DataWithAxes per PyMoDAQ 5.x
  - Naming: snake_case for functions/vars, PascalCase for classes, UPPER_SNAKE for constants
  - Errors: raise ValueError/RuntimeError with clear messages; no bare except; preserve original exceptions
  - Logging: prefer PyMoDAQ/logging patterns; avoid prints in library code
  - Threading: no __del__ on controllers; explicit close()/disconnect() only (see THREADING_SAFETY_GUIDELINES.md)
  - PyMoDAQ data: set source=DataSource.raw; units as string; DataActuator usage:
    - Single-axis: position.value()
    - Multi-axis: position.data[0]

- Commit hygiene
  - Run black, isort, flake8, pytest before committing
  - Do not commit large data, secrets, or hardware configs

- References
  - See CLAUDE.md for deep project context and standards
