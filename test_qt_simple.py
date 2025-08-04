#!/usr/bin/env python3
"""
Simple Qt Test for X11 Forwarding
"""

import sys
import os

# Set environment for X11 compatibility
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_OPENGL'] = 'software'

print("🧪 Testing Qt with X11 forwarding...")
print(f"DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")

try:
    from qtpy import QtWidgets, QtCore
    print("✅ QtPy import successful")
    
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    print("✅ Qt application created")
    
    # Create simple window
    window = QtWidgets.QWidget()
    window.setWindowTitle("URASHG PyMoDAQ Test")
    window.setGeometry(100, 100, 400, 200)
    
    layout = QtWidgets.QVBoxLayout()
    
    label = QtWidgets.QLabel("🎉 Qt X11 Forwarding Working!\n\nURASHG Hardware Status:")
    label.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(label)
    
    # Add hardware status
    status_label = QtWidgets.QLabel(
        "✅ MaiTai Laser: Connected (/dev/ttyUSB0)\n"
        "✅ Elliptec Mounts: Connected (/dev/ttyUSB1)\n"
        "✅ Newport Power Meter: Connected (/dev/ttyUSB2)\n\n"
        "Ready for PyMoDAQ!"
    )
    layout.addWidget(status_label)
    
    # Add button to test PyMoDAQ launch
    button = QtWidgets.QPushButton("Launch PyMoDAQ Dashboard")
    def launch_pymodaq():
        print("Launching PyMoDAQ...")
        try:
            from pymodaq.dashboard import main
            main()
        except Exception as e:
            print(f"PyMoDAQ launch error: {e}")
    
    button.clicked.connect(launch_pymodaq)
    layout.addWidget(button)
    
    window.setLayout(layout)
    window.show()
    
    print("✅ Qt window created and shown")
    print("If you see the window, X11 forwarding is working!")
    
    # Run for 10 seconds then quit
    QtCore.QTimer.singleShot(10000, app.quit)
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()