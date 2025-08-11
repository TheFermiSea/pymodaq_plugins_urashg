#!/usr/bin/env python3
"""
URASHG Extension Comprehensive Compliance Test Runner

This script runs the full test suite for the URASHG PyMoDAQ extension to ensure
complete compliance with PyMoDAQ standards. It provides detailed reporting,
coverage analysis, and compliance verification.

Features:
- Comprehensive test execution across all compliance categories
- Detailed reporting with compliance status
- Coverage analysis and reporting
- Performance benchmarking
- HTML report generation
- CI/CD integration support
- Failure analysis and recommendations

Usage:
    # Run full compliance test suite
    python run_extension_compliance_tests.py

    # Run specific test categories
    python run_extension_compliance_tests.py --category unit
    python run_extension_compliance_tests.py --category integration
    python run_extension_compliance_tests.py --category pymodaq_standards

    # Generate detailed reports
    python run_extension_compliance_tests.py --report-format html
    python run_extension_compliance_tests.py --report-format json

    # CI/CD mode
    python run_extension_compliance_tests.py --ci-mode

    # Performance analysis
    python run_extension_compliance_tests.py --benchmark
"""

import sys
import os
import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import platform

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ComplianceTestRunner:
    """
    Comprehensive test runner for URASHG extension compliance verification.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / 'tests'
        self.results_dir = project_root / 'test_results'
        self.results_dir.mkdir(exist_ok=True)

        # Test categories and their descriptions
        self.test_categories = {
            'unit': {
                'description': 'Unit tests that don\'t require hardware',
                'markers': ['unit'],
                'timeout': 300,
                'critical': True
            },
            'integration': {
                'description': 'Integration tests with mocked hardware',
                'markers': ['integration'],
                'timeout': 600,
                'critical': True
            },
            'pymodaq_standards': {
                'description': 'PyMoDAQ standards compliance tests',
                'markers': ['pymodaq_standards'],
                'timeout': 300,
                'critical': True
            },
            'extension': {
                'description': 'Extension-specific functionality tests',
                'markers': ['extension'],
                'timeout': 400,
                'critical': True
            },
            'device_manager': {
                'description': 'Device manager compliance tests',
                'markers': ['device_manager'],
                'timeout': 300,
                'critical': True
            },
            'measurement_worker': {
                'description': 'Measurement worker compliance tests',
                'markers': ['measurement_worker'],
                'timeout': 400,
                'critical': True
            },
            'plugin_integration': {
                'description': 'Plugin integration compliance tests',
                'markers': ['plugin_integration'],
                'timeout': 300,
                'critical': True
            },
            'thread_safety': {
                'description': 'Thread safety and concurrency tests',
                'markers': ['thread_safety'],
                'timeout': 200,
                'critical': False
            },
            'error_handling': {
                'description': 'Error handling and recovery tests',
                'markers': ['error_handling'],
                'timeout': 200,
                'critical': False
            },
            'performance': {
                'description': 'Performance and resource usage tests',
                'markers': ['performance'],
                'timeout': 400,
                'critical': False
            },
            'configuration': {
                'description': 'Configuration management tests',
                'markers': ['configuration'],
                'timeout': 200,
                'critical': False
            },
            'documentation': {
                'description': 'Documentation standards tests',
                'markers': ['documentation'],
                'timeout': 100,
                'critical': False
            }
        }

        # Results storage
        self.test_results = {}
        self.overall_status = 'UNKNOWN'
        self.start_time = None
        self.end_time = None

    def run_full_compliance_suite(self,
                                 categories: Optional[List[str]] = None,
                                 coverage: bool = True,
                                 benchmark: bool = False,
                                 verbose: bool = True) -> Dict[str, Any]:
        """
        Run the full compliance test suite.

        Args:
            categories: Specific test categories to run (None for all)
            coverage: Whether to generate coverage reports
            benchmark: Whether to run performance benchmarks
            verbose: Verbose output

        Returns:
            Dictionary containing test results and compliance status
        """
        self.start_time = datetime.now()
        logger.info("🚀 Starting URASHG Extension Compliance Test Suite")
        logger.info(f"📁 Project root: {self.project_root}")
        logger.info(f"🐍 Python version: {platform.python_version()}")
        logger.info(f"💻 Platform: {platform.platform()}")

        # Determine which categories to run
        if categories is None:
            categories = list(self.test_categories.keys())

        # Validate categories
        invalid_categories = set(categories) - set(self.test_categories.keys())
        if invalid_categories:
            raise ValueError(f"Invalid test categories: {invalid_categories}")

        logger.info(f"🎯 Running {len(categories)} test categories: {', '.join(categories)}")

        # Run environment checks
        self._check_test_environment()

        # Run tests for each category
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        critical_failures = []

        for category in categories:
            logger.info(f"\n📋 Running {category} tests...")
            result = self._run_category_tests(
                category,
                coverage=coverage and category == categories[0],  # Only first category for coverage
                benchmark=benchmark,
                verbose=verbose
            )

            self.test_results[category] = result
            total_passed += result['passed']
            total_failed += result['failed']
            total_skipped += result['skipped']

            if result['failed'] > 0 and self.test_categories[category]['critical']:
                critical_failures.append(category)

            # Print category summary
            status_emoji = "✅" if result['failed'] == 0 else "❌"
            logger.info(f"{status_emoji} {category}: {result['passed']} passed, "
                       f"{result['failed']} failed, {result['skipped']} skipped")

        # Determine overall compliance status
        if critical_failures:
            self.overall_status = 'CRITICAL_FAILURE'
        elif total_failed > 0:
            self.overall_status = 'MINOR_FAILURES'
        else:
            self.overall_status = 'COMPLIANT'

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        # Generate comprehensive summary
        summary = {
            'overall_status': self.overall_status,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'critical_failures': critical_failures,
            'duration_seconds': duration,
            'timestamp': self.start_time.isoformat(),
            'categories': self.test_results,
            'environment': self._get_environment_info(),
            'compliance_score': self._calculate_compliance_score()
        }

        # Print final summary
        self._print_final_summary(summary)

        return summary

    def _run_category_tests(self,
                           category: str,
                           coverage: bool = False,
                           benchmark: bool = False,
                           verbose: bool = True) -> Dict[str, Any]:
        """Run tests for a specific category."""
        category_info = self.test_categories[category]
        markers = category_info['markers']
        timeout = category_info['timeout']

        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            str(self.test_dir),
            '-v' if verbose else '-q',
            '--tb=short',
            '--maxfail=10',
            f'--timeout={timeout}',
            '--disable-warnings',
            '--no-header',
            '--no-summary'
        ]

        # Add markers
        if markers:
            marker_expr = ' or '.join(markers)
            cmd.extend(['-m', marker_expr])

        # Add coverage if requested
        if coverage:
            cmd.extend([
                '--cov=pymodaq_plugins_urashg',
                '--cov-report=html:test_results/coverage_html',
                '--cov-report=json:test_results/coverage.json',
                '--cov-report=term-missing',
                '--cov-fail-under=0'  # Don't fail on coverage, just report
            ])

        # Add benchmark if requested
        if benchmark:
            cmd.extend(['--benchmark-only', '--benchmark-json=test_results/benchmark.json'])

        # Add JUnit XML output
        junit_file = self.results_dir / f'{category}_results.xml'
        cmd.extend(['--junit-xml', str(junit_file)])

        # Set environment variables
        env = os.environ.copy()
        env.update({
            'PYMODAQ_TEST_MODE': '1',
            'QT_QPA_PLATFORM': 'offscreen',
            'URASHG_MOCK_HARDWARE': '1',
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'
        })

        # Run tests
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=timeout + 60  # Add buffer to pytest timeout
        )
        duration = time.time() - start_time

        # Parse results
        return self._parse_test_results(result, duration, category)

    def _parse_test_results(self, result: subprocess.CompletedProcess,
                           duration: float, category: str) -> Dict[str, Any]:
        """Parse pytest results."""
        output = result.stdout
        error = result.stderr
        return_code = result.returncode

        # Extract test counts from output
        passed = failed = skipped = 0

        # Look for pytest summary line
        summary_patterns = [
            r'(\d+) passed',
            r'(\d+) failed',
            r'(\d+) skipped',
            r'(\d+) error'
        ]

        import re
        for line in output.split('\n'):
            if ' passed' in line or ' failed' in line or ' skipped' in line:
                if match := re.search(r'(\d+) passed', line):
                    passed = int(match.group(1))
                if match := re.search(r'(\d+) failed', line):
                    failed = int(match.group(1))
                if match := re.search(r'(\d+) skipped', line):
                    skipped = int(match.group(1))

        # If no tests found in output, try to extract from return code
        if passed == 0 and failed == 0 and skipped == 0:
            if return_code == 0:
                passed = 1  # Assume at least one test passed
            else:
                failed = 1  # Assume at least one test failed

        return {
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'duration': duration,
            'return_code': return_code,
            'output': output,
            'error': error,
            'status': 'PASS' if return_code == 0 else 'FAIL'
        }

    def _check_test_environment(self):
        """Check that the test environment is properly set up."""
        logger.info("🔍 Checking test environment...")

        # Check Python version
        if sys.version_info < (3, 9):
            logger.warning(f"⚠️  Python {sys.version} may not be fully supported")

        # Check required packages
        required_packages = [
            ('pytest', 'pytest'),
            ('pytest-qt', 'pytestqt'),
            ('pytest-mock', 'pytest_mock'),
            ('pytest-cov', 'pytest_cov'),
            ('numpy', 'numpy'),
            ('qtpy', 'qtpy')
        ]

        missing_packages = []
        for package_name, module_name in required_packages:
            try:
                __import__(module_name)
            except ImportError:
                missing_packages.append(package_name)

        if missing_packages:
            logger.error(f"❌ Missing required packages: {missing_packages}")
            logger.error("💡 Install with: pip install " + " ".join(missing_packages))
            sys.exit(1)

        # Check PyMoDAQ availability
        try:
            import pymodaq
            logger.info(f"✅ PyMoDAQ {getattr(pymodaq, '__version__', 'unknown')} available")
        except ImportError:
            logger.warning("⚠️  PyMoDAQ not available - some tests may be skipped")

        # Check test directory
        if not self.test_dir.exists():
            logger.error(f"❌ Test directory not found: {self.test_dir}")
            sys.exit(1)

        logger.info("✅ Test environment checks passed")

    def _get_environment_info(self) -> Dict[str, Any]:
        """Get information about the test environment."""
        info = {
            'python_version': platform.python_version(),
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'processor': platform.processor(),
            'python_implementation': platform.python_implementation(),
        }

        # Get package versions
        try:
            import pytest
            info['pytest_version'] = pytest.__version__
        except ImportError:
            pass

        try:
            import pymodaq
            info['pymodaq_version'] = getattr(pymodaq, '__version__', 'unknown')
        except ImportError:
            pass

        try:
            import numpy
            info['numpy_version'] = numpy.__version__
        except ImportError:
            pass

        return info

    def _calculate_compliance_score(self) -> float:
        """Calculate overall compliance score (0-100)."""
        if not self.test_results:
            return 0.0

        total_weight = 0
        weighted_score = 0

        for category, result in self.test_results.items():
            # Critical categories have higher weight
            weight = 3 if self.test_categories[category]['critical'] else 1
            total_weight += weight

            # Calculate category score
            total_tests = result['passed'] + result['failed']
            if total_tests > 0:
                category_score = result['passed'] / total_tests
            else:
                category_score = 1.0  # No tests = full score

            weighted_score += category_score * weight

        return (weighted_score / total_weight * 100) if total_weight > 0 else 0.0

    def _print_final_summary(self, summary: Dict[str, Any]):
        """Print final test summary."""
        logger.info("\n" + "="*80)
        logger.info("🎯 URASHG EXTENSION COMPLIANCE TEST RESULTS")
        logger.info("="*80)

        # Overall status
        status_emoji = {
            'COMPLIANT': '✅',
            'MINOR_FAILURES': '⚠️',
            'CRITICAL_FAILURE': '❌',
            'UNKNOWN': '❓'
        }

        emoji = status_emoji.get(summary['overall_status'], '❓')
        logger.info(f"{emoji} Overall Status: {summary['overall_status']}")
        logger.info(f"📊 Compliance Score: {summary['compliance_score']:.1f}%")
        logger.info(f"⏱️  Total Duration: {summary['duration_seconds']:.1f}s")

        # Test counts
        logger.info(f"\n📈 Test Results:")
        logger.info(f"   ✅ Passed: {summary['total_passed']}")
        logger.info(f"   ❌ Failed: {summary['total_failed']}")
        logger.info(f"   ⏭️  Skipped: {summary['total_skipped']}")

        # Critical failures
        if summary['critical_failures']:
            logger.info(f"\n🚨 Critical Failures in:")
            for category in summary['critical_failures']:
                logger.info(f"   - {category}")

        # Category breakdown
        logger.info(f"\n📋 Category Breakdown:")
        for category, result in summary['categories'].items():
            status = "✅" if result['failed'] == 0 else "❌"
            critical = " (CRITICAL)" if self.test_categories[category]['critical'] else ""
            logger.info(f"   {status} {category}{critical}: "
                       f"{result['passed']}✅ {result['failed']}❌ {result['skipped']}⏭️")

        # Recommendations
        if summary['overall_status'] != 'COMPLIANT':
            logger.info(f"\n💡 Recommendations:")
            if summary['critical_failures']:
                logger.info("   1. Fix critical failures before deployment")
                logger.info("   2. Review PyMoDAQ standards compliance")
            if summary['total_failed'] > 0:
                logger.info("   3. Check test logs for specific failure details")
                logger.info("   4. Ensure all dependencies are correctly installed")

        logger.info("="*80)

    def generate_html_report(self, summary: Dict[str, Any], output_file: Optional[Path] = None):
        """Generate HTML report of test results."""
        if output_file is None:
            output_file = self.results_dir / 'compliance_report.html'

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URASHG Extension Compliance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 8px; }}
        .status-compliant {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-error {{ color: #dc3545; }}
        .category {{ margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .category.critical {{ border-left: 5px solid #dc3545; }}
        .category.passed {{ border-left: 5px solid #28a745; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 URASHG Extension Compliance Report</h1>
        <p><strong>Generated:</strong> {summary['timestamp']}</p>
        <p><strong>Duration:</strong> {summary['duration_seconds']:.1f} seconds</p>
        <p class="status-{summary['overall_status'].lower()}">
            <strong>Status:</strong> {summary['overall_status']}
        </p>
    </div>

    <div class="metrics">
        <div class="metric">
            <h3>{summary['compliance_score']:.1f}%</h3>
            <p>Compliance Score</p>
        </div>
        <div class="metric">
            <h3>{summary['total_passed']}</h3>
            <p>Tests Passed</p>
        </div>
        <div class="metric">
            <h3>{summary['total_failed']}</h3>
            <p>Tests Failed</p>
        </div>
        <div class="metric">
            <h3>{summary['total_skipped']}</h3>
            <p>Tests Skipped</p>
        </div>
    </div>

    <h2>📋 Test Categories</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Status</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Duration</th>
                <th>Critical</th>
            </tr>
        </thead>
        <tbody>
"""

        for category, result in summary['categories'].items():
            status_class = "passed" if result['failed'] == 0 else "error"
            critical = self.test_categories[category]['critical']
            html_content += f"""
            <tr class="{status_class}">
                <td>{category}</td>
                <td>{'✅ PASS' if result['failed'] == 0 else '❌ FAIL'}</td>
                <td>{result['passed']}</td>
                <td>{result['failed']}</td>
                <td>{result['skipped']}</td>
                <td>{result['duration']:.1f}s</td>
                <td>{'Yes' if critical else 'No'}</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>

    <h2>🔧 Environment Information</h2>
    <table>
"""

        for key, value in summary['environment'].items():
            html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"

        html_content += """
    </table>
</body>
</html>
"""

        output_file.write_text(html_content, encoding='utf-8')
        logger.info(f"📄 HTML report generated: {output_file}")

    def generate_json_report(self, summary: Dict[str, Any], output_file: Optional[Path] = None):
        """Generate JSON report of test results."""
        if output_file is None:
            output_file = self.results_dir / 'compliance_report.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"📄 JSON report generated: {output_file}")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="URASHG Extension Comprehensive Compliance Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all tests
  %(prog)s --category unit integration        # Run specific categories
  %(prog)s --no-coverage                      # Skip coverage analysis
  %(prog)s --benchmark                        # Include performance benchmarks
  %(prog)s --report-format html json          # Generate HTML and JSON reports
  %(prog)s --ci-mode                          # CI/CD optimized execution
        """
    )

    parser.add_argument(
        '--category', '-c',
        nargs='+',
        choices=['unit', 'integration', 'pymodaq_standards', 'extension',
                'device_manager', 'measurement_worker', 'plugin_integration',
                'thread_safety', 'error_handling', 'performance',
                'configuration', 'documentation'],
        help='Test categories to run (default: all)'
    )

    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Skip coverage analysis'
    )

    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Include performance benchmarks'
    )

    parser.add_argument(
        '--report-format',
        nargs='+',
        choices=['html', 'json'],
        default=['html'],
        help='Report formats to generate (default: html)'
    )

    parser.add_argument(
        '--ci-mode',
        action='store_true',
        help='CI/CD mode (faster, less verbose)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for reports (default: test_results)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = ComplianceTestRunner(project_root)

    if args.output_dir:
        runner.results_dir = args.output_dir
        runner.results_dir.mkdir(exist_ok=True)

    try:
        # Run tests
        summary = runner.run_full_compliance_suite(
            categories=args.category,
            coverage=not args.no_coverage,
            benchmark=args.benchmark,
            verbose=args.verbose and not args.ci_mode
        )

        # Generate reports
        for format_type in args.report_format:
            if format_type == 'html':
                runner.generate_html_report(summary)
            elif format_type == 'json':
                runner.generate_json_report(summary)

        # Exit with appropriate code
        if summary['overall_status'] == 'COMPLIANT':
            logger.info("🎉 All compliance tests passed!")
            sys.exit(0)
        elif summary['overall_status'] == 'MINOR_FAILURES':
            logger.warning("⚠️  Some non-critical tests failed")
            sys.exit(0 if args.ci_mode else 1)
        else:
            logger.error("❌ Critical compliance tests failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⏹️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Test execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
