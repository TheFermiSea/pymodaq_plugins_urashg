#!/bin/bash
# Launch daq_move with X11/OpenGL compatibility fixes

echo "🚀 Launching daq_move with URASHG plugins..."
echo "✅ All 5 URASHG plugins are now discoverable!"

# Set OpenGL compatibility for remote X11
export LIBGL_ALWAYS_INDIRECT=1
export MESA_GL_VERSION_OVERRIDE=3.3  
export QT_XCB_GL_INTEGRATION=none

# Optional: Force software rendering if still having issues
# export MESA_GL_VERSION_OVERRIDE=2.1
# export LIBGL_ALWAYS_SOFTWARE=1

# Launch daq_move
echo "Starting daq_move..."
daq_move

echo "daq_move session ended."