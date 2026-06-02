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
    Write-Error "LightRAG GraphML file not found: $GraphMl"
}

& $exportScript -GraphMl $GraphMl -OutputDir $OutputDir
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$graphJson = Join-Path $OutputDir "graph.json"
$indexHtml = Join-Path $OutputDir "index.html"
if (-not (Test-Path -LiteralPath $graphJson)) {
    Write-Error "Expected exported graph JSON at $graphJson"
}
if (-not (Test-Path -LiteralPath $indexHtml)) {
    Write-Error "Expected exported graph HTML at $indexHtml"
}

$graph = Get-Content -Raw -Path $graphJson | ConvertFrom-Json
$nodeCount = [int]$graph.meta.node_count
$edgeCount = [int]$graph.meta.edge_count

if ($nodeCount -lt $MinNodes) {
    Write-Error "Expected at least $MinNodes node(s), got $nodeCount."
}
if ($edgeCount -lt $MinEdges) {
    Write-Error "Expected at least $MinEdges edge(s), got $edgeCount."
}
if (-not $graph.nodes -or $graph.nodes.Count -ne $nodeCount) {
    Write-Error "graph.json nodes array does not match meta.node_count."
}
if (-not $graph.edges -or $graph.edges.Count -ne $edgeCount) {
    Write-Error "graph.json edges array does not match meta.edge_count."
}

Write-Output "LightRAG graph export check passed: $nodeCount node(s), $edgeCount edge(s)."
