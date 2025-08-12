PyMoDAQ URASHG Plugin Package
==============================

A **PyMoDAQ 5.x compliant** plugin package for **μRASHG (micro Rotational Anisotropy Second Harmonic Generation)** microscopy systems. This package provides complete hardware control and experimental automation for polarimetric SHG measurements following PyMoDAQ standards.

Overview
--------

The URASHG plugin package enables sophisticated polarimetric second harmonic generation measurements through PyMoDAQ's modular framework with full PyMoDAQ 5.x compliance:

- **Standards-compliant architecture**: Follows PyMoDAQ plugin development guidelines
- **Multi-device coordination**: Integrated laser control, polarization optics, cameras, and power meters
- **Real-time data acquisition**: High-speed polarimetric measurements with PyMoDAQ framework integration
- **Unified extension**: Single comprehensive extension for complete system control
- **Hardware abstraction**: Works with real hardware or simulation mode

Hardware Support
-----------------

Cameras
~~~~~~~
- **Photometrics Prime BSI** - sCMOS camera with PyVCAM integration
- Full camera control: exposure, gain, ROI, readout modes
- Real-time SHG image acquisition

Motion Control
~~~~~~~~~~~~~~
- **Thorlabs ELL14 Rotation Mounts** - Polarization control (QWP, HWP)
- **MaiTai Laser** - Wavelength control and EOM power modulation
- **Newport ESP300** - Precision positioning stages

Detection
~~~~~~~~~
- **Newport 1830-C Power Meter** - Optical power monitoring
- Real-time power measurements during scans

Installation
------------

Prerequisites
~~~~~~~~~~~~~

**Python Environment**::

    # Requires Python 3.9+
    python --version  # Should be 3.9 or higher

Installation Steps
~~~~~~~~~~~~~~~~~~

1. **Basic Installation** (all plugins except camera)::

    pip install pymodaq-plugins-urashg

2. **Development Installation**::

    git clone https://github.com/PyMoDAQ/pymodaq_plugins_urashg.git
    cd pymodaq_plugins_urashg
    pip install -e .

3. **Full Installation with Hardware Support**::

    # For camera support (Windows only)
    pip install "pymodaq-plugins-urashg[hardware]"

Optional Hardware Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some plugins require platform-specific hardware libraries:

**Photometrics Camera Support** (Windows only)::

    # Install PVCAM SDK from Photometrics
    # Then install with hardware dependencies:
    pip install "pymodaq-plugins-urashg[hardware]"

**Note**: On Linux/macOS, the camera plugin will run in simulation mode when PyVCAM is unavailable.

Verify Installation
~~~~~~~~~~~~~~~~~~~

::

    # Test plugin discovery
    python -c "
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec
    print('✓ All plugins import successfully')
    "

    # Test PyVCAM integration (if hardware dependencies installed)
    python -c "
    try:
        import pyvcam
        from pyvcam import pvc
        print('✓ PyVCAM available')
        pvc.init_pvcam()
        print(f'✓ PVCAM initialized, {pvc.get_cam_total()} cameras found')
        pvc.uninit_pvcam()
    except ImportError:
        print('ℹ PyVCAM not available - camera will run in simulation mode')
    "
    "

Quick Start
-----------

Manual Launch
~~~~~~~~~~~~~

::

    # Setup environment
    source .venv/bin/activate
    source /etc/profile.d/pvcam-sdk.sh

    # Launch PyMoDAQ Dashboard
    python -m pymodaq.dashboard

Then look for URASHG plugins in:

- **Move plugins**: Add Module → Move → DAQ_Move_Elliptec, DAQ_Move_MaiTai, DAQ_Move_ESP300
- **Viewer plugins**: Add Module → Viewer → DAQ_2DViewer_PrimeBSI, DAQ_0DViewer_Newport1830C
- **Extensions**: Extensions → URASHGMicroscopyExtension

Plugin Overview
---------------

Camera Plugin: DAQ_2DViewer_PrimeBSI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Features:**

- Real-time SHG imaging with Photometrics Prime BSI
- Full PyVCAM integration with hardware control
- Simulation mode for development without hardware
- ROI selection and binning support
- Temperature monitoring and control

**Key Parameters:**

