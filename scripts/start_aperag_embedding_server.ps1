param(
    [int]$Port = 18101,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $repoRoot "data\aperag"
$pidFile = Join-Path $runtimeDir "embedding_server.pid"
$stdoutLogFile = Join-Path $runtimeDir "embedding_server.out.log"
$stderrLogFile = Join-Path $runtimeDir "embedding_server.err.log"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if ($Stop) {
    if (Test-Path -LiteralPath $pidFile) {
        $pidValue = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pidValue) {
            $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force
                Write-Output "ApeRAG embedding server остановлен: PID $($process.Id)"
            }
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
    else {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($connection) {
            Stop-Process -Id $connection.OwningProcess -Force
            Write-Output "ApeRAG embedding server остановлен: PID $($connection.OwningProcess)"
        }
        else {
            Write-Output "ApeRAG embedding server PID file не найден, порт $Port свободен."
        }
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    $pythonExe = "python"
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
    if ($health.status -eq "healthy") {
        Write-Output "ApeRAG embedding server уже запущен: http://127.0.0.1:$Port"
        exit 0
    }
}
catch {
    # Server is not running yet.
}

$quotedPython = '"' + $pythonExe + '"'
$quotedRoot = '"' + $repoRoot + '"'
$quotedStdout = '"' + $stdoutLogFile + '"'
$quotedStderr = '"' + $stderrLogFile + '"'
$command = "cd /d $quotedRoot && start `"stat-arb-aperag-embedding`" /b $quotedPython -m uvicorn --app-dir src stat_arb.scripts.openai_embedding_server:app --host 127.0.0.1 --port $Port > $quotedStdout 2> $quotedStderr"

cmd.exe /c $command

for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        if ($health.status -eq "healthy") {
            Write-Output "ApeRAG embedding server запущен: http://127.0.0.1:$Port"
            Write-Output "Model: $($health.model)"
            $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($connection) {
                Set-Content -LiteralPath $pidFile -Value $connection.OwningProcess
            }
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

Write-Error "ApeRAG embedding server не стартовал. Логи: $stdoutLogFile, $stderrLogFile"
