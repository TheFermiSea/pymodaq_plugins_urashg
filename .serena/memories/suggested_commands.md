# Essential Development Commands

## Package Management
```bash
# Install in development mode
pip install -e .

# Install with optional dependencies
pip install -e .[dev]      # Development tools
pip install -e .[mock]     # Mock devices for testing
pip install -e .[galvo]    # Future galvo integration
```

## Code Quality & Formatting
```bash
# Format code (always run these together)
black src/
isort src/

# Linting
flake8 src/

# Install pre-commit hooks
pre-commit install
```

## Testing Commands
```bash
# Run all tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires hardware)
pytest tests/integration/ -m "hardware"

# Mock device tests
pytest tests/mock/

# Skip slow tests
pytest -m "not slow"

# With coverage
pytest --cov=pymodaq_plugins_urashg --cov-report=term-missing
```

## Documentation
```bash
# Build documentation
sphinx-build docs/ docs/_build/

# Serve documentation locally
python -m http.server 8000 --directory docs/_build/
```

## Darwin System Utilities
```bash
# Basic file operations
ls -la          # List files with details
find . -name "*.py"  # Find Python files
grep -r "pattern" src/  # Search in source code
cd /path/to/dir     # Change directory
```