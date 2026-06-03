param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "serve_aperag_graph.ps1") -Port $Port
Start-Process "http://127.0.0.1:$Port/"
