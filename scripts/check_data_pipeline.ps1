$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$linuxPython = Join-Path $repoRoot ".venv/bin/python"
$python = if (Test-Path -LiteralPath $windowsPython) { $windowsPython } else { $linuxPython }
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $windowsPython или $linuxPython. Сначала выполните 'uv sync'."
}

Write-Output "Проверка data pipeline checkpoint..."
Push-Location $repoRoot
try {
    & $python -m stat_arb.scripts.check_data_pipeline
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
