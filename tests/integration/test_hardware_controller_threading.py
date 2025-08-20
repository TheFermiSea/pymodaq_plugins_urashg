#!/usr/bin/env python3
"""
Debug version to isolate the import issue causing CI hangs.

This minimal test aims to identify what's causing the "No module named pip" error
and potential hanging in CI environments.
"""

import pytest
import gc
import sys
from pathlib import Path

# Add project to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.timeout(5)
def test_basic_imports():
    """Test that we can import the controller modules without errors."""

    # Test 1: Try to import ESP300Controller
    try:
        print("Attempting to import ESP300Controller...")
        from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller
        print("✅ ESP300Controller import successful")

        # Check for __del__ method
        has_del = hasattr(ESP300Controller, '__del__')
        print(f"ESP300Controller has __del__ method: {has_del}")
        assert not has_del, "ESP300Controller should not have __del__ method"

    except Exception as e:
        print(f"❌ ESP300Controller import failed: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Failed to import ESP300Controller: {e}")

    # Test 2: Try to import Newport1830CController
    try:
        print("Attempting to import Newport1830CController...")
        from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import Newport1830CController
        print("✅ Newport1830CController import successful")

        # Check for __del__ method
        has_del = hasattr(Newport1830CController, '__del__')
        print(f"Newport1830CController has __del__ method: {has_del}")
        assert not has_del, "Newport1830CController should not have __del__ method"

    except Exception as e:
        print(f"❌ Newport1830CController import failed: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Failed to import Newport1830CController: {e}")


@pytest.mark.timeout(5)
def test_safe_instantiation():
    """Test safe instantiation without any real initialization."""

    try:
        from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller
        from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import Newport1830CController

        print("Testing ESP300Controller instantiation...")
        # Just test class creation without calling any methods
        esp_class = ESP300Controller
        print(f"ESP300Controller class: {esp_class}")

        print("Testing Newport1830CController instantiation...")
        newport_class = Newport1830CController
        print(f"Newport1830CController class: {newport_class}")

        # Force garbage collection
        gc.collect()
        print("✅ Garbage collection completed")

    except Exception as e:
        print(f"❌ Safe instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Safe instantiation failed: {e}")


if __name__ == "__main__":
    """Standalone execution for debugging."""
    print("Debug Threading Safety Test")
    print("=" * 30)

    try:
        print("=" * 30)
        print("TEST 1: Basic Imports")
        print("=" * 30)
        test_basic_imports()

        print("\n" + "=" * 30)
        print("TEST 2: Safe Instantiation")
        print("=" * 30)
        test_safe_instantiation()

        print("\n🎉 All debug tests passed!")

    except Exception as e:
        print(f"\n❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
