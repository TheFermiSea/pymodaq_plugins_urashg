#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify PyMoDAQ URASHG plugin installation and integration.

This script tests:
1. Package importability
2. Plugin discovery by PyMoDAQ
3. Individual plugin class imports
4. Extension discovery
5. Configuration system

Run this after installing the plugin package to verify everything is working.
"""

import sys
import traceback
from pathlib import Path

def test_package_import():
    """Test basic package import and version detection."""
    print("=" * 60)
    print("1. Testing Package Import")
    print("=" * 60)

    try:
        import pymodaq_plugins_urashg
        print(f"✓ Package imported successfully")
        print(f"✓ Version: {pymodaq_plugins_urashg.__version__}")

        # Test config
        config = pymodaq_plugins_urashg.config
        print(f"✓ Config object available: {type(config).__name__}")

        return True
    except Exception as e:
        print(f"✗ Package import failed: {e}")
        traceback.print_exc()
        return False

def test_plugin_discovery():
    """Test PyMoDAQ's plugin discovery system."""
    print("\n" + "=" * 60)
    print("2. Testing Plugin Discovery")
    print("=" * 60)

    try:
<<<<<<< HEAD
        # Import PyMoDAQ's plugin utilities - use v5.x API
        from pymodaq import get_instrument_plugins
        all_plugins = get_instrument_plugins()
        
        # Extract our URASHG plugins
        move_plugins = []
        viewer_plugins = []
        
        for plugin_info in all_plugins:
            if 'urashg' in plugin_info['parent_module'].__name__:
                if plugin_info['type'] == 'daq_move':
                    move_plugins.append(plugin_info['name'])
                elif plugin_info['type'] in ['daq_0Dviewer', 'daq_1Dviewer', 'daq_2Dviewer']:
                    viewer_plugins.append(plugin_info['name'])

        print(f"✓ Found {len(move_plugins)} URASHG move plugins:")
        for plugin in move_plugins:
            print(f"  - {plugin}")

        print(f"✓ Found {len(viewer_plugins)} URASHG viewer plugins:")
        for plugin in viewer_plugins:
=======
        # Import PyMoDAQ's plugin utilities
        from pymodaq.daq_utils import daq_utils

        # Get available plugins
        move_plugins = daq_utils.get_plugins('move')
        viewer_plugins = daq_utils.get_plugins('viewer')

        # Filter for URASHG plugins
        urashg_move = [p for p in move_plugins if 'urashg' in p.lower()]
        urashg_viewer = [p for p in viewer_plugins if 'urashg' in p.lower()]

        print(f"✓ Found {len(urashg_move)} URASHG move plugins:")
        for plugin in urashg_move:
            print(f"  - {plugin}")

        print(f"✓ Found {len(urashg_viewer)} URASHG viewer plugins:")
        for plugin in urashg_viewer:
>>>>>>> architecture_compliance_fix
            print(f"  - {plugin}")

        # Expected plugins
        expected_move = ['ESP300', 'Elliptec', 'MaiTai']
        expected_viewer = ['Newport1830C', 'PrimeBSI']

<<<<<<< HEAD
        missing_move = set(expected_move) - set(move_plugins)
        missing_viewer = set(expected_viewer) - set(viewer_plugins)
=======
        found_move = [p.split('/')[-1] for p in urashg_move]
        found_viewer = [p.split('/')[-1] for p in urashg_viewer]

        missing_move = set(expected_move) - set(found_move)
        missing_viewer = set(expected_viewer) - set(found_viewer)
>>>>>>> architecture_compliance_fix

        if missing_move:
            print(f"⚠ Missing move plugins: {missing_move}")
        if missing_viewer:
            print(f"⚠ Missing viewer plugins: {missing_viewer}")

        if not missing_move and not missing_viewer:
            print("✓ All expected plugins discovered!")

<<<<<<< HEAD
        return len(move_plugins) > 0 or len(viewer_plugins) > 0
=======
        return len(urashg_move) > 0 or len(urashg_viewer) > 0
>>>>>>> architecture_compliance_fix

    except Exception as e:
        print(f"✗ Plugin discovery failed: {e}")
        traceback.print_exc()
        return False

