#!/bin/bash

# Code formatting script for the RAG system
# This script runs all code formatting tools in the correct order

set -e

echo "🔧 Running code quality checks and formatting..."

echo "📝 Formatting code with Black..."
uv run black backend/ main.py

echo "📦 Sorting imports with isort..."
uv run isort backend/ main.py

echo "✅ Code formatting complete!"