#!/bin/bash
# Compile and install vLLM from git source with specific branch/tag
# Usage: bash scripts/compile_vllm_from_git.sh [branch|tag|latest]
# Default: main
# Examples:
#   bash scripts/compile_vllm_from_git.sh           # main branch
#   bash scripts/compile_vllm_from_git.sh latest    # latest release tag
#   bash scripts/compile_vllm_from_git.sh v0.29.0rc4  # specific tag

set -e

# Parse arguments
REQUESTED="${1:-main}"
BUILD_DIR="/tmp/vllm-build"

echo "========================================="
echo "vLLM Git Compilation"
echo "========================================="
echo
echo "Requested: $REQUESTED"
echo "Build directory: $BUILD_DIR"
echo

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ ERROR: No virtual environment activated"
    echo "  Please activate venv first: source .venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"
echo

# Detect pip command (prefer uv if available)
if command -v uv &> /dev/null; then
    PIP_CMD="uv pip"
    echo "Using uv for package management"
else
    PIP_CMD="python -m pip"
    echo "Using pip for package management"
fi
echo

# Show current vLLM version
echo "Current vLLM version:"
$PIP_CMD show vllm | grep Version || echo "Not installed"
echo

# Verify CUDA availability
echo "Checking CUDA..."
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | cut -d',' -f1)
    echo "✓ CUDA: $CUDA_VERSION"
    export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
else
    if [ -z "$CUDA_HOME" ]; then
        echo "❌ ERROR: nvcc not found and CUDA_HOME not set"
        echo "  Please set CUDA_HOME to your CUDA installation directory"
        echo "  Example: export CUDA_HOME=/usr/local/cuda"
        exit 1
    else
        echo "⚠ WARNING: nvcc not found, using CUDA_HOME=$CUDA_HOME"
    fi
fi
echo

# Confirm before proceeding
read -p "Continue with git compilation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Clone or update repository
echo "========================================="
echo "Step 1: Fetching vLLM source"
echo "========================================="
echo

if [ -d "$BUILD_DIR/.git" ]; then
    echo "Updating existing clone..."
    cd "$BUILD_DIR"
    git fetch origin --tags
else
    echo "Cloning vLLM repository..."
    rm -rf "$BUILD_DIR"
    git clone https://github.com/vllm-project/vllm.git "$BUILD_DIR"
    cd "$BUILD_DIR"
    git fetch origin --tags
fi

# Resolve "latest" to actual latest tag
if [ "$REQUESTED" = "latest" ]; then
    echo
    echo "Finding latest release tag..."
    BRANCH=$(git tag -l "v*" | grep -E "^v[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$" | sort -V | tail -1)
    if [ -z "$BRANCH" ]; then
        echo "❌ ERROR: No release tags found"
        exit 1
    fi
    echo "✓ Latest tag: $BRANCH"
else
    BRANCH="$REQUESTED"
fi

# Validate and checkout
if git show-ref --verify --quiet "refs/tags/$BRANCH"; then
    # It's a tag
    echo "Checking out tag: $BRANCH"
    git checkout "$BRANCH"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
    # It's a branch
    echo "Checking out branch: $BRANCH"
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    echo "❌ ERROR: '$BRANCH' is not a valid branch or tag on remote"
    exit 1
fi

COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=format:"%s")
echo
echo "✓ Repository ready"
echo "  Target: $BRANCH"
echo "  Commit: $COMMIT_HASH - $COMMIT_MSG"
echo

# Step 2: Uninstall existing vLLM
echo "========================================="
echo "Step 2: Removing existing vLLM"
echo "========================================="
echo

$PIP_CMD uninstall -y vllm || true
echo "✓ Existing vLLM uninstalled"
echo

# Step 3: Set build environment
echo "========================================="
echo "Step 3: Configuring build environment"
echo "========================================="
echo

export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.0;8.6;8.9;9.0}"
export MAX_JOBS="${MAX_JOBS:-$(nproc)}"
export VLLM_TARGET_DEVICE="${VLLM_TARGET_DEVICE:-cuda}"

echo "Build configuration:"
echo "  CUDA_HOME: $CUDA_HOME"
echo "  TORCH_CUDA_ARCH_LIST: $TORCH_CUDA_ARCH_LIST"
echo "  MAX_JOBS: $MAX_JOBS"
echo "  VLLM_TARGET_DEVICE: $VLLM_TARGET_DEVICE"
echo

# Step 4: Install build dependencies
echo "========================================="
echo "Step 4: Installing build dependencies"
echo "========================================="
echo

$PIP_CMD install --upgrade pip setuptools wheel ninja packaging cmake
echo "✓ Build dependencies installed"
echo

# Step 5: Build and install vLLM
echo "========================================="
echo "Step 5: Building vLLM from source"
echo "========================================="
echo
echo "⏱️  This may take 10-15 minutes..."
echo

cd "$BUILD_DIR"
$PIP_CMD install --no-build-isolation -v -e .

echo
echo "✓ vLLM built and installed"
echo

# Step 6: Verify installation
echo "========================================="
echo "Step 6: Verifying installation"
echo "========================================="
echo

if ! VLLM_VERSION=$(python -c "import vllm; print(vllm.__version__)" 2>&1); then
    echo "❌ ERROR: Failed to import vLLM"
    echo "$VLLM_VERSION"
    exit 1
fi
echo "✓ vLLM version: $VLLM_VERSION"

if python -c "import vllm; import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>&1 | grep -q "True"; then
    echo "✓ CUDA available"
else
    echo "⚠ WARNING: CUDA not available in Python/PyTorch"
fi
echo

# Step 7: Summary
echo "========================================="
echo "✅ Compilation Complete!"
echo "========================================="
echo
echo "Installed:"
echo "  Version: $VLLM_VERSION"
echo "  Target: $BRANCH ($COMMIT_HASH)"
echo "  Build dir: $BUILD_DIR (kept for development)"
echo
echo "To rebuild with latest changes:"
echo "  bash scripts/compile_vllm_from_git.sh $REQUESTED"
echo
echo "To rebuild manually:"
if git show-ref --verify --quiet "refs/tags/$BRANCH"; then
    echo "  cd $BUILD_DIR && git fetch --tags && git checkout $BRANCH && pip install --no-build-isolation -e ."
else
    echo "  cd $BUILD_DIR && git pull origin $BRANCH && pip install --no-build-isolation -e ."
fi
echo
echo "To clean up build directory:"
echo "  rm -rf $BUILD_DIR"
echo
