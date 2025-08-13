# PyMoDAQ URASHG Plugin Project Overview

## Purpose
This is a PyMoDAQ plugin package for URASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy systems. It provides complete automation and control for polarimetric SHG measurements.

## Key Hardware Components
- **Red Pitaya FPGA**: PID laser stabilization with memory-mapped register access
- **Thorlabs ELL14 rotation mounts**: Serial communication for polarization control (3 mounts: QWP, HWP incident, HWP analyzer)  
- **Photometrics Prime BSI camera**: PyVCAM-based 2D detection with ROI support

## Tech Stack
- **Python 3.8+** with PyMoDAQ framework ≥4.0.0
- **PyVCAM** for camera control (with graceful fallback handling)
- **elliptec** library for Thorlabs rotation mount control
- **pytest** for testing with hardware/mock markers
- **black** and **isort** for code formatting
- **flake8** for linting
- **setuptools** build system with modern pyproject.toml configuration

## Plugin Architecture
- **Move Plugins**: `DAQ_Move_Elliptec.py` (rotation mounts), `DAQ_Move_MaiTai.py` (laser control)
- **Viewer Plugins**: `DAQ_Viewer_PrimeBSI.py` (camera interface)
- **Hardware Abstraction**: Low-level control utilities in `hardware/urashg/` directory