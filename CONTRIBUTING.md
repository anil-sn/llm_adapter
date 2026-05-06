# Contributing to LLM Adapter

Thank you for your interest in contributing to LLM Adapter! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to maintain a welcoming and inclusive community.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- NVIDIA GPU with 80GB+ VRAM (for Nemotron-3 Super 120B)
- CUDA 12.1 or higher
- `uv` package manager (recommended) or pip

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter

# Install dependencies
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Project Structure

```
llm_adapter/
├── src/llm_adapter/    # Main source code
├── tests/                    # Test suite
├── scripts/                  # Management scripts
├── config/                   # Configuration files
├── docs/                     # Documentation
└── archive/                  # Deprecated code
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### 2. Make Changes

- Follow coding standards (see below)
- Add tests for new features
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
python test_all.py

# Run specific test file
python tests/unit/test_adapter_unit.py

# Run quick test suite
python test_all.py --quick
```

### 4. Commit Changes

Use conventional commit messages:

```bash
git commit -m "feat: add new adapter for X"
git commit -m "fix: resolve issue with Y"
git commit -m "docs: update README with Z"
git commit -m "test: add tests for W"
```

### Commit Message Format

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Build process or auxiliary tool changes

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) for code style
- Use [PEP 257](https://pep257.org/) for docstrings
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)

### Docstring Format

All public modules, functions, classes, and methods must have docstrings:

```python
"""
Module description.

Author: Anil Srirangapatna Nagesh
Version: 1.0
Created: 2026-04-27
"""

def function_name(param1: str, param2: int) -> bool:
    """
    Function description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When description
    """
```

### Type Hints

Use type hints for all function parameters and return values:

```python
from typing import Any, Dict, List, Optional

def process_data(
    data: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ...
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately

```python
import logging

logger = logging.getLogger(__name__)

def process_request(request: dict) -> dict:
    try:
        # Process request
        return result
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
```

## Testing

### Test Structure

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- End-to-end tests: `tests/e2e/`

### Writing Tests

```python
import pytest

def test_example_function():
    """Test description."""
    result = example_function()
    assert result == expected_value
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=llm_adapter

# Specific test file
pytest tests/unit/test_example.py

# Verbose output
pytest -v
```

## Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Update documentation if needed
3. Add tests for new features
4. Follow coding standards
5. Squash unnecessary commits

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Test update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new features
- [ ] No new warnings

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed code
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Tests pass
```

## Documentation

### Updating Documentation

- Update README.md for user-facing changes
- Add or update docstrings for code changes
- Update docs/ for architectural changes
- Add examples for new features

### Documentation Style

- Use clear, concise language
- Include code examples
- Document edge cases
- Keep it up-to-date

## Questions?

If you have questions, please open an issue or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
