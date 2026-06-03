$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$exportScript = Join-Path $PSScriptRoot "export_aperag_graph.ps1"
$graphJson = Join-Path $repoRoot "docs\knowledge_graph\graph.json"
$indexHtml = Join-Path $repoRoot "docs\knowledge_graph\index.html"

Write-Output "Проверка экспорта графа знаний ApeRAG..."
& $exportScript

if (-not (Test-Path -LiteralPath $graphJson)) {
    Write-Error "graph.json не создан: $graphJson"
}
if (-not (Test-Path -LiteralPath $indexHtml)) {
    Write-Error "index.html не найден: $indexHtml"
}

$graph = Get-Content -LiteralPath $graphJson -Raw | ConvertFrom-Json
if ($graph.source -ne "ApeRAG") {
    Write-Error "graph.json должен иметь source=ApeRAG"
}
if ([int]$graph.counts.nodes -le 0 -or [int]$graph.counts.edges -le 0) {
    Write-Error "ApeRAG graph пустой: nodes=$($graph.counts.nodes), edges=$($graph.counts.edges)"
}
if (-not (Select-String -LiteralPath $indexHtml -Pattern "aperag-knowledge-graph" -Quiet)) {
    Write-Error "index.html не похож на просмотрщик графа знаний ApeRAG."
}

Write-Output "Проверка экспорта графа знаний ApeRAG прошла: nodes=$($graph.counts.nodes), edges=$($graph.counts.edges)"
