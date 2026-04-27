"""
ClaudeAdapter for LLM Orchestrator

Protocol Enforcer Claude Adapter:
Guarantees Anthropic Messages API compliance via a state-driven emitter.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

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
        # 1. Budgeting: Unified clamping happens at end with tool overhead
        self.thinking_requested = body.get("enable_thinking", False) or body.get("include_thinking", False)

        # Estimate input tokens for message_start (improved heuristic)
        # Count actual message content instead of JSON structure
        messages_text = " ".join([
            str(m.get("content", "")) for m in body.get("messages", [])
        ])
        system_text = str(body.get("system", ""))
        total_text = messages_text + system_text

        # Realistic: ~2 chars per token (safety margin in clamp_max_tokens)
        self.estimated_input_tokens = int(len(total_text) / 2.0)

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

        # Validate: Final messages must have at least one user/assistant message (not just system)
        # This catches edge cases where all messages were filtered out during processing
        has_user_or_assistant = any(
            msg.get("role") in ["user", "assistant"]
            for msg in openai_messages
        )
        if not has_user_or_assistant:
            raise ValueError("messages: must contain at least one user or assistant message")

        # 4. Tool Mapping (for Claude Code CLI compatibility)
        tools = body.get("tools")
        openai_tools = []
        if tools:
            for t in tools:
                tool_type = t.get("type", "")

                # Already in OpenAI format (type="function")
                if tool_type == "function":
                    openai_tools.append(t)

                # Anthropic format with input_schema
                elif "input_schema" in t:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema")
                        }
                    })

                # Anthropic built-in tools (web_search_20250305, bash_20241022, etc.)
                elif tool_type.startswith("web_search"):
                    # Note: max_uses, allowed_domains, blocked_domains are Anthropic-specific
                    # and not supported by vLLM - they will be ignored
                    logger.debug(f"Converting Anthropic web_search tool (type: {tool_type})")
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name", "web_search"),
                            "description": t.get("description", "Search the web for current information"),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The search query"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    })

                elif tool_type.startswith("bash"):
                    logger.debug(f"Converting Anthropic bash tool (type: {tool_type})")
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name", "bash"),
                            "description": t.get("description", "Execute bash commands in a persistent session"),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "The bash command to run"
                                    },
                                    "restart": {
                                        "type": "boolean",
                                        "description": "Set to true to restart the bash session"
                                    }
                                },
                                "required": ["command"]
                            }
                        }
                    })

                elif tool_type.startswith("text_editor"):
                    logger.debug(f"Converting Anthropic text_editor tool (type: {tool_type})")
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name", "text_editor"),
                            "description": t.get("description", "Edit text files"),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "The editor command (view, create, str_replace, insert, undo_edit)"
                                    },
                                    "path": {
                                        "type": "string",
                                        "description": "Path to the file"
                                    }
                                },
                                "required": ["command", "path"]
                            }
                        }
                    })

                elif tool_type.startswith("computer"):
                    logger.debug(f"Converting Anthropic computer tool (type: {tool_type})")
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name", "computer"),
                            "description": t.get("description", "Computer control tool"),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "action": {
                                        "type": "string",
                                        "description": "The action to perform"
                                    }
                                },
                                "required": ["action"]
                            }
                        }
                    })

                else:
                    # Unknown tool type - log warning and skip to avoid vLLM validation errors
                    logger.warning(f"Unknown tool type '{tool_type}' for tool '{t.get('name')}' - skipping. "
                                   f"If this is a custom tool, ensure it uses 'input_schema' format.")
                    continue

        # 5. TokenGuard: Calculate dynamic tool overhead
        # Dynamic tool overhead: 100 tokens base + 50 per parameter
        if openai_tools:
            tool_overhead = 0
            for tool in openai_tools:
                tool_overhead += 100  # Base overhead
                func = tool.get("function", {})
                params = func.get("parameters", {}).get("properties", {})
                tool_overhead += len(params) * 50
            body["__tool_overhead_tokens__"] = tool_overhead

        # Unified clamping (single pass, 5% safety margin)
        body = self.clamp_max_tokens(body, self.max_context)
        clamped_max_tokens = body.get("max_tokens")

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
