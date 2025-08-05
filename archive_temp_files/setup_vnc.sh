#!/bin/bash
# VNC Setup Script for URASHG PyMoDAQ

echo "🔧 Setting up VNC for PyMoDAQ access..."

# Create VNC directory if it doesn't exist
mkdir -p ~/.vnc

# Create VNC startup script
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
# VNC startup script for PyMoDAQ

# Start a basic desktop environment
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
export XDG_SESSION_TYPE=x11

# Set environment for PyMoDAQ
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export LIBGL_ALWAYS_SOFTWARE=1

# Start window manager (using xfce4 if available, otherwise openbox)
if command -v startxfce4 &> /dev/null; then
    startxfce4 &
elif command -v openbox &> /dev/null; then
    openbox &
else
    # Basic window manager
    twm &
fi

# Start a terminal
if command -v xfce4-terminal &> /dev/null; then
    xfce4-terminal &
elif command -v gnome-terminal &> /dev/null; then
    gnome-terminal &
else
    xterm &
fi
EOF

# Make xstartup executable
chmod +x ~/.vnc/xstartup

echo "✅ VNC startup script created"

# Create VNC config file for better settings
cat > ~/.vnc/config << 'EOF'
# VNC Configuration for PyMoDAQ
session=xfce
geometry=1920x1080
localhost=no
alwaysshared=yes
EOF

echo "✅ VNC config file created"

# Create systemd service for VNC (optional)
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/vncserver@.service << 'EOF'
[Unit]
Description=Remote desktop service (VNC)
After=syslog.target network.target

[Service]
Type=simple
User=%i
ExecStartPre=/bin/sh -c '/usr/bin/vncserver -kill :%i > /dev/null 2>&1 || :'
ExecStart=/usr/bin/vncserver :%i -geometry 1920x1080 -alwaysshared -localhost no
ExecStop=/usr/bin/vncserver -kill :%i

[Install]
WantedBy=default.target
EOF

echo "✅ VNC systemd service created"

echo ""
echo "🔧 VNC Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Set VNC password: vncpasswd"
echo "2. Start VNC server: vncserver :1"
echo "3. Connect from your laptop using VNC client to: <server-ip>:5901"
echo ""
echo "To stop VNC server: vncserver -kill :1"
echo ""