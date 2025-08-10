# UV Environment Setup Guide

This document provides a comprehensive guide for setting up the μRASHG microscopy extension using `uv`, the modern Python package and project manager.

## Why UV?

We've chosen `uv` as the standard dependency manager for this project because:

- **Speed**: Up to 10-100x faster than pip for package installation and resolution
- **Reliability**: Better dependency resolution and conflict detection
- **Modern**: Built-in support for Python version management and virtual environments
- **Reproducible**: Lock files ensure identical environments across machines
- **Future-proof**: Actively developed with backing from Astral (makers of Ruff)

## Prerequisites

### 1. Install UV

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Or using conda/mamba
conda install -c conda-forge uv
```

### 2. Verify Installation

```bash
uv --version
# Should show: uv 0.7.12 or newer
```

## Project Setup

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd pymodaq_plugins_urashg
```

### 2. Python Version Management

The project is configured to use Python 3.12, which provides the best compatibility with PyMoDAQ 5.x:

```bash
# Check available Python versions
uv python list

# Install Python 3.12 if not available
uv python install 3.12

# Verify the project is pinned to Python 3.12
cat .python-version
# Should show: 3.12
```

### 3. Install Dependencies

#### Basic Installation (Core functionality)

```bash
# Sync the environment with locked dependencies
uv sync

# Activate the environment
source .venv/bin/activate

# Or run commands directly with uv
uv run python --version
```

#### Development Installation (with dev tools)

```bash
# Install with development dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

#### Hardware-Specific Installation

For different hardware setups, install the appropriate extras:

```bash
# Full hardware support (cameras, rotation mounts, etc.)
uv sync --extra hardware

# PyRPL Red Pitaya integration
uv sync --extra pyrpl

# Mock devices for testing
uv sync --extra mock

# All extras for complete development environment
uv sync --all-extras
```

### 4. Install Project in Development Mode

```bash
# Install the project itself in editable mode
uv pip install -e .
```

## Launching the Extension

With the UV environment properly set up, you can launch the μRASHG extension:

### Method 1: Direct UV Run

```bash
# Run the extension directly with uv
uv run python launch_urashg_extension.py
```

### Method 2: Activated Environment

```bash
# Activate the environment
source .venv/bin/activate

# Run the extension
python launch_urashg_extension.py
```

### Method 3: Shell Script (Unix/Linux/macOS)

```bash
# Use the provided shell wrapper
./run_urashg_extension.sh
```

## Project Structure

```
pymodaq_plugins_urashg/
├── .python-version          # Python version specification (3.12)
├── pyproject.toml           # Project configuration and dependencies
├── uv.lock                  # Locked dependency versions
├── .venv/                   # Virtual environment (created by uv)
├── src/                     # Source code
├── tests/                   # Test suite
├── launch_urashg_extension.py # Main launcher script
└── UV_ENVIRONMENT_SETUP.md  # This document
```

## Dependency Management

### Adding New Dependencies

```bash
# Add a runtime dependency
uv add numpy>=1.20.0

# Add a development dependency
uv add --dev pytest>=7.0

# Add an optional dependency to an extra group
uv add --optional hardware opencv-python>=4.5.0
```

### Updating Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific dependency
uv add package-name@latest
```

### Managing Extras

The project defines several optional dependency groups:

- `dev`: Development tools (pytest, black, flake8, etc.)
- `hardware`: Hardware-specific libraries (cameras, motors, etc.)
- `pyrpl`: PyRPL Red Pitaya integration
- `mock`: Mock devices for testing
- `galvo`: Future galvo mirror support

## Environment Variables

The UV environment automatically handles Python path configuration. However, you may need to set:

```bash
# For GUI applications (if running on headless systems)
export DISPLAY=:0

# For PyMoDAQ configuration (optional)
export PYMODAQ_DATA_DIR="$HOME/.pymodaq/data"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. PyMoDAQ Import Errors

```bash
# Verify PyMoDAQ installation
uv run python -c "import pymodaq; print(pymodaq.__version__)"

# If fails, reinstall PyMoDAQ
uv add --upgrade pymodaq>=5.0.0
```

#### 2. Qt Backend Issues

```bash
# Install Qt dependencies
uv add PySide6>=6.0.0
# or
uv add PyQt5>=5.15.0
```

#### 3. Hardware Library Conflicts

```bash
# Install specific hardware dependencies
uv sync --extra hardware

# For camera support
uv add pyvcam>=2.2.0

# For rotation mounts
uv add elliptec>=0.1.0
```

#### 4. Lock File Conflicts

```bash
# Regenerate lock file
rm uv.lock
uv sync
```

### Environment Inspection

```bash
# Show project info
uv run python -c "import sys; print(sys.executable)"

# List installed packages
uv pip list

# Show environment location
uv venv --show-path
```

## Performance Optimization

### 1. Use UV's Speed Features

```bash
# Use UV's parallel installation
uv sync --concurrent-downloads 8

# Cache management
uv cache dir
uv cache clean
```

### 2. Development Workflow

```bash
# Fast dependency check
uv sync --frozen

# Development server with auto-reload
uv run python launch_urashg_extension.py --reload
```

## CI/CD Integration

For automated environments (GitHub Actions, etc.):

```yaml
# .github/workflows/test.yml
- name: Setup UV
  uses: astral-sh/setup-uv@v1
  with:
    version: "latest"

- name: Install dependencies
  run: uv sync --all-extras

- name: Run tests
  run: uv run pytest
```

## Migration from Other Tools

### From pip + venv

```bash
# UV automatically detects requirements.txt
uv add --requirements requirements.txt

# Or migrate manually
uv add $(cat requirements.txt)
```

### From conda

```bash
# Export conda environment
conda env export > environment.yml

# Manually add dependencies to pyproject.toml
# UV doesn't directly import conda environments
```

## Best Practices

1. **Always use locked installations**: Run `uv sync` instead of `uv add` for consistent environments
2. **Pin Python version**: Use `.python-version` file for consistency
3. **Use extras for optional features**: Keep core dependencies minimal
4. **Regular updates**: Update lock file periodically with `uv sync --upgrade`
5. **Documentation**: Update this file when adding new dependencies or workflows

## Advanced Configuration

### Custom UV Configuration

Create a `uv.toml` file for project-specific UV settings:

```toml
[pip]
index-url = "https://pypi.org/simple"

[python]
downloads = "manual"

[tool.uv]
cache-dir = ".uv-cache"
```

### Global UV Configuration

```bash
# Set global cache directory
export UV_CACHE_DIR="$HOME/.cache/uv"

# Configure concurrent downloads
export UV_CONCURRENT_DOWNLOADS=8
```

## Support and Resources

- **UV Documentation**: https://docs.astral.sh/uv/
- **PyMoDAQ Documentation**: https://pymodaq.cnrs.fr/
- **Project Issues**: Use the GitHub issue tracker for project-specific problems
- **UV Issues**: https://github.com/astral-sh/uv/issues

## Summary

This UV-based setup provides:

✅ **Fast and reliable** dependency management  
✅ **Reproducible environments** across machines  
✅ **Modern Python tooling** with excellent performance  
✅ **Clear separation** of runtime, development, and hardware dependencies  
✅ **Easy maintenance** and updates  
✅ **Future-proof** tooling choices  

The μRASHG microscopy extension is now ready for development and production use with a modern, efficient Python environment.