$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-RequiredCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $global:LASTEXITCODE = 0
    & $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Проверка завершилась с ошибкой: $ScriptPath (exit code $LASTEXITCODE)"
    }
}

Write-Output "Проверка Task 14: совместимость agent boundaries 1-13..."

Push-Location $repoRoot
try {
    Invoke-RequiredCheck ".\scripts\check_data_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_memory_agent_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_hypothesis_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_statistical_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_backtest_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_critic_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_report_pipeline.ps1"
    Invoke-RequiredCheck ".\scripts\check_coordinator_pipeline.ps1"

    uv run pytest `
        tests/integration/test_agents_checkpoint_integration.py `
        tests/unit/test_check_agents_checkpoint.py `
        -q `
        --no-cov `
        -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка Task 14 прошла."
