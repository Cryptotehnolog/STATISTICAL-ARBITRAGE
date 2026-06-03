param(
    [int]$Port = 8765,
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$viewerRoot = Join-Path $repoRoot "docs\knowledge_graph"
$url = "http://127.0.0.1:$Port/"

function Stop-GraphServerPort {
    param([int]$ServerPort)

    $lines = netstat -ano | Select-String -Pattern "127\.0\.0\.1:$ServerPort\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim() -split "\s+")
        $processId = [int]$parts[-1]
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}
if (-not $SkipExport) {
    & (Join-Path $PSScriptRoot "export_aperag_graph.ps1")
}

try {
    $existing = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
    if ($existing.Content -like "*aperag-knowledge-graph*") {
        Write-Output "Сервер графа знаний ApeRAG уже запущен: $url"
        return
    }
    Stop-GraphServerPort -ServerPort $Port
    Start-Sleep -Seconds 1
} catch {
    # Сервер еще не запущен, продолжаем старт.
}

$stdoutLog = Join-Path $repoRoot "data\logs\aperag_graph_server.out.log"
$stderrLog = Join-Path $repoRoot "data\logs\aperag_graph_server.err.log"
New-Item -ItemType Directory -Path (Split-Path -Parent $stdoutLog) -Force | Out-Null

$command = "cmd.exe /c cd /d `"$viewerRoot`" && `"$python`" -m http.server $Port --bind 127.0.0.1 --directory `"$viewerRoot`" > `"$stdoutLog`" 2> `"$stderrLog`""
$shell = New-Object -ComObject WScript.Shell
$shell.Run($command, 0, $false) | Out-Null

Start-Sleep -Seconds 2
try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
    if ($response.Content -notlike "*aperag-knowledge-graph*") {
        Write-Error "На порту $Port отвечает не просмотрщик графа знаний ApeRAG."
    }
} catch {
    Write-Error "Сервер графа знаний ApeRAG не стартовал. Проверьте, свободен ли порт $Port. Логи: $stdoutLog, $stderrLog"
}

Write-Output "Сервер графа знаний ApeRAG запущен: $url"
