# PyMoDAQ URASHG Plugin Package

A PyMoDAQ 5.x compliant plugin for μRASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy systems. This package provides hardware control and experimental automation for polarimetric SHG measurements with a unified GUI.

## Status: Production Ready

-   **GUI Interface**: Fully functional unified interface for complete system control.
-   **Mock Device Support**: Comprehensive simulation for testing without hardware.
-   **PyMoDAQ 5.x Compliance**: All compliance tests passing.
-   **Plugin Discovery**: All plugins are discoverable by the PyMoDAQ framework.
-   **Measurement System**: Functional calibration and measurement workflows.

## Important Notice

This is an unofficial plugin package developed by TheFermiSea. It is not endorsed or maintained by the PyMoDAQ team.

-   **Repository**: https://github.com/TheFermiSea/pymodaq_plugins_urashg
-   **Author**: TheFermiSea (squires.b@gmail.com)
-   **PyMoDAQ Compatibility**: 5.x
-   **Support**: Community-driven.

## Overview

The URASHG plugin package enables polarimetric second harmonic generation measurements through PyMoDAQ's modular framework. It features a standards-compliant architecture, multi-device coordination, real-time data acquisition, and a unified extension for system control. It works with both real hardware and in a simulation mode.

## Plugin Components

### Move Plugins (Motion Control)
-   **DAQ_Move_Elliptec**: Thorlabs ELL14 rotation mount control.
-   **DAQ_Move_MaiTai**: MaiTai Ti:Sapphire laser control.
-   **DAQ_Move_ESP300**: Newport ESP300 multi-axis motion controller.

### Viewer Plugins (Detection)
-   **DAQ_2DViewer_PrimeBSI**: Photometrics Prime BSI sCMOS camera control.
-   **DAQ_0DViewer_Newport1830C**: Newport 1830-C optical power meter.

### Extensions
-   **URASHGMicroscopyExtension**: Comprehensive microscopy control interface.

## Hardware Support

-   **Cameras**: Photometrics Prime BSI (sCMOS).
-   **Motion Control**: Thorlabs ELL14, MaiTai Laser, Newport ESP300.
-   **Detection**: Newport 1830-C Power Meter.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/TheFermiSea/pymodaq_plugins_urashg.git
    cd pymodaq_plugins_urashg
    ```
2.  **Install dependencies**:
    ```bash
    pip install -e .
    ```
    For hardware-specific dependencies:
    ```bash
    pip install -e .[hardware]
    ```

## Usage

The recommended way to use this plugin is through the standalone GUI:

```bash
python src/pymodaq_plugins_urashg/extensions/urashg_microscopy_extension.py
```

The plugins can also be used within the main PyMoDAQ dashboard.

## Development

To set up a development environment, install the development dependencies:

```bash
pip install -e .[dev]
```

Run tests using `pytest`.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
