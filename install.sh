#!/bin/bash

# DataDog Analyser Installation Script
# This script sets up the DataDog analyser with a virtual environment

set -e  # Exit on any error

echo "========================================="
echo "DataDog Analyser Installation Script"
echo "========================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Found Python $python_version"

# Check if version is 3.8 or higher
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Error: Python 3.8 or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "📁 Working in: $SCRIPT_DIR"

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

python3 -m venv venv
echo "✅ Virtual environment created"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "🔧 Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Install test dependencies
echo "🔧 Installing test dependencies..."
pip install -r test_requirements.txt
echo "✅ Test dependencies installed"

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x main.py
chmod +x run_tests.py
echo "✅ Scripts made executable"

# Run a quick test
echo "🔧 Running quick test..."
python main.py --help > /dev/null
echo "✅ Quick test passed"

echo ""
echo "========================================="
echo "✅ Installation Complete!"
echo "========================================="
echo ""
echo "To use the DataDog analyser:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the analyser:"
echo "   python main.py --scan-dir /Users/pratik/dev/ccm"
echo ""
echo "3. To run tests:"
echo "   python run_tests.py"
echo ""
echo "4. To deactivate virtual environment when done:"
echo "   deactivate"
echo ""
echo "For help and usage examples:"
echo "   python main.py --help"
echo ""
echo "Report location: ./reports/datadog_analysis_report.html"
echo "========================================="