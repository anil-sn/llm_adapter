"""Custom reasoning parser for Muse-Glimmer models.

Muse-Glimmer uses custom thinking markers instead of standard <|begin_of_thought|>:
- Thinking start: <|start|>assistant to=self<|message|>
- Thinking end: <|eom|>
- Content: <|start|>assistant<|message|>
- Content end: <|eot|>
"""

from vllm.reasoning.abs_reasoning_parsers import ReasoningParser


class MuseGlimmerReasoningParser(ReasoningParser):
    """Parser for Muse-Glimmer reasoning format."""

    reasoning_start_str = "<|start|>assistant to=self<|message|>"
    reasoning_end_str = "<|eom|>"

    def __init__(self, tokenizer=None):
        super().__init__(tokenizer)

    @classmethod
    def parser_name(cls) -> str:
        return "muse_glimmer"
