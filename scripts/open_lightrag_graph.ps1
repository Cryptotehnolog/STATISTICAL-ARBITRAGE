param(
    [int]$Port = 8765,
    [string]$Bind = "127.0.0.1",
    [switch]$SkipExport,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$serveScript = Join-Path $PSScriptRoot "serve_lightrag_graph.ps1"
$url = "http://$Bind`:$Port/docs/knowledge_graph/index.html"

$serveArgs = @{
    Port = $Port
    Bind = $Bind
}

if ($SkipExport) {
    $serveArgs.SkipExport = $true
}

& $serveScript @serveArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $NoBrowser) {
    Start-Process $url
}

Write-Output "Viewer графа LightRAG: $url"
