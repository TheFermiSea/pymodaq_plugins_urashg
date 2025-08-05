#!/bin/bash
# Start PyMoDAQ in a VNC session for reliable remote access

VNC_DISPLAY=":1"
VNC_PORT="5901"
VNC_GEOMETRY="1400x1000"

echo "=== PyMoDAQ VNC Setup ==="
echo "This will start PyMoDAQ in a VNC session for stable remote access"
echo ""

# Check if VNC is already running on display 1
if pgrep -f "Xvnc.*:1" > /dev/null; then
    echo "VNC server already running on display :1"
    echo "To connect: use VNC viewer to connect to $(hostname):5901"
    echo "To kill existing session: vncserver -kill :1"
    exit 1
fi

# Create VNC startup script
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XKL_XMODMAP_DISABLE=1

# Start a basic window manager
/usr/bin/startxfce4 &
# Or if xfce4 is not available, try other window managers
# /usr/bin/mate-session &
# /usr/bin/gnome-session &
# /usr/bin/fluxbox &

# Wait a bit for the window manager to start
sleep 2

# Set PyMoDAQ environment for better compatibility
export QT_X11_NO_MITSHM=1
export QT_GRAPHICSSYSTEM=native
export QT_AUTO_SCREEN_SCALE_FACTOR=0

# Start a terminal
/usr/bin/xfce4-terminal &
EOF

chmod +x ~/.vnc/xstartup

echo "Starting VNC server on display $VNC_DISPLAY..."
echo "Geometry: $VNC_GEOMETRY"
echo ""

# Start VNC server
vncserver $VNC_DISPLAY -geometry $VNC_GEOMETRY -depth 24

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ VNC Server started successfully!"
    echo ""
    echo "🔗 Connection Information:"
    echo "   VNC Server: $(hostname):$VNC_PORT"
    echo "   Display: $VNC_DISPLAY"
    echo "   Geometry: $VNC_GEOMETRY"
    echo ""
    echo "📱 To connect:"
    echo "   1. Use any VNC viewer (TigerVNC, RealVNC, etc.)"
    echo "   2. Connect to: $(hostname):$VNC_PORT"
    echo "   3. Or use SSH tunnel: ssh -L 5901:localhost:5901 $(whoami)@$(hostname)"
    echo ""
    echo "🚀 To start PyMoDAQ:"
    echo "   1. Open terminal in VNC session"
    echo "   2. Run: dashboard"
    echo ""
    echo "🛑 To stop VNC server:"
    echo "   vncserver -kill $VNC_DISPLAY"
else
    echo "❌ Failed to start VNC server"
    exit 1
fi