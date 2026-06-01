$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$unitCheck = Join-Path $PSScriptRoot "check_unit.ps1"
$packageDataDir = Join-Path $repoRoot "src\stat_arb\data"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

if (Test-Path -LiteralPath $packageDataDir) {
    Write-Error "Runtime data must not live under src/stat_arb/data. Use the top-level data/ directory instead."
}

Push-Location $repoRoot
try {
    & $python -m ruff check --no-cache src tests
    & $unitCheck
}
finally {
    Pop-Location
}
