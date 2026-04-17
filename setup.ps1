# memos-proxy stack setup — Windows (PowerShell)
# Run with: .\setup.ps1
# If blocked by execution policy: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"

function ok   { param($msg) Write-Host "[ok] $msg"    -ForegroundColor Green  }
function warn { param($msg) Write-Host "[warn] $msg"  -ForegroundColor Yellow }
function fail { param($msg) Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "memos-proxy stack setup"
Write-Host "========================"
Write-Host ""

# --- prerequisites ---

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    fail "Docker is not installed. Get it at https://docs.docker.com/get-docker/"
}
try { docker info 2>&1 | Out-Null } catch { fail "Docker daemon is not running. Start Docker Desktop and re-run." }
ok "Docker"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    fail "Ollama is not installed. Get it at https://ollama.com/download"
}
ok "Ollama"

# --- .env ---

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    warn ".env created from .env.example — open it and set MEMOS_API_KEY before continuing."
    exit 0
}

$envContent = Get-Content ".env" -Raw
if ($envContent -match "your-key-here") {
    fail ".env still has the placeholder key. Edit .env and set MEMOS_API_KEY=<your-real-key>"
}
ok ".env"

# --- docker services ---

Write-Host ""
Write-Host "Starting Docker services..."
docker compose up -d --build
ok "memos-proxy       -> http://localhost:11435"
ok "ollama-mcp-bridge -> http://localhost:11436  (Memos models + MCP tools)"
ok "open-webui        -> http://localhost:3333"

# --- openclaw ---

Write-Host ""
Write-Host "Installing OpenClaw..."

$openclawInstalled = Get-Command openclaw -ErrorAction SilentlyContinue

if ($openclawInstalled) {
    warn "OpenClaw already installed, skipping install."
} else {
    $env:OLLAMA_HOST = "http://localhost:11436"
    try {
        ollama launch openclaw --headless
        ok "OpenClaw installed"
    } catch {
        warn "OpenClaw install failed — run manually: `$env:OLLAMA_HOST='http://localhost:11436'; ollama launch openclaw"
    }
}

# Start OpenClaw gateway pointed at the bridge
if (Get-Command openclaw -ErrorAction SilentlyContinue) {
    $env:OLLAMA_HOST = "http://localhost:11436"
    Start-Process -NoNewWindow -FilePath "openclaw" -ArgumentList "gateway", "start", "--headless"
    ok "OpenClaw gateway started (using Memos models via bridge)"
}

Write-Host ""
Write-Host "Done. Open http://localhost:3333 to start chatting." -ForegroundColor Green
Write-Host ""
Write-Host "  Memos models available:"
Write-Host "    qwen3-32b  .  deepseek-r1  .  qwen2.5-72b-instruct"
Write-Host ""
Write-Host "  To stop everything:"
Write-Host "    docker compose down; openclaw gateway stop"
Write-Host ""
