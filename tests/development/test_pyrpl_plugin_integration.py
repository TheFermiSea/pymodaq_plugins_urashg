#!/usr/bin/env python3
"""
Test PyRPL Plugin Integration for URASHG Project

This script validates that the external pymodaq_plugins_pyrpl package
is properly integrated and accessible within the URASHG workflow.

Usage:
    python test_pyrpl_plugin_integration.py
"""

import sys
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_pyrpl_plugin_import():
    """Test that PyRPL plugins can be imported correctly."""
    try:
        import pymodaq_plugins_pyrpl

        logger.info("✅ PyRPL plugin package imported successfully")

        # Test specific plugin import
        from pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID import (
            DAQ_Move_PyRPL_PID,
        )

        logger.info("✅ PyRPL PID plugin imported successfully")

    except ImportError as e:
        logger.error(f"❌ PyRPL plugin import failed: {e}")
        assert False, f"PyRPL plugin import failed: {e}"


def test_plugin_discovery():
    """Test that PyMoDAQ can discover the PyRPL plugins."""
    try:
        from pymodaq.utils.daq_utils import get_entrypoints

        # Get move plugins
        move_plugins = get_entrypoints("pymodaq.move_plugins")
        pyrpl_move_plugins = [
            name
            for name, ep in move_plugins.items()
            if "pyrpl" in ep.module_name.lower()
        ]

        if pyrpl_move_plugins:
            logger.info(f"✅ PyRPL move plugins discovered: {pyrpl_move_plugins}")
        else:
            logger.warning("⚠️  No PyRPL move plugins found in entry points")

        # Get viewer plugins
        viewer_plugins = get_entrypoints("pymodaq.viewer_plugins")
        pyrpl_viewer_plugins = [
            name
            for name, ep in viewer_plugins.items()
            if "pyrpl" in ep.module_name.lower()
        ]

        if pyrpl_viewer_plugins:
            logger.info(f"✅ PyRPL viewer plugins discovered: {pyrpl_viewer_plugins}")
        else:
            logger.info("ℹ️  No PyRPL viewer plugins found (this is expected)")

        assert len(pyrpl_move_plugins) > 0, "No PyRPL move plugins found in entry points"

    except Exception as e:
        logger.error(f"❌ Plugin discovery failed: {e}")
        assert False, f"Plugin discovery failed: {e}"


def test_pyrpl_library_import():
    """Test that the PyRPL library itself can be imported."""
    try:
        import pyrpl

        logger.info(
            f"✅ PyRPL library imported successfully (version: {getattr(pyrpl, '__version__', 'unknown')})"
        )

        # Test basic PyRPL functionality (without hardware)
        from pyrpl.curvedb import CurveDB

        logger.info("✅ PyRPL core functionality accessible")

    except ImportError as e:
        logger.error(f"❌ PyRPL library import failed: {e}")
        assert False, f"PyRPL library import failed: {e}"


def test_urashg_experiment_integration():
    """Test that URASHG experiments can reference PyRPL plugins."""
    try:
        from pymodaq_plugins_urashg.experiments.wavelength_dependent_rashg import (
            WavelengthDependentRASHGExperiment,
        )

        # Check that experiment references PyRPL_PID instead of URASHG_PyRPL_PID
        experiment = WavelengthDependentRASHGExperiment()
        required_modules = experiment.required_modules

        assert "PyRPL_PID" in required_modules, "URASHG experiment does not reference PyRPL_PID plugin"
        logger.info(
            "✅ URASHG experiment correctly references external PyRPL_PID plugin"
        )

        if "URASHG_PyRPL_PID" not in required_modules:
            logger.info(
                "✅ Internal URASHG_PyRPL_PID plugin correctly removed from requirements"
            )
        else:
            logger.warning(
                "⚠️  Internal URASHG_PyRPL_PID still referenced - potential conflict"
            )

    except Exception as e:
        logger.error(f"❌ URASHG experiment integration test failed: {e}")
        assert False, f"URASHG experiment integration test failed: {e}"


def main():
    """Run all PyRPL integration tests."""
    logger.info("🧪 Running PyRPL Plugin Integration Tests")
    logger.info("=" * 50)

    tests = [
        ("PyRPL Plugin Import", test_pyrpl_plugin_import),
        ("PyRPL Library Import", test_pyrpl_library_import),
        ("Plugin Discovery", test_plugin_discovery),
        ("URASHG Experiment Integration", test_urashg_experiment_integration),
    ]

    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Integration Test Results")
    logger.info("=" * 50)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! PyRPL integration is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
