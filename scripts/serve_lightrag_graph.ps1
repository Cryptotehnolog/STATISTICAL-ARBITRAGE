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
        Write-Output "PID-файл viewer-а LightRAG не найден."
        return
    }

    $state = Get-Content -Raw -Path $activePidPath | ConvertFrom-Json
    $process = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $state.pid -Force
        Write-Output "Остановлен процесс viewer-а LightRAG: $($state.pid)."
    }
    else {
        Write-Output "Процесс viewer-а LightRAG $($state.pid) не запущен."
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
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

if (-not $SkipExport) {
    & $exportScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $viewerPath)) {
    Write-Error "Сгенерированный viewer не найден: $viewerPath. Сначала выполните scripts/export_lightrag_graph.ps1."
}

$url = "http://$Bind`:$Port/docs/knowledge_graph/index.html"

if (Test-ViewerUrl -Url $url) {
    Write-Output "Viewer графа LightRAG уже доступен: $url"
    exit 0
}

if (-not (Test-Path -LiteralPath (Split-Path $pidPath))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $pidPath) | Out-Null
}

Push-Location $repoRoot
try {
    if ($Foreground) {
        Write-Output "Viewer графа LightRAG доступен: $url"
        Write-Output "Нажмите Ctrl+C, чтобы остановить server."
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
        Write-Error "Не удалось запустить viewer графа LightRAG на $Bind`:$Port."
    }

    @{
        pid = $process.Id
        url = $url
        started_at = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -Path $pidPath -Encoding UTF8

    Write-Output "Viewer графа LightRAG запущен: $url"
    Write-Output "Процесс server-а: $($process.Id)"
    Write-Output "Остановить: .\scripts\serve_lightrag_graph.ps1 -Port $Port -Stop"
}
finally {
    Pop-Location
}
