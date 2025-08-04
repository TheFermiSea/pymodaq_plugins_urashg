#!/usr/bin/env python3
"""
PyMoDAQ Launcher with OpenGL completely disabled
"""

import sys
import os

# CRITICAL: Set these BEFORE importing Qt
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_OPENGL'] = 'none'  # Completely disable OpenGL
os.environ['QT_XCB_GL_INTEGRATION'] = 'none'  # No OpenGL integration
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '1.4'  # Very old OpenGL version
os.environ['LIBGL_ALWAYS_INDIRECT'] = '1'

# Disable all graphics acceleration
os.environ['QT_GRAPHICSSYSTEM'] = 'raster'
os.environ['QT_STYLE_OVERRIDE'] = 'fusion'
os.environ['XLIB_SKIP_ARGB_VISUALS'] = '1'

# Disable Qt's OpenGL widgets completely
os.environ['QT_OPENGL_WIDGET'] = '0'

print("🔧 PyMoDAQ No-OpenGL Launcher")
print("=" * 40)
print(f"DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")
print("OpenGL: DISABLED")
print("Graphics: Software raster")
print()

try:
    # Test Qt first
    from qtpy import QtWidgets
    print("✅ Qt import successful")
    
    # Create minimal app to test
    app = QtWidgets.QApplication(sys.argv)
    print("✅ Qt application created")
    
    # Force software rendering
    app.setAttribute(QtWidgets.QApplication.AA_UseSoftwareOpenGL, True)
    
    print("🚀 Starting PyMoDAQ Dashboard...")
    
    # Import and start PyMoDAQ
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils import daq_utils as utils
    from pymodaq.utils.gui_utils import DockArea
    
    # Create main window
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1200, 800)
    win.setWindowTitle("URASHG PyMoDAQ Dashboard")
    
    # Create dashboard
    dashboard = DashBoard(area)
    win.show()
    
    print("✅ PyMoDAQ Dashboard started successfully!")
    print("🔬 Your URASHG plugins are ready:")
    print("   - MaiTai Laser: DAQ_Move_MaiTai")
    print("   - Elliptec Mounts: DAQ_Move_Elliptec")
    print("   - PrimeBSI Camera: DAQ_2DViewer_PrimeBSI")
    
    # Run the application
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"❌ Error launching PyMoDAQ: {e}")
    import traceback
    traceback.print_exc()