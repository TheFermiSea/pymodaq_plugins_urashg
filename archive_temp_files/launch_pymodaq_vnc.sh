#!/bin/bash
# PyMoDAQ Launcher for VNC Environment

echo "🔬 Launching PyMoDAQ in VNC environment..."

# Set up environment for PyMoDAQ in VNC
export DISPLAY=:1
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

# Navigate to our URASHG plugin directory
cd /home/maitai/pymodaq_plugins_urashg

echo "Environment:"
echo "  DISPLAY: $DISPLAY"
echo "  Current directory: $(pwd)"
echo "  Available hardware controllers: ✅"
echo ""
echo "Starting PyMoDAQ Dashboard..."

# Launch PyMoDAQ
python -m pymodaq.dashboard