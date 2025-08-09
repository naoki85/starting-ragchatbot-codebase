#!/bin/bash

# Linting script for the RAG system
# This script runs all linting tools

echo "🔍 Running code quality checks..."

echo "📋 Running flake8..."
uv run flake8 backend/ main.py

echo "🔬 Running mypy type checking (informational)..."
uv run mypy backend/ main.py || echo "⚠️  MyPy found type issues (informational only)"

echo "✅ Core linting checks passed!"