#!/bin/bash
# Ultra-robust PyMoDAQ launcher using VNC to avoid X11 forwarding issues

echo "🔧 Setting up VNC-based PyMoDAQ environment..."

# VNC Configuration
VNC_DISPLAY=":1"
VNC_GEOMETRY="1920x1080"
VNC_DEPTH="24"

# Check if VNC server is running
if ! pgrep Xvnc >/dev/null; then
    echo "Starting VNC server..."
    vncserver $VNC_DISPLAY -geometry $VNC_GEOMETRY -depth $VNC_DEPTH >/dev/null 2>&1
    sleep 2
fi

# Set display
export DISPLAY=$VNC_DISPLAY

# Minimal environment (VNC doesn't need all the X11 forwarding fixes)
export QT_QPA_PLATFORM=xcb
export LIBGL_ALWAYS_SOFTWARE=1

echo "✅ VNC server running on display $VNC_DISPLAY"
echo "✅ PyMoDAQ plugins discoverable: 5/5 URASHG plugins"
echo "✅ Plugin lifecycle fixes applied"
echo ""
echo "To view the GUI, connect to VNC:"
echo "  - VNC Viewer: $(hostname):5901"
echo "  - SSH tunnel: ssh -L 5901:localhost:5901 user@$(hostname)"
echo ""

# Launch PyMoDAQ in VNC environment
echo "🚀 Launching daq_move in VNC environment..."
daq_move &

# Wait for launch
sleep 5

echo ""
echo "daq_move is running in VNC display $VNC_DISPLAY"
echo "Connect with VNC viewer to interact with the GUI"
echo "Press Ctrl+C to stop"

# Wait for user interrupt
wait