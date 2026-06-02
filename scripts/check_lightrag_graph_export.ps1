param(
    [string]$GraphMl = "",
    [string]$OutputDir = "",
    [int]$MinNodes = 1,
    [int]$MinEdges = 1
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$exportScript = Join-Path $PSScriptRoot "export_lightrag_graph.ps1"

if (-not $GraphMl) {
    $GraphMl = Join-Path $repoRoot "data\lightrag\graph_chunk_entity_relation.graphml"
}
if (-not $OutputDir) {
    $OutputDir = Join-Path $repoRoot "data\test_tmp\lightrag_graph_export_check"
}

if (-not (Test-Path -LiteralPath $GraphMl)) {
    Write-Error "Файл LightRAG GraphML не найден: $GraphMl"
}

& $exportScript -GraphMl $GraphMl -OutputDir $OutputDir
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$graphJson = Join-Path $OutputDir "graph.json"
$indexHtml = Join-Path $OutputDir "index.html"
if (-not (Test-Path -LiteralPath $graphJson)) {
    Write-Error "Ожидался экспортированный graph.json: $graphJson"
}
if (-not (Test-Path -LiteralPath $indexHtml)) {
    Write-Error "Ожидался экспортированный index.html: $indexHtml"
}

$graph = Get-Content -Raw -Path $graphJson | ConvertFrom-Json
$nodeCount = [int]$graph.meta.node_count
$edgeCount = [int]$graph.meta.edge_count

if ($nodeCount -lt $MinNodes) {
    Write-Error "Ожидалось минимум $MinNodes узлов, получено $nodeCount."
}
if ($edgeCount -lt $MinEdges) {
    Write-Error "Ожидалось минимум $MinEdges связей, получено $edgeCount."
}
if (-not $graph.nodes -or $graph.nodes.Count -ne $nodeCount) {
    Write-Error "Массив nodes в graph.json не совпадает с meta.node_count."
}
if (-not $graph.edges -or $graph.edges.Count -ne $edgeCount) {
    Write-Error "Массив edges в graph.json не совпадает с meta.edge_count."
}

Write-Output "Проверка экспорта графа LightRAG прошла: узлы $nodeCount, связи $edgeCount."
