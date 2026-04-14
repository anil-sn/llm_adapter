#!/bin/bash
# clean.sh - Remove all Python cache files and logs

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🧹 Cleaning: $BASE_DIR"

# Remove .pyc files
find "$BASE_DIR" -name "*.pyc" -delete
echo "✅ Removed .pyc files"

# Remove __pycache__ directories
find "$BASE_DIR" -type d -name "__pycache__" -exec rm -rf {} +
echo "✅ Removed __pycache__ directories"

# Remove .pyo files
find "$BASE_DIR" -name "*.pyo" -delete
echo "✅ Removed .pyo files"

# Remove .pyd files (Windows)
find "$BASE_DIR" -name "*.pyd" -delete
echo "✅ Removed .pyd files"

# Remove compiled .pyc in .ruff_cache or similar
rm -rf "$BASE_DIR/.ruff_cache"
rm -rf "$BASE_DIR/.mypy_cache"
rm -rf "$BASE_DIR/.pytest_cache"
echo "✅ Removed test/lint caches"

# Remove old logs
find "$BASE_DIR" -name "*.log" -delete
rm -rf "$BASE_DIR/logs"
echo "✅ Removed old logs"

# Remove stale PID files
find "$BASE_DIR" -name ".*.pid" -delete
echo "✅ Removed stale PID files"

echo "✨ Cleanup complete!"