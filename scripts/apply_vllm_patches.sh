#!/bin/bash
#
# Apply vLLM patches for NVFP4 Marlin FP4 dimension padding
# This script is idempotent - safe to run multiple times
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VLLM_MARLIN_FILE=".venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/utils/marlin_utils_fp4.py"
PATCH_MARKER="# PATCH APPLIED: Marlin FP4 padding fix"

echo "[Patch] Checking vLLM Marlin FP4 file..."

if [ ! -f "$VLLM_MARLIN_FILE" ]; then
    echo "[Error] vLLM file not found: $VLLM_MARLIN_FILE"
    echo "[Error] Is the virtual environment activated?"
    exit 1
fi

# Check if already patched
if grep -q "$PATCH_MARKER" "$VLLM_MARLIN_FILE"; then
    echo "[Patch] Marlin FP4 padding already applied. Skipping."
else
    echo "[Patch] Backing up original file..."
    cp "$VLLM_MARLIN_FILE" "patches/marlin_utils_fp4.py.backup.$(date +%Y%m%d_%H%M%S)"

    echo "[Patch] Applying Marlin FP4 padding fix..."

    # Apply the patch using Python to ensure correct line handling
    python3 << 'EOF'
import re

file_path = ".venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/utils/marlin_utils_fp4.py"

with open(file_path, 'r') as f:
    content = f.read()

# Add patch marker
patch_marker = "# PATCH APPLIED: Marlin FP4 padding fix\n"

# Find the repack_weight function and add padding logic
old_pattern = r'(    # WEIGHT\n    # Repack weights to marlin format\n)(    def repack_weight\(weight: torch\.Tensor, name: str\) -> torch\.Tensor:)'

new_code = r'''\1    # Marlin kernel requires dimensions divisible by 64
    # Pad size_n if needed (similar to FP8 marlin_utils)
    TILE_SIZE = 64

    def pad_to_tile(size):
        """Pad dimension to next multiple of TILE_SIZE"""
        if size % TILE_SIZE == 0:
            return size, 0
        return ((size + TILE_SIZE - 1) // TILE_SIZE) * TILE_SIZE, ((size + TILE_SIZE - 1) // TILE_SIZE) * TILE_SIZE - size

\2'''

content = re.sub(old_pattern, new_code, content)

# Fix the repack_weight function body
old_body = r'''    def repack_weight\(weight: torch\.Tensor, name: str\) -> torch\.Tensor:
        tensor_list = \[\]
        num_shards = 2 if is_act_and_mul else 1
        if "w13" in name:
            size_n, size_k = N \* num_shards, K
        else:
            size_n, size_k = K, N

        assert weight\.shape == \(E, size_n, size_k // 2\)'''

new_body = '''    def repack_weight(weight: torch.Tensor, name: str) -> torch.Tensor:
        tensor_list = []
        num_shards = 2 if is_act_and_mul else 1
        if "w13" in name:
            size_n, size_k = N * num_shards, K
        else:
            size_n, size_k = K, N

        # Pad size_n to tile boundary if needed
        E = weight.shape[0]  # Define E outside conditional
        orig_size_n = size_n
        size_n_padded, padding = pad_to_tile(size_n)

        if padding > 0:
            # Need to pad the weight tensor
            # weight shape: (E, size_n, size_k // 2)
            pad_shape = (E, padding, weight.shape[2])
            pad_tensor = torch.zeros(pad_shape, dtype=weight.dtype, device=weight.device)
            weight_padded = torch.cat([weight, pad_tensor], dim=1)
        else:
            weight_padded = weight

        assert weight_padded.shape[0] == E
        assert weight_padded.shape[1] == size_n_padded
        assert weight_padded.shape[2] == size_k // 2'''

content = re.sub(old_body, new_body, content)

# Fix the loop to use padded weight and size
old_loop = r'''        for i in range\(E\):
            qweight = weight\[i\]\.view\(torch\.int32\)\.T\.contiguous\(\)

            marlin_qweight = ops\.gptq_marlin_repack\(
                b_q_weight=qweight,
                perm=perm,
                size_k=size_k,
                size_n=size_n,'''

new_loop = '''        for i in range(E):
            qweight = weight_padded[i].view(torch.int32).T.contiguous()

            marlin_qweight = ops.gptq_marlin_repack(
                b_q_weight=qweight,
                perm=perm,
                size_k=size_k,
                size_n=size_n_padded,'''

content = re.sub(old_loop, new_loop, content)

# Fix the premute_scales function to use padded dimensions
old_scales = r'''    def premute_scales\(
        scales: torch\.Tensor, g_scales: torch\.Tensor, name: str
    \) -> tuple\[torch\.Tensor, torch\.Tensor\]:
        scales = scales\.to\(param_dtype\)

        tensor_list = \[\]
        num_shards = 2 if is_act_and_mul else 1
        if "w13" in name:
            size_n, size_k = N \* num_shards, K
        else:
            size_n, size_k = K, N

        # All experts share one global_scale'''

