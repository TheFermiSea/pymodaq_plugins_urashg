#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UV Management Script for μRASHG Microscopy Extension

This script provides convenient commands for managing the UV-based Python
environment for the μRASHG microscopy extension project.

Usage:
    python manage_uv.py <command> [options]

Commands:
    setup       - Initial project setup with UV
    install     - Install dependencies
    launch      - Launch the μRASHG extension
    test        - Run tests
    clean       - Clean environment and caches
    status      - Show environment status
    help        - Show this help

Examples:
    python manage_uv.py setup
    python manage_uv.py install --hardware
    python manage_uv.py launch
    python manage_uv.py test --coverage
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path
import shutil

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a styled header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

def run_command(cmd, description="", check=True, capture_output=False):
    """Run a shell command with optional description."""
    if description:
        print_info(f"{description}...")

    print(f"{Colors.OKCYAN}$ {' '.join(cmd)}{Colors.ENDC}")

    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result
        else:
            result = subprocess.run(cmd, check=check)
            return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        if capture_output and e.stderr:
            print(e.stderr)
        return None
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        return None

def check_uv_installed():
    """Check if UV is installed."""
    result = run_command(['uv', '--version'], capture_output=True, check=False)
    if result and result.returncode == 0:
        version = result.stdout.strip()
        print_success(f"UV {version} is installed")
        return True
    else:
        print_error("UV is not installed")
        print_info("Install UV with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def setup_project():
    """Initial project setup."""
    print_header("μRASHG Project Setup")

    if not check_uv_installed():
        return False

    # Check Python version
    print_info("Checking Python version...")
    python_version_file = Path('.python-version')
    if python_version_file.exists():
        version = python_version_file.read_text().strip()
        print_success(f"Python version pinned to: {version}")
    else:
        print_info("Pinning Python version to 3.12...")
        run_command(['uv', 'python', 'pin', '3.12'])

    # Install Python if needed
    print_info("Installing Python 3.12 if needed...")
    run_command(['uv', 'python', 'install', '3.12'], check=False)

    # Sync environment
    print_info("Setting up virtual environment and installing dependencies...")
    result = run_command(['uv', 'sync'], "Syncing dependencies")

    if result and result.returncode == 0:
        print_success("Project setup completed successfully!")
        print_info("Next steps:")
        print("  1. Install hardware dependencies: python manage_uv.py install --hardware")
        print("  2. Launch the extension: python manage_uv.py launch")
        return True
    else:
        print_error("Project setup failed")
        return False

def install_dependencies(args):
    """Install dependencies with optional extras."""
    print_header("Installing Dependencies")

    if not check_uv_installed():
        return False

    # Build UV sync command
    cmd = ['uv', 'sync']

    if args.hardware:
        cmd.extend(['--extra', 'hardware'])
        print_info("Installing hardware dependencies...")

    if args.pyrpl:
        cmd.extend(['--extra', 'pyrpl'])
        print_info("Installing PyRPL dependencies...")

    if args.dev:
        cmd.extend(['--extra', 'dev'])
        print_info("Installing development dependencies...")

    if args.all:
        cmd.append('--all-extras')
        print_info("Installing all optional dependencies...")

    if args.upgrade:
        cmd.append('--upgrade')
        print_info("Upgrading dependencies...")

    result = run_command(cmd, "Installing dependencies")

    if result and result.returncode == 0:
        print_success("Dependencies installed successfully!")

        # Install additional hardware packages if needed
        if args.hardware:
            print_info("Installing additional hardware packages...")
            # These are installed separately due to git dependencies
            run_command(['uv', 'add', 'pyvcam@git+https://github.com/Photometrics/PyVCAM.git'],
                       "Installing PyVCAM", check=False)
            run_command(['uv', 'add', 'elliptec@git+https://github.com/roesel/elliptec.git'],
                       "Installing Elliptec", check=False)

        return True
    else:
        print_error("Dependency installation failed")
        return False

def launch_extension():
    """Launch the μRASHG extension."""
    print_header("Launching μRASHG Extension")

    if not check_uv_installed():
        return False

    # Check if dependencies are installed
    result = run_command(['uv', 'run', 'python', '-c', 'import pymodaq'],
                        capture_output=True, check=False)

    if not result or result.returncode != 0:
        print_error("PyMoDAQ not found in environment")
        print_info("Run: python manage_uv.py install")
        return False

    print_success("Environment ready")
    print_info("Launching μRASHG extension...")

    # Launch the extension
    launcher_script = Path('launch_urashg_uv.py')
    if launcher_script.exists():
        result = run_command(['uv', 'run', 'python', str(launcher_script)])
    else:
        # Fallback to original launcher
        result = run_command(['uv', 'run', 'python', 'launch_urashg_extension.py'])

    return result and result.returncode == 0

def run_tests(args):
    """Run the test suite."""
    print_header("Running Tests")

    if not check_uv_installed():
        return False

    # Build pytest command
    cmd = ['uv', 'run', 'pytest']

    if args.coverage:
        cmd.extend(['--cov=pymodaq_plugins_urashg', '--cov-report=term-missing'])

    if args.verbose:
        cmd.append('-v')

    if args.filter:
        cmd.extend(['-k', args.filter])

    if args.hardware:
        cmd.extend(['-m', 'hardware'])
    elif args.unit:
        cmd.extend(['-m', 'unit'])

    # Add test directory
    cmd.append('tests/')

    result = run_command(cmd, "Running tests")
    return result and result.returncode == 0

def clean_environment():
    """Clean the environment and caches."""
    print_header("Cleaning Environment")

    # Remove virtual environment
    venv_path = Path('.venv')
    if venv_path.exists():
        print_info("Removing virtual environment...")
        shutil.rmtree(venv_path)
        print_success("Virtual environment removed")

    # Clean UV cache
    if check_uv_installed():
        run_command(['uv', 'cache', 'clean'], "Cleaning UV cache")

    # Remove Python cache files
    print_info("Removing Python cache files...")
    for path in Path('.').rglob('__pycache__'):
        shutil.rmtree(path)
    for path in Path('.').rglob('*.pyc'):
        path.unlink()

    print_success("Environment cleaned")

def show_status():
    """Show environment status."""
    print_header("Environment Status")

    # UV version
    if check_uv_installed():
        result = run_command(['uv', '--version'], capture_output=True)
        if result:
            print_success(f"UV: {result.stdout.strip()}")

    # Python version
    python_version_file = Path('.python-version')
    if python_version_file.exists():
        version = python_version_file.read_text().strip()
        print_success(f"Python version (pinned): {version}")

    # Virtual environment
    venv_path = Path('.venv')
    if venv_path.exists():
        print_success("Virtual environment: Present")

        # Python executable
        result = run_command(['uv', 'run', 'python', '--version'], capture_output=True, check=False)
        if result and result.returncode == 0:
            print_success(f"Python executable: {result.stdout.strip()}")

        # PyMoDAQ status
        result = run_command(['uv', 'run', 'python', '-c', 'import pymodaq; print(f"PyMoDAQ {pymodaq.__version__}")'],
                           capture_output=True, check=False)
        if result and result.returncode == 0:
            print_success(f"PyMoDAQ: {result.stdout.strip()}")
        else:
            print_warning("PyMoDAQ: Not installed")

        # Package count
        result = run_command(['uv', 'pip', 'list'], capture_output=True, check=False)
        if result and result.returncode == 0:
            package_count = len(result.stdout.strip().split('\n')) - 2  # Subtract header lines
            print_success(f"Installed packages: {package_count}")
    else:
        print_warning("Virtual environment: Not found")

    # Lock file
    lock_file = Path('uv.lock')
    if lock_file.exists():
        print_success("Dependency lock file: Present")
    else:
        print_warning("Dependency lock file: Missing")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="UV management script for μRASHG microscopy extension",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_uv.py setup                    # Initial setup
  python manage_uv.py install --hardware      # Install with hardware deps
  python manage_uv.py launch                  # Launch extension
  python manage_uv.py test --coverage         # Run tests with coverage
  python manage_uv.py clean                   # Clean environment
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup command
    subparsers.add_parser('setup', help='Initial project setup')

    # Install command
    install_parser = subparsers.add_parser('install', help='Install dependencies')
    install_parser.add_argument('--hardware', action='store_true', help='Install hardware dependencies')
    install_parser.add_argument('--pyrpl', action='store_true', help='Install PyRPL dependencies')
    install_parser.add_argument('--dev', action='store_true', help='Install development dependencies')
    install_parser.add_argument('--all', action='store_true', help='Install all optional dependencies')
    install_parser.add_argument('--upgrade', action='store_true', help='Upgrade dependencies')

    # Launch command
    subparsers.add_parser('launch', help='Launch μRASHG extension')

    # Test command
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('--coverage', action='store_true', help='Run with coverage')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    test_parser.add_argument('--filter', '-k', help='Filter tests by keyword')
    test_parser.add_argument('--hardware', action='store_true', help='Run hardware tests only')
    test_parser.add_argument('--unit', action='store_true', help='Run unit tests only')

    # Clean command
    subparsers.add_parser('clean', help='Clean environment and caches')

    # Status command
    subparsers.add_parser('status', help='Show environment status')

    # Help command
    subparsers.add_parser('help', help='Show help')

    args = parser.parse_args()

    if not args.command or args.command == 'help':
        parser.print_help()
        return 0

    # Execute command
    success = False

    if args.command == 'setup':
        success = setup_project()
    elif args.command == 'install':
        success = install_dependencies(args)
    elif args.command == 'launch':
        success = launch_extension()
    elif args.command == 'test':
        success = run_tests(args)
    elif args.command == 'clean':
        clean_environment()
        success = True
    elif args.command == 'status':
        show_status()
        success = True

    return 0 if success else 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
