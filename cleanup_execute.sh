#!/bin/bash
# LLM Adapter Cleanup Script
# Removes ~41 outdated/redundant files
# KEEPS: All configs (including unused ones per user request)

set -e

echo "🧹 Starting cleanup..."
echo ""

# Count files before
BEFORE=$(find . -type f | wc -l)

# Remove old documentation (root level)
echo "📄 Removing old documentation..."
rm -f CLEANUP_SUMMARY.md
rm -f QWEN36_DEPLOYMENT.md
rm -f VLLM_CUDA_COMPATIBILITY.md
rm -f CODE_OF_CONDUCT.md
rm -f CONTRIBUTING.md
rm -f "~"  # Backup file

# Remove docs/ subdirectory old files
echo "📚 Cleaning docs/ directory..."
rm -f docs/PHASE0_TEST_PLAN.md
rm -f docs/README_TESTING.md
rm -f docs/README_V3_EXTREME.md
rm -f docs/REORGANIZATION.md
rm -f docs/CLAUDE_CODE_COMPATIBILITY_FIXES.md
rm -f docs/CLAUDE_CODE_SETUP.md
rm -f docs/CLAUDE.md
rm -f docs/API_COMPLIANCE_REVIEW.md

# NOTE: Keeping all config files per user request
echo "⚙️  Keeping all config files (per user request)..."
# NOT deleting: config-qwen.yaml, config-qwen-1m.yaml, config-nemotron.yaml, config-emergency-4k.yaml

# Remove deprecated code
echo "🗑️  Removing archive/deprecated..."
rm -rf archive/

# Remove setup scripts (one-time use, complete)
echo "🔧 Removing one-time setup scripts..."
rm -f scripts/setup/install_nvidia_driver.sh
rm -f scripts/setup/install_nvidia_from_source.sh
rm -f scripts/setup/upgrade_nvidia_driver.sh
rm -f scripts/setup/test_cuda_install.sh
rm -f scripts/setup/test_nvidia_prerequisites.sh
rm -f scripts/setup/setup_claude_code_cli.sh
rm -f scripts/setup/validate_claude_code_cli.sh
rm -f scripts/setup/fix_paths_after_reorganization.sh
rm -f scripts/setup/download_reasoning_parser.sh
rm -f scripts/setup/run_claude_adapter.py

# Remove redundant test scripts
echo "🧪 Removing redundant test scripts..."
rm -rf scripts/testing/
rm -f scripts/test_deepseek_phase0.py
rm -f scripts/run_phase0_test.sh

# Remove old utility scripts
echo "🛠️  Removing old utility scripts..."
rm -f scripts/cleanup.sh
rm -f scripts/cleanup_project.py
rm -f scripts/switch_model.sh
rm -f scripts/find_python.sh
rm -f scripts/install_python312.sh
rm -f scripts/install_python312_pyenv.sh
rm -f scripts/setup_venv.sh
rm -f scripts/run_tests.sh
rm -f scripts/check_system_compatibility.sh

# Remove superseded tests
echo "🔬 Removing old test files..."
rm -f tests/test_config_system.py
rm -f tests/test_qwen_adapter.py

# Remove empty/unused directories
echo "📁 Removing empty directories..."
rmdir adapters 2>/dev/null || echo "   (adapters directory not empty or doesn't exist)"
rmdir tests 2>/dev/null || echo "   (tests directory not empty or doesn't exist)"

# Count files after
AFTER=$(find . -type f | wc -l)
REMOVED=$((BEFORE - AFTER))

echo ""
echo "✅ Cleanup complete!"
echo "   Files before: $BEFORE"
echo "   Files after:  $AFTER"
echo "   Files removed: $REMOVED"
echo ""
echo "📦 Remaining structure:"
find . -maxdepth 2 -type d | grep -v ".venv" | grep -v ".git" | grep -v "__pycache__" | sort
