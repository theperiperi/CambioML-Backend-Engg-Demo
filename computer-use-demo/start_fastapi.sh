#!/bin/bash

# FastAPI Startup Script
# This script starts the FastAPI application locally

set -e

echo "Starting FastAPI Computer Use Demo..."

# Check if we're in the right directory
if [ ! -f "fastapi_app/main.py" ]; then
    echo "Error: Please run this script from the computer-use-demo directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r fastapi_app/requirements.txt

# Install additional dependencies for the computer_use_demo
if [ -f "dev-requirements.txt" ]; then
    echo "Installing development dependencies..."
    pip install -r dev-requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the FastAPI application
echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

cd fastapi_app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 