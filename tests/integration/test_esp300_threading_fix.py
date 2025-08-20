#!/usr/bin/env python3
"""
Test ESP300 plugin initialization to verify threading crash fix.

This test simulates PyMoDAQ's plugin initialization process to verify that the
ESP300Controller __del__ method fix prevents QThread crashes.
"""

import logging
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300 import DAQ_Move_ESP300


def test_esp300_initialization():
    """Test ESP300 plugin initialization and cleanup without crashes."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Testing ESP300 plugin initialization...")

    try:
        # Create plugin instance
        plugin = DAQ_Move_ESP300()

        # Mock connection parameters for safe testing
        plugin.settings.child("connection_group", "mock_mode").setValue(True)
        plugin.settings.child("axes_config", "num_axes").setValue(3)

        logger.info("Initializing ESP300 plugin in mock mode...")

        # Initialize plugin (this is where the crash occurred)
        try:
            plugin.ini_stage_init()
            logger.info("✅ Plugin initialized successfully")

            # Test basic operations
            positions = plugin.get_actuator_value()
            logger.info(f"Current positions: {positions}")

            # Test move operation
            logger.info("Testing move operation...")
            plugin.move_abs([1.0, 2.0, 3.0])

            logger.info("✅ Move operation completed")

        except Exception as e:
            logger.error(f"❌ Plugin initialization failed: {e}")
            assert False, f"Plugin initialization failed: {e}"

        # Test cleanup (this is critical for thread safety)
        logger.info("Testing plugin cleanup...")
        plugin.close()
        logger.info("✅ Plugin closed successfully")

        # Force garbage collection to test __del__ behavior
        logger.info("Testing garbage collection behavior...")
        del plugin
        time.sleep(0.5)  # Allow GC to run
        logger.info("✅ Garbage collection completed without crash")

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        assert False, f"Test failed with exception: {e}"


def test_multiple_initializations():
    """Test multiple plugin initializations to stress-test threading."""
    logging.getLogger(__name__).info("Testing multiple plugin initializations...")

    for i in range(5):
        logging.getLogger(__name__).info(f"Initialization test {i+1}/5...")

        plugin = DAQ_Move_ESP300()
        plugin.settings.child("connection_group", "mock_mode").setValue(True)

        try:
            plugin.ini_stage_init()
        except Exception as e:
            logging.getLogger(__name__).error(f"❌ Failed on iteration {i+1}: {e}")
            assert False, f"Failed on iteration {i+1}: {e}"

        plugin.close()
        del plugin
        time.sleep(0.1)

    logging.getLogger(__name__).info("✅ Multiple initialization test passed")


if __name__ == "__main__":
    print("ESP300 Threading Fix Test")
    print("=" * 40)

    success = True

    # Test 1: Basic initialization
    print("\n1. Testing basic plugin initialization...")
    if not test_esp300_initialization():
        success = False

    # Test 2: Multiple initializations
    print("\n2. Testing multiple initializations...")
    if not test_multiple_initializations():
        success = False

    print("\n" + "=" * 40)
    if success:
        print("🎉 ALL TESTS PASSED - ESP300 threading fix verified!")
        print("The ESP300 plugin should now initialize without crashes.")
    else:
        print("❌ TESTS FAILED - Further investigation needed.")

    sys.exit(0 if success else 1)
