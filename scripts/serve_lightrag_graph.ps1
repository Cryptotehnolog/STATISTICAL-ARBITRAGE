param(
    [int]$Port = 8765,
    [string]$Bind = "127.0.0.1",
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$exportScript = Join-Path $PSScriptRoot "export_lightrag_graph.ps1"
$viewerPath = Join-Path $repoRoot "docs\knowledge_graph\index.html"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

if (-not $SkipExport) {
    & $exportScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $viewerPath)) {
    Write-Error "Expected generated viewer at $viewerPath. Run scripts/export_lightrag_graph.ps1 first."
}

$url = "http://$Bind`:$Port/docs/knowledge_graph/index.html"
Write-Output "Serving LightRAG graph viewer at $url"
Write-Output "Press Ctrl+C to stop the server."

Push-Location $repoRoot
try {
    & $python -m http.server $Port --bind $Bind
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
