#!/usr/bin/env python3
"""
Simple PyMoDAQ Launcher - OpenGL disabled
"""

import sys
import os

# Set environment BEFORE any imports
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_OPENGL'] = 'none'
os.environ['QT_XCB_GL_INTEGRATION'] = 'none'
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['QT_X11_NO_MITSHM'] = '1'

print("🔬 Starting PyMoDAQ for URASHG...")

try:
    # Direct PyMoDAQ launch
    from pymodaq.dashboard import main
    main()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()