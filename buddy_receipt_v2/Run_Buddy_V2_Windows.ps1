param([switch]$Serve)
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $base
try {
    $registryRoot = $base
    if (!(Test-Path (Join-Path $registryRoot 'brain_registry.py'))) {
        $registryRoot = Split-Path -Parent $base
    }
    if (!(Test-Path (Join-Path $registryRoot 'brain_registry.py'))) {
        throw 'brain_registry.py not found in demo folder or its parent.'
    }
    $env:PYTHONPATH = $registryRoot + ';' + $base
    # PowerShell 5.1 can default to cp1252; Python emits Unicode test checkmarks.
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUTF8 = '1'
    Write-Host 'BUDDY SIGNED RECEIPTS V2 - SOFTWARE DEMO TESTS' -ForegroundColor Cyan
    Write-Host ('Working directory: ' + $base)
    $cihPython = Join-Path $env:USERPROFILE 'Proof-of-Process-PoP\.venv\Scripts\python.exe'
    if (Test-Path $cihPython) { $py = $cihPython }
    else {
        $found = Get-Command python.exe -ErrorAction SilentlyContinue
        if (!$found) { throw 'Python is not installed and CIH .venv could not be found.' }
        $py = $found.Source
    }
    $nodeCmd = Get-Command node.exe -ErrorAction SilentlyContinue
    if (!$nodeCmd) { throw 'Node.js is required for cross-language tests.' }
    & $py (Join-Path $registryRoot 'brain_registry.py') --tests
    if ($LASTEXITCODE -ne 0) { throw 'BRAIN_REGISTRY_21_TESTS_FAILED' }
    & $py -m unittest -v test_v2
    if ($LASTEXITCODE -ne 0) { throw 'BUDDY_V2_PYTHON_TESTS_FAILED' }
    & $nodeCmd.Source test_v2_node.cjs
    if ($LASTEXITCODE -ne 0) { throw 'BUDDY_V2_CROSS_LANGUAGE_TESTS_FAILED' }
    & $nodeCmd.Source test_verifier_ui.cjs
    if ($LASTEXITCODE -ne 0) { throw 'BUDDY_V2_HTML_UI_TESTS_FAILED' }
    Write-Host 'BUDDY_V2_SOFTWARE_TESTS_PASS' -ForegroundColor Green
    if ($Serve) {
        Write-Host 'Open http://127.0.0.1:8768/verifier.html' -ForegroundColor Yellow
        Write-Host 'This server remains in the foreground; stop it with Ctrl+C.'
        & $py -m http.server 8768 --bind 127.0.0.1
    }
}
finally { Pop-Location }
