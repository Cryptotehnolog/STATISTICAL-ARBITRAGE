$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$unitCheck = Join-Path $PSScriptRoot "check_unit.ps1"
$packageDataDir = Join-Path $repoRoot "src\stat_arb\data"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

if (Test-Path -LiteralPath $packageDataDir) {
    Write-Error "Runtime data не должна жить в src/stat_arb/data. Используйте top-level директорию data/."
}

Push-Location $repoRoot
try {
    & $python -m ruff check --no-cache src tests
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    & $unitCheck
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
