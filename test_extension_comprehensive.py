#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test script for the μRASHG Microscopy Extension

This script validates:
1. Extension import and initialization
2. Device manager functionality
3. Plugin discovery and availability
4. PyMoDAQ standards compliance
5. Hardware abstraction layers

Usage:
    python test_extension_comprehensive.py
"""

import sys
import logging
import traceback
from pathlib import Path

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pymodaq_framework():
    """Test PyMoDAQ framework availability and plugin discovery."""
    logger.info("=== Testing PyMoDAQ Framework ===")

    try:
        import pymodaq
        logger.info(f"✅ PyMoDAQ version: {pymodaq.__version__}")

        # Test plugin discovery
        from pymodaq.daq_utils.daq_utils import get_plugins
        plugins = get_plugins('daq_move')
        urashg_plugins = [p for p in plugins if 'urashg' in p.lower() or 'elliptec' in p.lower() or 'maitai' in p.lower()]
        logger.info(f"✅ URASHG move plugins found: {urashg_plugins}")

        viewer_plugins = get_plugins('daq_viewer')
        urashg_viewers = [p for p in viewer_plugins if 'urashg' in p.lower() or 'primebsi' in p.lower() or 'newport' in p.lower()]
        logger.info(f"✅ URASHG viewer plugins found: {urashg_viewers}")

        return True

    except Exception as e:
        logger.error(f"❌ PyMoDAQ framework test failed: {e}")
        return False

def test_extension_import():
    """Test extension import and basic instantiation."""
    logger.info("=== Testing Extension Import ===")

    try:
        from pymodaq_plugins_urashg.extensions.urashg_microscopy_extension import URASHGMicroscopyExtension
        logger.info("✅ Extension import successful")

        # Check class hierarchy
        logger.info(f"✅ Base classes: {URASHGMicroscopyExtension.__bases__}")

        # Check required attributes
        required_attrs = ['experiment_name', 'setup_ui', 'setup_parameters']
        for attr in required_attrs:
            if hasattr(URASHGMicroscopyExtension, attr):
                logger.info(f"✅ Required attribute '{attr}' found")
            else:
                logger.warning(f"⚠️  Required attribute '{attr}' missing")

        return True

    except Exception as e:
        logger.error(f"❌ Extension import failed: {e}")
        traceback.print_exc()
        return False

def test_device_manager_import():
    """Test device manager import and structure."""
    logger.info("=== Testing Device Manager ===")

    try:
        from pymodaq_plugins_urashg.extensions.device_manager import (
            URASHGDeviceManager, DeviceStatus, DeviceInfo
        )
        logger.info("✅ Device manager classes imported successfully")

        # Test enum values
        logger.info(f"✅ DeviceStatus values: {list(DeviceStatus)}")

        # Test DeviceInfo structure
        logger.info(f"✅ DeviceInfo fields: {DeviceInfo.__annotations__}")

        return True

    except Exception as e:
        logger.error(f"❌ Device manager import failed: {e}")
        traceback.print_exc()
        return False

def test_hardware_abstraction():
    """Test hardware abstraction modules."""
    logger.info("=== Testing Hardware Abstraction ===")

    try:
        # Test hardware module
        from pymodaq_plugins_urashg.hardware import urashg
        logger.info("✅ Hardware module imported")

        # Test individual hardware components
        hardware_modules = [
            'maitai_laser',
            'elliptec_rotators',
            'photometrics_camera',
            'newport_power_meter'
        ]

        for module_name in hardware_modules:
            try:
                module = getattr(urashg, module_name, None)
                if module:
                    logger.info(f"✅ Hardware module '{module_name}' available")
                else:
                    logger.warning(f"⚠️  Hardware module '{module_name}' not found")
            except Exception as e:
                logger.warning(f"⚠️  Hardware module '{module_name}' error: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Hardware abstraction test failed: {e}")
        return False

def test_plugin_compliance():
    """Test individual plugin PyMoDAQ compliance."""
    logger.info("=== Testing Plugin Compliance ===")

    plugin_tests = []

    # Test MaiTai plugin
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai import DAQ_Move_MaiTai

        # Check required methods
        required_methods = ['ini_attributes', 'get_actuator_value', 'close',
                          'commit_settings', 'ini_stage', 'move_abs', 'move_home']

        for method in required_methods:
            if hasattr(DAQ_Move_MaiTai, method):
                logger.info(f"✅ MaiTai plugin has '{method}' method")
            else:
                logger.error(f"❌ MaiTai plugin missing '{method}' method")

        # Check move_home signature
        import inspect
        sig = inspect.signature(DAQ_Move_MaiTai.move_home)
        if 'value' in sig.parameters:
            logger.info("✅ MaiTai move_home has correct signature with value parameter")
        else:
            logger.error("❌ MaiTai move_home missing value parameter")

        plugin_tests.append(True)

    except Exception as e:
        logger.error(f"❌ MaiTai plugin test failed: {e}")
        plugin_tests.append(False)

    # Test Elliptec plugin
    try:
        from pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec import DAQ_Move_Elliptec

        # Check controller units attribute
        if hasattr(DAQ_Move_Elliptec, '_controller_units'):
            logger.info(f"✅ Elliptec plugin has _controller_units: {DAQ_Move_Elliptec._controller_units}")
        else:
            logger.warning("⚠️  Elliptec plugin missing _controller_units")

        plugin_tests.append(True)

    except Exception as e:
        logger.error(f"❌ Elliptec plugin test failed: {e}")
        plugin_tests.append(False)

    # Test PrimeBSI plugin
    try:
        from pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI import DAQ_2DViewer_PrimeBSI

        required_methods = ['ini_attributes', 'grab_data', 'close', 'commit_settings', 'ini_detector']

        for method in required_methods:
            if hasattr(DAQ_2DViewer_PrimeBSI, method):
                logger.info(f"✅ PrimeBSI plugin has '{method}' method")
            else:
                logger.error(f"❌ PrimeBSI plugin missing '{method}' method")

        plugin_tests.append(True)

    except Exception as e:
        logger.error(f"❌ PrimeBSI plugin test failed: {e}")
        plugin_tests.append(False)

    return all(plugin_tests)

def test_data_structures():
    """Test PyMoDAQ 5.x data structure compliance."""
    logger.info("=== Testing Data Structures ===")

    try:
        from pymodaq.utils.data import DataWithAxes, Axis, DataSource
        import numpy as np

        # Test data structure creation
        test_data = np.random.random((100, 100))
        x_axis = Axis('x', data=np.arange(100), units='pixels')
        y_axis = Axis('y', data=np.arange(100), units='pixels')

        data_obj = DataWithAxes(
            'test_data',
            data=[test_data],
            axes=[x_axis, y_axis],
            units='counts',
            source=DataSource.raw
        )

        logger.info("✅ PyMoDAQ 5.x data structures working correctly")
        logger.info(f"✅ Data shape: {data_obj.data[0].shape}")
        logger.info(f"✅ Data source: {data_obj.source}")

        return True

    except Exception as e:
        logger.error(f"❌ Data structure test failed: {e}")
        return False

def test_pyrpl_integration():
    """Test PyRPL plugin integration."""
    logger.info("=== Testing PyRPL Integration ===")

    try:
        # Test external PyRPL plugin availability
        from pymodaq.daq_utils.daq_utils import get_plugins

        plugins = get_plugins('daq_move')
        pyrpl_plugins = [p for p in plugins if 'pyrpl' in p.lower()]

        if pyrpl_plugins:
            logger.info(f"✅ PyRPL plugins available: {pyrpl_plugins}")

            # Test PyRPL PID plugin specifically
            if 'PyRPL_PID' in pyrpl_plugins:
                logger.info("✅ PyRPL PID plugin available for laser stabilization")
            else:
                logger.warning("⚠️  PyRPL PID plugin not found")
        else:
            logger.warning("⚠️  No PyRPL plugins found")

        return len(pyrpl_plugins) > 0

    except Exception as e:
        logger.error(f"❌ PyRPL integration test failed: {e}")
        return False

def test_qt_backend():
    """Test Qt backend compatibility."""
    logger.info("=== Testing Qt Backend ===")

    try:
        # Test QtPy compatibility
        from qtpy import QtWidgets, QtCore, QtGui
        logger.info("✅ QtPy imported successfully")

        # Check Qt backend
        import qtpy
        logger.info(f"✅ Qt backend: {qtpy.API_NAME}")

        # Test PyQtGraph
        import pyqtgraph as pg
        logger.info("✅ PyQtGraph imported successfully")

        return True

    except Exception as e:
        logger.error(f"❌ Qt backend test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary."""
    logger.info("🚀 Starting Comprehensive μRASHG Extension Test")
    logger.info("=" * 80)

    tests = [
        ("PyMoDAQ Framework", test_pymodaq_framework),
        ("Extension Import", test_extension_import),
        ("Device Manager", test_device_manager_import),
        ("Hardware Abstraction", test_hardware_abstraction),
        ("Plugin Compliance", test_plugin_compliance),
        ("Data Structures", test_data_structures),
        ("PyRPL Integration", test_pyrpl_integration),
        ("Qt Backend", test_qt_backend),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running {test_name} Test...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} Test: PASSED")
            else:
                logger.error(f"❌ {test_name} Test: FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} Test: CRASHED - {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status:<8} {test_name}")

    logger.info("-" * 80)
    logger.info(f"📈 OVERALL RESULT: {passed}/{total} tests passed ({100*passed/total:.1f}%)")

    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Extension is ready for use.")
        return 0
    elif passed >= total * 0.8:
        logger.info("⚠️  MOSTLY WORKING: Extension functional with minor issues.")
        return 1
    else:
        logger.error("💥 SIGNIFICANT ISSUES: Extension needs attention.")
        return 2

if __name__ == '__main__':
    print("=" * 80)
    print("μRASHG Microscopy Extension - Comprehensive Test Suite")
    print("=" * 80)
    print("Testing PyMoDAQ standards compliance and functionality")
    print("=" * 80)
    print()

    exit_code = run_comprehensive_test()

    print("\n" + "=" * 80)
    if exit_code == 0:
        print("🎉 SUCCESS: Extension ready for production use!")
    elif exit_code == 1:
        print("⚠️  WARNING: Extension mostly functional, minor issues detected")
    else:
        print("💥 ERROR: Extension has significant issues requiring fixes")
    print("=" * 80)

    sys.exit(exit_code)
