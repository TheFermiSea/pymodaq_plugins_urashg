#!/usr/bin/env python3
"""
Comprehensive X11 and Qt debugging for PyMoDAQ over SSH
This script tests different configurations to find what works
"""

import os
import sys
import subprocess

def run_command(cmd, description=""):
    """Run a command and return result"""
    print(f"\n=== {description} ===")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_x11_basic():
    """Test basic X11 functionality"""
    print("\n" + "="*50)
    print("TESTING BASIC X11 FUNCTIONALITY")
    print("="*50)
    
    # Check DISPLAY variable
    display = os.environ.get('DISPLAY', 'NOT SET')
    print(f"DISPLAY environment variable: {display}")
    
    # Test basic X11 apps
    run_command("echo 'Testing xeyes (should work)'")
    run_command("timeout 3s xeyes", "Basic X11 test with xeyes")
    
    # Test X11 server info
    run_command("xdpyinfo | head -20", "X11 display info")
    
    # Test GLX (OpenGL) support
    run_command("glxinfo | head -10", "OpenGL/GLX info")

def test_qt_configurations():
    """Test different Qt configurations"""
    print("\n" + "="*50) 
    print("TESTING QT CONFIGURATIONS")
    print("="*50)
    
    configurations = [
        {
            "name": "Default Qt",
            "env": {}
        },
        {
            "name": "Software rendering",
            "env": {
                "QT_QUICK_BACKEND": "software",
                "QT_XCB_GL_INTEGRATION": "none",
                "LIBGL_ALWAYS_SOFTWARE": "1",
                "QT_OPENGL": "software"
            }
        },
        {
            "name": "No OpenGL",
            "env": {
                "QT_OPENGL": "none",
                "QT_QUICK_BACKEND": "software"
            }
        },
        {
            "name": "X11 compatibility mode",
            "env": {
                "QT_X11_NO_MITSHM": "1",
                "QT_GRAPHICSSYSTEM": "native",
                "QT_AUTO_SCREEN_SCALE_FACTOR": "0"
            }
        }
    ]
    
    for config in configurations:
        print(f"\n--- Testing {config['name']} ---")
        
        # Set environment variables
        old_env = {}
        for key, value in config['env'].items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
            print(f"Set {key}={value}")
        
        # Test simple Qt app
        cmd = 'python3 -c "from qtpy import QtWidgets; app=QtWidgets.QApplication([]); print(\'Qt app created successfully\')"'
        success = run_command(cmd, f"Qt test - {config['name']}")
        
        # Restore environment
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")

def test_vnc_setup():
    """Debug VNC setup issues"""
    print("\n" + "="*50)
    print("DEBUGGING VNC SETUP")
    print("="*50)
    
    # Check if VNC is running
    run_command("ps aux | grep vnc", "Check for running VNC processes")
    run_command("ps aux | grep Xvfb", "Check for running Xvfb processes")
    
    # Check VNC configuration
    vnc_dir = os.path.expanduser("~/.vnc")
    if os.path.exists(vnc_dir):
        print(f"VNC directory exists: {vnc_dir}")
        run_command(f"ls -la {vnc_dir}", "VNC directory contents")
    else:
        print(f"VNC directory does not exist: {vnc_dir}")
    
    # Test basic VNC startup
    print("\nTesting minimal VNC setup...")
    run_command("vncserver -list", "List VNC sessions")

def test_ssh_forwarding():
    """Test SSH X11 forwarding configuration"""
    print("\n" + "="*50)
    print("TESTING SSH X11 FORWARDING")
    print("="*50)
    
    # Check SSH client configuration  
    run_command("echo $SSH_CLIENT", "SSH client info")
    run_command("echo $SSH_CONNECTION", "SSH connection info")
    
    # Check X11 forwarding
    run_command("echo $DISPLAY", "Display variable")
    run_command("xauth list", "X11 authentication")
    
    # Test X11 forwarding capability
    run_command("ssh -o BatchMode=yes -o ConnectTimeout=5 localhost 'echo X11 forwarding test'", "SSH X11 forwarding test")

def create_working_solution():
    """Create a solution based on findings"""
    print("\n" + "="*50)
    print("CREATING WORKING SOLUTION")
    print("="*50)
    
    solution_script = """#!/bin/bash
# PyMoDAQ X11 Solution - Based on debugging results

echo "=== PyMoDAQ X11 Forwarding Solution ==="

# Method 1: Force software rendering (most likely to work)
export QT_QPA_PLATFORM=xcb
export QT_QUICK_BACKEND=software  
export QT_XCB_GL_INTEGRATION=none
export LIBGL_ALWAYS_SOFTWARE=1
export QT_OPENGL=software
export QT_X11_NO_MITSHM=1
export QT_GRAPHICSSYSTEM=native
export QT_AUTO_SCREEN_SCALE_FACTOR=0

echo "Environment configured for X11 forwarding compatibility"
echo "Starting PyMoDAQ Dashboard..."

dashboard
"""
    
    with open('/home/maitai/pymodaq_plugins_urashg/pymodaq_x11_solution.sh', 'w') as f:
        f.write(solution_script)
    
    os.chmod('/home/maitai/pymodaq_plugins_urashg/pymodaq_x11_solution.sh', 0o755)
    print("Created pymodaq_x11_solution.sh")

def main():
    """Run all diagnostic tests"""
    print("PyMoDAQ X11 Forwarding Diagnostic Tool")
    print("This will test various configurations to find what works")
    
    test_x11_basic()
    test_ssh_forwarding() 
    test_qt_configurations()
    test_vnc_setup()
    create_working_solution()
    
    print("\n" + "="*50)
    print("DIAGNOSTIC COMPLETE")
    print("="*50)
    print("Check the output above to see what works.")
    print("Try running: ./pymodaq_x11_solution.sh")

if __name__ == "__main__":
    main()