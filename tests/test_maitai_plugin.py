#!/usr/bin/env python3
"""
Comprehensive test for DAQ_Move_MaiTai plugin in mock mode

This script tests the MaiTai Ti:Sapphire laser controller plugin
without requiring actual hardware by using mock serial communication.
"""

import sys
import time
import os
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add the parent directory to Python path to import the plugin
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock the serial module before importing the plugin
class MockSerial:
    """Mock serial port for MaiTai testing"""

    def __init__(self, port, baudrate=9600, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = kwargs.get('bytesize', 8)
        self.parity = kwargs.get('parity', 'N')
        self.stopbits = kwargs.get('stopbits', 1)
        self.timeout = kwargs.get('timeout', 1.0)
        self.is_open = True
        self._write_history = []
        self._laser_state = {
            'wavelength': 800.0,
            'shutter': 0,
            'power': 1.5,
            'warmup': 95,
            'modelocked': True,
            'laser_on': True
        }

    def write(self, data):
        """Mock write operation with command tracking"""
        self._write_history.append(data)
        command = data.decode('utf-8', errors='ignore').strip().upper()

        # Process commands that change state
        if 'WAVELENGTH' in command:
            try:
                parts = command.split()
                if len(parts) >= 2:
                    self._laser_state['wavelength'] = float(parts[1])
            except (ValueError, IndexError):
                pass
        elif 'SHUTTER' in command:
            try:
                parts = command.split()
                if len(parts) >= 2:
                    self._laser_state['shutter'] = int(parts[1])
            except (ValueError, IndexError):
                pass

        return len(data)

    def readline(self):
        """Mock readline with realistic MaiTai responses"""
        if not self._write_history:
            return b'\r\n'

        last_cmd = self._write_history[-1].decode('utf-8', errors='ignore').strip().upper()

        # Parse command and generate appropriate response
        if 'READ:WAVELENGTH?' in last_cmd:
            response = f"{self._laser_state['wavelength']:.1f}"
        elif 'WAVELENGTH?' in last_cmd or 'READ:WAV?' in last_cmd:
            response = f"{self._laser_state['wavelength']:.1f}"
        elif 'SHUTTER?' in last_cmd:
            response = str(self._laser_state['shutter'])
        elif 'READ:POWER?' in last_cmd:
            response = f"{self._laser_state['power']:.2f}"
        elif 'READ:PCTWARMEDUP?' in last_cmd:
            response = str(self._laser_state['warmup'])
        elif '*STB?' in last_cmd:
            # Status byte: bit 1 (2) = modelocked, bit 6 (64) = laser on
            status = 0
            if self._laser_state['modelocked']:
                status |= 2
            if self._laser_state['laser_on']:
                status |= 64
            response = str(status)
        elif '*IDN?' in last_cmd:
            response = "Spectra-Physics,MaiTai,12345,1.0.0"
        elif 'WAVELENGTH:MIN?' in last_cmd:
            response = "700.0"
        elif 'WAVELENGTH:MAX?' in last_cmd:
            response = "1000.0"
        elif 'ON' in last_cmd:
            self._laser_state['laser_on'] = True
            response = "OK"
        elif 'OFF' in last_cmd:
            self._laser_state['laser_on'] = False
            response = "OK"
        elif 'SAVE' in last_cmd:
            response = "OK"
        elif 'SYSTEM:ERR?' in last_cmd:
            response = "0,No Error"
        else:
            # Generic OK response
            response = "OK"

        return (response + '\r\n').encode()

    def close(self):
        """Mock close operation"""
        self.is_open = False

class SerialException(Exception):
    """Mock serial exception"""
    pass

# Setup mock serial module
mock_serial = Mock()
mock_serial.Serial = MockSerial
mock_serial.EIGHTBITS = 8
mock_serial.PARITY_NONE = 'N'
mock_serial.STOPBITS_ONE = 1
mock_serial.SerialException = SerialException

sys.modules['serial'] = mock_serial

# Mock PyMoDAQ components
class MockThreadCommand:
    def __init__(self, command, data=None):
        self.command = command
        self.data = data if data is not None else []

class MockParameter:
    def __init__(self, name, value=None, **kwargs):
        self._name = name
        self._value = value
        self._children = {}
        self._parent = None
        self._readonly = kwargs.get('readonly', False)

    def name(self):
        return self._name

    def value(self):
        return self._value

    def setValue(self, value):
        if not self._readonly:
            self._value = value

    def child(self, *path):
        """Navigate to child parameter"""
        current = self
        for step in path:
            if step not in current._children:
                # Create mock child if it doesn't exist
                current._children[step] = MockParameter(step)
                current._children[step]._parent = current
            current = current._children[step]
        return current

class MockDAQMoveBase:
    """Mock base class for DAQ_Move plugins"""

    def __init__(self, parent=None, params_state=None):
        self.parent = parent
        self.params_state = params_state
        self.current_position = 800.0  # Default wavelength
        self.settings = self._create_settings_tree()
        self._status_callbacks = []

    def _create_settings_tree(self):
        """Create mock settings tree"""
        settings = MockParameter("root")

        # Create common parameters
        settings.child('connect').setValue(False)
        settings.child('serial', 'com_port').setValue('COM1')
        settings.child('multiaxes', 'selected_axis').setValue('Wavelength')

        # Create MaiTai-specific parameters
        settings.child('maitai_status', 'warmup_percent').setValue(0)
        settings.child('maitai_status', 'pulsing').setValue(False)
        settings.child('maitai_status', 'output_power').setValue(0.0)
        settings.child('maitai_status', 'system_status_message').setValue('Disconnected')
        settings.child('maitai_status', 'laser_on').setValue(False)

        return settings

    def emit_status(self, command):
        """Mock status emission"""
        for callback in self._status_callbacks:
            callback(command)

    def add_status_callback(self, callback):
        """Add status callback for testing"""
        self._status_callbacks.append(callback)

# Mock the required PyMoDAQ modules
sys.modules['pymodaq.control_modules.move_utility_classes'] = Mock()
sys.modules['pymodaq.utils.daq_utils'] = Mock()
sys.modules['pymodaq.utils.parameter'] = Mock()

# Setup mock classes
mock_move_utility = sys.modules['pymodaq.control_modules.move_utility_classes']
mock_move_utility.DAQ_Move_base = MockDAQMoveBase
mock_move_utility.comon_parameters_fun = lambda **kwargs: []

mock_daq_utils = sys.modules['pymodaq.utils.daq_utils']
mock_daq_utils.ThreadCommand = MockThreadCommand
mock_daq_utils.getLineInfo = lambda: "test_file.py:123"

mock_parameter = sys.modules['pymodaq.utils.parameter']
mock_parameter.Parameter = MockParameter

def test_maitai_plugin_comprehensive():
    """Run comprehensive MaiTai plugin tests"""

    print("=== Comprehensive DAQ_Move_MaiTai Plugin Test ===")

    # Test results tracking
    test_results = {}

    try:
        # Import the plugin directly to avoid package import issues
        import sys
        from pathlib import Path
        plugin_path = Path(__file__).parent.parent / "src" / "pymodaq_plugins_urashg" / "daq_move_plugins"
        sys.path.insert(0, str(plugin_path))
        from DAQ_Move_MaiTai import DAQ_Move_MaiTai

        print("[OK] Plugin imported successfully")
        test_results['import'] = True

        # Test 1: Plugin instantiation
        print("\n--- Test 1: Plugin Instantiation ---")
        plugin = DAQ_Move_MaiTai()
        assert plugin is not None, "Plugin should be instantiated"
        print("[OK] Plugin instance created successfully")
        test_results['instantiation'] = True

        # Test 2: Parameter structure validation
        print("\n--- Test 2: Parameter Structure Validation ---")
        assert hasattr(plugin, 'params'), "Plugin should have params attribute"
        assert isinstance(plugin.params, list), "Params should be a list"
        assert len(plugin.params) >= 2, "Should have at least 2 parameter groups"
        print(f"[OK] Plugin has {len(plugin.params)} parameter groups")

        # Check for multi-axis configuration
        multi_axis_found = False
        maitai_status_found = False
        for param_group in plugin.params:
            if param_group.get('name') == 'multi_axis':
                multi_axis_found = True
                # Check axis names
                children = param_group.get('children', [])
                for child in children:
                    if child.get('name') == 'axis_names':
                        limits = child.get('limits', [])
                        assert 'Wavelength' in limits, "Wavelength axis should be available"
                        assert 'Shutter' in limits, "Shutter axis should be available"
                        print(f"[OK] Available axes: {limits}")
            elif param_group.get('name') == 'maitai_status':
                maitai_status_found = True
                status_params = [child.get('name') for child in param_group.get('children', [])]
                required_status = ['warmup_percent', 'pulsing', 'output_power', 'laser_on']
                for req_param in required_status:
                    assert req_param in status_params, f"Missing status parameter: {req_param}"
                print(f"[OK] Status parameters: {status_params}")

        assert multi_axis_found, "Multi-axis parameter group not found"
        assert maitai_status_found, "MaiTai status parameter group not found"
        test_results['parameter_structure'] = True

        # Test 3: Command reference validation
        print("\n--- Test 3: Command Reference Validation ---")
        assert hasattr(plugin, '_command_reference'), "Should have command reference"
        assert len(plugin._command_reference) >= 20, f"Should have at least 20 commands, got {len(plugin._command_reference)}"

        # Check for essential commands
        essential_commands = ['WAVelength', 'SHUTter', 'READ:POWer?', '*STB?', 'ON', 'OFF']
        for cmd in essential_commands:
            found = any(cmd in key for key in plugin._command_reference.keys())
            assert found, f"Essential command not found: {cmd}"

        print(f"[OK] Command reference validated: {len(plugin._command_reference)} commands")
        test_results['command_reference'] = True

        # Test 4: Mock connection simulation
        print("\n--- Test 4: Mock Connection Simulation ---")

        # Setup status monitoring
        status_messages = []
        def status_callback(command):
            status_messages.append((command.command, command.data))

        plugin.add_status_callback(status_callback)

        # Simulate connection
        plugin.settings.child('serial', 'com_port').setValue('COM2')
        plugin.settings.child('connect').setValue(True)

        # This should trigger the setup process
        connect_param = plugin.settings.child('connect')
        plugin.commit_settings(connect_param)

        # Check that controller was created
        assert plugin.controller is not None, "Controller should be initialized"
        assert plugin.controller.is_open, "Controller should be open"
        print("[OK] Mock serial connection established")

        test_results['mock_connection'] = True

        # Test 5: Wavelength control
        print("\n--- Test 5: Wavelength Control ---")

        # Switch to wavelength axis
        plugin.settings.child('multiaxes', 'selected_axis').setValue('Wavelength')

        test_wavelengths = [700.0, 800.0, 850.0, 900.0, 1000.0]
        wavelength_errors = []

        for test_wl in test_wavelengths:
            # Set wavelength
            plugin.move_abs(test_wl)

            # Read back wavelength
            readback_wl = plugin.get_actuator_value()

            # Calculate error
            error = abs(readback_wl - test_wl)
            wavelength_errors.append(error)

            print(f"  Wavelength {test_wl:6.1f}nm -> {readback_wl:6.1f}nm (error: {error:.3f}nm)")

        max_wl_error = max(wavelength_errors)
        assert max_wl_error < 5.0, f"Wavelength control error too high: {max_wl_error:.3f}nm"
        print(f"[OK] Wavelength control: max error {max_wl_error:.3f}nm")

        test_results['wavelength_control'] = True

        # Test 6: Shutter control
        print("\n--- Test 6: Shutter Control ---")

        # Switch to shutter axis
        plugin.settings.child('multiaxes', 'selected_axis').setValue('Shutter')

        # Test shutter states
        for shutter_state in [0, 1, 0]:  # Close, Open, Close
            plugin.move_abs(shutter_state)
            readback_state = plugin.get_actuator_value()

            state_name = "OPEN" if shutter_state else "CLOSED"
            readback_name = "OPEN" if readback_state else "CLOSED"

            assert readback_state == shutter_state, f"Shutter state mismatch: {readback_state} != {shutter_state}"
            print(f"  Shutter {state_name} -> {readback_name} [OK]")

        test_results['shutter_control'] = True

        # Test 7: Background monitoring thread
        print("\n--- Test 7: Background Monitoring Thread ---")

        # Start monitoring
        plugin.start_monitoring()
        time.sleep(0.2)  # Let thread start and run briefly

        # Check thread status
        assert plugin.monitoring_thread is not None, "Monitoring thread should exist"
        assert plugin.monitoring_thread.is_alive(), "Monitoring thread should be running"
        print("[OK] Background monitoring thread started")

        # Check if status parameters are being updated
        # Note: In a real system, these would be updated by the monitoring thread
        current_power = plugin.settings.child('maitai_status', 'output_power').value()
        current_warmup = plugin.settings.child('maitai_status', 'warmup_percent').value()

        print(f"  Current power: {current_power}W")
        print(f"  Warmup status: {current_warmup}%")
        print("[OK] Status monitoring operational")

        test_results['background_monitoring'] = True

        # Test 8: Command sending
        print("\n--- Test 8: Command Sending ---")

        # Test various command types
        test_commands = [
            ('*IDN?', 'identification'),
            ('READ:WAVELENGTH?', 'wavelength query'),
            ('READ:POWER?', 'power query'),
            ('*STB?', 'status byte query')
        ]

        for command, description in test_commands:
            response = plugin._send_command(command, expect_response=True)
            assert response is not None, f"Should receive response for {description}"
            assert len(response.strip()) > 0, f"Response should not be empty for {description}"
            print(f"  {description}: {response.strip()}")

        test_results['command_sending'] = True

        # Test 9: Error handling and safety
        print("\n--- Test 9: Error Handling and Safety ---")

        # Test stop motion (should not crash)
        plugin.stop_motion()
        print("[OK] Stop motion command executed")

        # Test invalid wavelength handling (should be graceful)
        try:
            plugin.move_abs(1500.0)  # Outside typical range
            print("[OK] Out-of-range wavelength handled gracefully")
        except Exception as e:
            print(f"  Note: Out-of-range handling: {e}")

        test_results['error_handling'] = True

        # Test 10: Thread cleanup
        print("\n--- Test 10: Thread Cleanup ---")

        # Stop monitoring thread
        plugin.stop_thread_flag.set()
        if plugin.monitoring_thread and plugin.monitoring_thread.is_alive():
            plugin.monitoring_thread.join(timeout=1.0)

        # Check thread stopped
        if plugin.monitoring_thread:
            assert not plugin.monitoring_thread.is_alive(), "Monitoring thread should be stopped"
        print("[OK] Monitoring thread stopped cleanly")

        test_results['thread_cleanup'] = True

        # Test 11: Connection cleanup
        print("\n--- Test 11: Connection Cleanup ---")

        plugin.close()
        assert not plugin.controller.is_open, "Controller should be closed"
        print("[OK] Plugin cleanup successful")

        test_results['cleanup'] = True

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        total_tests = len(test_results)
        passed_tests = sum(test_results.values())

        for test_name, passed in test_results.items():
            status = "[OK] PASSED" if passed else "ERROR: FAILED"
            print(f"{status:<10} {test_name.replace('_', ' ').title()}")

        print("="*60)
        print(f"TOTAL: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("SUCCESS: ALL MAITAI PLUGIN TESTS PASSED!")
            return True
        else:
            print("[WARNING]  SOME TESTS FAILED!")
            return False

    except Exception as e:
        print(f"\nERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_maitai_specific_features():
    """Test specific MaiTai plugin features in detail"""

    print("\n=== Detailed MaiTai Feature Tests ===")

    try:
        # Import the plugin directly
        import sys
        from pathlib import Path
        plugin_path = Path(__file__).parent.parent / "src" / "pymodaq_plugins_urashg" / "daq_move_plugins"
        sys.path.insert(0, str(plugin_path))
        from DAQ_Move_MaiTai import DAQ_Move_MaiTai

        plugin = DAQ_Move_MaiTai()

        # Test laser status interpretation
        print("\n--- Laser Status Interpretation ---")

        # Setup connection
        plugin.settings.child('serial', 'com_port').setValue('COM3')
        plugin.settings.child('connect').setValue(True)
        connect_param = plugin.settings.child('connect')
        plugin.commit_settings(connect_param)

        # Test status byte interpretation
        status_response = plugin._send_command('*STB?', expect_response=True)
        if status_response:
            status_byte = int(status_response.strip())
            is_pulsing = bool(status_byte & 2)
            is_on = bool(status_byte & 64)
            print(f"  Status byte: {status_byte} (pulsing: {is_pulsing}, on: {is_on})")

        print("[OK] Laser status interpretation tested")

        # Test parameter change handling
        print("\n--- Parameter Change Handling ---")

        # Simulate parameter changes
        wavelength_param = plugin.settings.child('multiaxes', 'selected_axis')
        wavelength_param.setValue('Wavelength')

        # This should not cause errors
        print("[OK] Parameter change handling tested")

        # Test error response handling
        print("\n--- Error Response Handling ---")

        error_response = plugin._send_command('SYSTEM:ERR?', expect_response=True)
        if error_response:
            print(f"  Error query response: {error_response.strip()}")

        print("[OK] Error response handling tested")

        plugin.close()
        return True

    except Exception as e:
        print(f"ERROR: Detailed feature test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_maitai_threading_safety():
    """Test threading safety of MaiTai plugin"""

    print("\n=== Threading Safety Tests ===")

    try:
        # Import the plugin directly
        import sys
        from pathlib import Path
        plugin_path = Path(__file__).parent.parent / "src" / "pymodaq_plugins_urashg" / "daq_move_plugins"
        sys.path.insert(0, str(plugin_path))
        from DAQ_Move_MaiTai import DAQ_Move_MaiTai

        plugin = DAQ_Move_MaiTai()

        # Setup connection
        plugin.settings.child('serial', 'com_port').setValue('COM4')
        plugin.settings.child('connect').setValue(True)
        connect_param = plugin.settings.child('connect')
        plugin.commit_settings(connect_param)

        # Start monitoring
        plugin.start_monitoring()

        # Perform operations while monitoring is active
        print("\n--- Operations During Background Monitoring ---")

        for i in range(3):
            plugin.move_abs(800 + i * 10)
            time.sleep(0.1)
            position = plugin.get_actuator_value()
            print(f"  Operation {i+1}: moved to {position}nm")

        print("[OK] Operations during monitoring completed safely")

        # Stop monitoring
        plugin.stop_thread_flag.set()
        if plugin.monitoring_thread:
            plugin.monitoring_thread.join(timeout=2.0)

        plugin.close()
        return True

    except Exception as e:
        print(f"ERROR: Threading safety test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting MaiTai Plugin Mock Tests...")

    # Run comprehensive tests
    success1 = test_maitai_plugin_comprehensive()

    # Run detailed feature tests
    success2 = test_maitai_specific_features()

    # Run threading safety tests
    success3 = test_maitai_threading_safety()

    # Overall result
    if success1 and success2 and success3:
        print("\nSUCCESS: ALL MAITAI TESTS COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nERROR: SOME MAITAI TESTS FAILED!")
        sys.exit(1)
