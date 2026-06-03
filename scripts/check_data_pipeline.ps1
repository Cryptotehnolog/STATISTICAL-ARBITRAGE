$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

Write-Output "Проверка data pipeline checkpoint..."
Push-Location $repoRoot
try {
    & $python -m stat_arb.scripts.check_data_pipeline
}
finally {
    Pop-Location
}
