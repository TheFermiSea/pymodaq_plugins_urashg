#!/usr/bin/env python3
"""
Comprehensive test for DAQ_Move_Elliptec plugin in mock mode

This script tests the Thorlabs Elliptec rotation mount controller plugin
without requiring actual hardware by using mock serial communication.
"""

import sys
import time
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import threading

# Add the parent directory to Python path to import the plugin
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock the serial module before importing the plugin
class MockSerial:
    """Mock serial port for Elliptec testing"""

    def __init__(self, port, baudrate=9600, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = kwargs.get('bytesize', 8)
        self.parity = kwargs.get('parity', 'N')
        self.stopbits = kwargs.get('stopbits', 1)
        self.timeout = kwargs.get('timeout', 1.0)
        self.is_open = True
        self._write_history = []
        self._position_state = {}  # Track position for each address

    def write(self, data):
        """Mock write operation with command tracking"""
        self._write_history.append(data)
        return len(data)

    def readline(self):
        """Mock readline with realistic Elliptec responses"""
        if not self._write_history:
            return b'\r\n'

        last_cmd = self._write_history[-1].decode('utf-8', errors='ignore').strip()

        # Extract address and command
        if len(last_cmd) < 3:
            return b'\r\n'

        address = last_cmd[0]
        command = last_cmd[1:3].lower()
        data_part = last_cmd[3:] if len(last_cmd) > 3 else ""

        # Initialize position state for address if needed
        if address not in self._position_state:
            self._position_state[address] = 0

        # Generate appropriate responses
        if command == 'in':
            # Device information response
            # Format: <addr>IN<type><sn><year><fw><hw><travel><pulses>
            response = f"{address}IN0F14290000602019050105016800000004000"
            return response.encode() + b'\r\n'

        elif command == 'gp':
            # Get position response
            # Format: <addr>PO<8-digit hex position>
            position = self._position_state[address]
            hex_pos = f"{position & 0xFFFFFFFF:08X}"
            response = f"{address}PO{hex_pos}"
            return response.encode() + b'\r\n'

        elif command == 'gs':
            # Get status response
            # Format: <addr>GS<2-digit status code>
            response = f"{address}GS00"  # 00 = OK
            return response.encode() + b'\r\n'

        elif command == 'ma':
            # Move absolute - extract and store position
            if data_part:
                try:
                    new_position = int(data_part, 16)
                    self._position_state[address] = new_position
                except ValueError:
                    pass
            response = f"{address}MA"
            return response.encode() + b'\r\n'

        elif command == 'ho':
            # Home command - reset position to 0
            self._position_state[address] = 0
            direction = data_part if data_part else "1"
            response = f"{address}HO{direction}"
            return response.encode() + b'\r\n'

        elif command == 'st':
            # Stop command
            response = f"{address}ST"
            return response.encode() + b'\r\n'

        elif command == 'om':
            # Optimize motor - long operation simulation
            time.sleep(0.01)  # Simulate brief optimization
            response = f"{address}OM"
            return response.encode() + b'\r\n'

        else:
            # Generic acknowledgment
            response = f"{address}{command.upper()}"
            return response.encode() + b'\r\n'

    def reset_input_buffer(self):
        """Mock buffer reset"""
        pass

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

    def name(self):
        return self._name

    def value(self):
        return self._value

    def setValue(self, value):
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
        self.current_position = 0.0
        self.settings = self._create_settings_tree()
        self._status_callbacks = []

    def _create_settings_tree(self):
        """Create mock settings tree"""
        settings = MockParameter("root")

        # Create common parameters
        settings.child('connect').setValue(False)
        settings.child('serial', 'com_port').setValue('COM1')
        settings.child('multiaxes', 'selected_axis').setValue('HWP_inc')

        # Create Elliptec-specific parameters
        settings.child('elliptec_settings', 'home_on_connect').setValue(True)
        settings.child('elliptec_settings', 'addresses', 'address_HWP_inc').setValue('2')
        settings.child('elliptec_settings', 'addresses', 'address_QWP').setValue('3')
        settings.child('elliptec_settings', 'addresses', 'address_HWP_ana').setValue('8')

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
mock_parameter.pymodaq_ptypes = Mock()

def test_elliptec_plugin_comprehensive():
    """Run comprehensive Elliptec plugin tests"""

    print("=== Comprehensive DAQ_Move_Elliptec Plugin Test ===")

    # Test results tracking
    test_results = {}

    try:
        # Import the plugin directly to avoid package import issues
        import sys
        from pathlib import Path
        plugin_path = Path(__file__).parent.parent / "src" / "pymodaq_plugins_urashg" / "daq_move_plugins"
        sys.path.insert(0, str(plugin_path))
        from DAQ_Move_Elliptec import DAQ_Move_Elliptec

        print("[OK] Plugin imported successfully")
        test_results['import'] = True

        # Test 1: Plugin instantiation
        print("\n--- Test 1: Plugin Instantiation ---")
        plugin = DAQ_Move_Elliptec()
        assert plugin is not None, "Plugin should be instantiated"
        print("[OK] Plugin instance created successfully")
        test_results['instantiation'] = True

        # Test 2: Parameter structure validation
        print("\n--- Test 2: Parameter Structure Validation ---")
        assert hasattr(plugin, 'params'), "Plugin should have params attribute"
        assert isinstance(plugin.params, list), "Params should be a list"
        assert len(plugin.params) >= 2, "Should have at least 2 parameter groups"
        print(f"[OK] Plugin has {len(plugin.params)} parameter groups")

        # Test axis configuration
        assert hasattr(plugin, '_axis_names'), "Should have _axis_names attribute"
        assert len(plugin._axis_names) == 3, "Should have 3 axes"
        assert plugin._axis_names == ["HWP_inc", "QWP", "HWP_ana"], "Incorrect axis names"
        print(f"[OK] Axis names validated: {plugin._axis_names}")

        assert hasattr(plugin, '_default_addresses'), "Should have _default_addresses"
        assert len(plugin._default_addresses) == 3, "Should have 3 default addresses"
        assert plugin._default_addresses == ["2", "3", "8"], "Incorrect default addresses"
        print(f"[OK] Default addresses validated: {plugin._default_addresses}")

        test_results['parameter_structure'] = True

        # Test 3: Error codes and commands validation
        print("\n--- Test 3: Error Codes and Commands Validation ---")
        assert hasattr(plugin, '_error_codes'), "Should have error codes dictionary"
        assert len(plugin._error_codes) == 14, f"Should have 14 error codes, got {len(plugin._error_codes)}"
        assert '00' in plugin._error_codes, "Should have OK error code"
        assert plugin._error_codes['00'] == "OK, no error", "Incorrect OK error message"
        print(f"[OK] Error codes validated: {len(plugin._error_codes)} codes")

        assert hasattr(plugin, '_command_reference'), "Should have command reference"
        assert len(plugin._command_reference) == 34, f"Should have 34 commands, got {len(plugin._command_reference)}"
        required_commands = ['in', 'gs', 'ma', 'gp', 'ho', 'st']
        for cmd in required_commands:
            assert cmd in plugin._command_reference, f"Missing required command: {cmd}"
        print(f"[OK] Command reference validated: {len(plugin._command_reference)} commands")

        test_results['error_codes_commands'] = True

        # Test 4: Address resolution
        print("\n--- Test 4: Address Resolution ---")
        for axis in plugin._axis_names:
            address = plugin.get_axis_address(axis)
            assert address in plugin._default_addresses, f"Invalid address for {axis}: {address}"
            print(f"[OK] {axis} -> Address {address}")

        test_results['address_resolution'] = True

        # Test 5: Mock connection simulation
        print("\n--- Test 5: Mock Connection Simulation ---")

        # Setup status monitoring
        status_messages = []
        def status_callback(command):
            status_messages.append((command.command, command.data))

        plugin.add_status_callback(status_callback)

        # Simulate connection
        plugin.settings.child('serial', 'com_port').setValue('COM3')
        plugin.settings.child('connect').setValue(True)

        # This should trigger the setup process
        connect_param = plugin.settings.child('connect')
        plugin.commit_settings(connect_param)

        # Check that controller was created
        assert plugin.controller is not None, "Controller should be initialized"
        assert plugin.controller.is_open, "Controller should be open"
        print("[OK] Mock serial connection established")

        # Check that pulses_per_deg was calculated for all axes
        assert len(plugin.pulses_per_deg) == 3, f"Should have pulses/deg for all axes, got {len(plugin.pulses_per_deg)}"
        for axis in plugin._axis_names:
            assert axis in plugin.pulses_per_deg, f"Missing pulses/deg for {axis}"
            assert plugin.pulses_per_deg[axis] > 0, f"Invalid pulses/deg for {axis}"
        print(f"[OK] Pulses per degree calculated for {len(plugin.pulses_per_deg)} axes")

        test_results['mock_connection'] = True

        # Test 6: Position conversion accuracy
        print("\n--- Test 6: Position Conversion Accuracy ---")

        test_positions = [0.0, 45.0, 90.0, -45.0, 180.0, -90.0]
        conversion_errors = []

        for test_pos in test_positions:
            # Move to position
            plugin.move_abs(test_pos)

            # Get position back
            readback_pos = plugin.get_actuator_value()

            # Calculate conversion error
            error = abs(readback_pos - test_pos)
            conversion_errors.append(error)

            print(f"  Position {test_pos:6.1f}° -> {readback_pos:6.1f}° (error: {error:.3f}°)")

        max_error = max(conversion_errors)
        avg_error = sum(conversion_errors) / len(conversion_errors)

        assert max_error < 1.0, f"Maximum conversion error too high: {max_error:.3f}°"
        print(f"[OK] Position conversion: max error {max_error:.3f}°, avg error {avg_error:.3f}°")

        test_results['position_conversion'] = True

        # Test 7: Multi-axis operation
        print("\n--- Test 7: Multi-axis Operation ---")

        for axis in plugin._axis_names:
            # Switch to axis
            plugin.settings.child('multiaxes', 'selected_axis').setValue(axis)

            # Test movement
            test_angle = 30.0
            plugin.move_abs(test_angle)
            position = plugin.get_actuator_value()

            print(f"[OK] {axis}: moved to {position:.1f}°")

        test_results['multi_axis'] = True

        # Test 8: Error handling
        print("\n--- Test 8: Error Handling ---")

        # Test status checking
        current_axis = plugin.settings.child('multiaxes', 'selected_axis').value()
        address = plugin.get_axis_address(current_axis)
        status_code = plugin._check_status(address)

        assert status_code is not None, "Status check should return a code"
        print(f"[OK] Status check returned: {status_code}")

        test_results['error_handling'] = True

        # Test 9: Stop motion
        print("\n--- Test 9: Stop Motion ---")

        plugin.stop_motion()
        print("[OK] Stop motion command executed")

        test_results['stop_motion'] = True

        # Test 10: Motor optimization (brief test)
        print("\n--- Test 10: Motor Optimization ---")

        # Note: This is a mock test - real optimization takes minutes
        original_pos = plugin.get_actuator_value()
        plugin.run_optimization()

        # Position might change during optimization, that's normal
        final_pos = plugin.get_actuator_value()
        print(f"[OK] Motor optimization completed (pos: {original_pos:.1f}° -> {final_pos:.1f}°)")

        test_results['motor_optimization'] = True

        # Test 11: Cleanup
        print("\n--- Test 11: Cleanup ---")

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
            print("SUCCESS: ALL ELLIPTEC PLUGIN TESTS PASSED!")
            return True
        else:
            print("[WARNING]  SOME TESTS FAILED!")
            return False

    except Exception as e:
        print(f"\nERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_elliptec_features():
    """Test specific Elliptec plugin features in detail"""

    print("\n=== Detailed Feature Tests ===")

    try:
        # Import the plugin directly
        import sys
        from pathlib import Path
        plugin_path = Path(__file__).parent.parent / "src" / "pymodaq_plugins_urashg" / "daq_move_plugins"
        sys.path.insert(0, str(plugin_path))
        from DAQ_Move_Elliptec import DAQ_Move_Elliptec

        plugin = DAQ_Move_Elliptec()

        # Test home-on-connect feature
        print("\n--- Home-on-Connect Feature ---")
        plugin.settings.child('elliptec_settings', 'home_on_connect').setValue(True)
        plugin.settings.child('serial', 'com_port').setValue('COM4')
        plugin.settings.child('connect').setValue(True)

        connect_param = plugin.settings.child('connect')
        plugin.commit_settings(connect_param)

        print("[OK] Home-on-connect feature tested")

        # Test wait for action completion
        print("\n--- Action Completion Waiting ---")
        address = plugin.get_axis_address()
        plugin._wait_for_action_completion(address)
        print("[OK] Action completion waiting tested")

        # Test command sending with data
        print("\n--- Command Sending with Data ---")
        response = plugin.send_command("2", "ma", "00001000")
        assert response is not None, "Should receive response"
        print(f"[OK] Command with data sent, response: {response.strip()}")

        plugin.close()

        return True

    except Exception as e:
        print(f"ERROR: Detailed feature test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Elliptec Plugin Mock Tests...")

    # Run comprehensive tests
    success1 = test_elliptec_plugin_comprehensive()

    # Run detailed feature tests
    success2 = test_specific_elliptec_features()

    # Overall result
    if success1 and success2:
        print("\nSUCCESS: ALL ELLIPTEC TESTS COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nERROR: SOME ELLIPTEC TESTS FAILED!")
        sys.exit(1)
