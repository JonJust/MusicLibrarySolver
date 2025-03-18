#!/bin/bash
set -e  # Stop script on error

echo "Installing dependencies..."
pip install --upgrade setuptools wheel

echo "Building the package..."
python setup.py bdist_wheel

echo "Reinstalling the package..."
pip install --force-reinstall dist/*.whl

echo "Installation complete. You can now run 'cue-splitter' and 'music-stats'."
