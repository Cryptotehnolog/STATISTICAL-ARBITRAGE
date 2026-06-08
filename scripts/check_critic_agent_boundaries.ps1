$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentPath = Join-Path $repoRoot "src\stat_arb\agents\critic.py"

if (-not (Test-Path -LiteralPath $agentPath)) {
    Write-Error "Critic Agent boundary не найден: $agentPath"
}

$source = Get-Content -LiteralPath $agentPath -Raw

if ($source -match "ApeRAGMemoryClient|write_markdown_document|aperag_client") {
    Write-Error "Critic Agent не должен писать напрямую в ApeRAG; используйте MemoryAgentService."
}

if ($source -notmatch "MemoryWriteRequest" -or $source -notmatch "memory_service\.write") {
    Write-Error "Critic Agent summary должен проходить через MemoryAgentService-compatible writer."
}

if (
    $source -notmatch "StoredCriticReview" -or
    $source -notmatch "session\.add\(stored\)" -or
    $source -notmatch "session\.flush\(\)"
) {
    Write-Error "Critic Agent должен писать structured review в registry перед memory summary."
}

if ($source -match "max_turnover: float =|approve_when_no_issues: bool =|reject_issue_prefixes: tuple\\[str, \\.\\.\\.\\] =") {
    Write-Error "Critic Agent не должен прятать research-impacting defaults в policy config."
}

Write-Output "Проверка Critic Agent boundaries прошла."
