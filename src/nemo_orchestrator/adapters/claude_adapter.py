import json
import logging
import uuid
import time
from typing import Any, AsyncGenerator, List, Dict, Union
from .openai_adapter import OpenAIAdapter

logger = logging.getLogger("claude-adapter")

SYSTEM_GUARD_CONTENT = "Respond concisely. No reasoning. No meta-commentary like 'Okay, the user sent...'"

class ClaudeAdapter(OpenAIAdapter):
    """
    Protocol Enforcer Claude Adapter:
    Guarantees Anthropic Messages API compliance via a state-driven emitter.
    """
    def __init__(self, max_context: int = 32768):
        super().__init__(max_context=max_context)
        self.thinking_requested = False
        self.incoming_protocol = "openai"
        self.message_id = f"msg_{uuid.uuid4().hex}"
        self.estimated_input_tokens = 0

    def is_prefill(self, content: str) -> bool:
        prefill_tokens = ['{', '[', '```', '{"', '[{', '<']
        trimmed = str(content).strip()
        return trimmed in prefill_tokens or len(trimmed) <= 2

    def build_request(self, body: dict) -> dict:
        # 1. Budgeting: Clamping with the Enforcer heuristic
        body = self.clamp_max_tokens(body, self.max_context)
        self.thinking_requested = body.get("enable_thinking", False) or body.get("include_thinking", False)

        # Estimate input tokens for message_start (improved heuristic)
        # Count actual message content instead of JSON structure
        messages_text = " ".join([
            str(m.get("content", "")) for m in body.get("messages", [])
        ])
        system_text = str(body.get("system", ""))
        total_text = messages_text + system_text

        # Rough estimate: ~4 chars per token for English text
        # Add 10% for JSON overhead
        self.estimated_input_tokens = int((len(total_text) / 4.0) * 1.1)

        # 2. Protocol Identification
        if body.get("__protocol__") == "anthropic" or "system" in body:
            self.incoming_protocol = "anthropic"

        body.pop("__protocol__", None)

        # 3. Message Normalization (Chat Template Integrity)
        system_input = body.get("system", "")
        messages = body.get("messages", [])

        final_system_parts = []
        def flatten_system(content):
            if isinstance(content, list):
                return " ".join([str(c.get("text", c.get("content", ""))) for c in content if isinstance(c, dict)])
            return str(content)

        if system_input: final_system_parts.append(flatten_system(system_input))

        other_messages = []
        for m in messages:
            if m.get("role") == "system":
                final_system_parts.append(flatten_system(m.get("content", "")))
            else: other_messages.append(m)

        # Validate: messages array cannot be empty (must have at least one user/assistant message)
        if not other_messages:
            raise ValueError("messages: field required")

        if not self.thinking_requested and not any("No reasoning" in p for p in final_system_parts):
            final_system_parts.insert(0, SYSTEM_GUARD_CONTENT)

        openai_messages = []
        if final_system_parts:
            openai_messages.append({"role": "system", "content": "\n".join(final_system_parts)})

        for m in other_messages:
            role = m.get("role")
            content = m.get("content")

            if role == "assistant" and self.is_prefill(content): continue

            if isinstance(content, list):
                text_parts = []
                for block in content:
                    b_type = block.get("type")
                    if b_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif b_type == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id"),
                            "content": str(block.get("content", ""))
                        })
                # Only update content if there are text parts
                if text_parts:
                    m["content"] = " ".join(text_parts)
                else:
                    # Skip this message - it only had tool_result blocks which were already added
                    continue

            if role != "tool":
                openai_messages.append(m)

        # 4. Tool Mapping (for Claude Code CLI compatibility)
        tools = body.get("tools")
        openai_tools = []
        if tools:
            for t in tools:
                if "input_schema" in t:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema")
                        }
                    })
                else: openai_tools.append(t)

        # 5. TokenGuard: Clamp max_tokens to respect model's max_model_len
        requested_max_tokens = body.get("max_tokens", 1024)

        # Adjust estimated tokens for tool definitions overhead (Claude Code CLI sends large tool schemas)
        tool_overhead = len(openai_tools) * 800 if openai_tools else 0  # ~800 tokens per tool definition
        adjusted_input_tokens = self.estimated_input_tokens + tool_overhead

        # Calculate available output space (reserve 30% safety margin for tokenization variance)
        available_output = int((self.max_context - adjusted_input_tokens) * 0.7)
        available_output = max(512, available_output)  # Ensure minimum 512 tokens

        # Clamp to available space
        clamped_max_tokens = min(requested_max_tokens, available_output)

        if clamped_max_tokens < requested_max_tokens:
            logger.warning(
                f"TokenGuard: Clamped max_tokens from {requested_max_tokens} to {clamped_max_tokens} "
                f"(input_est: {self.estimated_input_tokens}, tools_overhead: {tool_overhead}, "
                f"total_est: {adjusted_input_tokens}, context: {self.max_context})"
            )

        return {
            "model": body.get("model"),
            "messages": openai_messages,
            "stream": body.get("stream", False),
            "max_tokens": clamped_max_tokens,
            "temperature": body.get("temperature", 0.7),
            "tools": openai_tools if openai_tools else None,
            "tool_choice": "auto" if openai_tools else None,
            "extra_body": {"enable_thinking": True} if self.thinking_requested else None
        }

    def normalize_response(self, resp: dict) -> dict:
        """Standard JSON response normalization."""
        # Ensure usage invariants
        usage = resp.get("usage") or {}
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or self.estimated_input_tokens
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 1
        usage_obj = {"input_tokens": input_tokens, "output_tokens": output_tokens}

        if "choices" in resp:
            for choice in resp["choices"]:
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or msg.get("thinking") or ""
                had_content = bool(content)

                # If no content but reasoning exists, move it
                if not content and reasoning:
                    content = reasoning
                    msg["content"] = content

                msg.pop("reasoning", None)
                msg.pop("thinking", None)

                # Strip <think>...</think> XML tags if thinking not requested
                if had_content and not self.thinking_requested:
                    import re
                    # Remove <think>...</think> tags and their content
                    content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
                    # Also handle unclosed </think> tags
                    content = re.sub(r'</think>\s*', '', content)

                    # Remove reasoning patterns (aggressive filtering for Nemotron-3)
                    # Pattern 1: "User asks/said..." at start
                    content = re.sub(r'^(The user (asks?|said?|wants?|requests?)|User (asks?|said?)):.*?\n\n', '', content, flags=re.DOTALL)
                    content = re.sub(r'^(The user (asks?|said?|wants?|requests?)|User (asks?|said?)):.*?(?=\n[A-Z0-9])', '', content)

                    # Pattern 2: Remove "We need to..." / "We'll..." / "Let's..." thinking
                    content = re.sub(r'^We (need to|must|should|will|\'ll).*?\.\s*', '', content, flags=re.MULTILINE)
                    content = re.sub(r'^Let\'s.*?\.\s*', '', content, flags=re.MULTILINE)
                    content = re.sub(r'^I (will|\'ll|should|must).*?\.\s*', '', content, flags=re.MULTILINE)

                    # Pattern 3: If starts with meta-commentary, extract just the answer after double newline
                    if re.match(r'^(Okay|Hmm|So|The user|User|We|I will|I\'ll|First)', content):
                        if "\n\n" in content:
                            parts = content.split("\n\n")
                            # Get the last substantial part
                            for part in reversed(parts):
                                if part.strip() and not re.match(r'^(We|I will|I\'ll|Let\'s|The user)', part):
                                    content = part.strip()
                                    break

                    msg["content"] = content.strip()

        if self.incoming_protocol == "anthropic":
            content = []
            stop_reason = "end_turn"

            if "choices" in resp:
                m = resp["choices"][0]["message"]
                choice = resp["choices"][0]

                # Add tool_use blocks
                tool_calls = m.get("tool_calls", [])
                for tc in tool_calls:
                    try: args = json.loads(tc["function"]["arguments"])
                    except: args = {}
                    content.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": args})

                # Add text content ONLY if no tools are present
                # Claude Code CLI has issues when text blocks appear with tool_use
                if not tool_calls and m.get("content"):
                    content.append({"type": "text", "text": m["content"]})

                # Set stop_reason based on finish_reason
                finish_reason = choice.get("finish_reason", "stop")
                if tool_calls or finish_reason == "tool_calls":
                    stop_reason = "tool_use"
                elif finish_reason == "length":
                    stop_reason = "max_tokens"
                elif finish_reason in ["stop", "end_turn"]:
                    stop_reason = "end_turn"

            # Protocol Invariant: Never return empty content
            if not content:
                content = [{"type": "text", "text": " "}]

            return {
                "id": self.message_id,
                "type": "message",
                "role": "assistant",
                "content": content,
                "model": resp.get("model"),
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "usage": usage_obj
            }
        return resp

    async def stream(self, client: Any, target_url: str, request: dict) -> AsyncGenerator[bytes, None]:
        """
        STATE-DRIVEN EMITTER:
        Guarantees the exact SSE sequence required by Anthropic SDKs.
        """
        if self.incoming_protocol != "anthropic":
            async for chunk in super().stream(client, target_url, request): yield chunk
            return

        def sse(event_type, data):
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()

        # STATE 1: message_start
        yield sse("message_start", {
            "type": "message_start",
            "message": {
                "id": self.message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": request.get("model"),
                "usage": {"input_tokens": self.estimated_input_tokens, "output_tokens": 0}
            }
        })

        content_sent = False
        final_usage = {"prompt_tokens": self.estimated_input_tokens, "completion_tokens": 0}
        tool_use_detected = False
        content_block_started = False
        buffered_text_chunks = []  # Buffer text until we know if tools are present

        # Tool call accumulator - maps index to accumulated tool call data
        tool_calls_by_index = {}  # {0: {"id": "...", "name": "...", "arguments": "..."}, ...}

        # STATE 2 & 3: Stream processing (will send content_block_start based on what we see)
        async with client.stream("POST", target_url, json=request, timeout=None) as response:
            # Check HTTP status before processing
            if response.status_code != 200:
                try:
                    error_text = await response.aread()
                    error_msg = error_text.decode('utf-8')
                except:
                    error_msg = f"HTTP {response.status_code}"

                logger.error(f"vLLM stream error: {error_msg}")
                # Send error event for Claude Code CLI compatibility
                yield sse("error", {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": error_msg
                    }
                })
                return

            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]": continue

                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    choice = chunk["choices"][0]

                    # Check for tool_calls (vLLM streams them incrementally)
                    tool_calls = delta.get("tool_calls", [])
                    if tool_calls:
                        tool_use_detected = True
                        # Accumulate tool call chunks by index
                        for tc in tool_calls:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_by_index:
                                tool_calls_by_index[idx] = {
                                    "id": tc.get("id"),
                                    "type": tc.get("type", "function"),
                                    "function": {"name": None, "arguments": ""}
                                }

                            # Accumulate id if present
                            if "id" in tc:
                                tool_calls_by_index[idx]["id"] = tc["id"]

                            # Accumulate function details
                            if "function" in tc:
                                func = tc["function"]
                                if "name" in func:
                                    tool_calls_by_index[idx]["function"]["name"] = func["name"]
                                if "arguments" in func:
                                    tool_calls_by_index[idx]["function"]["arguments"] += func["arguments"]

                        continue  # Don't send text, accumulate tools

                    if "text" in delta and "content" not in delta: delta["content"] = delta.pop("text")

                    # If we detect tool_use, skip all text content
                    if tool_use_detected or choice.get("finish_reason") == "tool_calls":
                        tool_use_detected = True
                        continue

                    if not self.thinking_requested:
                        if "reasoning" in delta or "thinking" in delta: continue
                        if content_sent == False and delta.get("content", "").startswith("Okay,"): continue

                    text = delta.get("content", "")
                    if text:
                        # Filter out <think>...</think> tags in streaming mode
                        if not self.thinking_requested and ("<think>" in text or "</think>" in text):
                            import re
                            # Remove any <think> or </think> tags from the chunk
                            text = re.sub(r'</?think>', '', text)
                            # Strip any content that looks like thinking
                            if not text.strip():
                                continue

                        if text:
                            # Buffer text instead of sending immediately
                            # We'll send it only if no tool_calls are detected
                            buffered_text_chunks.append(text)

                    if "usage" in chunk and chunk["usage"]:
                        final_usage = chunk["usage"]

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error in stream chunk: {e}, line: {line[:100]}")
                    continue
                except (KeyError, IndexError) as e:
                    logger.warning(f"Missing field in chunk: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected streaming error: {e}")
                    # Don't silently continue - log and potentially fail
                    continue

        # STATE 4: Decide what to send based on tool detection
        if tool_use_detected and tool_calls_by_index:
            # Tool calls detected - send ONLY tool_use blocks with proper streaming format
            for idx in sorted(tool_calls_by_index.keys()):
                tc = tool_calls_by_index[idx]
                try:
                    # Extract tool call details with proper error handling
                    tool_id = tc.get("id")
                    if not tool_id:
                        logger.error(f"Tool call missing 'id' at index {idx}")
                        continue

                    function = tc.get("function", {})
                    tool_name = function.get("name")
                    if not tool_name:
                        logger.error(f"Tool call missing 'name' at index {idx}")
                        continue

                    # CRITICAL FIX: Send empty input in content_block_start
                    # per Anthropic SSE spec: https://docs.anthropic.com/en/api/streaming
                    yield sse("content_block_start", {
                        "type": "content_block_start",
                        "index": idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": {}  # MUST be empty - actual input comes via input_json_delta
                        }
                    })

                    # Send accumulated arguments as input_json_delta event
                    # Claude Code CLI expects this incremental format
                    args_str = function.get("arguments", "")
                    if args_str:
                        yield sse("content_block_delta", {
                            "type": "content_block_delta",
                            "index": idx,
                            "delta": {
                                "type": "input_json_delta",
                                "partial_json": args_str
                            }
                        })

                    yield sse("content_block_stop", {"type": "content_block_stop", "index": idx})

                except Exception as e:
                    logger.error(f"Failed to process tool call at index {idx}: {e}")
                    continue

            # Set stop_reason to tool_use
            stop_reason_final = "tool_use"
            content_sent = True
        else:
            # No tools - send buffered text
            if buffered_text_chunks:
                # Send content_block_start
                yield sse("content_block_start", {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""}
                })
                content_block_started = True

                # Send all buffered text as deltas
                for text in buffered_text_chunks:
                    yield sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": text}
                    })

                content_sent = True

            # STATE 4b: Protocol Invariant Enforcement (text mode fallback)
            if not content_sent:
                if not content_block_started:
                    yield sse("content_block_start", {
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {"type": "text", "text": ""}
                    })
                    content_block_started = True
                yield sse("content_block_delta", {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": " "}
                })

            # STATE 5: Termination sequence (text mode)
            if content_block_started:
                yield sse("content_block_stop", {"type": "content_block_stop", "index": 0})
            stop_reason_final = "end_turn"

        # STATE 6: Final message_delta and message_stop
        
        output_tokens = final_usage.get("completion_tokens") or 1
        yield sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason_final, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens}
        })

        yield sse("message_stop", {"type": "message_stop"})
