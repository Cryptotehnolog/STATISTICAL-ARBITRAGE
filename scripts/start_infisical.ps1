param(
    [string]$ComposeFile = "infra/infisical/docker-compose.yml",
    [string]$EnvPath = "infra/infisical/.env",
    [string]$ProjectName = "stat-arb-infisical",
    [switch]$Pull
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $repoRoot $ComposeFile
$envFile = Join-Path $repoRoot $EnvPath

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "Infisical .env не найден: $EnvPath. Сначала запустите scripts/init_infisical_env.ps1."
}

Push-Location (Split-Path -Parent $composePath)
try {
    if ($Pull) {
        Write-Output "Обновление Docker images для Infisical..."
        docker compose --env-file $envFile -p $ProjectName -f $composePath pull
    }

    Write-Output "Запуск локального Infisical stack..."
    docker compose --env-file $envFile -p $ProjectName -f $composePath up -d
    Write-Output "Infisical запускается. UI: http://localhost:$((Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^INFISICAL_HOST_PORT=' }) -replace '^INFISICAL_HOST_PORT=', '')"
}
finally {
    Pop-Location
}
