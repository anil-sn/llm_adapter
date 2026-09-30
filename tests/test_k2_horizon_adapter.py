from llm_adapter.adapters.k2_horizon_adapter import K2HorizonAdapter


def test_k2_request_bypasses_chat_template_and_keeps_content():
    adapter = K2HorizonAdapter(max_context=32768)
    request = adapter.build_request({
        "model": "k2-horizon-7b",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 32,
    })

    assert "messages" not in request
    assert request["prompt"] == (
        "<|ifm|im_start|>user\nWhat is 2+2?<|ifm|im_end|>"
        "<|ifm|im_start|>assistant\n<ifm|think>\n"
    )


def test_k2_completion_response_is_openai_chat_response():
    response = K2HorizonAdapter().normalize_response({
        "id": "cmpl-1", "created": 1, "model": "k2-horizon-7b",
        "choices": [{"text": "4", "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 15, "completion_tokens": 1, "total_tokens": 16},
    })

    assert response["object"] == "chat.completion"
    assert response["choices"][0]["message"] == {"role": "assistant", "content": "4"}
    assert response["usage"]["prompt_tokens"] == 15


def test_k2_tools_are_rendered_and_parsed_as_openai_tool_calls():
    adapter = K2HorizonAdapter()
    request = adapter.build_request({
        "model": "k2-horizon-7b",
        "messages": [{"role": "user", "content": "Use echo."}],
        "tools": [{"type": "function", "function": {
            "name": "echo", "parameters": {"type": "object", "properties": {}}
        }}],
    })

    assert "<ifm|tools>" in request["prompt"]
    response = adapter.normalize_response({"choices": [{
        "text": (
            '<ifm|tool_calls><ifm|tool_call>{"name":"echo","arguments":{}}'
            '</ifm|tool_call></ifm|tool_calls>'
        )
    }]})
    assert response["choices"][0]["finish_reason"] == "tool_calls"
