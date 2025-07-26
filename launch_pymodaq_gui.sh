#!/bin/bash
# PyMoDAQ GUI Launcher with X11 Compatibility
# Various Qt/OpenGL workarounds for X11 forwarding

echo "🔬 Launching PyMoDAQ Dashboard with X11 compatibility settings..."

# Method 1: Software rendering
echo "Trying Method 1: Software rendering..."
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export QT_QUICK_BACKEND=software
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export QT_OPENGL=software
export QT_LOGGING_RULES="qt5ct.debug=false"
export MESA_GL_VERSION_OVERRIDE=2.1
export LIBGL_ALWAYS_INDIRECT=1

# Disable problematic Qt features
export QT_XCB_GL_INTEGRATION=none
export QT_STYLE_OVERRIDE=fusion

echo "Environment set. Launching PyMoDAQ..."
python -m pymodaq.dashboard 2>&1