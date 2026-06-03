param(
    [switch]$SkipApeRAG,
    [switch]$SkipInfisical,
    [switch]$SkipOmniRoute,
    [switch]$SkipEmbeddingServer,
    [switch]$ShutdownWsl
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Write-VmmemMemory {
    param([string]$Label)

    $process = Get-Process -Name "VmmemWSL" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $process) {
        Write-Output "$Label VmmemWSL не запущен."
        return
    }

    $memoryMb = [math]::Round($process.WorkingSet64 / 1MB, 0)
    Write-Output "$Label VmmemWSL memory: $memoryMb MB"
}

function Test-DockerAvailable {
    try {
        docker version --format "{{.Server.Version}}" | Out-Null
        return $true
    }
    catch {
        Write-Output "Docker недоступен. Возможно, Docker Desktop уже остановлен."
        return $false
    }
}

Write-Output "Остановка тяжелой runtime-инфраструктуры проекта..."
Write-VmmemMemory -Label "До остановки:"

Push-Location $repoRoot
try {
    if (-not $SkipEmbeddingServer) {
        Write-Output "- Остановка локального ApeRAG embedding server"
        .\scripts\start_aperag_embedding_server.ps1 -Stop | Write-Output
    }

    $needsDocker = -not ($SkipApeRAG -and $SkipInfisical -and $SkipOmniRoute)
    if ($needsDocker -and (Test-DockerAvailable)) {
        if (-not $SkipApeRAG) {
            Write-Output "- Остановка ApeRAG Docker stack"
            .\scripts\start_aperag.ps1 -Stop | Write-Output
        }

        if (-not $SkipInfisical) {
            Write-Output "- Остановка Infisical Docker stack"
            $composePath = Join-Path $repoRoot "infra\infisical\docker-compose.yml"
            $envFile = Join-Path $repoRoot "infra\infisical\.env"
            if (Test-Path -LiteralPath $envFile) {
                docker compose --env-file $envFile -p stat-arb-infisical -f $composePath stop
            }
            else {
                Write-Output "Infisical .env не найден, stack пропущен."
            }
        }

        if (-not $SkipOmniRoute) {
            Write-Output "- Остановка OmniRoute container"
            $omniRoute = docker ps -a --filter "name=^/omniroute$" --format "{{.Names}}" |
                Select-Object -First 1
            if ($omniRoute) {
                docker stop omniroute | Out-Null
                Write-Output "OmniRoute остановлен."
            }
            else {
                Write-Output "OmniRoute container не найден, пропущен."
            }
        }
    }

    if ($ShutdownWsl) {
        Write-Output "- Остановка WSL для освобождения памяти"
        wsl --shutdown
    }
}
finally {
    Pop-Location
}

Write-VmmemMemory -Label "После остановки:"
Write-Output "Runtime-инфраструктура остановлена без удаления данных."
