param(
    [int]$Port = 8765,
    [string]$Bind = "127.0.0.1",
    [switch]$SkipExport,
    [switch]$Foreground,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$exportScript = Join-Path $PSScriptRoot "export_lightrag_graph.ps1"
$viewerPath = Join-Path $repoRoot "docs\knowledge_graph\index.html"
$pidPath = Join-Path $repoRoot "data\lightrag_graph_viewer_server_$Port.json"
$legacyPidPath = Join-Path $repoRoot "data\lightrag_graph_viewer_server.json"

function Stop-ViewerServer {
    $activePidPath = $pidPath
    if (-not (Test-Path -LiteralPath $activePidPath) -and (Test-Path -LiteralPath $legacyPidPath)) {
        $activePidPath = $legacyPidPath
    }

    if (-not (Test-Path -LiteralPath $activePidPath)) {
        Write-Output "No LightRAG graph viewer PID file found."
        return
    }

    $state = Get-Content -Raw -Path $activePidPath | ConvertFrom-Json
    $process = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $state.pid -Force
        Write-Output "Stopped LightRAG graph viewer server process $($state.pid)."
    }
    else {
        Write-Output "LightRAG graph viewer server process $($state.pid) is not running."
    }
    Remove-Item -LiteralPath $activePidPath -Force -ErrorAction SilentlyContinue
}

function Test-ViewerUrl {
    param(
        [string]$Url,
        [int]$TimeoutSec = 2
    )

    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri $Url `
            -TimeoutSec $TimeoutSec
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    }
    catch {
        return $false
    }
}

if ($Stop) {
    Stop-ViewerServer
    exit 0
}

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

if (Test-ViewerUrl -Url $url) {
    Write-Output "LightRAG graph viewer is already served at $url"
    exit 0
}

if (-not (Test-Path -LiteralPath (Split-Path $pidPath))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $pidPath) | Out-Null
}

Push-Location $repoRoot
try {
    if ($Foreground) {
        Write-Output "Serving LightRAG graph viewer at $url"
        Write-Output "Press Ctrl+C to stop the server."
        & $python -m http.server $Port --bind $Bind
        exit $LASTEXITCODE
    }

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList @("-m", "http.server", $Port, "--bind", $Bind) `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Seconds 1
    $started = $false
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        if (Test-ViewerUrl -Url $url) {
            $started = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not $started) {
        $maybeProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
        if ($maybeProcess) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Error "Failed to start LightRAG graph viewer server on $Bind`:$Port."
    }

    @{
        pid = $process.Id
        url = $url
        started_at = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -Path $pidPath -Encoding UTF8

    Write-Output "LightRAG graph viewer started at $url"
    Write-Output "Server process: $($process.Id)"
    Write-Output "Stop it with: .\scripts\serve_lightrag_graph.ps1 -Port $Port -Stop"
}
finally {
    Pop-Location
}
