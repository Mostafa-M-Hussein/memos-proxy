#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
fail() { echo -e "${RED}[error]${NC} $1"; exit 1; }

echo ""
echo "memos-proxy stack setup"
echo "========================"
echo ""

# --- prerequisites ---

command -v docker &>/dev/null || fail "Docker is not installed. Get it at https://docs.docker.com/get-docker/"
docker info &>/dev/null       || fail "Docker daemon is not running. Start Docker and re-run."
ok "Docker"

command -v ollama &>/dev/null || fail "Ollama is not installed. Get it at https://ollama.com/download"
ok "Ollama"

# --- .env ---

if [ ! -f .env ]; then
  cp .env.example .env
  warn ".env created from .env.example — open it and set your MEMOS_API_KEY before continuing."
  exit 0
fi

if grep -q "your-key-here" .env; then
  fail ".env still has the placeholder key. Edit .env and set MEMOS_API_KEY=<your-real-key>"
fi

ok ".env"

# --- docker services ---

echo ""
echo "Starting Docker services..."
docker compose up -d --build
ok "memos-proxy   → http://localhost:11435"
ok "ollama-mcp-bridge → http://localhost:11436  (Memos models + MCP tools)"
ok "open-webui    → http://localhost:3333"

# --- openclaw ---

echo ""
echo "Installing OpenClaw..."

if command -v openclaw &>/dev/null; then
  warn "OpenClaw already installed, skipping install."
else
  OLLAMA_HOST=http://localhost:11436 ollama launch openclaw --headless || \
    warn "OpenClaw install failed — run manually: OLLAMA_HOST=http://localhost:11436 ollama launch openclaw"
fi

# Point OpenClaw's gateway at the memos bridge
if command -v openclaw &>/dev/null; then
  OLLAMA_HOST=http://localhost:11436 openclaw gateway start --headless 2>/dev/null &
  ok "OpenClaw gateway started (using Memos models via bridge)"
fi

echo ""
echo "Done. Open http://localhost:3333 to start chatting."
echo ""
echo "  Memos models available:"
echo "    qwen3-32b · deepseek-r1 · qwen2.5-72b-instruct"
echo ""
echo "  To stop everything:"
echo "    docker compose down && openclaw gateway stop"
echo ""
