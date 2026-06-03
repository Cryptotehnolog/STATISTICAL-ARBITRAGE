param(
    [switch]$SkipApeRAG,
    [switch]$SkipInfisical,
    [switch]$SkipOmniRoute,
    [switch]$SkipEmbeddingServer,
    [switch]$SkipChecks
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

function Assert-DockerAvailable {
    try {
        docker version --format "{{.Server.Version}}" | Out-Null
    }
    catch {
        Write-Error "Docker недоступен. Запустите Docker Desktop и повторите команду."
    }
}

Write-Output "Запуск runtime-инфраструктуры проекта..."
Write-VmmemMemory -Label "До запуска:"

Push-Location $repoRoot
try {
    $needsDocker = -not ($SkipApeRAG -and $SkipInfisical -and $SkipOmniRoute)
    if ($needsDocker) {
        Assert-DockerAvailable
    }

    if (-not $SkipEmbeddingServer) {
        Write-Output "- Запуск локального ApeRAG embedding server"
        .\scripts\start_aperag_embedding_server.ps1 | Write-Output
    }

    if (-not $SkipOmniRoute) {
        Write-Output "- Запуск OmniRoute container"
        $omniRoute = docker ps -a --filter "name=^/omniroute$" --format "{{.Names}}" |
            Select-Object -First 1
        if ($omniRoute) {
            docker start omniroute | Out-Null
            Write-Output "OmniRoute запущен."
        }
        else {
            Write-Error "OmniRoute container не найден. Создайте его перед запуском runtime-инфраструктуры."
        }
    }

    if (-not $SkipInfisical) {
        Write-Output "- Запуск Infisical Docker stack"
        .\scripts\start_infisical.ps1 | Write-Output
    }

    if (-not $SkipApeRAG) {
        Write-Output "- Запуск ApeRAG Docker stack"
        .\scripts\start_aperag.ps1 | Write-Output
    }

    if (-not $SkipChecks) {
        Write-Output "- Быстрая проверка runtime-инфраструктуры"
        if (-not $SkipInfisical) {
            .\scripts\check_infisical.ps1 | Write-Output
        }
        if (-not $SkipApeRAG) {
            .\scripts\check_aperag.ps1 | Write-Output
        }
        if (-not $SkipOmniRoute) {
            .\scripts\check_omniroute.ps1 | Write-Output
        }
    }
}
finally {
    Pop-Location
}

Write-VmmemMemory -Label "После запуска:"
Write-Output "Runtime-инфраструктура запущена."
