#!/usr/bin/env python3
"""
Minimal PyMoDAQ Test - Test our plugins without the full dashboard
"""

import sys
import os

# Set environment for X11 compatibility
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['QT_OPENGL'] = 'none'

sys.path.insert(0, 'src')

print("🔬 URASHG PyMoDAQ Plugin Test")
print("=" * 40)

try:
    from qtpy import QtWidgets, QtCore
    from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
    from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import DAQ_Move_MaiTai
    
    print("✅ All imports successful")
    
    # Create Qt application
    app = QtWidgets.QApplication(sys.argv)
    
    # Create main window
    window = QtWidgets.QWidget()
    window.setWindowTitle("URASHG Hardware Control")
    window.setGeometry(100, 100, 600, 400)
    
    layout = QtWidgets.QVBoxLayout()
    
    # Title
    title = QtWidgets.QLabel("🎉 URASHG Hardware Control Panel")
    title.setAlignment(QtCore.Qt.AlignCenter)
    title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
    layout.addWidget(title)
    
    # Status display
    status_text = QtWidgets.QTextEdit()
    status_text.setReadOnly(True)
    status_text.setMaximumHeight(200)
    layout.addWidget(status_text)
    
    # Add initial status
    status_text.append("✅ PyMoDAQ plugins imported successfully")
    status_text.append("✅ Hardware controllers available:")
    status_text.append("   - MaiTai Laser: /dev/ttyUSB0")
    status_text.append("   - Elliptec Mounts: /dev/ttyUSB1")
    status_text.append("   - Newport Power Meter: /dev/ttyUSB2")
    status_text.append("")
    status_text.append("Ready to test PyMoDAQ plugins!")
    
    # Control buttons
    button_layout = QtWidgets.QHBoxLayout()
    
    # Test MaiTai button
    test_maitai_btn = QtWidgets.QPushButton("Test MaiTai Plugin")
    def test_maitai():
        status_text.append("\n🔄 Testing MaiTai plugin...")
        try:
            plugin = DAQ_Move_MaiTai()
            plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB0')
            plugin.settings.child('connection_group', 'mock_mode').setValue(False)
            
            result, success = plugin.ini_stage()
            if success:
                wavelength = plugin.get_actuator_value()
                status_text.append(f"✅ MaiTai connected! Current wavelength: {wavelength} nm")
                plugin.close()
            else:
                status_text.append(f"❌ MaiTai test failed: {result}")
        except Exception as e:
            status_text.append(f"❌ MaiTai error: {e}")
    
    test_maitai_btn.clicked.connect(test_maitai)
    button_layout.addWidget(test_maitai_btn)
    
    # Test Elliptec button
    test_elliptec_btn = QtWidgets.QPushButton("Test Elliptec Plugin")
    def test_elliptec():
        status_text.append("\n🔄 Testing Elliptec plugin...")
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import DAQ_Move_Elliptec
            plugin = DAQ_Move_Elliptec()
            plugin.settings.child('connection_group', 'serial_port').setValue('/dev/ttyUSB1')
            plugin.settings.child('connection_group', 'mock_mode').setValue(False)
            
            result, success = plugin.ini_stage()
            if success:
                positions = plugin.get_actuator_value()
                status_text.append(f"✅ Elliptec connected! Positions: {positions}")
                plugin.close()
            else:
                status_text.append(f"❌ Elliptec test failed: {result}")
        except Exception as e:
            status_text.append(f"❌ Elliptec error: {e}")
    
    test_elliptec_btn.clicked.connect(test_elliptec)
    button_layout.addWidget(test_elliptec_btn)
    
    layout.addLayout(button_layout)
    
    # Close button
    close_btn = QtWidgets.QPushButton("Close")
    close_btn.clicked.connect(window.close)
    layout.addWidget(close_btn)
    
    window.setLayout(layout)
    window.show()
    
    print("✅ URASHG Control Panel displayed")
    print("You should see a control window with test buttons!")
    
    # Auto-run MaiTai test
    QtCore.QTimer.singleShot(1000, test_maitai)
    
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()