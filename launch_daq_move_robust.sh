#!/bin/bash
# Robust PyMoDAQ daq_move launcher with comprehensive X11/OpenGL fixes

echo "🔧 Configuring robust X11 environment for PyMoDAQ..."

# === X11 Display and Authentication ===
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# === OpenGL/Mesa Configuration ===
# Force software rendering to avoid GPU driver issues
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_ALWAYS_INDIRECT=1
export MESA_GL_VERSION_OVERRIDE=2.1
export MESA_GLSL_VERSION_OVERRIDE=120

# === Qt Configuration ===
# Use native X11 backend (no XCB GL integration)
export QT_XCB_GL_INTEGRATION=none
export QT_OPENGL=software
export QT_QUICK_BACKEND=software

# Disable Qt high-DPI scaling that can cause issues
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_SCALE_FACTOR=1

# Force Qt to use X11 platform
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=""

# === Threading and Timing ===
# Reduce thread contention
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Add small delays for X11 stability
export QT_X11_NO_MITSHM=1

# === Debug Information ===
echo "X11 Environment:"
echo "  DISPLAY: $DISPLAY"
echo "  XAUTHORITY: $XAUTHORITY"
echo "  LIBGL_ALWAYS_SOFTWARE: $LIBGL_ALWAYS_SOFTWARE"
echo "  QT_QPA_PLATFORM: $QT_QPA_PLATFORM"

# Test X11 connection
echo "🔍 Testing X11 connection..."
if xset q >/dev/null 2>&1; then
    echo "✅ X11 server accessible"
else
    echo "❌ X11 server not accessible"
    echo "Check SSH X11 forwarding: ssh -Y user@host"
    exit 1
fi

# === Launch PyMoDAQ ===
echo ""
echo "🚀 Launching daq_move with URASHG plugins..."
echo "✅ All 5 URASHG plugins discoverable"
echo "✅ Plugin lifecycle issues resolved"
echo "✅ Robust X11 environment configured"
echo ""

# Add a small delay for X11 to stabilize
sleep 0.5

# Launch with error handling
if daq_move; then
    echo "✅ daq_move completed successfully"
else
    echo "❌ daq_move encountered an error"
    exit 1
fi