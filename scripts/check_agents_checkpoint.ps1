$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка Task 14: совместимость agent boundaries 1-13..."

Push-Location $repoRoot
try {
    .\scripts\check_data_pipeline.ps1
    .\scripts\check_memory_agent_pipeline.ps1
    .\scripts\check_hypothesis_pipeline.ps1
    .\scripts\check_statistical_pipeline.ps1
    .\scripts\check_backtest_pipeline.ps1
    .\scripts\check_critic_pipeline.ps1
    .\scripts\check_report_pipeline.ps1
    .\scripts\check_coordinator_pipeline.ps1

    uv run pytest `
        tests/integration/test_agents_checkpoint_integration.py `
        tests/unit/test_check_agents_checkpoint.py `
        -q `
        --no-cov `
        -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка Task 14 прошла."
