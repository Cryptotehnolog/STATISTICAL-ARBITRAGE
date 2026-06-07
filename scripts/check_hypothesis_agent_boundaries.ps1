$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentPath = Join-Path $repoRoot "src\stat_arb\agents\hypothesis.py"

if (-not (Test-Path -LiteralPath $agentPath)) {
    Write-Error "Hypothesis Agent boundary не найден: $agentPath"
}

$source = Get-Content -LiteralPath $agentPath -Raw

if ($source -match "ApeRAGMemoryClient|write_markdown_document|aperag_client") {
    Write-Error "Hypothesis Agent не должен писать напрямую в ApeRAG; используйте MemoryAgentService."
}

if ($source -notmatch "MemoryWriteRequest" -or $source -notmatch "memory_service\.write") {
    Write-Error "Hypothesis Agent summary должен проходить через MemoryAgentService-compatible writer."
}

$hasRegistryAdd = $source.Contains("session.add(")
$hasRegistryFlush = $source.Contains("session.flush()")
if ($source -notmatch "Hypothesis" -or -not $hasRegistryAdd -or -not $hasRegistryFlush) {
    Write-Error "Hypothesis Agent должен писать structured hypotheses в registry перед memory summary."
}

if ($source -match "min_abs_correlation: float =|min_market_cap: int =|max_pairs: int =") {
    Write-Error "Hypothesis Agent не должен прятать research-impacting defaults в generation config."
}

Write-Output "Проверка Hypothesis Agent boundaries прошла."
