#!/bin/bash
# Script to run PyMoDAQ dashboard over SSH X11 forwarding
# This disables hardware acceleration to prevent X11/OpenGL crashes

echo "Starting PyMoDAQ Dashboard for remote X11 access..."
echo "This configuration disables hardware acceleration for SSH compatibility"

# Set environment variables to disable hardware acceleration
export QT_QUICK_BACKEND=software
export QT_XCB_GL_INTEGRATION=none  
export LIBGL_ALWAYS_SOFTWARE=1
export QT_OPENGL=software
export QT_GRAPHICSSYSTEM=native

# Also disable any Qt scaling that might cause issues
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_SCALE_FACTOR=1

echo "Environment configured for remote access:"
echo "  QT_QUICK_BACKEND=$QT_QUICK_BACKEND"
echo "  QT_XCB_GL_INTEGRATION=$QT_XCB_GL_INTEGRATION"
echo "  LIBGL_ALWAYS_SOFTWARE=$LIBGL_ALWAYS_SOFTWARE"
echo "  QT_OPENGL=$QT_OPENGL"

echo ""
echo "Launching PyMoDAQ Dashboard..."

# Launch the dashboard
dashboard