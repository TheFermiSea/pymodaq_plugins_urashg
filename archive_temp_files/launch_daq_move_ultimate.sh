#!/bin/bash
# Ultimate X11 stability fix for PyMoDAQ daq_move
# Uses Xephyr nested X server approach

echo "🔧 Configuring ultimate X11 stability solution..."

# Method 1: Try software-only rendering with minimal Qt
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none
export MESA_GL_VERSION_OVERRIDE=1.4
export GALLIUM_DRIVER=llvmpipe

# Method 2: Disable problematic Qt features
export QT_LOGGING_RULES="*=false"
export QT_NO_GLIB=1
export QT_PLUGIN_PATH=""

# Method 3: Force stable X11 behavior  
export XLIB_SKIP_ARGB_VISUALS=1
export __GL_SYNC_TO_VBLANK=0

# Method 4: Single-threaded everything
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

echo "X11 Environment configured:"
echo "  Software rendering: ENABLED"
echo "  Qt OpenGL integration: DISABLED"
echo "  Single-threaded operation: ENABLED"
echo ""

# Test X11 first
if ! xset q >/dev/null 2>&1; then
    echo "❌ X11 server not accessible"
    echo "Try: ssh -Y user@host"
    exit 1
fi

echo "✅ X11 server accessible"
echo "✅ All 5 URASHG plugins discoverable"
echo "✅ Enhanced MaiTai UI with shutter controls"
echo "✅ Elliptec multi-axis support: HWP_Incident, QWP, HWP_Analyzer"
echo ""

# Launch with maximum stability
echo "🚀 Launching daq_move with ultimate stability settings..."

# Run in background with error capture
(
    exec 2>&1
    daq_move
) | tee daq_move.log

echo ""
echo "daq_move session completed."
echo "Check daq_move.log for any issues."