- Exposure time: 1-10000 ms
- Gain settings: 1x, 2x, 4x
- Readout ports: Multiple port selection
- Clear modes: Pre-sequence, Never
- ROI: Configurable region of interest

Motion Plugins
~~~~~~~~~~~~~~

**DAQ_Move_Elliptec** - Polarization Control

- Controls up to 3 Thorlabs ELL14 rotation mounts
- Axes: HWP Incident, QWP, HWP Analyzer
- Serial communication with multi-drop addressing
- Precision: 0.1° angular resolution

**DAQ_Move_MaiTai** - Laser Control

- Wavelength control: 700-1000 nm
- EOM power modulation support
- Serial communication with status monitoring
- Real-time wavelength feedback

**DAQ_Move_ESP300** - Positioning

- Newport ESP300 motion controller
- Multiple axis coordination
- Precision positioning for sample manipulation

Power Meter Plugin: DAQ_0DViewer_Newport1830C
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Real-time optical power monitoring
- Multiple wavelength support
- Integration with measurement sequences
- Auto-ranging and averaging

Configuration
-------------

Hardware Configuration
~~~~~~~~~~~~~~~~~~~~~~

Edit ``src/pymodaq_plugins_urashg/hardware/urashg/__init__.py``::

    # Serial port assignments
    ELLIPTEC_PORT = "/dev/ttyUSB1"  # Rotation mounts
    MAITAI_PORT = "/dev/ttyUSB0"    # Laser
    NEWPORT_PORT = "/dev/ttyS0"     # Power meter

    # Camera settings
    CAMERA_COOLING_TEMP = -20  # °C
    DEFAULT_EXPOSURE = 100     # ms

Plugin Parameters
~~~~~~~~~~~~~~~~~

Each plugin supports extensive parameter customization through PyMoDAQ's parameter system. Key settings:

- **Exposure times**: Optimized for SHG signal levels
- **Polarization ranges**: Configurable angular sweeps
- **Integration times**: Balanced speed vs. signal quality
- **ROI settings**: Focus on sample regions of interest

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**PyVCAM Installation**::

    # Error: KeyError: 'PVCAM_SDK_PATH'
    export PVCAM_SDK_PATH="/opt/pvcam/sdk"
    source /etc/profile.d/pvcam-sdk.sh

**Plugin Discovery**::

    # If plugins don't appear in PyMoDAQ:
    rm -rf ~/.pymodaq/cache/  # Clear cache
    uv pip uninstall pymodaq-plugins-urashg
    uv pip install -e .       # Reinstall

**Serial Communication**::

    # Check device permissions
    sudo usermod -a -G dialout $USER  # Add user to dialout group
    sudo chmod 666 /dev/ttyUSB*        # Grant permissions

**Camera Issues**::

    # Test PVCAM directly
    /opt/pvcam/bin/PVCamTest/x86_64/PVCamTest

    # Check camera temperature
    python -c "
    from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI
    camera = DAQ_2DViewer_PrimeBSI()
    camera.ini_detector()
    print(f'Camera ready, simulation mode: {camera.simulation_mode}')
    "

Performance Tips
~~~~~~~~~~~~~~~~

1. **Optimize exposure times** based on SHG signal strength
2. **Use ROI** to reduce data transfer and increase frame rates
3. **Enable hardware binning** for improved signal-to-noise
4. **Monitor temperature** for stable long-term measurements
5. **Use appropriate averaging** for noise reduction

Support
-------

Getting Help
~~~~~~~~~~~~

1. **Check logs**: PyMoDAQ logs provide detailed error information
2. **Test individual plugins**: Isolate issues to specific components
3. **Hardware verification**: Test devices with manufacturer software
4. **GitHub Issues**: Report bugs and feature requests

Contributing
~~~~~~~~~~~~

1. **Fork the repository**
2. **Create feature branch**: ``git checkout -b feature/new-device``
3. **Follow coding standards**: Use Black formatter and type hints
4. **Add tests**: Ensure new code is tested
5. **Submit pull request**: Include clear description of changes

License
-------

MIT License - see ``LICENSE`` file for details.

Acknowledgments
---------------

- **PyMoDAQ Team** - Framework and architecture
- **Photometrics** - PyVCAM library and camera support
- **Thorlabs** - Elliptec rotation mount hardware
- **Newport** - Power meter and motion control hardware
- **μRASHG Research Community** - Scientific guidance and testing
