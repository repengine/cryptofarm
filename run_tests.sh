#!/bin/bash
# Script to run tests without Poetry's venv issue

# Set up the environment
export PATH=~/.local/bin:$PATH
export PYTHONPATH=/home/nate/projects/cryptofarm/src

# Run pytest with Poetry but suppress the venv error
poetry run pytest "$@" 2>&1 | grep -v "The virtual environment found in .*/airdrops/venv seems to be broken" | grep -v "Recreating virtualenv"