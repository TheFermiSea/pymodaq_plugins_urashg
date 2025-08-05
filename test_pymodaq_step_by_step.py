#!/usr/bin/env python3
"""
Step-by-step PyMoDAQ debugging
Test each component individually to isolate the problem
"""

import os
import sys
import subprocess
import time

def test_step(step_name, test_func):
    """Run a test step and report results"""
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print('='*60)
    
    try:
        result = test_func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\nRESULT: {status}")
        return result
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def step1_basic_python():
    """Test basic Python and imports"""
    print("Testing basic Python environment...")
    
    try:
        import sys
        print(f"Python version: {sys.version}")
        
        import qtpy
        print(f"QtPy available: {qtpy.__version__}")
        
        print("Testing basic Qt import...")
        from qtpy import QtWidgets, QtCore
        print("Qt imports successful")
        
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False

def step2_qt_application():
    """Test Qt application creation"""
    print("Testing Qt application creation...")
    
    try:
        from qtpy import QtWidgets
        
        # Try to create QApplication
        app = QtWidgets.QApplication.instance()
        if app is None:
            print("Creating new QApplication...")
            app = QtWidgets.QApplication([])
        else:
            print("Using existing QApplication")
        
        print("QApplication created successfully")
        return True
        
    except Exception as e:
        print(f"Qt application error: {e}")
        return False

def step3_simple_widget():
    """Test simple Qt widget"""
    print("Testing simple Qt widget creation...")
    
    try:
        from qtpy import QtWidgets
        
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        
        # Create a simple widget
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Test Widget")
        widget.resize(300, 200)
        
        print("Simple widget created successfully")
        
        # Try to show it briefly
        widget.show()
        app.processEvents()
        time.sleep(0.5)
        widget.hide()
        
        print("Widget shown and hidden successfully")
        return True
        
    except Exception as e:
        print(f"Widget error: {e}")
        return False

def step4_pymodaq_imports():
    """Test PyMoDAQ imports"""
    print("Testing PyMoDAQ imports...")
    
    try:
        import pymodaq
        print(f"PyMoDAQ version: {pymodaq.__version__}")
        
        from pymodaq.dashboard import DashBoard
        print("DashBoard import successful")
        
        return True
        
    except Exception as e:
        print(f"PyMoDAQ import error: {e}")
        return False

def step5_dashboard_creation():
    """Test PyMoDAQ dashboard creation"""
    print("Testing PyMoDAQ dashboard creation...")
    
    try:
        from qtpy import QtWidgets
        from pymodaq.dashboard import DashBoard
        
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        
        print("Creating dashboard components...")
        
        # The issue might be here - let's try to create the dashboard step by step
        # First, let's see what DashBoard expects
        import inspect
        sig = inspect.signature(DashBoard.__init__)
        print(f"DashBoard.__init__ signature: {sig}")
        
        return True
        
    except Exception as e:
        print(f"Dashboard creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def step6_environment_test():
    """Test different environment configurations"""
    print("Testing with different environment configurations...")
    
    configs = [
        ("Default", {}),
        ("Software Rendering", {
            "QT_QUICK_BACKEND": "software",
            "QT_XCB_GL_INTEGRATION": "none", 
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "QT_OPENGL": "software"
        }),
        ("X11 Compatibility", {
            "QT_X11_NO_MITSHM": "1",
            "QT_GRAPHICSSYSTEM": "native"
        })
    ]
    
    for config_name, env_vars in configs:
        print(f"\n--- Testing {config_name} ---")
        
        # Save original environment
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
            print(f"Set {key}={value}")
        
        try:
            from qtpy import QtWidgets
            app = QtWidgets.QApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([])
            
            widget = QtWidgets.QLabel("Test")
            widget.show()
            app.processEvents()
            widget.hide()
            
            print(f"✅ {config_name} works")
            
        except Exception as e:
            print(f"❌ {config_name} failed: {e}")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    return True

def main():
    """Run all test steps"""
    print("PyMoDAQ Step-by-Step Debugging")
    print("This will test each component individually")
    
    steps = [
        ("Basic Python Environment", step1_basic_python),
        ("Qt Application Creation", step2_qt_application), 
        ("Simple Qt Widget", step3_simple_widget),
        ("PyMoDAQ Imports", step4_pymodaq_imports),
        ("Dashboard Creation", step5_dashboard_creation),
        ("Environment Testing", step6_environment_test)
    ]
    
    results = []
    for step_name, step_func in steps:
        result = test_step(step_name, step_func)
        results.append((step_name, result))
        
        if not result:
            print(f"\n⚠️  Stopping at failed step: {step_name}")
            break
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for step_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {step_name}")
    
    print(f"\nNext steps based on results above...")

if __name__ == "__main__":
    main()