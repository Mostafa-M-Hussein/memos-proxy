"""
MemOS Universal Proxy
=====================
Speaks both Ollama API and OpenAI API, forwards everything to MemOS hosted models.
No local GPU needed. All inference runs on MemOS servers.

SETUP:
    pip install fastapi uvicorn httpx

RUN:
    1. Stop local ollama first:  systemctl stop ollama
    2. Start proxy:              python memos_proxy.py

USE WITH OLLAMA CLI:
    OLLAMA_HOST=http://localhost:11434 ollama run qwen3-32b
    OLLAMA_HOST=http://localhost:11434 ollama run deepseek-r1
    OLLAMA_HOST=http://localhost:11434 ollama list

USE WITH AIDER:
    OPENAI_API_BASE=http://localhost:11434/v1 OPENAI_API_KEY=dummy aider --model openai/qwen3-32b

USE WITH CURL (Ollama format):
    curl http://localhost:11434/api/chat -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'

USE WITH CURL (OpenAI format):
    curl http://localhost:11434/v1/chat/completions \\
      -H "Content-Type: application/json" \\
      -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'

USE WITH OPEN WEBUI:
    Set Ollama URL to http://localhost:11434

AVAILABLE MODELS:
    - qwen3-32b             (good balance of speed/quality)
    - deepseek-r1           (reasoning model)
    - qwen2.5-72b-instruct  (largest, best quality)
"""

import os
import json
import time
import uuid
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

app = FastAPI()

MEMOS_URL = "https://memos.memtensor.cn/api/openmem/v1/chat"
MEMOS_KEY = os.environ.get("MEMOS_API_KEY", "your-memos-api-key-here")
PORT = 11435

MODEL_MAP = {
    "qwen3-32b": "qwen3-32b",
    "deepseek-r1": "deepseek-r1",
    "qwen2.5-72b-instruct": "qwen2.5-72b-instruct",
}

def resolve_model(name: str) -> str:
    return MODEL_MAP.get(name, "qwen3-32b")


def extract_from_messages(messages: list) -> tuple[str | None, str]:
    system = None
    for msg in messages:
        if msg["role"] == "system":
            system = msg["content"]

    query = messages[-1]["content"] if messages else ""

    if len(messages) > 2:
        convo = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            prefix = "User" if msg["role"] == "user" else "Assistant"
            convo.append(f"{prefix}: {msg['content']}")
        query = "\n\n".join(convo)

    return system, query


def call_memos(query: str, model: str, system: str = None, stream: bool = False,
               temperature: float = 0.7, max_tokens: int = 8192):
    """Build MemOS request payload."""
    body = {
        "user_id": "local_proxy",
        "conversation_id": f"proxy_{uuid.uuid4().hex[:12]}",
        "query": query,
        "model_name": model,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "add_message_on_answer": False,
    }
    if system:
        body["system_prompt"] = system
    return body


MEMOS_HEADERS = {
    "Authorization": f"Token {MEMOS_KEY}",
    "Content-Type": "application/json",
}


# ============================================================
# OLLAMA-COMPATIBLE ENDPOINTS
# ============================================================

@app.get("/api/tags")
async def ollama_list_models():
    """ollama list / ollama run calls this to discover models."""
    return {
        "models": [
            {
                "name": name,
                "model": name,
                "modified_at": "2025-01-01T00:00:00Z",
                "size": 0,
                "digest": "memos-remote",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "qwen",
                    "parameter_size": "32B" if "32b" in name else "72B" if "72b" in name else "unknown",
                    "quantization_level": "remote",
                },
            }
            for name in MODEL_MAP.keys()
        ]
    }


@app.post("/api/show")
async def ollama_show_model(request: Request):
    """ollama run calls this to get model info before chatting."""
    body = await request.json()
    name = body.get("name", body.get("model", "qwen3-32b"))
    model = resolve_model(name)
    return {
        "modelfile": f"# Remote model via MemOS: {model}",
        "parameters": "temperature 0.7\nstop <|im_end|>",
        "template": "{{ .System }}\n{{ .Prompt }}",
        "details": {
            "parent_model": "",
            "format": "gguf",
            "family": "qwen",
            "parameter_size": "32B" if "32b" in model else "72B" if "72b" in model else "unknown",
            "quantization_level": "remote",
        },
    }


@app.head("/")
@app.get("/")
async def ollama_health():
    """Ollama CLI pings this to check if server is alive."""
    return "Ollama is running"


