$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка Report Agent pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_backtest_report_generation.py `
        tests/unit/test_report_agent.py `
        tests/unit/test_check_report_pipeline.py `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка Report Agent pipeline прошла."
