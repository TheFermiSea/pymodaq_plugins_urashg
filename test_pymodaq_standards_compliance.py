#!/usr/bin/env python3
"""
Comprehensive PyMoDAQ Standards Compliance Test Suite

This test suite verifies that all URASHG plugins comply with PyMoDAQ 5.x standards,
including the critical issues that were causing extension integration failures.

Tests cover:
1. Plugin signature compliance (move_home with value=None parameter)
2. DataActuator usage patterns (correct .value() vs problematic .data[0][0])
3. Threading safety (no problematic __del__ methods)
4. Data structure compliance (DataWithAxes with proper source)
5. Import statement compliance (PyMoDAQ 4+ patterns)
6. Plugin lifecycle compliance (proper ini_stage, close, etc.)

Usage:
    python test_pymodaq_standards_compliance.py [--verbose] [--fix-issues]

Options:
    --verbose      Enable detailed logging
    --fix-issues   Automatically apply fixes for detected issues
"""

import sys
import logging
import argparse
import inspect
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class PyMoDAQComplianceChecker:
    """Main compliance checker for PyMoDAQ standards."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = []
        self.plugins = []
        self.passed_tests = 0
        self.total_tests = 0

    def find_plugins(self) -> List[Path]:
        """Find all PyMoDAQ plugin files."""
        plugin_patterns = [
            "**/daq_move_*.py",
            "**/daq_*viewer_*.py",
            "**/daq_*Dviewer_*.py"
        ]

        plugins = []
        for pattern in plugin_patterns:
            plugins.extend(self.project_root.glob(pattern))

        # Filter out template and legacy files
        filtered = []
        for plugin in plugins:
            if any(exclude in str(plugin) for exclude in ['template', 'urashg_2', '__pycache__']):
                continue
            filtered.append(plugin)

        self.plugins = filtered
        return filtered

    def test_move_home_signature_compliance(self) -> bool:
        """Test 1: move_home() method signature compliance."""
        print("\n" + "="*60)
        print("TEST 1: move_home() Method Signature Compliance")
        print("="*60)

        issues_found = []
        compliant_plugins = []

        for plugin_file in self.plugins:
            if 'daq_move_' not in plugin_file.name:
                continue  # Only move plugins need move_home

            try:
                # Read and parse the file
                with open(plugin_file, 'r') as f:
                    content = f.read()

                # Check for move_home method
                if 'def move_home(' not in content:
                    issues_found.append({
                        'file': plugin_file,
                        'issue': 'Missing move_home() method',
                        'severity': 'HIGH',
                        'description': 'All PyMoDAQ move plugins must implement move_home()'
                    })
                    continue

                # Parse AST to check signature
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == 'move_home':
                        args = [arg.arg for arg in node.args.args]

                        # Check for PyMoDAQ 5.x compliance: move_home(self, value=None)
                        if len(args) < 2 or 'value' not in args:
                            issues_found.append({
                                'file': plugin_file,
                                'issue': 'move_home() missing value=None parameter',
                                'severity': 'CRITICAL',
                                'description': 'PyMoDAQ 5.x requires move_home(self, value=None) signature',
                                'fix': 'Change def move_home(self): to def move_home(self, value=None):'
                            })
                        else:
                            compliant_plugins.append(plugin_file.name)
                        break

            except Exception as e:
                issues_found.append({
                    'file': plugin_file,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ CRITICAL ISSUES FOUND: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                if 'fix' in issue:
                    print(f"   🔧 Fix: {issue['fix']}")
                print()
        else:
            print("✅ All move plugins have compliant move_home() signatures")

        if compliant_plugins:
            print(f"✅ Compliant plugins ({len(compliant_plugins)}):")
            for plugin in compliant_plugins:
                print(f"   - {plugin}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def test_dataactuator_usage_patterns(self) -> bool:
        """Test 2: DataActuator usage pattern compliance."""
        print("\n" + "="*60)
        print("TEST 2: DataActuator Usage Pattern Compliance")
        print("="*60)

        issues_found = []
        compliant_patterns = []

        # Problematic patterns that cause UI failure
        problematic_patterns = [
            r'position\.data\[0\]\[0\]',  # WRONG - causes UI failure
            r'positions\.data\[0\]\[0\]',
            r'float\(.*\.data\[0\]\[0\]\)',
        ]

        # Correct patterns for PyMoDAQ 5.x
        correct_patterns = [
            r'position\.value\(\)',       # CORRECT for single-axis
            r'positions\.data\[0\]',      # CORRECT for multi-axis (no second [0])
        ]

        for plugin_file in self.plugins:
            if 'daq_move_' not in plugin_file.name:
                continue  # Focus on move plugins

            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()

                # Check for problematic patterns
                for pattern in problematic_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues_found.append({
                            'file': plugin_file,
                            'issue': f'Problematic DataActuator pattern: {pattern}',
                            'severity': 'CRITICAL',
                            'description': 'This pattern causes UI integration failure',
                            'matches': matches,
                            'fix': 'Use position.value() for single-axis or positions.data[0] for multi-axis'
                        })

                # Check for correct patterns
                has_correct_pattern = False
                for pattern in correct_patterns:
                    if re.search(pattern, content):
                        has_correct_pattern = True
                        break

                if has_correct_pattern and not any(re.search(p, content) for p in problematic_patterns):
                    compliant_patterns.append(plugin_file.name)

            except Exception as e:
                issues_found.append({
                    'file': plugin_file,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ CRITICAL DATAACTUATOR ISSUES: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                print(f"   💥 {issue['description']}")
                if 'fix' in issue:
                    print(f"   🔧 Fix: {issue['fix']}")
                print()
        else:
            print("✅ All plugins use correct DataActuator patterns")

        if compliant_patterns:
            print(f"✅ Compliant plugins ({len(compliant_patterns)}):")
            for plugin in compliant_patterns:
                print(f"   - {plugin}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def test_threading_safety_compliance(self) -> bool:
        """Test 3: Threading safety compliance."""
        print("\n" + "="*60)
        print("TEST 3: Threading Safety Compliance")
        print("="*60)

        issues_found = []
        safe_files = []

        # Check all Python files in hardware directory
        hardware_files = list(self.project_root.glob("**/hardware/**/*.py"))
        all_files = self.plugins + hardware_files

        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                # Check for problematic __del__ methods
                if re.search(r'def __del__\(', content):
                    # Check if it's safely implemented
                    del_sections = re.findall(r'def __del__\(.*?\n(.*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)

                    for section in del_sections:
                        if any(dangerous in section for dangerous in ['close', 'disconnect', 'cleanup']):
                            issues_found.append({
                                'file': file_path,
                                'issue': 'Dangerous __del__ method with cleanup operations',
                                'severity': 'HIGH',
                                'description': 'Can cause Qt threading conflicts during garbage collection',
                                'fix': 'Remove __del__ method, use explicit cleanup in close() method'
                            })
                            break
                    else:
                        safe_files.append(file_path.name)
                else:
                    safe_files.append(file_path.name)

            except Exception as e:
                issues_found.append({
                    'file': file_path,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ THREADING SAFETY ISSUES: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                print(f"   ⚠️  {issue['description']}")
                if 'fix' in issue:
                    print(f"   🔧 Fix: {issue['fix']}")
                print()
        else:
            print("✅ All files are thread-safe (no dangerous __del__ methods)")

        print(f"✅ Thread-safe files: {len(safe_files)}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def test_data_structure_compliance(self) -> bool:
        """Test 4: PyMoDAQ 5.x data structure compliance."""
        print("\n" + "="*60)
        print("TEST 4: Data Structure Compliance")
        print("="*60)

        issues_found = []
        compliant_files = []

        # Check viewer plugins for DataWithAxes usage
        viewer_plugins = [p for p in self.plugins if 'viewer' in p.name]

        for plugin_file in viewer_plugins:
            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()

                # Check for PyMoDAQ 5.x imports
                if 'from pymodaq_data.data import' not in content and 'DataWithAxes' in content:
                    issues_found.append({
                        'file': plugin_file,
                        'issue': 'Missing PyMoDAQ 5.x data imports',
                        'severity': 'HIGH',
                        'description': 'Should import from pymodaq_data.data',
                        'fix': 'Add: from pymodaq_data.data import DataWithAxes, DataSource'
                    })

                # Check for proper DataSource usage
                if 'DataWithAxes' in content:
                    if 'source=DataSource' not in content:
                        issues_found.append({
                            'file': plugin_file,
                            'issue': 'Missing DataSource in DataWithAxes',
                            'severity': 'MEDIUM',
                            'description': 'PyMoDAQ 5.x requires source parameter',
                            'fix': 'Add source=DataSource.raw to DataWithAxes calls'
                        })
                    else:
                        compliant_files.append(plugin_file.name)

            except Exception as e:
                issues_found.append({
                    'file': plugin_file,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ DATA STRUCTURE ISSUES: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                print(f"   💡 {issue['description']}")
                if 'fix' in issue:
                    print(f"   🔧 Fix: {issue['fix']}")
                print()
        else:
            print("✅ All viewer plugins use correct data structures")

        if compliant_files:
            print(f"✅ Compliant viewer plugins ({len(compliant_files)}):")
            for plugin in compliant_files:
                print(f"   - {plugin}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def test_plugin_lifecycle_compliance(self) -> bool:
        """Test 5: Plugin lifecycle method compliance."""
        print("\n" + "="*60)
        print("TEST 5: Plugin Lifecycle Compliance")
        print("="*60)

        issues_found = []
        compliant_plugins = []

        # Required methods for different plugin types
        move_required_methods = ['ini_stage', 'close', 'get_actuator_value', 'move_abs', 'move_rel', 'stop_motion']
        viewer_required_methods = ['ini_detector', 'close', 'grab_data']

        for plugin_file in self.plugins:
            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()

                # Determine plugin type and required methods
                if 'daq_move_' in plugin_file.name:
                    required_methods = move_required_methods
                    plugin_type = 'move'
                elif 'viewer' in plugin_file.name:
                    required_methods = viewer_required_methods
                    plugin_type = 'viewer'
                else:
                    continue

                # Check for required methods
                missing_methods = []
                for method in required_methods:
                    if f'def {method}(' not in content:
                        missing_methods.append(method)

                if missing_methods:
                    issues_found.append({
                        'file': plugin_file,
                        'issue': f'Missing required {plugin_type} plugin methods: {missing_methods}',
                        'severity': 'HIGH',
                        'description': f'PyMoDAQ {plugin_type} plugins must implement all required methods',
                        'missing_methods': missing_methods
                    })
                else:
                    compliant_plugins.append(plugin_file.name)

            except Exception as e:
                issues_found.append({
                    'file': plugin_file,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ LIFECYCLE COMPLIANCE ISSUES: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                print(f"   📋 {issue['description']}")
                print()
        else:
            print("✅ All plugins implement required lifecycle methods")

        if compliant_plugins:
            print(f"✅ Compliant plugins ({len(compliant_plugins)}):")
            for plugin in compliant_plugins:
                print(f"   - {plugin}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def test_import_statement_compliance(self) -> bool:
        """Test 6: Import statement compliance for PyMoDAQ 4+."""
        print("\n" + "="*60)
        print("TEST 6: Import Statement Compliance")
        print("="*60)

        issues_found = []
        compliant_files = []

        # Deprecated imports that should be updated
        deprecated_imports = {
            'from pymodaq.daq_utils': 'from pymodaq.utils',
            'from pymodaq.utils.daq_utils import DataFromPlugins': 'from pymodaq.utils.data import DataFromPlugins',
            'from pymodaq.DAQ_Move': 'from pymodaq.control_modules',
            'from pymodaq.DAQ_Viewer': 'from pymodaq.control_modules',
        }

        for plugin_file in self.plugins:
            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()

                file_issues = []
                for old_import, new_import in deprecated_imports.items():
                    if old_import in content:
                        file_issues.append({
                            'old': old_import,
                            'new': new_import
                        })

                if file_issues:
                    issues_found.append({
                        'file': plugin_file,
                        'issue': 'Deprecated import statements',
                        'severity': 'MEDIUM',
                        'description': 'Using PyMoDAQ 3.x import patterns',
                        'imports': file_issues
                    })
                else:
                    compliant_files.append(plugin_file.name)

            except Exception as e:
                issues_found.append({
                    'file': plugin_file,
                    'issue': f'Parse error: {e}',
                    'severity': 'ERROR'
                })

        # Report results
        if issues_found:
            print(f"❌ IMPORT STATEMENT ISSUES: {len(issues_found)}")
            for issue in issues_found:
                print(f"   📁 {issue['file'].name}")
                print(f"   🚨 {issue['issue']}")
                if 'imports' in issue:
                    for imp in issue['imports']:
                        print(f"      OLD: {imp['old']}")
                        print(f"      NEW: {imp['new']}")
                print()
        else:
            print("✅ All plugins use current import statements")

        if compliant_files:
            print(f"✅ Compliant files ({len(compliant_files)}):")
            for f in compliant_files:
                print(f"   - {f}")

        self.issues.extend(issues_found)
        self.total_tests += 1
        if not issues_found:
            self.passed_tests += 1

        return len(issues_found) == 0

    def generate_compliance_report(self) -> str:
        """Generate comprehensive compliance report."""
        report = []
        report.append("PyMoDAQ Standards Compliance Report")
        report.append("=" * 60)
        report.append(f"Project: URASHG Microscopy Extension")
        report.append(f"Plugins analyzed: {len(self.plugins)}")
        report.append(f"Tests passed: {self.passed_tests}/{self.total_tests}")
        report.append("")

        if self.issues:
            # Group issues by severity
            critical_issues = [i for i in self.issues if i.get('severity') == 'CRITICAL']
            high_issues = [i for i in self.issues if i.get('severity') == 'HIGH']
            medium_issues = [i for i in self.issues if i.get('severity') == 'MEDIUM']

            report.append(f"🚨 CRITICAL ISSUES ({len(critical_issues)}):")
            report.append("These MUST be fixed for proper PyMoDAQ integration")
            for issue in critical_issues:
                report.append(f"  • {issue['file'].name}: {issue['issue']}")
            report.append("")

            if high_issues:
                report.append(f"⚠️  HIGH PRIORITY ISSUES ({len(high_issues)}):")
                for issue in high_issues:
                    report.append(f"  • {issue['file'].name}: {issue['issue']}")
                report.append("")

            if medium_issues:
                report.append(f"💡 MEDIUM PRIORITY ISSUES ({len(medium_issues)}):")
                for issue in medium_issues:
                    report.append(f"  • {issue['file'].name}: {issue['issue']}")
                report.append("")
        else:
            report.append("🎉 ALL TESTS PASSED - FULLY COMPLIANT!")

        report.append("Key PyMoDAQ 5.x Requirements:")
        report.append("1. ✅ move_home(self, value=None) signature")
        report.append("2. ✅ DataActuator: position.value() for single-axis")
        report.append("3. ✅ DataActuator: positions.data[0] for multi-axis")
        report.append("4. ✅ No dangerous __del__ methods")
        report.append("5. ✅ DataWithAxes with source=DataSource.raw")
        report.append("6. ✅ Current import statements")

        return "\n".join(report)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='PyMoDAQ Standards Compliance Test')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--fix-issues', action='store_true', help='Automatically apply fixes')
    args = parser.parse_args()

    setup_logging(args.verbose)

    print("PyMoDAQ Standards Compliance Test Suite")
    print("=" * 60)
    print("Testing URASHG plugins for PyMoDAQ 5.x compliance")
    print("This test identifies issues that prevent proper extension integration")

    # Initialize checker
    checker = PyMoDAQComplianceChecker(project_root)

    # Find plugins
    plugins = checker.find_plugins()
    print(f"\nFound {len(plugins)} plugins to analyze:")
    for plugin in plugins:
        print(f"  - {plugin.relative_to(project_root)}")

    # Run all compliance tests
    all_tests_passed = True

    tests = [
        checker.test_move_home_signature_compliance,
        checker.test_dataactuator_usage_patterns,
        checker.test_threading_safety_compliance,
        checker.test_data_structure_compliance,
        checker.test_plugin_lifecycle_compliance,
        checker.test_import_statement_compliance,
    ]

    for test in tests:
        try:
            test_passed = test()
            if not test_passed:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            all_tests_passed = False

    # Generate and display report
    print("\n" + "=" * 60)
    print("FINAL COMPLIANCE REPORT")
    print("=" * 60)

    report = checker.generate_compliance_report()
    print(report)

    # Summary
    if all_tests_passed:
        print("\n🎉 SUCCESS: All PyMoDAQ standards compliance tests passed!")
        print("The URASHG extension should integrate properly with PyMoDAQ.")
        return 0
    else:
        critical_issues = [i for i in checker.issues if i.get('severity') == 'CRITICAL']
        if critical_issues:
            print(f"\n💥 FAILURE: {len(critical_issues)} critical issues must be fixed!")
            print("These issues prevent proper PyMoDAQ extension integration.")
            print("\nMost Critical Fixes Needed:")
            for issue in critical_issues[:3]:  # Show top 3
                print(f"  1. {issue['file'].name}: {issue['issue']}")
                if 'fix' in issue:
                    print(f"     Fix: {issue['fix']}")
        else:
            print(f"\n⚠️  {len(checker.issues)} issues found, but no critical ones.")
            print("Extension should work, but improvements recommended.")

        return 1

if __name__ == "__main__":
    sys.exit(main())
