#!/usr/bin/env python3
"""
Comprehensive test runner for all PyMoDAQ URASHG plugins

This script runs complete mock testing for all three plugins in the URASHG
microscopy system: Elliptec rotation mounts, MaiTai laser, and Prime BSI camera.
"""

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path


def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title):
    """Print formatted subsection header"""
    print("\n" + "-" * 60)
    print(f" {title}")
    print("-" * 60)


def check_environment():
    """Check if the test environment is properly set up"""
    print_section("Environment Check")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(
            f"[ERROR] Python {python_version.major}.{python_version.minor} detected - Python 3.8+ required"
        )
        return False
    else:
        print(
            f"[OK] Python {python_version.major}.{python_version.minor}.{python_version.micro} detected"
        )

    # Check required modules
    required_modules = [
        ("numpy", "numpy"),
        ("unittest.mock", "unittest.mock"),
        ("pathlib", "pathlib"),
    ]

    missing_modules = []
    for module_name, import_name in required_modules:
        try:
            importlib.import_module(import_name)
            print(f"[OK] {module_name} available")
        except ImportError:
            missing_modules.append(module_name)
            print(f"[MISSING] {module_name} not available")

    if missing_modules:
        print(f"\n[WARNING]  Missing required modules: {', '.join(missing_modules)}")
        print("Please run: python setup_test_environment.py")
        return False

    # Check plugin files exist
    plugin_files = [
        "src/pymodaq_plugins_urashg/daq_move_plugins/DAQ_Move_Elliptec.py",
        "src/pymodaq_plugins_urashg/daq_move_plugins/DAQ_Move_MaiTai.py",
        "src/pymodaq_plugins_urashg/daq_viewer_plugins/plugins_2D/DAQ_Viewer_PrimeBSI.py",
    ]

    base_path = Path(__file__).parent.parent
    missing_files = []

    for plugin_file in plugin_files:
        full_path = base_path / plugin_file
        if full_path.exists():
            print(f"[OK] {plugin_file}")
        else:
            missing_files.append(plugin_file)
            print(f"ERROR: {plugin_file}")

    if missing_files:
        print(f"\n[WARNING]  Missing plugin files: {len(missing_files)} files")
        return False

    print("\nSUCCESS: Environment check passed!")
    return True


def run_individual_test(test_script):
    """Run an individual test script"""
    test_path = Path(__file__).parent / test_script

    if not test_path.exists():
        print(f"ERROR: Test script not found: {test_script}")
        return False, f"Script not found: {test_script}"

    try:
        print(f"Running {test_script}...")
        start_time = time.time()

        # Run the test script
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )  # 5 minute timeout

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"[OK] {test_script} PASSED ({duration:.1f}s)")
            return True, f"PASSED in {duration:.1f}s"
        else:
            print(f"ERROR: {test_script} FAILED ({duration:.1f}s)")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
            return False, f"FAILED in {duration:.1f}s"

    except subprocess.TimeoutExpired:
        print(f"ERROR: {test_script} TIMEOUT")
        return False, "TIMEOUT after 5 minutes"
    except Exception as e:
        print(f"ERROR: {test_script} ERROR: {e}")
        return False, f"ERROR: {e}"


def run_plugin_tests():
    """Run all plugin tests"""
    print_section("Plugin Tests")

    # Define test scripts and their descriptions
    test_scripts = [
        ("test_elliptec_plugin.py", "Elliptec Rotation Mount Controller"),
        ("test_maitai_plugin.py", "MaiTai Ti:Sapphire Laser Controller"),
        ("test_camera_plugin.py", "Prime BSI sCMOS Camera"),
    ]

    results = {}
    total_start_time = time.time()

    for script, description in test_scripts:
        print(f"\n[TESTING] {description}")
        print(f"   Script: {script}")

        success, message = run_individual_test(script)
        results[description] = (success, message)

        if success:
            print(f"   Result: [PASS] {message}")
        else:
            print(f"   Result: [FAIL] {message}")

    total_end_time = time.time()
    total_duration = total_end_time - total_start_time

    return results, total_duration


def generate_test_report(results, total_duration):
    """Generate comprehensive test report"""
    print_header("Test Report")

    # Summary statistics
    total_tests = len(results)
    passed_tests = sum(1 for success, _ in results.values() if success)
    failed_tests = total_tests - passed_tests

    print(f"Total Tests:    {total_tests}")
    print(f"Passed Tests:   {passed_tests}")
    print(f"Failed Tests:   {failed_tests}")
    print(f"Success Rate:   {(passed_tests/total_tests)*100:.1f}%")
    print(f"Total Duration: {total_duration:.1f} seconds")

    # Detailed results
    print("\nDetailed Results:")
    print("-" * 80)

    for test_name, (success, message) in results.items():
        status = "[PASSED]" if success else "[FAILED]"
        print(f"{status:<12} {test_name:<40} {message}")

    # Plugin-specific validation
    print("\nPlugin Validation Summary:")
    print("-" * 80)

    plugin_validations = {
        "Elliptec Rotation Mount Controller": [
            "3 axes (HWP_inc, QWP, HWP_ana)",
            "13 error codes defined",
            "25 commands in reference",
            "Serial communication simulation",
            "Position conversion accuracy",
            "Multi-axis operation",
        ],
        "MaiTai Ti:Sapphire Laser Controller": [
            "Wavelength and shutter control",
            "Background status monitoring",
            "Serial communication protocol",
            "Threading safety",
            "Command reference validation",
            "Safety system simulation",
        ],
        "Prime BSI sCMOS Camera": [
            "PyVCAM integration simulation",
            "Parameter discovery and configuration",
            "ROI functionality",
            "Data acquisition simulation",
            "Advanced settings handling",
            "Temperature monitoring",
        ],
    }

    for plugin_name, validations in plugin_validations.items():
        plugin_success = results.get(plugin_name, (False, ""))[0]
        status_symbol = "[PASS]" if plugin_success else "[FAIL]"

        print(f"\n{status_symbol} {plugin_name}:")
        for validation in validations:
            print(f"    • {validation}")

    return passed_tests == total_tests


