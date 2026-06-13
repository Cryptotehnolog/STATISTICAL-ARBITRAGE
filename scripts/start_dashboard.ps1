param(
    [int]$Port = 8501,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $repoRoot "data\dashboard"
$pidFile = Join-Path $runtimeDir "dashboard.pid"
$stdoutLogFile = Join-Path $runtimeDir "dashboard.out.log"
$stderrLogFile = Join-Path $runtimeDir "dashboard.err.log"
$appPath = Join-Path $repoRoot "src\stat_arb\dashboard\app.py"
$uvExe = "uv"

if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

function Stop-DashboardProcess {
    if (Test-Path -LiteralPath $pidFile) {
        $pidValue = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pidValue) {
            $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force
                Write-Output "Dashboard остановлен: PID $($process.Id)"
            }
        }
        Remove-Item -LiteralPath $pidFile -Force
        return
    }

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($connection) {
        Stop-Process -Id $connection.OwningProcess -Force
        Write-Output "Dashboard остановлен: PID $($connection.OwningProcess)"
    }
    else {
        Write-Output "Dashboard не был запущен на http://localhost:$Port"
    }
}

if ($Stop) {
    Stop-DashboardProcess
    exit 0
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$Port" -UseBasicParsing -TimeoutSec 3
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        Write-Output "Dashboard уже запущен: http://localhost:$Port"
        exit 0
    }
}
catch {
    # Dashboard is not responding yet.
}

$streamlitArgs = @(
    "run",
    "streamlit",
    "run",
    "src\stat_arb\dashboard\app.py",
    "--server.port",
    "$Port",
    "--server.address",
    "localhost",
    "--server.headless",
    "true",
    "--browser.gatherUsageStats",
    "false"
)

Start-Process `
    -FilePath $uvExe `
    -ArgumentList $streamlitArgs `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLogFile `
    -RedirectStandardError $stderrLogFile `
    -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($connection) {
                Set-Content -LiteralPath $pidFile -Value $connection.OwningProcess
            }
            Write-Output "Dashboard запущен: http://localhost:$Port"
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

Write-Error "Dashboard не стартовал за 45 секунд. Логи: $stdoutLogFile, $stderrLogFile"
