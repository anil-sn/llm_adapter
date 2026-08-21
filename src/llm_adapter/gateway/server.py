#!/usr/bin/env python3
"""
LLM Orchestrator Gateway v7.0 - Model-Agnostic Router
- Multi-model support via layered configuration
- Protocol translation (Anthropic → OpenAI)
- Dynamic adapter routing
- Load balancing with pulse scheduling

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import hashlib
import json
import uvicorn
import httpx
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path

from llm_adapter.adapters.factory import get_adapter
from llm_adapter.scheduler.pulse_scheduler import PulseScheduler
from llm_adapter.utils.config_loader import load_config, ConfigError
from llm_adapter.utils.user_detector import get_user_detector
from llm_adapter.middleware.auth import require_user_identification
from llm_adapter.middleware.api_key_auth import get_api_key_manager, require_api_key

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("llm-gateway")

# Project root is 3 levels up: gateway/ -> llm_adapter/ -> src/ -> project/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Load configuration using layered config system
try:
    config = load_config(project_root=PROJECT_ROOT, validate=True)
    model_info = config.get('model', {}).get('id', 'adapter-gateway')
    logger.info(f"Configuration loaded: {model_info}")
except ConfigError as e:
    logger.error(f"Configuration error: {e}")
    logger.error("Hint: Set LLM_CONFIG environment variable")
    raise
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

app = FastAPI()
client = httpx.AsyncClient(timeout=None)

MAX_BATCH = config.get("inference", {}).get("max_num_seqs", 64)
scheduler = PulseScheduler(max_batch_size=MAX_BATCH)

# Gateway advertises this name to clients (for adapter routing)
SERVED_MODEL = config.get("model", {}).get("served_model_name", "nemotron-3-super")
# vLLM uses the same name (no translation needed)
VLLM_MODEL = SERVED_MODEL

# Initialize user detector
user_detector = get_user_detector(PROJECT_ROOT)
logger.info("User detection initialized")

# Initialize API key manager
api_key_manager = get_api_key_manager(PROJECT_ROOT)
logger.info("API key authentication initialized")

# Dynamic Model Discovery Cache
MODEL_CACHE = {
    "models": {},       # model_id_lower -> {"url": str, "exact_id": str}
    "raw_data": [],     # list of model dicts for /v1/models response
    "last_updated": 0.0 # timestamp
}
CACHE_TTL = 5.0  # seconds
cache_lock = asyncio.Lock()

async def get_active_models() -> dict:
    import time
    async with cache_lock:
        now = time.time()
        if now - MODEL_CACHE["last_updated"] < CACHE_TTL:
            return MODEL_CACHE

        new_models = {}
        new_raw_data = []

        # We probe ports 8000 to 8007 to find active vLLM replicas
        # Use a short timeout so we don't block requests if replicas are offline
        async with httpx.AsyncClient(timeout=1.0) as local_client:
            tasks = []
            ports = list(range(8000, 8008))
            for port in ports:
                tasks.append(local_client.get(f"http://127.0.0.1:{port}/v1/models"))
            
            # Run all probes in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for port, res in zip(ports, results):
                if not isinstance(res, Exception) and res.status_code == 200:
                    try:
                        data = res.json()
                        url = f"http://127.0.0.1:{port}"
                        # Check standard OpenAI v1/models structure: {"data": [...]}
                        for m in data.get("data", []):
                            m_id = m.get("id")
                            if m_id:
                                # Create a copy and anonymize/sanitize the root model ID to avoid exposing it
                                m_copy = m.copy()
                                if "root" in m_copy:
                                    m_copy["root"] = m_id
                                
                                # Map the model ID to its replica URL
                                new_models[m_id.lower()] = {
                                    "url": url,
                                    "exact_id": m_id
                                }
                                new_raw_data.append(m_copy)
                    except Exception as e:
                        logger.warning(f"Error parsing models from port {port}: {e}")

        # Update cache if we found any active models, or if the cache was completely empty
        # (to avoid serving an empty list if there's a temporary network hiccup)
        if new_models or not MODEL_CACHE["models"]:
            MODEL_CACHE["models"] = new_models
            MODEL_CACHE["raw_data"] = new_raw_data
            MODEL_CACHE["last_updated"] = now
            logger.info(f"Discovered active models: {list(new_models.keys())}")

        return MODEL_CACHE

@app.on_event("startup")
async def startup_event():
    scheduler.start()

REPLICAS = [
    f"http://127.0.0.1:{config.get('replicas', {}).get('base_port', 8000) + i}"
    for i in range(config.get("replicas", {}).get("count", 1))
]

@app.get("/v1/models")
async def list_models():
    import time
    cache = await get_active_models()
    if cache["raw_data"]:
        return {
            "object": "list",
            "data": cache["raw_data"]
        }
    
    # Static fallback if no active vLLM replica is detected yet
    # Build the list from configured model IDs so /v1/models reflects what we expect to serve
    fallback_ids = [
        m.get("id", f"unknown-{i}")
        for i, m in enumerate(config.get("models", {}).get("backends", []))
    ] or ["Coder", "Reasoner"]
    return {
        "object": "list",
        "data": [
            {
                "id": fid,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "llm-adapter",
                "max_model_len": config.get("inference", {}).get("max_model_len", 900000),
            }
            for fid in fallback_ids
        ]
    }

@app.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    """
    POST /v1/messages/count_tokens compatible endpoint for Claude Code.
    Provides realistic token count estimation (approx 2 chars per token).
    """
    try:
        user = require_api_key(request, api_key_manager)
    except Exception as e:
        if hasattr(e, 'status_code') and hasattr(e, 'detail'):
            return JSONResponse(status_code=e.status_code, content=e.detail)
        else:
            return JSONResponse(status_code=401, content={"error": "authentication_required", "message": "API key required"})

    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except:
        return JSONResponse(status_code=400, content={"error": "invalid_json"})

    messages_text = ""
    for m in body.get("messages", []):
        content = m.get("content", "")
        if isinstance(content, str):
            messages_text += content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    messages_text += block["text"]
                    
    system_text = str(body.get("system", ""))
    total_text = messages_text + system_text
    
    # Conservative estimate: max(1, ~2 characters per token)
    estimated_tokens = max(1, (len(total_text) + 1) // 2)
    
    return JSONResponse({"input_tokens": estimated_tokens})

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_router(request: Request, path: str):
    # ENFORCE API KEY AUTHENTICATION for all POST requests (GPU access)
    # GET requests (like /v1/models) are allowed without authentication
    if request.method == "POST":
        try:
            user = require_api_key(request, api_key_manager)
            # Log the API key used for this request (for audit trail)
            api_key = None
            auth_header = request.headers.get("Authorization")
            if auth_header:
                if auth_header.startswith("Bearer "):
                    api_key = auth_header[7:].strip()
                else:
                    api_key = auth_header.strip()
            if not api_key:
                api_key = request.headers.get("X-API-Key") or request.headers.get("ANTHROPIC_API_KEY")

            # Store API key info in request state for logging
            if api_key:
                request.state.api_key = f"{api_key[:15]}..." if len(api_key) > 15 else api_key
            else:
                request.state.api_key = "localhost-bypass"
        except Exception as e:
            # Return error response (JSONResponse already imported at top)
            if hasattr(e, 'status_code') and hasattr(e, 'detail'):
                return JSONResponse(status_code=e.status_code, content=e.detail)
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "authentication_required",
                        "message": "Valid API key required to access GPU",
                        "example": "curl -H 'Authorization: Bearer sk-your-key' ..."
                    }
                )
    else:
        # For GET requests, use optional detection (for logging purposes)
        user = user_detector.detect_user(request)

    replica_idx = 0
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except (json.JSONDecodeError, ValueError):
        body = {}

    # Protocol detection
    is_anthropic = "messages" in path and "chat" not in path
    if is_anthropic:
        body["__protocol__"] = "anthropic"

    is_chat_path = "chat/completions" in path or "messages" in path

    if request.method == "POST" and is_chat_path:
        requested_model_raw = str(body.get('model', 'Coder'))
        requested_model_lower = requested_model_raw.lower()
        
        # Log request with API key info
        api_key_info = getattr(request.state, 'api_key', 'unknown')
        logger.info(f"[{user}] Request: {requested_model_raw} - Stream: {body.get('stream', False)} - Key: {api_key_info}")

        # Fetch currently active models dynamically
        active_cache = await get_active_models()
        active_models = active_cache["models"]

        target_model_name = None
        target_replica_url = None

        # 1. Exact Match
        if requested_model_lower in active_models:
            target_model_name = active_models[requested_model_lower]["exact_id"]
            target_replica_url = active_models[requested_model_lower]["url"]
        else:
            # 2. Heuristic fallback based on query terms
            if "reasoner" in requested_model_lower or "qwq" in requested_model_lower or "think" in requested_model_lower:
                # Look for a reasoning model (any model containing reasoner or qwq)
                reasoner_models = [m for m in active_models.keys() if "reasoner" in m or "qwq" in m]
                if reasoner_models:
                    target_model_name = active_models[reasoner_models[0]]["exact_id"]
                    target_replica_url = active_models[reasoner_models[0]]["url"]
            elif "coder" in requested_model_lower:
                # Look for a coder model
                coder_models = [m for m in active_models.keys() if "coder" in m or "qwen" in m and "qwq" not in m]
                if coder_models:
                    target_model_name = active_models[coder_models[0]]["exact_id"]
                    target_replica_url = active_models[coder_models[0]]["url"]

            # 3. If no specific match found, fallback to standard non-reasoning models first
            if not target_model_name:
                non_reasoners = [m for m in active_models.keys() if "reasoner" not in m and "qwq" not in m]
                if non_reasoners:
                    target_model_name = active_models[non_reasoners[0]]["exact_id"]
                    target_replica_url = active_models[non_reasoners[0]]["url"]
                elif active_models:
                    # Absolute fallback to first available
                    first_model_key = list(active_models.keys())[0]
                    target_model_name = active_models[first_model_key]["exact_id"]
                    target_replica_url = active_models[first_model_key]["url"]

        # 4. If absolutely nothing is running, fall back to hardcoded defaults
        if not target_model_name or not target_replica_url:
            if "reasoner" in requested_model_lower or "qwq" in requested_model_lower:
                target_model_name = "reasoner"
                target_replica_url = "http://127.0.0.1:8001"
            else:
                target_model_name = "qwen3-coder-fp8"
                target_replica_url = "http://127.0.0.1:8000"

        logger.info(f"[{user}] Dynamic Route: '{requested_model_raw}' mapped to target '{target_model_name}' on {target_replica_url}")

        # Use the mapped vLLM model name when forwarding requests
        body["model"] = target_model_name

        # Use ClaudeAdapter for Anthropic requests, NemotronAdapter for OpenAI
        adapter = get_adapter("claude-haiku-4-5-20251001" if is_anthropic else target_model_name)

        vllm_path = "/v1/chat/completions" if is_anthropic else f"/{path.lstrip('/')}"
        target_url = f"{target_replica_url}{vllm_path}"

        try:
            refined_request = adapter.build_request(body)

            # Log what we're sending to vLLM for debugging
            if "messages" not in refined_request:
                logger.error(f"WARNING: No messages in refined request! Original keys: {list(body.keys())}")
            is_streaming = body.get("stream", False)
            client_requested_streaming = is_streaming  # Remember original client request

            # WORKAROUND: Force non-streaming for models with tool streaming bugs
            # - Gemma 4: infinite loops and JSON corruption (vLLM bug #39043)
            # - Mistral Medium 3.5: IndexError in tool parser during streaming (vLLM 0.20.2)
            needs_tool_workaround = (
                (SERVED_MODEL.startswith("gemma")) or
                (SERVED_MODEL.startswith("mistral") or "claude-haiku" in SERVED_MODEL)
            )
            if is_streaming and needs_tool_workaround and refined_request.get("tools"):
                logger.warning(f"[{user}] {SERVED_MODEL} + tools + streaming detected - forcing non-streaming (vLLM bug workaround)")
                is_streaming = False  # Force vLLM to non-streaming
                refined_request["stream"] = False
                # Remove stream_options when forcing non-streaming (vLLM validation)
                refined_request.pop("stream_options", None)

        except ValueError as e:
            # Validation error - return Anthropic-formatted error
            logger.warning(f"[{user}] Validation Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=400)
        except Exception as e:
            # Unexpected adapter error
            logger.error(f"[{user}] Adapter Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=500)

        # Process the request
        try:

            if is_streaming:
                async def stream_wrapper():
                    try:
                        async for chunk in adapter.stream(client, target_url, refined_request):
                            yield chunk
                    except Exception as e:
                        logger.error(f"[{user}] Stream Error: {e}")
                    finally:
                        pass
                return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
            else:
                try:
                    resp = await client.post(target_url, json=refined_request, timeout=None)
                    if resp.status_code != 200:
                        logger.error(f"[{user}] vLLM Error: HTTP {resp.status_code} - {resp.text[:300]}")
                        # Log the exact request that caused the error
                        logger.error(f"Request body sent: {json.dumps(refined_request, indent=2)[:2000]}")
                        return JSONResponse(resp.json() if resp.text else {"error": resp.text}, status_code=resp.status_code)
                    resp_json = resp.json()
                    # Normalize response through adapter for proper format
                    resp_json = adapter.normalize_response(resp_json)
                    usage = resp_json.get("usage", {})
                    api_key_info = getattr(request.state, 'api_key', 'unknown')
                    logger.info(f"[{user}] Response: {usage.get('input_tokens', 0) + usage.get('output_tokens', 0)} tokens - Input: {usage.get('input_tokens', 0)}, Output: {usage.get('output_tokens', 0)} - Key: {api_key_info}")

                    # If client requested streaming but we forced non-streaming, convert to SSE
                    if client_requested_streaming:
                        async def fake_stream():
                            # Convert non-streaming response to SSE format
                            # This happens when tools force non-streaming but client expects SSE
                            yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': resp_json.get('id'), 'type': 'message', 'role': 'assistant', 'content': [], 'model': resp_json.get('model'), 'usage': usage}})}\n\n".encode()

                            for idx, block in enumerate(resp_json.get('content', [])):
                                if block['type'] == 'text':
                                    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': idx, 'content_block': {'type': 'text', 'text': ''}})}\n\n".encode()
                                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': idx, 'delta': {'type': 'text_delta', 'text': block['text']}})}\n\n".encode()
                                    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': idx})}\n\n".encode()
                                elif block['type'] == 'tool_use':
                                    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': idx, 'content_block': {'type': 'tool_use', 'id': block['id'], 'name': block['name'], 'input': {}}})}\n\n".encode()
                                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': idx, 'delta': {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}})}\n\n".encode()
                                    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': idx})}\n\n".encode()

                            yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': resp_json.get('stop_reason'), 'stop_sequence': None}, 'usage': {'output_tokens': usage.get('output_tokens', 0)}})}\n\n".encode()
                            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n".encode()

                        return StreamingResponse(fake_stream(), media_type="text/event-stream")

                    return JSONResponse(resp_json)
                except Exception as e:
                    logger.error(f"[{user}] Request Error: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": str(e)
                        }
                    }
                    return JSONResponse(error_response, status_code=500)
        except Exception as e:
            logger.error(f"[{user}] Unexpected Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=500)

    # Direct passthrough
    target_url = f"{REPLICAS[replica_idx]}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body_bytes,
            params=request.query_params,
            timeout=None
        )
        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"[{user}] Passthrough Error: {e}")
        return JSONResponse({"error": f"Passthrough Error: {str(e)}"}, status_code=502)

if __name__ == "__main__":
    port = config["cluster"]["gateway_port"]
    logger.info(f"Nemo-Gateway ACTIVE on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
