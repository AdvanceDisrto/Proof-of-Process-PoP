# iNNOVULIS CIH sovereign software node: one-command Windows setup.
# No Auth0, JWT, Supabase credential, mock signatures or self-enrollment via HTTP.
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$keyFile = Join-Path $env:LOCALAPPDATA "iNNOVULIS\CIH\signing-keys.json"
$identityFile = Join-Path $env:LOCALAPPDATA "iNNOVULIS\CIH\local-krdid-identity.json"
$logs = Join-Path $env:LOCALAPPDATA "iNNOVULIS\CIH\logs"
$branch = "feature/innovulis-cih-sovereign-portal-20261110"
Push-Location $repo
try {
    if ((git branch --show-current) -ne $branch) {
        throw "Expected branch $branch. No branch changed."
    }
    if (git status --porcelain --untracked-files=no) {
        throw "Tracked local modifications exist; aborting before update."
    }
    git pull --ff-only origin $branch
    if ($LASTEXITCODE -ne 0) { throw "Safe Git fast-forward failed." }

    Write-Host "[CIH] RUNNING ALL TESTS" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup-cih-windows.ps1" -TestOnly
    if ($LASTEXITCODE -ne 0) { throw "CIH tests failed." }
    if (!(Test-Path $python)) { throw "Virtual Python environment missing." }

    if (!(Test-Path $keyFile)) {
        & $python -m cih_api.provision_keys
        if ($LASTEXITCODE -ne 0) { throw "Node key provisioning failed." }
    }
    if (!(Test-Path $identityFile)) {
        & $python -m cih_api.krdid init-local
        if ($LASTEXITCODE -ne 0) { throw "Local .krdid identity initialization failed." }
    }

    $enrollments = (& $python -m cih_api.krdid list) -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0 -or $enrollments -notmatch "local-test-node\.krdid ENROLLED") {
        throw "Local .krdid identity is not enrolled in current trusted registry. Do not auto-accept an untrusted key."
    }

    $node = Get-Content $keyFile -Raw | ConvertFrom-Json
    if ([Convert]::FromBase64String($node.CIH_ED25519_PRIVATE_KEY_B64).Length -ne 32 -or [Convert]::FromBase64String($node.CIH_ED25519_PUBLIC_KEY_B64).Length -ne 32) {
        throw "Malformed persistent CIH node keypair."
    }
    $env:CIH_ED25519_PRIVATE_KEY_B64 = $node.CIH_ED25519_PRIVATE_KEY_B64
    $env:CIH_ED25519_PUBLIC_KEY_B64 = $node.CIH_ED25519_PUBLIC_KEY_B64
    $env:CIH_ALLOWED_ORIGINS = "https://artifactgptm.com,https://www.artifactgptm.com,https://igptm-matrix-artifact-preview.onrender.com"

    $endpoint = "http://127.0.0.1:8000"
    $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq "127.0.0.1" } | Select-Object -First 1
    if ($listener) {
        $oldPid = [int]$listener.OwningProcess
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $oldPid"
        if (!$process -or $process.CommandLine -notmatch "uvicorn\s+cih_api\.app:app") {
            throw "Port 8000 belongs to an unrecognized process. Nothing stopped."
        }
        $old = Invoke-RestMethod "$endpoint/api/v1/health" -TimeoutSec 4
        if ($old.service -ne "cih-evidence-api") { throw "Unexpected service on port 8000" }
        Write-Host "[CIH] Replacing confirmed old CIH server PID $oldPid" -ForegroundColor Cyan
        Stop-Process -Id $oldPid
        for ($n=0; $n -lt 30; $n++) {
            if (!(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Milliseconds 300
        }
        if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
            throw "Port 8000 is still occupied."
        }
    }

    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    $outLog = Join-Path $logs "sovereign.stdout.log"
    $errLog = Join-Path $logs "sovereign.stderr.log"
    $server = Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "cih_api.app:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $repo -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru

    $health = $null
    for ($n=0; $n -lt 40; $n++) {
        try {
            $health = Invoke-RestMethod "$endpoint/api/v1/health" -TimeoutSec 2
            if ($health.status -eq "RUNNING") { break }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (!$health -or $health.status -ne "RUNNING") {
        throw "CIH failed to boot. Inspect $errLog"
    }
    if ($health.auth_provider -ne "LOCAL_KRDID_ED25519" -or !$health.auth_configured -or !$health.signer_configured -or !$health.trusted_key_configured -or !$health.storage_configured) {
        throw "Sovereign CIH readiness incomplete; inspect health response."
    }

    Write-Host "[CIH] PERFORMING REAL SIGNED LOCAL HTTP RECEIPT" -ForegroundColor Cyan
    & $python -m cih_api.krdid smoke --url $endpoint
    if ($LASTEXITCODE -ne 0) { throw "Actual receipt issuance or verification failed." }

    Write-Host "CIH SOVEREIGN SOFTWARE PROCESS VERIFIED" -ForegroundColor Green
    Write-Host "PID: $($server.Id)"
    Write-Host "Swagger: $endpoint/docs"
    Write-Host "Registry: $($health.krdid_enrolled_count) enrolled identities"
    Write-Host "Storage: $($health.storage_provider)"
    Write-Host "Not hardware attestation, independent truth or replicated consensus."
}
finally {
    foreach ($name in @("CIH_ED25519_PRIVATE_KEY_B64","CIH_ED25519_PUBLIC_KEY_B64","CIH_ALLOWED_ORIGINS")) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    $node = $null
    Pop-Location
}
