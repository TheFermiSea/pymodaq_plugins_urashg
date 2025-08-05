#!/bin/bash
# Fix X11 forwarding for PyMoDAQ
# This script sets up all the necessary environment variables to make Qt work over X11

echo "🔧 Setting up X11 environment for PyMoDAQ..."

# Kill any existing VNC servers first
pkill -f Xvnc

# Force Qt to use software rendering and disable problematic features
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export QT_QUICK_BACKEND=software
export QT_OPENGL=software
export QT_XCB_GL_INTEGRATION=none

# OpenGL software rendering
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_ALWAYS_INDIRECT=1
export GALLIUM_DRIVER=llvmpipe
export MESA_GL_VERSION_OVERRIDE=2.1
export MESA_GLSL_VERSION_OVERRIDE=120

# Disable hardware acceleration
export QT_GRAPHICSSYSTEM=raster
export QT_STYLE_OVERRIDE=fusion

# Disable compositing and effects
export QT_COMP=0
export QT_NO_GLIB=1

# X11 specific fixes
export XLIB_SKIP_ARGB_VISUALS=1

# PyQt5 specific fixes
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_SCALE_FACTOR=1

# Debugging (comment out for cleaner output)
# export QT_LOGGING_RULES="*.debug=false"
export QT_DEBUG_PLUGINS=0

echo "Environment variables set:"
echo "  QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo "  LIBGL_ALWAYS_SOFTWARE: $LIBGL_ALWAYS_SOFTWARE"
echo "  DISPLAY: $DISPLAY"

echo ""
echo "🚀 Launching PyMoDAQ with X11 fixes..."

# Navigate to our project directory
cd /home/maitai/pymodaq_plugins_urashg

# Launch PyMoDAQ with minimal startup
python -c "
import sys
import os
print('Python path:', sys.executable)
print('Current directory:', os.getcwd())
print('DISPLAY:', os.environ.get('DISPLAY', 'Not set'))

# Test Qt import first
try:
    from qtpy import QtWidgets
    print('✅ QtPy import successful')
    
    # Create minimal app to test
    app = QtWidgets.QApplication(sys.argv)
    print('✅ Qt application created successfully')
    
    # Now try PyMoDAQ
    print('Starting PyMoDAQ...')
    from pymodaq.dashboard import main
    main()
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"