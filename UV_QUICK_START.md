# UV Quick Start Guide

**Fast setup for the μRASHG Microscopy Extension using UV**

## 🚀 Quick Setup (5 minutes)

### 1. Install UV
```bash
# Install UV (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup Project
```bash
# Clone and setup (if not done already)
cd pymodaq_plugins_urashg

# Complete setup with one command
python manage_uv.py setup
```

### 3. Launch Extension
```bash
# Launch the μRASHG extension
python manage_uv.py launch
```

**That's it!** 🎉

## 📋 Common Commands

| Task | Command |
|------|---------|
| **Setup project** | `python manage_uv.py setup` |
| **Install dependencies** | `python manage_uv.py install` |
| **Install hardware deps** | `python manage_uv.py install --hardware` |
| **Launch extension** | `python manage_uv.py launch` |
| **Run tests** | `python manage_uv.py test` |
| **Check status** | `python manage_uv.py status` |
| **Clean environment** | `python manage_uv.py clean` |

## 🔧 Direct UV Commands

| Task | Command |
|------|---------|
| **Sync dependencies** | `uv sync` |
| **Launch extension** | `uv run python launch_urashg_uv.py` |
| **Run tests** | `uv run pytest tests/` |
| **Python version** | `uv run python --version` |

## ⚡ Why UV?

- **10-100x faster** than pip
- **Reliable** dependency resolution
- **Modern** Python environment management
- **Lock files** for reproducible installs
- **Future-proof** tooling

## 🆘 Troubleshooting

**Problem**: `command not found: uv`
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal
```

**Problem**: `PyMoDAQ not found`
```bash
# Install dependencies
python manage_uv.py install
```

**Problem**: Extension won't start
```bash
# Check environment
python manage_uv.py status

# Clean and rebuild
python manage_uv.py clean
python manage_uv.py setup
```

## 📚 Detailed Documentation

- **Complete setup guide**: `UV_ENVIRONMENT_SETUP.md`
- **Development guide**: `CLAUDE.md`
- **Project documentation**: `README.md`

## ✅ Environment Status Check

```bash
python manage_uv.py status
```

Expected output:
```
✅ UV: uv 0.7.12
✅ Python version (pinned): 3.12
✅ Virtual environment: Present
✅ Python executable: Python 3.12.10
✅ PyMoDAQ: PyMoDAQ 5.0.18
✅ Installed packages: 150+
✅ Dependency lock file: Present
```

---

**Ready to start μRASHG experiments!** 🔬