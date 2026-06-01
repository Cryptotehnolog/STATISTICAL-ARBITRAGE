$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$unitCheck = Join-Path $PSScriptRoot "check_unit.ps1"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

Push-Location $repoRoot
try {
    & $python -m ruff check --no-cache src tests
    & $unitCheck
}
finally {
    Pop-Location
}
