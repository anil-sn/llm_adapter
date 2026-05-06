"""
LLM Adapter Main Entry Point

Main entry point for running the LLM Adapter gateway server.

Usage:
    python -m llm_adapter.main

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from llm_adapter.gateway.server import app, logger


def main():
    """Main entry point for the orchestrator."""
    import uvicorn
    from llm_adapter.utils.config_loader import load_config
    
    # Load configuration
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    config = load_config(project_root=PROJECT_ROOT, validate=False)
    
    port = config.get("cluster", {}).get("gateway_port", 8000)
    
    logger.info(f"Starting LLM Adapter Gateway on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
