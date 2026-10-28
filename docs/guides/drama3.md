# Drama 3 through the llm_adapter gateway

`llm_adapter` can expose Drama 3 under the same gateway URL and API key as its
chat models. The manager selects the runtime from `inference_backend` in the
model config: existing model configs select `vllm`, while `config-drama3.yaml`
selects `sglang_omni`. The gateway forwards `/v1/audio/speech` requests to
SGLang-Omni. No vLLM server is used for Drama 3.

## Start SGLang-Omni

Install the dedicated runtime declared in
`runtimes/sglang_omni/pyproject.toml` with uv:

```bash
uv sync --project runtimes/sglang_omni
```

This creates an isolated runtime environment at
`runtimes/sglang_omni/.venv`; the Drama 3 config already points to its
`sgl-omni` executable. Keeping this runtime separate avoids mixing its PyTorch
2.14.1 requirement with the root project's PyTorch 2.13.0 pin. See the
[official SGLang-Omni installation guide](https://sgl-project.github.io/sglang-omni/get_started/installation.html)
and [Drama 3 cookbook](https://sgl-project.github.io/sglang-omni/cookbook/fishaudio_drama3.html).

The config follows the cookbook's two-GPU placement: the TTS engine is on GPU 0
and the vocoder is on GPU 1. It gives the vocoder a 20% memory share because
the default 10% share on this 48 GB GPU failed the startup check for the
default 2,048-frame decode limit. The config maps the public model name
`drama-3` to `http://127.0.0.1:8000`.
From the `llm_adapter` project root, use the same manager commands as other models:

```bash
LLM_CONFIG=config/config-drama3.yaml uv run python scripts/setup/llm_manager.py stop
LLM_CONFIG=config/config-drama3.yaml uv run python scripts/setup/llm_manager.py start
```

`start` launches SGLang-Omni and the gateway; `stop` stops both. The selected
runtime is determined by the config file for each command.

## Generate speech through the gateway

Set `LLM_API_KEY` to a key accepted by the gateway, then send the same
`/v1/audio/speech` payload SGLang-Omni accepts:

```bash
curl -X POST http://localhost:8888/v1/audio/speech \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"drama-3","input":"Hello from Drama 3."}' \
  --output drama3.wav
```

Voice cloning works by including `references` with an audio path and transcript.
For streaming, set `"stream": true` and a supported response format such as
`"response_format": "pcm"`; the gateway streams the SGLang-Omni response
through unchanged.

The gateway's `/v1/models` list includes configured external backends, so chat
models and the audio model can be discovered from one URL. This first
integration routes SGLang-Omni's audio endpoint; it does not translate audio
requests into chat-completion requests.
