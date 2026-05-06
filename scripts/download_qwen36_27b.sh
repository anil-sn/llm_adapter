#!/bin/bash
# Download Qwen 3.6 27B AWQ model

set -e

MODEL_ID="cyankiwi/Qwen3.6-27B-AWQ-4bit"

echo "Downloading ${MODEL_ID}..."
echo "This will download ~14-16GB"
echo ""

python3 << 'EOF'
from huggingface_hub import snapshot_download
import os

model_id = "cyankiwi/Qwen3.6-27B-AWQ-4bit"

print(f"Starting download of {model_id}")

try:
    cache_dir = snapshot_download(
        repo_id=model_id,
        cache_dir=os.path.expanduser("~/.cache/huggingface/hub"),
        resume_download=True,
        local_files_only=False,
        max_workers=4  # Parallel downloads
    )
    print(f"\n✓ SUCCESS: Model downloaded to: {cache_dir}")
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    exit(1)
EOF

echo ""
echo "Download complete!"
echo ""
echo "Now start the LLM with:"
echo "  LLM_CONFIG=config/config-qwen36-27b.yaml python3 scripts/setup/llm_manager.py start"
