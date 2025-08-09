#!/bin/bash

# Complete quality check script for the RAG system
# This script runs formatting, linting, and tests

set -e

echo "🚀 Running complete code quality pipeline..."

# Run formatting
echo "🔧 Step 1: Formatting code..."
./scripts/format.sh

# Run linting
echo "🔍 Step 2: Running linting checks..."
./scripts/lint.sh

# Run tests
echo "🧪 Step 3: Running tests..."
uv run pytest backend/tests/ -v

echo "✅ All quality checks passed! Code is ready for commit."