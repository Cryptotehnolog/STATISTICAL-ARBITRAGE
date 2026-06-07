$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка backtest pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_backtest_core.py `
        tests/unit/test_backtest_costs.py `
        tests/unit/test_backtest_metrics.py `
        tests/unit/test_backtest_baseline.py `
        tests/unit/test_backtest_sensitivity.py `
        tests/unit/test_backtest_reproducibility.py `
        tests/unit/test_backtest_walk_forward.py `
        tests/unit/test_backtest_agent.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка backtest pipeline прошла."
