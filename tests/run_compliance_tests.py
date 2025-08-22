#!/usr/bin/env python
"""
Development test runner for PyMoDAQ compliance tests.

This script provides a convenient way to run the PyMoDAQ compliance test suite
during development with colored output and summary reporting.
"""

import subprocess
import sys
from pathlib import Path


def run_compliance_tests():
    """Run PyMoDAQ compliance tests with development-friendly output."""

    print("🔍 Running PyMoDAQ v5 Compliance Tests")
    print("=" * 60)

    # Change to project directory
    project_root = Path(__file__).parent

    # Run pytest with verbose output and colored results
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_pymodaq_compliance.py",
        "-v",
        "--tb=short",
        "--color=yes",
        "-x",  # Stop on first failure
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,
            text=True
        )

        print("\n" + "=" * 60)

        if result.returncode == 0:
            print("🎉 ALL COMPLIANCE TESTS PASSED!")
            print("✅ URASHG extension is fully PyMoDAQ v5 compliant")
            return True
        else:
            print("❌ Some compliance tests failed")
            print("💡 Check the output above for details")
            return False

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_specific_test_class(test_class=None):
    """Run a specific test class for targeted testing."""

    project_root = Path(__file__).parent

    if test_class:
        test_target = f"tests/test_pymodaq_compliance.py::{test_class}"
        print(f"🔍 Running specific test class: {test_class}")
    else:
        test_target = "tests/test_pymodaq_compliance.py"
        print("🔍 Running all compliance tests")

    cmd = [
        sys.executable, "-m", "pytest",
        test_target,
        "-v",
        "--tb=short",
        "--color=yes"
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        test_class = sys.argv[1]
        success = run_specific_test_class(test_class)
    else:
        success = run_compliance_tests()

    # Available test classes for reference
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\nAvailable test classes:")
        print("  TestPyMoDAQCompliance    - Core compliance tests")
        print("  TestEntryPoints          - Entry point registration tests")
        print("  TestConfiguration        - Configuration module tests")
        print("  TestPluginIntegration    - Plugin integration tests")
        print("\nUsage:")
        print("  python run_compliance_tests.py                    # Run all tests")
        print("  python run_compliance_tests.py TestEntryPoints    # Run specific class")
        sys.exit(0)

    sys.exit(0 if success else 1)
