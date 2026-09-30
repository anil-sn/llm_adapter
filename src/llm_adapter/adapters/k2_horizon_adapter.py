"""K2-Horizon adapter that avoids vLLM's remote-code chat-template path."""

import time
import uuid
import json
import re
from typing import Any

from .openai_adapter import OpenAIAdapter
from .claude_adapter import ClaudeAdapter


class K2HorizonAdapter(OpenAIAdapter):
    """Translate OpenAI chat requests into K2-Horizon raw completions.

    K2-Horizon currently drops message content when vLLM applies its chat
    template with ``trust_remote_code=True``.  Supplying a pre-rendered prompt
    to ``/v1/completions`` bypasses that code path entirely.
    """

    uses_completions_endpoint = True

    _START = "<|ifm|im_start|>"
    _END = "<|ifm|im_end|>"

    def __init__(self, *args, default_reasoning_effort: str = "low", **kwargs):
        super().__init__(*args, **kwargs)
        self.default_reasoning_effort = default_reasoning_effort

    @staticmethod
    def _text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # OpenAI text content parts are safe to flatten. Image/audio parts
            # cannot be represented by this text-only model.
            return "\n".join(
                part.get("text", "") for part in content
                if isinstance(part, dict) and part.get("type", "text") in {"text", "input_text"}
            )
        return "" if content is None else str(content)

    @classmethod
    def render_prompt(
        cls, messages: list[dict], reasoning_effort: str = "high", tools: list[dict] | None = None,
        tool_choice: Any = None,
    ) -> str:
        """Render the text-only subset of K2's published chat template."""
        prompt: list[str] = []
        if tools:
            functions = [tool.get("function", tool) for tool in tools]
            tool_spec = json.dumps(functions, ensure_ascii=False, separators=(",", ":"))
            force_instruction = ""
            if tool_choice == "required":
                force_instruction = " You must call one of the available tools."
            elif isinstance(tool_choice, dict):
                name = tool_choice.get("function", {}).get("name")
                if name:
                    force_instruction = f" You must call the `{name}` tool."
            prompt.append(
                f"{cls._START}system\n# Tools\nYou may call the available tools.\n"
                f"<ifm|tools>{tool_spec}</ifm|tools>\n\n"
                "To call a tool, emit JSON in this exact form:\n"
                "<ifm|tool_calls><ifm|tool_call>{\"name\": \"FUNCTION_NAME\", "
                "\"arguments\": {}}</ifm|tool_call></ifm|tool_calls>"
                + force_instruction + f"{cls._END}"
            )
        for message in messages:
            role = message.get("role")
            content = cls._text(message.get("content"))
            if role in {"system", "user", "tool"}:
                prompt.append(f"{cls._START}{role}\n{content}{cls._END}")
            elif role == "assistant":
                thought = (
                    message.get("think")
                    or message.get("reasoning_content")
                    or message.get("reasoning")
                    or ""
                )
                prior_calls = []
                for call in message.get("tool_calls") or []:
                    function = call.get("function", call)
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    prior_calls.append({"name": function.get("name"), "arguments": arguments})
                calls = "".join(
                    f"<ifm|tool_calls><ifm|tool_call>{json.dumps(call, ensure_ascii=False)}</ifm|tool_call>"
                    "</ifm|tool_calls>" for call in prior_calls
                )
                prompt.append(
                    f"{cls._START}assistant<ifm|think>\n{thought}</ifm|think>"
                    f"{content}{calls}{cls._END}"
                )

        think_tag = {"high": "think", "medium": "think_fast", "low": "think_faster"}.get(
            reasoning_effort, "think"
        )
        prompt.append(f"{cls._START}assistant\n<ifm|{think_tag}>\n")
        return "".join(prompt)

    def build_request(self, body: dict) -> dict:
        request = self.clamp_max_tokens(body.copy(), self.max_context)
        effort = request.pop("reasoning_effort", self.default_reasoning_effort)
        extra_body = request.pop("extra_body", None) or {}
        effort = extra_body.get("chat_template_kwargs", {}).get("reasoning_effort", effort)
        tools = request.pop("tools", None)
        # These are chat-completions controls, not valid /v1/completions fields.
        tool_choice = request.pop("tool_choice", None)
        request["prompt"] = self.render_prompt(request.pop("messages", []), effort, tools, tool_choice)
        request.pop("chat_template_kwargs", None)
        request.pop("stream_options", None)
        return request

    @staticmethod
    def _usage(usage: dict) -> dict:
        return {
            "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
            "total_tokens": usage.get("total_tokens", 0),
        }

    def normalize_response(self, resp: dict) -> dict:
        choice = (resp.get("choices") or [{}])[0]
        content, tool_calls = self._extract_tool_calls(choice.get("text", ""))
        return {
            "id": resp.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
            "object": "chat.completion",
            "created": resp.get("created", int(time.time())),
            "model": resp.get("model"),
            "choices": [{
                "index": choice.get("index", 0),
                "message": {"role": "assistant", "content": content, **({"tool_calls": tool_calls} if tool_calls else {})},
                "finish_reason": "tool_calls" if tool_calls else choice.get("finish_reason"),
            }],
            "usage": self._usage(resp.get("usage", {})),
        }

    @staticmethod
    def _extract_tool_calls(text: str) -> tuple[str, list[dict]]:
        """Convert K2's tagged JSON calls to OpenAI's tool_calls structure."""
        calls = []
        for raw in re.findall(r"<ifm\|tool_call>(.*?)</ifm\|tool_call>", text, flags=re.DOTALL):
            try:
                call = json.loads(raw.strip())
                name, arguments = call.get("name"), call.get("arguments", {})
            except json.JSONDecodeError:
                # K2's default tool_call_format is XML. The function name is
                # the first line; values are plain text unless valid JSON.
                lines = raw.strip().splitlines()
                name = lines[0].strip() if lines else ""
                arguments = {}
                for key, value in re.findall(
                    r"<ifm\|arg_key>(.*?)</ifm\|arg_key>\s*"
                    r"(?:<ifm\|arg_type>.*?</ifm\|arg_type>\s*)?"
                    r"<ifm\|arg_value>(.*?)</ifm\|arg_value>", raw, flags=re.DOTALL,
                ):
                    value = value.strip()
                    try:
                        arguments[key.strip()] = json.loads(value)
                    except json.JSONDecodeError:
                        arguments[key.strip()] = value
            if name and isinstance(arguments, dict):
                calls.append({
                    "id": f"call_{uuid.uuid4().hex[:24]}", "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
                })
        clean = re.sub(r"<ifm\|tool_calls>.*?</ifm\|tool_calls>", "", text, flags=re.DOTALL)
        # K2 writes private reasoning before closing the generation prompt's
        # think tag. It must not be returned as assistant-visible text.
        clean = re.sub(r"^.*?</ifm\|think(?:_fast|_faster)?>", "", clean, flags=re.DOTALL).strip()
        return clean, calls

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        choice = (chunk.get("choices") or [{}])[0]
        return {
            "id": chunk.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
            "object": "chat.completion.chunk",
            "created": chunk.get("created", int(time.time())),
            "model": chunk.get("model"),
            "choices": [{
                "index": choice.get("index", 0),
                "delta": {"content": choice.get("text", "")},
                "finish_reason": choice.get("finish_reason"),
            }],
        }

    async def stream(self, client: Any, target_url: str, request: dict):
        """Emit normalized SSE only after K2's private reasoning is complete.

        K2 puts the closing ``</ifm|think>`` tag in an arbitrary raw-completion
        chunk. Forwarding chunks directly leaks that tag to OpenAI clients.
        Buffering also lets XML tool calls be emitted as standard tool_calls.
        """
        headers = {"Content-Type": "application/json"}
        text_parts: list[str] = []
        response_id = None
        created = None
        model = request.get("model")
        finish_reason = None
        async with client.stream("POST", target_url, headers=headers, json=request, timeout=None) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                try:
                    chunk = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                response_id = chunk.get("id", response_id)
                created = chunk.get("created", created)
                model = chunk.get("model", model)
                choice = (chunk.get("choices") or [{}])[0]
                text_parts.append(choice.get("text", ""))
                finish_reason = choice.get("finish_reason", finish_reason)

        normalized = self.normalize_response({
            "id": response_id, "created": created, "model": model,
            "choices": [{"text": "".join(text_parts), "finish_reason": finish_reason}],
        })
        choice = normalized["choices"][0]
        message = choice["message"]
        delta = {"role": "assistant"}
        if message.get("tool_calls"):
            delta["tool_calls"] = message["tool_calls"]
        elif message.get("content"):
            delta["content"] = message["content"]
        chunk = {
            "id": normalized["id"], "object": "chat.completion.chunk",
            "created": normalized["created"], "model": normalized["model"],
            "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n".encode()
        chunk["choices"][0]["delta"] = {}
        chunk["choices"][0]["finish_reason"] = choice.get("finish_reason")
        yield f"data: {json.dumps(chunk)}\n\n".encode()
        yield b"data: [DONE]\n\n"


class K2ClaudeAdapter(K2HorizonAdapter):
    """K2 raw-completion transport with Claude Messages API normalization."""

    def __init__(self, max_context: int = 32768, **kwargs):
        super().__init__(max_context=max_context, **kwargs)
        self._claude = ClaudeAdapter(max_context=max_context)

    def build_request(self, body: dict) -> dict:
        # ClaudeAdapter owns the Anthropic-to-OpenAI message and tool mapping;
        # K2HorizonAdapter then renders the resulting OpenAI request itself.
        return super().build_request(self._claude.build_request(body))

    def normalize_response(self, resp: dict) -> dict:
        return self._claude.normalize_response(super().normalize_response(resp))
