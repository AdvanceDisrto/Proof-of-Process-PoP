# iNNOVULIS CIH local setup — uses the actual Auth0/Ed25519 evidence backend.
# Run from the repository root in PowerShell.
# No fake PROVEN_TRUE/refuted-by-keyword logic.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")
if (-not (Test-Path ".venv")) {
    try { py -3.12 -m venv .venv }
    catch { python -m venv .venv }
}
$python = Join-Path (Resolve-Path ".venv") "Scripts\python.exe"
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $python -m pip install -r cih_api\requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
& $python -m pytest -q cih_api\test_app.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed; refusing to start API." }
Write-Host "CIH tests passed. Starting loopback-only development API." -ForegroundColor Green
Write-Host "Health: http://127.0.0.1:8000/api/v1/health"
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "Signing/receipt issuance remains disabled without valid Auth0 and secure signing env vars." -ForegroundColor Yellow
& $python -m uvicorn cih_api.app:app --host 127.0.0.1 --port 8000
