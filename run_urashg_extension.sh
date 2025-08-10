#!/bin/bash

# μRASHG Microscopy Extension - Shell Launcher
# This script ensures the correct Python environment is used

echo "=============================================================================="
echo "μRASHG Microscopy Extension - Shell Launcher"
echo "=============================================================================="
echo "Using Python 3.12 environment with PyMoDAQ 5.1.0a0"
echo "=============================================================================="
echo ""

# Set the correct Python interpreter
PYTHON_EXEC="/home/maitai/miniforge3/bin/python"

# Check if Python executable exists
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "❌ ERROR: Python executable not found at $PYTHON_EXEC"
    echo "Please check your PyMoDAQ installation path."
    exit 1
fi

# Display Python version
echo "🐍 Python version:"
$PYTHON_EXEC --version
echo ""

# Check PyMoDAQ availability
echo "🔍 Checking PyMoDAQ installation..."
if $PYTHON_EXEC -c "import pymodaq; print(f'✅ PyMoDAQ {pymodaq.__version__} found')" 2>/dev/null; then
    echo ""
else
    echo "❌ ERROR: PyMoDAQ not found in this Python environment"
    echo "Please install PyMoDAQ: pip install pymodaq"
    exit 1
fi

# Launch the extension
echo "🚀 Launching μRASHG Extension..."
echo "Note: This bypasses PyMoDAQ's extension discovery bug in version 5.1.0a0"
echo ""

# Run the launcher with proper error handling
if $PYTHON_EXEC launch_urashg_extension.py; then
    echo ""
    echo "✅ Extension launched successfully"
else
    exit_code=$?
    echo ""
    echo "⚠️  Extension exited with code: $exit_code"
    echo "This may be normal if you closed the GUI window."
fi

echo ""
echo "=============================================================================="
echo "μRASHG Extension Session Complete"
echo "=============================================================================="
