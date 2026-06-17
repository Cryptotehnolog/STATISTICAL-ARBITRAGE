$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$reportAgentPath = Join-Path $repoRoot "src\stat_arb\agents\report.py"

Write-Output "Проверка Report Agent pipeline..."

$reportAgentSource = Get-Content -LiteralPath $reportAgentPath -Raw
if (
    $reportAgentSource -notmatch "AgentAuditEvent" -or
    $reportAgentSource -notmatch "audit_writer\.append" -or
    $reportAgentSource -notmatch "report_artifacts_generated"
) {
    Write-Error "Report Agent должен писать operator-safe AgentAuditEvent через audit_writer после registry artifacts."
}

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
