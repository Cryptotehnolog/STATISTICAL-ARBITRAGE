$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка statistical testing pipeline..."

Push-Location $repoRoot
try {
    $agentSource = Get-Content -Path "src/stat_arb/agents/statistical_testing.py" -Raw
    if (
        $agentSource -notmatch "AgentAuditEvent" -or
        $agentSource -notmatch "audit_writer\.append" -or
        $agentSource -notmatch "statistical_test_persisted"
    ) {
        Write-Error "Statistical Testing Agent должен писать operator-safe AgentAuditEvent через audit_writer после registry persistence."
    }

    uv run pytest `
        tests/unit/test_statistical_testing_agent.py `
        tests/unit/test_cointegration.py `
        tests/unit/test_stationarity.py `
        tests/unit/test_hedge_ratio.py `
        tests/unit/test_stability_diagnostics.py `
        tests/unit/test_mean_reversion.py `
        tests/unit/test_regime.py `
        tests/unit/test_zscore.py `
        tests/unit/test_validation_windows.py `
        tests/unit/test_statistical_properties.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка statistical testing pipeline прошла."
