#!/bin/bash

# This script activates the virtual environment and starts the MCP FastAPI application.

echo "--- Starting Main Control Program ---"

# Activate the virtual environment
source ./venv/bin/activate

# Add the project root to the Python path
export PYTHONPATH=.
uvicorn mcp.main:app --reload --host 0.0.0.0

echo "--- MCP has been shut down. ---"