new_scales = '''    def premute_scales(
        scales: torch.Tensor, g_scales: torch.Tensor, name: str
    ) -> tuple[torch.Tensor, torch.Tensor]:
        scales = scales.to(param_dtype)

        tensor_list = []
        num_shards = 2 if is_act_and_mul else 1
        if "w13" in name:
            size_n, size_k = N * num_shards, K
        else:
            size_n, size_k = K, N

        # Pad size_n to match weight padding
        size_n_padded, _ = pad_to_tile(size_n)

        # All experts share one global_scale'''

content = re.sub(old_scales, new_scales, content)

# Fix marlin_permute_scales call to use padded size_n
content = re.sub(
    r'marlin_permute_scales\(\s+s=scale,\s+size_k=size_k,\s+size_n=size_n,',
    'marlin_permute_scales(\n                s=scale,\n                size_k=size_k,\n                size_n=size_n_padded,',
    content
)

# Add patch marker at the top
content = patch_marker + content

with open(file_path, 'w') as f:
    f.write(content)

print("[Patch] Successfully applied Marlin FP4 padding fix")
EOF

    echo "[Patch] Patch applied successfully!"
    echo "[Patch] Backup saved in patches/marlin_utils_fp4.py.backup.*"
fi

# -----------------------------------------------------------------------------
# Qwen3.5 & Qwen3.6 Pruned MoE (num_experts_per_layer) Patch
# -----------------------------------------------------------------------------
echo "[Patch] Checking Qwen3.5/Next num_experts_per_layer patches..."

QWEN3_NEXT_FILE=".venv/lib/python3.12/site-packages/vllm/model_executor/models/qwen3_next.py"
QWEN3_5_FILE=".venv/lib/python3.12/site-packages/vllm/model_executor/models/qwen3_5.py"
QWEN_PATCH_MARKER="# PATCH APPLIED: Qwen num_experts_per_layer fix"

# Check if QWEN3_NEXT_FILE is already patched
if ! grep -q "$QWEN_PATCH_MARKER" "$QWEN3_NEXT_FILE"; then
    echo "[Patch] Applying Qwen3_Next num_experts_per_layer fix..."
    cp "$QWEN3_NEXT_FILE" "patches/qwen3_next.py.backup.$(date +%Y%m%d_%H%M%S)"
    python3 -c '
file_path = "'"$QWEN3_NEXT_FILE"'"
with open(file_path, "r") as f:
    content = f.read()

# Replace self.n_routed_experts = config.num_experts with layer-specific logic
old_line = "        self.n_routed_experts = config.num_experts"
new_line = """        # PATCH APPLIED: Qwen num_experts_per_layer fix
        try:
            parts = prefix.split(".")
            layers_idx = parts.index("layers")
            layer_idx = int(parts[layers_idx + 1])
        except (ValueError, IndexError):
            layer_idx = None

        if layer_idx is not None and hasattr(config, "num_experts_per_layer"):
            self.n_routed_experts = config.num_experts_per_layer[layer_idx]
        else:
            self.n_routed_experts = config.num_experts"""

if old_line in content:
    content = content.replace(old_line, new_line, 1)
    with open(file_path, "w") as f:
        f.write(content)
    print("[Patch] Successfully applied qwen3_next.py patch")
else:
    print("[Warning] Could not find target line in qwen3_next.py")
'
fi

# Check if QWEN3_5_FILE is already patched
if ! grep -q "$QWEN_PATCH_MARKER" "$QWEN3_5_FILE"; then
    echo "[Patch] Applying Qwen3_5 num_experts_per_layer load_weights fix..."
    cp "$QWEN3_5_FILE" "patches/qwen3_5.py.backup.$(date +%Y%m%d_%H%M%S)"
    python3 -c '
file_path = "'"$QWEN3_5_FILE"'"
with open(file_path, "r") as f:
    content = f.read()

old_block = """        num_experts = (
            self.config.num_experts if hasattr(self.config, "num_experts") else 0
        )
        for name, loaded_weight in weights:"""

new_block = """        # PATCH APPLIED: Qwen num_experts_per_layer fix
        num_experts = (
            self.config.num_experts if hasattr(self.config, "num_experts") else 0
        )
        for name, loaded_weight in weights:
            # Dynamically determine the correct number of experts for this specific layer parameter
            try:
                parts = name.split(".")
                layers_idx = parts.index("layers")
                layer_idx = int(parts[layers_idx + 1])
            except (ValueError, IndexError):
                layer_idx = None

            if layer_idx is not None and hasattr(self.config, "num_experts_per_layer"):
                num_experts = self.config.num_experts_per_layer[layer_idx]
            else:
                num_experts = (
                    self.config.num_experts if hasattr(self.config, "num_experts") else 0
                )"""

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with open(file_path, "w") as f:
        f.write(content)
    print("[Patch] Successfully applied qwen3_5.py patch")
else:
    print("[Warning] Could not find target block in qwen3_5.py")
'
fi
