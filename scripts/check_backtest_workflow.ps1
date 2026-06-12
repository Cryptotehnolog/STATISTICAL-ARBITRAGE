$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка backtest workflow..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_backtest_workflow.py `
        tests/unit/test_cli_data.py::test_experiment_execute_stage_runs_backtesting_and_completes_task `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка backtest workflow прошла."
