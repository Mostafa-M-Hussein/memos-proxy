# memos-proxy

Use MemOS hosted models (qwen3-32b, deepseek-r1, qwen2.5-72b-instruct) through the Ollama CLI or any OpenAI-compatible tool. No local GPU needed.

## Setup

### Docker (recommended)

```bash
# clone and run
git clone https://github.com/Mostafa-M-Hussein/memos-proxy.git
cd memos-proxy
MEMOS_API_KEY=your-key-here docker compose up -d
```

Or build and run directly:

```bash
docker build -t memos-proxy .
docker run -d -p 11435:11435 -e MEMOS_API_KEY=your-key-here memos-proxy
```

Get your API key from [MemOS dashboard](https://memos.memtensor.cn).

### Manual

```bash
pip install fastapi uvicorn httpx
MEMOS_API_KEY=your-key-here python memos_proxy.py
```

## Usage

```bash
# interactive chat
./memos

# pick a model
./memos deepseek-r1

# one-shot
./memos run qwen3-32b "explain monads"

# list models
./memos list

# use with aider
./memos aider
./memos aider deepseek-r1

# just the proxy server
./memos serve
./memos stop
```

## How it works

```
ollama run qwen3-32b
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
