#!/bin/bash
# PyMoDAQ Dashboard X11 Wrapper
# This script sets the correct environment and launches PyMoDAQ dashboard

echo "=================================================="
echo "PyMoDAQ Dashboard - X11 Forwarding Solution"
echo "=================================================="
echo "Fixing X11/OpenGL issues for SSH remote access"
echo ""

# Set environment variables for X11 compatibility
export QT_X11_NO_MITSHM=1
export QT_GRAPHICSSYSTEM=native
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QUICK_BACKEND=software
export QT_OPENGL=software

echo "✅ Environment configured:"
echo "   QT_X11_NO_MITSHM=$QT_X11_NO_MITSHM"
echo "   LIBGL_ALWAYS_SOFTWARE=$LIBGL_ALWAYS_SOFTWARE"
echo "   QT_OPENGL=$QT_OPENGL"
echo ""

echo "🚀 Launching PyMoDAQ Dashboard..."
echo "   (This should work without crashing XQuartz)"
echo ""

# Launch the Python dashboard
python dashboard_x11_fixed.py

echo ""
echo "Dashboard session ended."