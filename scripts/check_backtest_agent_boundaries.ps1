$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentPath = Join-Path $repoRoot "src\stat_arb\agents\backtest.py"

if (-not (Test-Path -LiteralPath $agentPath)) {
    Write-Error "Backtest Agent boundary не найден: $agentPath"
}

$source = Get-Content -LiteralPath $agentPath -Raw

if ($source -match "ApeRAGMemoryClient|write_markdown_document|aperag_client") {
    Write-Error "Backtest Agent не должен писать напрямую в ApeRAG; используйте MemoryAgentService."
}

if ($source -notmatch "MemoryWriteRequest" -or $source -notmatch "memory_service\.write") {
    Write-Error "Backtest Agent summary должен проходить через MemoryAgentService-compatible writer."
}

if (
    $source -notmatch "AgentAuditEvent" -or
    $source -notmatch "audit_writer\.append" -or
    $source -notmatch "backtest_result_persisted"
) {
    Write-Error "Backtest Agent должен писать operator-safe AgentAuditEvent через audit_writer после registry persistence."
}

if ($source -notmatch "StoredBacktestResult" -or $source -notmatch "session\.add\(stored\)" -or $source -notmatch "session\.flush\(\)") {
    Write-Error "Backtest Agent должен писать structured results в registry перед memory summary."
}

if ($source -notmatch "DataQualityReportRecord" -or $source -notmatch "passed data quality report") {
    Write-Error "Backtest Agent должен проверять passed DataQualityReport перед backtest persistence."
}

Write-Output "Проверка Backtest Agent boundaries прошла."
