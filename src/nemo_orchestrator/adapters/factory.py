import logging
import re
import yaml
from pathlib import Path
from .claude_adapter import ClaudeAdapter
from .openai_adapter import OpenAIAdapter
from .nemotron_adapter import NemotronAdapter

logger = logging.getLogger("adapter-factory")

# Load rules from config
# Project root is 4 levels up: factory.py -> adapters/ -> nemo_orchestrator/ -> src/ -> project/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

if not CONFIG_FILE.exists():
    # Fallback for old structure
    CONFIG_FILE = PROJECT_ROOT / "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)
    RULES = config.get("model_rules", [])
    MAX_CONTEXT = config.get("inference", {}).get("max_model_len", 32768)

def get_adapter(model_id: str) -> OpenAIAdapter:
    """
    Dynamically returns the appropriate adapter instance based on config rules.
    """
    selected_type = "openai" # Default
    
    for rule in RULES:
        pattern = rule.get("pattern", "")
        if re.search(pattern, model_id, re.IGNORECASE):
            selected_type = rule.get("adapter", "openai")
            break

    # Instantiate the selected adapter with context awareness
    if selected_type == "claude":
        adapter = ClaudeAdapter(max_context=MAX_CONTEXT)
    elif selected_type == "nemotron":
        adapter = NemotronAdapter(max_context=MAX_CONTEXT)
    else:
        adapter = OpenAIAdapter(max_context=MAX_CONTEXT)

    logger.info(f"Model: {model_id} | Adapter: {adapter.__class__.__name__}")
    return adapter
