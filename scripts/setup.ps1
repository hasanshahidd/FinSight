# FinSight AI — Windows quickstart
# Usage:  .\scripts\setup.ps1
# Bootstraps backend + frontend, seeds data, ingests knowledge base.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> FinSight AI bootstrap" -ForegroundColor Cyan

# --- env file
if (-not (Test-Path "$root\.env")) {
  Copy-Item "$root\.env.example" "$root\.env"
  Write-Host "    Created .env (edit OPENAI_API_KEY before continuing)" -ForegroundColor Yellow
}

# --- backend
Write-Host "==> Backend" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

Write-Host "    Seeding mock transactions..."
python scripts\seed_db.py

Write-Host "    Ingesting knowledge base..."
python scripts\ingest_docs.py

# --- frontend
Write-Host "==> Frontend" -ForegroundColor Cyan
Set-Location "$root\frontend"
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}
npm install --silent

Write-Host ""
Write-Host "==> Done. To run:" -ForegroundColor Green
Write-Host "    Terminal 1:  cd backend  ; .\.venv\Scripts\Activate.ps1 ; uvicorn app.main:app --reload --port 8000"
Write-Host "    Terminal 2:  cd frontend ; npm run dev"
Write-Host "    Terminal 3:  docker compose up -d   (in project root, for n8n + Redis)"
