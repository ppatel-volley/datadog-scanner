#!/usr/bin/env python3
"""Test runner script for DataDog analyser."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Main test runner."""
    print("DataDog Analyser Test Suite")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("WARNING: Not running in a virtual environment!")
        print("It's recommended to run tests in a virtual environment.")
        print("Run: python -m venv venv && source venv/bin/activate")
        print()
    
    # Install test dependencies
    print("Installing test dependencies...")
    install_cmd = [sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"]
    if not run_command(install_cmd, "Installing test dependencies"):
        return 1
    
    # Run basic tests
    test_commands = [
        ([sys.executable, "-m", "pytest", "-v"], "Running all tests"),
        ([sys.executable, "-m", "pytest", "--cov=.", "--cov-report=term-missing"], "Running tests with coverage"),
        ([sys.executable, "-m", "pytest", "test_models.py", "-v"], "Testing models module"),
        ([sys.executable, "-m", "pytest", "test_config.py", "-v"], "Testing config module"),
        ([sys.executable, "-m", "pytest", "test_github_linker.py", "-v"], "Testing GitHub linker module"),
        ([sys.executable, "-m", "pytest", "test_datadog_detector.py", "-v"], "Testing DataDog detector module"),
        ([sys.executable, "-m", "pytest", "test_code_scanner.py", "-v"], "Testing code scanner module"),
    ]
    
    failed_tests = []
    
    for cmd, description in test_commands:
        if not run_command(cmd, description):
            failed_tests.append(description)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    if failed_tests:
        print(f"❌ {len(failed_tests)} test suite(s) failed:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1
    else:
        print("✅ All test suites passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())