@app.post("/api/chat")
async def ollama_chat(request: Request):
    """Ollama chat endpoint — used by 'ollama run <model>'."""
    body = await request.json()
    messages = body.get("messages", [])
    model = resolve_model(body.get("model", "qwen3-32b"))
    stream = body.get("stream", True)

    system, query = extract_from_messages(messages)
    # Always fetch non-streaming from MemOS (their streaming is unreliable)
    # Then simulate streaming back to the Ollama client
    memos_body = call_memos(query, model, system, stream=False)

    if not stream:
        async with httpx.AsyncClient(timeout=180) as client:
            res = await client.post(MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS)
            if res.status_code != 200:
                return JSONResponse(status_code=res.status_code, content={"error": res.text})
            data = res.json()
            content = data.get("data", {}).get("response", "")
            return {
                "model": model,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "message": {"role": "assistant", "content": content},
                "done": True,
                "total_duration": 0,
                "eval_count": 0,
            }

    # Fetch full response from MemOS, then drip-feed it word-by-word to Ollama CLI
    async def fake_stream():
        async with httpx.AsyncClient(timeout=180) as client:
            res = await client.post(MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS)
            if res.status_code != 200:
                yield json.dumps({"model": model, "message": {"role": "assistant", "content": f"Error: {res.text}"}, "done": True}) + "\n"
                return

            data = res.json()
            content = data.get("data", {}).get("response", "")

            # Send word by word so it looks like streaming in the terminal
            words = content.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                chunk = {
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "message": {"role": "assistant", "content": token},
                    "done": False,
                }
                yield json.dumps(chunk) + "\n"

            # Final done message
            yield json.dumps({
                "model": model,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "total_duration": 0,
                "eval_count": 0,
            }) + "\n"

    return StreamingResponse(fake_stream(), media_type="application/x-ndjson")


@app.post("/api/generate")
async def ollama_generate(request: Request):
    """Ollama generate endpoint — used by some tools."""
    body = await request.json()
    model = resolve_model(body.get("model", "qwen3-32b"))
    prompt = body.get("prompt", "")
    system = body.get("system", None)
    stream = body.get("stream", True)

    memos_body = call_memos(prompt, model, system, stream=False)

    if not stream:
        async with httpx.AsyncClient(timeout=180) as client:
            res = await client.post(MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS)
            if res.status_code != 200:
                return JSONResponse(status_code=res.status_code, content={"error": res.text})
            data = res.json()
            content = data.get("data", {}).get("response", "")
            return {
                "model": model,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response": content,
                "done": True,
            }

    async def fake_stream_generate():
        async with httpx.AsyncClient(timeout=180) as client:
            res = await client.post(MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS)
            if res.status_code != 200:
                yield json.dumps({"model": model, "response": f"Error: {res.text}", "done": True}) + "\n"
                return

            data = res.json()
            content = data.get("data", {}).get("response", "")

            words = content.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield json.dumps({"model": model, "response": token, "done": False}) + "\n"

            yield json.dumps({"model": model, "response": "", "done": True}) + "\n"

    return StreamingResponse(fake_stream_generate(), media_type="application/x-ndjson")


# ============================================================
# OPENAI-COMPATIBLE ENDPOINTS
# ============================================================

@app.get("/v1/models")
async def openai_list_models():
    return {
        "object": "list",
        "data": [
            {"id": name, "object": "model", "owned_by": "memos"}
            for name in MODEL_MAP.keys()
        ]
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    model = resolve_model(body.get("model", "qwen3-32b"))

    system, query = extract_from_messages(messages)
    memos_body = call_memos(query, model, system, stream=stream,
                            temperature=body.get("temperature", 0.7),
                            max_tokens=body.get("max_tokens", 8192))

    if not stream:
        async with httpx.AsyncClient(timeout=180) as client:
            res = await client.post(MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS)
            if res.status_code != 200:
                return JSONResponse(status_code=res.status_code, content={"error": {"message": res.text}})
            data = res.json()
            content = data.get("data", {}).get("response", "")
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    async def generate_openai():
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream("POST", MEMOS_URL, json=memos_body, headers=MEMOS_HEADERS) as res:
                async for line in res.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("type") == "end":
                        chunk = {
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

                    content = payload.get("content", "")
                    if content:
                        chunk = {
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(generate_openai(), media_type="text/event-stream")


if __name__ == "__main__":
    print(f"MemOS Universal Proxy on http://localhost:{PORT}")
    print(f"Models: {list(MODEL_MAP.keys())}")
    print()
    print("Ollama CLI:")
    print(f"  OLLAMA_HOST=http://localhost:{PORT} ollama run qwen3-32b")
    print(f"  OLLAMA_HOST=http://localhost:{PORT} ollama list")
    print()
    print("Aider:")
    print(f"  OPENAI_API_BASE=http://localhost:{PORT}/v1 OPENAI_API_KEY=dummy aider --model openai/qwen3-32b")
    print()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