def test_plugin_imports():
    """Test individual plugin class imports."""
    print("\n" + "=" * 60)
    print("3. Testing Plugin Class Imports")
    print("=" * 60)

    plugins_to_test = [
        ('DAQ_Move_Elliptec', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_Elliptec'),
        ('DAQ_Move_MaiTai', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_MaiTai'),
        ('DAQ_Move_ESP300', 'pymodaq_plugins_urashg.daq_move_plugins.daq_move_ESP300'),
        ('DAQ_2DViewer_PrimeBSI', 'pymodaq_plugins_urashg.daq_viewer_plugins.plugins_2D.daq_2Dviewer_PrimeBSI'),
        ('DAQ_0DViewer_Newport1830C', 'pymodaq_plugins_urashg.daq_viewer_plugins.plugins_0D.daq_0Dviewer_Newport1830C'),
    ]

    success_count = 0
    for class_name, module_path in plugins_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            plugin_class = getattr(module, class_name)
            print(f"✓ {class_name} imported successfully")

            # Test if it has required PyMoDAQ plugin attributes
            if hasattr(plugin_class, 'params'):
                print(f"  - Has params definition")
            if hasattr(plugin_class, '_controller_units'):
                print(f"  - Has controller units: {plugin_class._controller_units}")

            success_count += 1
        except Exception as e:
            print(f"✗ {class_name} import failed: {e}")

    print(f"\n✓ Successfully imported {success_count}/{len(plugins_to_test)} plugins")
    return success_count == len(plugins_to_test)

def test_extension_discovery():
    """Test extension discovery."""
    print("\n" + "=" * 60)
    print("4. Testing Extension Discovery")
    print("=" * 60)

    try:
        import pkg_resources

        # Check for extensions
        extensions = list(pkg_resources.iter_entry_points('pymodaq.extensions'))
        urashg_extensions = [ep for ep in extensions if 'urashg' in ep.name.lower()]

        print(f"✓ Found {len(urashg_extensions)} URASHG extensions:")
        for ext in urashg_extensions:
            print(f"  - {ext.name}: {ext.module_name}")

        # Test extension import
        if urashg_extensions:
            ext = urashg_extensions[0]
            try:
                extension_class = ext.load()
                print(f"✓ Extension {ext.name} loaded successfully")
                return True
            except Exception as e:
                print(f"✗ Extension {ext.name} loading failed: {e}")
                return False
        else:
            print("⚠ No URASHG extensions found")
            return False

    except Exception as e:
        print(f"✗ Extension discovery failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration system."""
    print("\n" + "=" * 60)
    print("5. Testing Configuration System")
    print("=" * 60)

    try:
        from pymodaq_plugins_urashg.utils import Config

        config = Config()
        print(f"✓ Config object created: {type(config).__name__}")

        # Check config template path
        template_path = config.config_template_path
        print(f"✓ Config template path: {template_path}")

        if template_path.exists():
            print(f"✓ Config template file exists")
        else:
            print(f"⚠ Config template file not found: {template_path}")

        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_hardware_abstraction():
    """Test hardware abstraction layer."""
    print("\n" + "=" * 60)
    print("6. Testing Hardware Abstraction Layer")
    print("=" * 60)

    try:
        from pymodaq_plugins_urashg.hardware import urashg
        print("✓ Hardware abstraction layer imported")

        # Check if main hardware modules are available
        hardware_modules = ['camera_utils', 'elliptec_wrapper', 'maitai_control', 'newport1830c_controller']

        for module_name in hardware_modules:
            try:
                module = getattr(urashg, module_name, None)
                if module is not None:
                    print(f"  ✓ {module_name} available")
                else:
                    print(f"  ⚠ {module_name} not found")
            except Exception as e:
                print(f"  ✗ {module_name} error: {e}")

        return True

    except Exception as e:
        print(f"✗ Hardware abstraction test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests and provide summary."""
    print("PyMoDAQ URASHG Plugin Integration Test")
    print("=" * 60)

    tests = [
        ("Package Import", test_package_import),
        ("Plugin Discovery", test_plugin_discovery),
        ("Plugin Imports", test_plugin_imports),
        ("Extension Discovery", test_extension_discovery),
        ("Configuration", test_configuration),
        ("Hardware Abstraction", test_hardware_abstraction),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:25} {status}")

    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Plugin installation is successful.")
        print("\nYou can now:")
        print("  1. Launch PyMoDAQ dashboard")
        print("  2. Create move/viewer modules using URASHG plugins")
        print("  3. Use the URASHG microscopy extension")
        return 0
    else:
        print(f"\n⚠ {total - passed} tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
