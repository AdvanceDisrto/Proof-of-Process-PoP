param([switch]$TestOnly)
# iNNOVULIS CIH ΔiΔ — safe Windows PowerShell setup from repository root.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $made = $false
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.12 --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                & py -3.12 -m venv .venv
                if ($LASTEXITCODE -ne 0) { throw "Could not create Python 3.12 virtual environment." }
                $made = $true
            }
        }
        if (-not $made) {
            & python -m venv .venv
            if ($LASTEXITCODE -ne 0) { throw "Could not create Python virtual environment." }
        }
    }
    & $python -m pip install -r cih_api\requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "Installing dependencies failed." }
    & $python -m pytest -q cih_api
    if ($LASTEXITCODE -ne 0) { throw "CIH tests failed; refusing to start server." }
    if ($TestOnly) {
        Write-Host "CIH Windows setup verified successfully." -ForegroundColor Green
        return
    }
    Write-Host "Starting CIH loopback-only development server." -ForegroundColor Green
    Write-Host "Health: http://127.0.0.1:8000/api/v1/health"
    Write-Host "API docs: http://127.0.0.1:8000/docs"
    Write-Host "Authentication and signed receipt issuance require verified Auth0 and pinned persistent keys." -ForegroundColor Yellow
    & $python -m uvicorn cih_api.app:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
