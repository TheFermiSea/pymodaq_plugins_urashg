#!/usr/bin/env python3
"""
Ultra-minimal test for hardware controller threading safety.

This test verifies that the problematic __del__ methods have been removed
from ESP300Controller and Newport1830C_controller classes, which were
causing QThread crashes during PyMoDAQ dashboard shutdown.

The test is designed to be as minimal as possible to avoid any hanging
in CI environments.
"""

import pytest
import gc
import sys
from pathlib import Path

# Add project to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.timeout(10)
def test_controller_classes_have_no_del_methods():
    """Test that problematic __del__ methods have been removed."""

    # Test ESP300Controller
    try:
        from pymodaq_plugins_urashg.hardware.urashg.esp300_controller import ESP300Controller

        # Check that __del__ method is not defined
        assert not hasattr(ESP300Controller, '__del__'), "ESP300Controller still has __del__ method"

        # Create instance briefly to test basic instantiation
        try:
            controller = ESP300Controller(port="mock", axes_config=[])
            del controller
        except Exception:
            # Initialization errors are acceptable - we only care about __del__ safety
            pass
        gc.collect()

    except ImportError:
        pytest.skip("ESP300Controller not available")

    # Test Newport1830C_controller
    try:
        from pymodaq_plugins_urashg.hardware.urashg.newport1830c_controller import Newport1830CController

        # Check that __del__ method is not defined
        assert not hasattr(Newport1830CController, '__del__'), "Newport1830CController still has __del__ method"

        # Create instance briefly to test basic instantiation
        try:
            controller = Newport1830CController()
            del controller
        except Exception:
            # Initialization errors are acceptable - we only care about __del__ safety
            pass
        gc.collect()

    except ImportError:
        pytest.skip("Newport1830CController not available")


@pytest.mark.timeout(5)
def test_garbage_collection_safety():
    """Test that garbage collection completes without hanging."""

    # Force garbage collection - this should not hang
    initial_count = len(gc.get_objects())
    gc.collect()
    final_count = len(gc.get_objects())

    # Test passes if garbage collection completes
    assert final_count <= initial_count


if __name__ == "__main__":
    """Standalone execution for debugging."""
    print("Ultra-Minimal Threading Safety Test")
    print("=" * 40)

    try:
        print("Testing controller classes...")
        test_controller_classes_have_no_del_methods()
        print("✅ Controller classes test passed")

        print("Testing garbage collection...")
        test_garbage_collection_safety()
        print("✅ Garbage collection test passed")

        print("\n🎉 All tests passed!")
        print("✅ __del__ methods have been properly removed")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
