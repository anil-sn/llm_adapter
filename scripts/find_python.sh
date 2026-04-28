#!/bin/bash

echo "Searching for Python installations..."
echo ""

# Check common Python versions
for version in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v $version &> /dev/null; then
        PY_VERSION=$($version --version 2>&1)
        PY_PATH=$(which $version)
        echo "✓ Found: $version"
        echo "  Version: $PY_VERSION"
        echo "  Path: $PY_PATH"
        echo ""
    fi
done

# Check pyenv if installed
if command -v pyenv &> /dev/null; then
    echo "pyenv is installed:"
    pyenv versions
    echo ""
fi

# Check deadsnakes PPA
if [ -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-*.list ]; then
    echo "✓ deadsnakes PPA is configured"
    echo "  Available Python versions:"
    apt-cache search python3.1[0-9] | grep "^python3.1[0-9] " | awk '{print "  - "$1}'
else
    echo "deadsnakes PPA not configured"
fi
