# LLM Adapter - Makefile
# Common commands for development and deployment

.PHONY: help install install-dev install-tools test test-comprehensive clean start stop status

# Default target
help:
	@echo "LLM Adapter - Available Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install core dependencies"
	@echo "  make install-dev      Install with dev dependencies"
	@echo "  make install-tools    Install with tool calling support"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run basic tests"
	@echo "  make test-comprehensive  Run comprehensive tool calling tests"
	@echo ""
	@echo "LLM Management:"
	@echo "  make start            Start the LLM (Qwen 27B)"
	@echo "  make stop             Stop the LLM"
	@echo "  make status           Check LLM status"
	@echo ""
	@echo "Development:"
	@echo "  make lint             Run code linter (ruff)"
	@echo "  make format           Format code (ruff)"
	@echo "  make clean            Clean build artifacts"
	@echo ""
	@echo "Quick Start:"
	@echo "  make install-tools && make start"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-tools:
	pip install -e ".[tools]"

install-all:
	pip install -e ".[dev,tools]"

# Testing
test:
	pytest tests/ -v

test-comprehensive:
	python tests/test_tool_calling_comprehensive.py

test-cov:
	pytest tests/ -v --cov=src/llm_adapter --cov-report=html

# LLM Management
start:
	@echo "Starting LLM (Qwen 3.6 27B)..."
	LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start

stop:
	@echo "Stopping LLM..."
	python scripts/setup/llm_manager.py stop

status:
	@echo "Checking LLM status..."
	python scripts/setup/llm_manager.py status

# Code Quality
lint:
	ruff check src/ tests/ examples/

format:
	ruff format src/ tests/ examples/

check:
	mypy src/

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/ dist/ build/

# Example runs
example-tools:
	python examples/tool_calling_example.py

# Quick test
quick-test:
	@echo "Testing API connection..."
	@curl -s http://localhost:8888/v1/models | python -m json.tool || echo "❌ API not running. Run 'make start' first."

# Full setup from scratch
setup:
	@echo "=== Full Setup ==="
	@echo "1. Installing dependencies..."
	$(MAKE) install-all
	@echo ""
	@echo "2. Setting up environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file"; fi
	@echo ""
	@echo "3. Ready! Next steps:"
	@echo "   - Edit .env if needed"
	@echo "   - Run 'make start' to start the LLM"
	@echo "   - Run 'make test' to verify installation"
