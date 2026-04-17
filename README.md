# memos-proxy

Use MemOS hosted models (qwen3-32b, deepseek-r1, qwen2.5-72b-instruct) through Open WebUI, OpenClaw, the Ollama CLI, or any OpenAI-compatible tool. No local GPU needed.

## Prerequisites

Install these manually before running the setup script:

| # | What | How |
|---|------|-----|
| 1 | **Docker** | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| 2 | **Ollama** | [ollama.com/download](https://ollama.com/download) |
| 3 | **OpenClaw** | After Ollama is installed: `ollama launch openclaw` |
| 4 | **MemOS API key** | Sign up at [memos-dashboard.openmem.net](https://memos-dashboard.openmem.net) |

Everything else is handled by the setup script. Stuck? [quick tutorial](https://www.youtube.com/watch?v=yxduL_jMHpA&feature=youtu.be)
## Quick start

```bash
git clone https://github.com/Mostafa-M-Hussein/memos-proxy.git
cd memos-proxy
```

**macOS / Linux**
```bash
cp .env.example .env        # paste your MEMOS_API_KEY
./setup.sh
```

**Windows (PowerShell)**
```powershell
copy .env.example .env      # paste your MEMOS_API_KEY
.\setup.ps1
```

> First run? If PowerShell blocks the script:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

That's it. The script will:
1. Start all Docker services
2. Install and start OpenClaw (via `ollama launch openclaw`), pre-configured to use Memos models

## Services

| Service | URL | What it does |
|---------|-----|--------------|
| open-webui | http://localhost:3333 | Browser chat UI |
| ollama-mcp-bridge | http://localhost:11436 | Memos models + MCP tool support |
| memos-proxy | http://localhost:11435 | Raw Ollama-compatible API |

Your local Ollama stays on `11434` — no conflicts.

## Architecture

```
open-webui (browser)
      │
      ▼
ollama-mcp-bridge :11436  ◄── OpenClaw (messaging: WhatsApp/Telegram/Slack)
      │
      ▼
memos-proxy :11435
      │
      ▼
MemOS Cloud  (qwen3-32b · deepseek-r1 · qwen2.5-72b-instruct)
```

## Manual usage

### Ollama CLI

```bash
OLLAMA_HOST=http://localhost:11436 ollama run qwen3-32b
OLLAMA_HOST=http://localhost:11436 ollama list
```

### aider

```bash
OPENAI_API_BASE=http://localhost:11435/v1 OPENAI_API_KEY=dummy aider --model openai/qwen3-32b
```

### curl

```bash
curl http://localhost:11435/api/chat \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'
```

## Stop everything

```bash
docker compose down && openclaw gateway stop
```

## Models

| Name | Notes |
|------|-------|
| `qwen3-32b` | default, good balance |
| `deepseek-r1` | reasoning |
| `qwen2.5-72b-instruct` | largest |
