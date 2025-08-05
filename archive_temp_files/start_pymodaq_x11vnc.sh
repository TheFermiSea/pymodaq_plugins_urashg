#!/bin/bash
# Start PyMoDAQ using Xvfb + x11vnc (lightweight virtual display + VNC)

DISPLAY_NUM="99"
VNC_PORT="5902" 
GEOMETRY="1400x1000"

echo "=== PyMoDAQ X11VNC Setup ==="
echo "Using Xvfb (virtual framebuffer) + x11vnc for remote access"
echo ""

# Kill any existing processes
pkill -f "Xvfb.*:$DISPLAY_NUM" 2>/dev/null
pkill -f "x11vnc.*:$DISPLAY_NUM" 2>/dev/null
sleep 1

# Start virtual X server
echo "Starting Xvfb on display :$DISPLAY_NUM..."
Xvfb :$DISPLAY_NUM -screen 0 ${GEOMETRY}x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2

# Check if Xvfb started successfully
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "❌ Failed to start Xvfb"
    exit 1
fi

echo "✅ Xvfb started (PID: $XVFB_PID)"

# Start x11vnc on the virtual display
echo "Starting x11vnc on port $VNC_PORT..."
x11vnc -display :$DISPLAY_NUM -N -forever -shared -rfbport $VNC_PORT &
VNC_PID=$!

# Wait for x11vnc to start
sleep 2

# Check if x11vnc started successfully
if ! kill -0 $VNC_PID 2>/dev/null; then
    echo "❌ Failed to start x11vnc"
    kill $XVFB_PID 2>/dev/null
    exit 1
fi

echo "✅ x11vnc started (PID: $VNC_PID)"
echo ""
echo "🔗 Connection Information:"
echo "   VNC Server: $(hostname):$VNC_PORT"
echo "   Display: :$DISPLAY_NUM"
echo "   Geometry: $GEOMETRY"
echo ""
echo "📱 To connect:"
echo "   1. Use VNC viewer to connect to: $(hostname):$VNC_PORT"
echo "   2. Or SSH tunnel: ssh -L $VNC_PORT:localhost:$VNC_PORT $(whoami)@$(hostname)"
echo ""

# Function to start PyMoDAQ in the virtual display
start_pymodaq() {
    echo "🚀 Starting PyMoDAQ Dashboard..."
    export DISPLAY=:$DISPLAY_NUM
    export QT_X11_NO_MITSHM=1
    export QT_GRAPHICSSYSTEM=native
    export QT_AUTO_SCREEN_SCALE_FACTOR=0
    
    # Start a simple window manager first
    fluxbox -display :$DISPLAY_NUM &
    sleep 2
    
    # Start PyMoDAQ
    dashboard &
    PYMODAQ_PID=$!
    
    echo "✅ PyMoDAQ Dashboard started (PID: $PYMODAQ_PID)"
    echo "Connect with VNC viewer to see the interface"
    
    return $PYMODAQ_PID
}

# Ask user if they want to start PyMoDAQ now
echo "🤖 Start PyMoDAQ Dashboard now? (y/n): "
read -r answer
if [[ $answer =~ ^[Yy]$ ]]; then
    start_pymodaq
fi

echo ""
echo "🛑 To stop everything:"
echo "   kill $XVFB_PID $VNC_PID"
echo "   Or run: pkill -f 'Xvfb.*:$DISPLAY_NUM'; pkill -f 'x11vnc.*:$DISPLAY_NUM'"

# Keep script running
echo ""
echo "Press Ctrl+C to stop all processes and exit"
trap "echo 'Stopping...'; kill $XVFB_PID $VNC_PID 2>/dev/null; exit" INT
wait