def run_integration_tests():
    """Run basic integration tests"""
    print_section("Integration Tests")

    try:
        # Test that all plugins can be imported together
        print("Testing plugin imports...")

        # Add source directory to path
        src_path = Path(__file__).parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        # Mock required modules before importing
        from unittest.mock import Mock

        # Mock PyMoDAQ base modules
        sys.modules["pymodaq.control_modules.move_utility_classes"] = Mock()
        sys.modules["pymodaq.control_modules.viewer_utility_classes"] = Mock()
        sys.modules["pymodaq.utils.daq_utils"] = Mock()
        sys.modules["pymodaq.utils.parameter"] = Mock()
        sys.modules["pymodaq.utils.data"] = Mock()
        sys.modules["serial"] = Mock()
        sys.modules["pyvcam"] = Mock()

        # Try importing all plugins
        try:
            from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_Elliptec import (
                DAQ_Move_Elliptec,
            )

            print("[OK] Elliptec plugin import successful")
        except Exception as e:
            print(f"ERROR: Elliptec plugin import failed: {e}")
            return False

        try:
            from pymodaq_plugins_urashg.daq_move_plugins.DAQ_Move_MaiTai import (
                DAQ_Move_MaiTai,
            )

            print("[OK] MaiTai plugin import successful")
        except Exception as e:
            print(f"ERROR: MaiTai plugin import failed: {e}")
            return False

        try:
            from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.DAQ_Viewer_PrimeBSI import (
                DAQ_2DViewer_PrimeBSI,
            )

            print("[OK] Camera plugin import successful")
        except Exception as e:
            print(f"ERROR: Camera plugin import failed: {e}")
            return False

        print("\n[SUCCESS] All integration tests passed!")
        return True

    except Exception as e:
        print(f"ERROR: Integration test failed: {e}")
        return False


def main():
    """Main test execution function"""
    print_header("PyMoDAQ URASHG Plugin Test Suite")
    print(
        "This test suite validates all plugins in mock mode without requiring hardware."
    )

    start_time = time.time()

    # Step 1: Environment check
    if not check_environment():
        print(
            "\n[ERROR] Environment check failed. Please set up the test environment first."
        )
        return 1

    # Step 2: Integration tests
    if not run_integration_tests():
        print("\n[ERROR] Integration tests failed. Check plugin imports.")
        return 1

    # Step 3: Plugin tests
    results, test_duration = run_plugin_tests()

    # Step 4: Generate report
    all_passed = generate_test_report(results, test_duration)

    # Final summary
    end_time = time.time()
    total_time = end_time - start_time

    print_header("Final Summary")

    if all_passed:
        print("SUCCESS: ALL TESTS PASSED!")
        print(
            "\nAll PyMoDAQ URASHG plugins have been successfully validated in mock mode."
        )
        print("The plugins are ready for integration with actual hardware.")
        print("\nNext steps:")
        print(
            "1. Connect actual hardware (Elliptec mounts, MaiTai laser, Prime BSI camera)"
        )
        print("2. Test plugins with real hardware in PyMoDAQ Dashboard")
        print("3. Calibrate hardware-specific parameters")
        print("4. Validate full system integration")
    else:
        print("[FAILED] SOME TESTS FAILED!")
        print(
            "\nPlease review the test results above and fix any issues before proceeding."
        )
        print("Check the individual test outputs for detailed error information.")

    print(f"\nTotal execution time: {total_time:.1f} seconds")

    return 0 if all_passed else 1


def setup_help():
    """Print setup instructions"""
    print_header("Setup Instructions")
    print(
        """
To set up the test environment, run these commands:

1. Install PyMoDAQ v5:
   pip install "pymodaq>=5.0.0"

2. Install testing dependencies:
   pip install pytest pytest-mock numpy qtpy

3. Install plugin-specific dependencies:
   pip install pyserial  # For Elliptec and MaiTai plugins

4. Run environment setup:
   python setup_test_environment.py

5. Run all tests:
   python run_all_tests.py

For individual plugin testing:
   python test_elliptec_plugin.py
   python test_maitai_plugin.py
   python test_camera_plugin.py
"""
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        setup_help()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] in ["--setup", "setup"]:
        # Run setup script
        setup_script = Path(__file__).parent / "setup_test_environment.py"
        if setup_script.exists():
            subprocess.run([sys.executable, str(setup_script)])
        else:
            print("Setup script not found. Please run setup manually.")
        sys.exit(0)
    else:
        sys.exit(main())
