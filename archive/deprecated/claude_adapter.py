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
        # DEBUG: Log what we receive
        import logging
        debug_logger = logging.getLogger("claude-adapter-debug")
        debug_logger.info(f"Received body keys: {list(body.keys())}")
        debug_logger.info(f"Has messages: {'messages' in body}")
        if 'messages' in body:
            debug_logger.info(f"Number of messages: {len(body['messages'])}")
            for i, m in enumerate(body['messages']):
                role = m.get('role', 'unknown')
                content_type = type(m.get('content')).__name__
                debug_logger.info(f"  Message {i}: role={role}, content_type={content_type}, content_len={len(str(m.get('content', '')))}")
        
        # 1. Budgeting: Clamping with the Enforcer heuristic
        body = self.clamp_max_tokens(body, self.max_context)
        self.thinking_requested = body.get("enable_thinking", False) or body.get("include_thinking", False)

        # Estimate input tokens for message_start (approximate)
        self.estimated_input_tokens = int(len(json.dumps(body)) / 2.5)

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
                    if b_type == "text": text_parts.append(block.get("text", ""))
                    elif b_type == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id"),
                            "content": str(block.get("content", ""))
                        })
                m["content"] = " ".join(text_parts) if text_parts else None

            if role != "tool": openai_messages.append(m)

        # CRITICAL: Ensure messages are never empty
        if not openai_messages:
            openai_messages = [{"role": "user", "content": "Hello"}]

        # 4. Tool Mapping
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

        return {
            "model": body.get("model"),
            "messages": openai_messages,
            "stream": body.get("stream", False),
            "max_tokens": body.get("max_tokens", 1024),
            "temperature": body.get("temperature", 0.7),
            "tools": openai_tools if openai_tools else None,
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

                # Only strip meta-commentary if we had actual content
                # (not when reasoning was moved to content)
                if had_content and not self.thinking_requested:
                    patterns = ["Okay, ", "Hmm, ", "The user asked ", "First, ", "I will "]
                    if any(content.startswith(p) for p in patterns):
                        original = content
                        if "\n\n" in content: content = content.split("\n\n", 1)[1].strip()
                        elif "\n" in content: content = content.split("\n", 1)[1].strip()
                        msg["content"] = content if content else original

        if self.incoming_protocol == "anthropic":
            content = []
            if "choices" in resp:
                m = resp["choices"][0]["message"]
                if m.get("content"): content.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    try: args = json.loads(tc["function"]["arguments"])
                    except: args = {}
                    content.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": args})
            
            # Protocol Invariant: Never return empty content
            if not content: content = [{"type": "text", "text": " "}]

            return {
                "id": self.message_id, "type": "message", "role": "assistant",
                "content": content, "model": resp.get("model"), "usage": usage_obj
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

        # STATE 2: content_block_start
        yield sse("content_block_start", {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        })

        content_sent = False
        final_usage = {"prompt_tokens": self.estimated_input_tokens, "completion_tokens": 0}

        # STATE 3: content_block_delta loop
        async with client.stream("POST", target_url, json=request, timeout=None) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]": continue
                
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    
                    if "text" in delta and "content" not in delta: delta["content"] = delta.pop("text")
                    
                    if not self.thinking_requested:
                        if "reasoning" in delta or "thinking" in delta: continue
                        if content_sent == False and delta.get("content", "").startswith("Okay,"): continue

                    text = delta.get("content", "")
                    if text:
                        content_sent = True
                        yield sse("content_block_delta", {
                            "type": "content_block_delta",
                            "index": 0,
                            "delta": {"type": "text_delta", "text": text}
                        })

                    if "usage" in chunk and chunk["usage"]:
                        final_usage = chunk["usage"]
                except: pass

        # STATE 4: Protocol Invariant Enforcement
        if not content_sent:
            yield sse("content_block_delta", {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": " "}
            })

        # STATE 5: Termination sequence
        yield sse("content_block_stop", {"type": "content_block_stop", "index": 0})
        
        output_tokens = final_usage.get("completion_tokens") or 1
        yield sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens}
        })
        
        yield sse("message_stop", {"type": "message_stop"})
