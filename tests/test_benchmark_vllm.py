"""Regression tests for reasoning-model benchmark stream accounting."""

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parent.parent / "scripts" / "benchmark_vllm.py"
SPEC = importlib.util.spec_from_file_location("benchmark_vllm", SCRIPT)
benchmark_vllm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark_vllm)


def test_stream_chunk_fields_counts_reasoning_and_final_usage():
    reasoning_chunk = {
        "choices": [{"delta": {"reasoning": "thinking"}}],
    }
    content, reasoning, completion_tokens, prompt_tokens = benchmark_vllm.VLLMBenchmark._stream_chunk_fields(reasoning_chunk)
    assert content == ""
    assert reasoning == "thinking"
    assert completion_tokens is None
    assert prompt_tokens is None

    usage_chunk = {
        "choices": [],
        "usage": {"prompt_tokens": 42, "completion_tokens": 128},
    }
    content, reasoning, completion_tokens, prompt_tokens = benchmark_vllm.VLLMBenchmark._stream_chunk_fields(usage_chunk)
    assert content == ""
    assert reasoning == ""
    assert completion_tokens == 128
    assert prompt_tokens == 42
