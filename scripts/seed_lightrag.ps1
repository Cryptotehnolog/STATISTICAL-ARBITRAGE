$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

Push-Location $repoRoot
try {
    & $python -m stat_arb.scripts.seed_lightrag @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
