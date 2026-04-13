# memos-proxy

Use MemOS hosted models (qwen3-32b, deepseek-r1, qwen2.5-72b-instruct) through the Ollama CLI or any OpenAI-compatible tool. No local GPU needed.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- A MemOS API key from [memos](memos-dashboard.openmem.net)
- [Ollama CLI](https://ollama.com/download) (optional, for `ollama run` usage)
- [aider](https://aider.chat/docs/install.html) (optional, `pip install aider-chat`)

## Quick start

```bash
git clone https://github.com/Mostafa-M-Hussein/memos-proxy.git
cd memos-proxy
cp .env.example .env       # paste your MEMOS_API_KEY in .env
docker compose up -d
```

Or inline:

```bash
MEMOS_API_KEY=your-key docker compose up -d
```

The proxy is now running on `http://localhost:11435`.

## Usage

### Ollama CLI

```bash
OLLAMA_HOST=http://localhost:11435 ollama run qwen3-32b
OLLAMA_HOST=http://localhost:11435 ollama run deepseek-r1
OLLAMA_HOST=http://localhost:11435 ollama list
```

### aider

```bash
OPENAI_API_BASE=http://localhost:11435/v1 OPENAI_API_KEY=dummy aider --model openai/qwen3-32b
```

### curl (OpenAI format)

```bash
curl http://localhost:11435/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'
```

### curl (Ollama format)

```bash
curl http://localhost:11435/api/chat \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'
```

### Open WebUI

Set Ollama URL to `http://localhost:11435`.

### Manual (without Docker)

```bash
pip install fastapi uvicorn httpx
MEMOS_API_KEY=your-key python memos_proxy.py
```

## How it works

```
your tool (ollama, aider, curl, etc.)
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ memos_proxy  │────▶│ MemOS Cloud  │
│ localhost    │◀────│ (runs model) │
└──────────────┘     └──────────────┘
       │
       ▼
  response back
  to your terminal
```

The proxy translates Ollama/OpenAI API calls into MemOS format. Your machine does zero inference.

## Models

| Name | Notes |
|------|-------|
| `qwen3-32b` | default, good balance |
| `deepseek-r1` | reasoning |
| `qwen2.5-72b-instruct` | largest |
