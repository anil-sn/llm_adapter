#!/usr/bin/env bash
# Control the four-model small fleet defined in config/model-fleet-small-4gpu.yaml.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
MANAGER="${PROJECT_DIR}/scripts/setup/llm_manager.py"
FLEET="config/model-fleet-small-4gpu.yaml"
ACTION="${1:-start}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing virtual environment: ${PYTHON_BIN}" >&2
  exit 1
fi

case "${ACTION}" in
  start)
    exec "${PYTHON_BIN}" "${MANAGER}" start-multi --fleet "${FLEET}"
    ;;
  stop)
    exec "${PYTHON_BIN}" "${MANAGER}" stop-multi --fleet "${FLEET}"
    ;;
  restart)
    "${PYTHON_BIN}" "${MANAGER}" stop-multi --fleet "${FLEET}"
    exec "${PYTHON_BIN}" "${MANAGER}" start-multi --fleet "${FLEET}"
    ;;
  status)
    exec "${PYTHON_BIN}" "${MANAGER}" status-multi --fleet "${FLEET}"
    ;;
  *)
    echo "Usage: $(basename "$0") {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
