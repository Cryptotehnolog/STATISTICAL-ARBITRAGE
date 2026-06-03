param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [string]$OutputDir = "docs\knowledge_graph",
    [int]$MaxNodes = 1000,
    [int]$MaxDepth = 3
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile
$outputPath = Join-Path $repoRoot $OutputDir
$graphJsonPath = Join-Path $outputPath "graph.json"
$indexPath = Join-Path $outputPath "index.html"

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
}
if (-not (Test-Path -LiteralPath $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath | Out-Null
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

if (-not $env:APERAG_API_BASE_URL -or -not $env:APERAG_API_KEY) {
    Write-Error "APERAG_API_BASE_URL или APERAG_API_KEY не заданы в $envPath"
}

$headers = @{ Authorization = "Bearer $env:APERAG_API_KEY" }

function Invoke-ApeRagJson {
    param(
        [string]$Path,
        [int]$TimeoutSec = 60
    )
    return Invoke-RestMethod -Method "GET" -Uri "$env:APERAG_API_BASE_URL$Path" -Headers $headers -TimeoutSec $TimeoutSec
}

$collections = Invoke-ApeRagJson -Path "/api/v1/collections?page=1&page_size=100"
$collection = $collections.items | Where-Object { $_.title -eq $CollectionTitle } | Select-Object -First 1
if (-not $collection) {
    Write-Error "ApeRAG collection не найдена: $CollectionTitle"
}

$labels = Invoke-ApeRagJson -Path "/api/v1/collections/$($collection.id)/graphs/labels"
$graph = Invoke-ApeRagJson -Path "/api/v1/collections/$($collection.id)/graphs?max_nodes=$MaxNodes&max_depth=$MaxDepth" -TimeoutSec 120

$nodes = @($graph.nodes)
$edges = @($graph.edges)
if ($nodes.Count -eq 0 -or $edges.Count -eq 0) {
    Write-Error "ApeRAG graph пустой: nodes=$($nodes.Count), edges=$($edges.Count)"
}

$exported = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    source = "ApeRAG"
    collection = [ordered]@{
        id = $collection.id
        title = $collection.title
    }
    counts = [ordered]@{
        labels = @($labels.labels).Count
        nodes = $nodes.Count
        edges = $edges.Count
    }
    labels = @($labels.labels)
    nodes = $nodes
    edges = $edges
}

$exported | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $graphJsonPath -Encoding UTF8

if (-not (Test-Path -LiteralPath $indexPath)) {
    Write-Error "Viewer index.html не найден: $indexPath"
}

Write-Output "ApeRAG graph export OK: labels=$(@($labels.labels).Count), nodes=$($nodes.Count), edges=$($edges.Count)"
Write-Output "Graph JSON: $graphJsonPath"
Write-Output "Viewer: $indexPath"
