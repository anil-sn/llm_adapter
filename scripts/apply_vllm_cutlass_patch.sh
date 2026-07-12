#!/bin/bash
#
# Apply vLLM patch for Cutlass FP8 weight_loader attribute double-assignment typo
# This script is idempotent - safe to run multiple times
#

set -euo pipefail

# Resolve script's directory and then project root (one level up)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

VLLM_CUTLASS_FILE=".venv/lib/python3.12/site-packages/vllm/model_executor/kernels/linear/scaled_mm/cutlass.py"
SOURCE_CUTLASS_FILE="/tmp/vllm-build/vllm/vllm/model_executor/kernels/linear/scaled_mm/cutlass.py"
PATCH_MARKER="# PATCH APPLIED: Cutlass FP8 weight_scale_name weight_loader fix"

patch_file() {
    local target_file="$1"
    local desc="$2"

    echo "[Patch] Checking $desc file at: $target_file"

    if [ ! -f "$target_file" ]; then
        echo "[Patch] File not found. Skipping."
        return 0
    fi

    # Check if already patched
    if grep -q "$PATCH_MARKER" "$target_file"; then
        echo "[Patch] Already applied to $desc. Skipping."
        return 0
    fi

    echo "[Patch] Backing up original $desc file..."
    cp "$target_file" "${target_file}.backup.$(date +%Y%m%d_%H%M%S)"

    echo "[Patch] Applying Cutlass FP8 weight_loader fix to $desc..."

    # Apply the patch using Python to ensure correct line handling
    python3 - "$target_file" << 'EOF'
import sys
import re

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    content = f.read()

# Add patch marker
patch_marker = "# PATCH APPLIED: Cutlass FP8 weight_scale_name weight_loader fix\n"

# Locate the typo block:
#            replace_parameter(layer, weight_scale_name, padded_scale.data)
#            set_weight_attrs(
#                getattr(layer, weight_name),
#                {
#                    "weight_loader": self.padded_weight_loader,
#                },
#            )

old_pattern = r'(\s+replace_parameter\(layer, weight_scale_name, padded_scale\.data\)\s+set_weight_attrs\(\s+getattr\(layer, )weight_name(\),\s+\{\s+"weight_loader": self\.padded_weight_loader,\s+\},\s+\))'

new_content, count = re.subn(old_pattern, r'\1weight_scale_name\2', content)

if count == 0:
    print(f"[Error] Typo pattern not found in {file_path}! Checking if already patched...")
    # Verify if it was already modified manually
    if "getattr(layer, weight_scale_name)" in content and "padded_scale.data" in content:
        print("[Patch] It seems already corrected.")
    else:
        raise ValueError(f"Could not find the target pattern to patch in {file_path}")
else:
    # Add patch marker at the top of the file
    new_content = patch_marker + new_content
    with open(file_path, 'w') as f:
        f.write(new_content)
    print(f"[Patch] Successfully patched {count} occurrence(s) in {file_path}")

EOF

    echo "[Patch] Patch applied successfully to $desc!"
}

# 1. Patch virtual environment file
patch_file "$VLLM_CUTLASS_FILE" "vLLM VirtualEnv package"

# 2. Patch source build file (so future compiles also have the fix)
patch_file "$SOURCE_CUTLASS_FILE" "vLLM Source build"
