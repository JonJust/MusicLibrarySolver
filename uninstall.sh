#!/bin/bash
set -e  # Stop script on error

PACKAGE_NAME="music_stats"

echo "Uninstalling $PACKAGE_NAME..."
pip uninstall -y $PACKAGE_NAME

echo "Checking for remaining installed CLI scripts..."
BIN_PATH=$(which cue-splitter || true)

if [ -n "$BIN_PATH" ]; then
    echo "Removing CLI commands manually..."
    rm -f $(which cue-splitter) $(which music-stats)
fi

echo "Cleaning up build artifacts..."
rm -rf build dist *.egg-info

echo "Uninstallation complete."
