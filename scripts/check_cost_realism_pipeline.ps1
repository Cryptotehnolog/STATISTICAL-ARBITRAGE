$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка capacity/cost realism pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_backtest_realism.py `
        tests/unit/test_backtest_sensitivity.py `
        tests/unit/test_critic_agent.py::test_critic_cost_realism_detection_flags_capacity_and_execution_scenarios `
        tests/unit/test_check_cost_realism_pipeline.py `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка capacity/cost realism pipeline прошла."
