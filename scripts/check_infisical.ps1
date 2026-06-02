param(
    [string]$ComposeFile = "infra/infisical/docker-compose.yml",
    [string]$EnvPath = "infra/infisical/.env",
    [string]$ProjectName = "stat-arb-infisical",
    [string]$BaseUrl = "",
    [int]$TimeoutSeconds = 20,
    [int]$StartupWaitSeconds = 90
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $repoRoot $ComposeFile
$envFile = Join-Path $repoRoot $EnvPath

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "Infisical .env не найден: $EnvPath. Сначала запустите scripts/init_infisical_env.ps1."
}

if (-not $BaseUrl) {
    $portLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^INFISICAL_HOST_PORT=" } | Select-Object -First 1
    $port = $portLine -replace "^INFISICAL_HOST_PORT=", ""
    if (-not $port) {
        $port = "8080"
    }
    $BaseUrl = "http://localhost:$port"
}

Write-Output "Проверка Docker stack Infisical..."
$services = docker compose --env-file $envFile -p $ProjectName -f $composePath ps --format json | ConvertFrom-Json
if (-not $services) {
    Write-Error "Docker stack Infisical не запущен."
}

$badServices = @($services | Where-Object { $_.State -ne "running" })
if ($badServices.Count -gt 0) {
    $names = ($badServices | ForEach-Object { "$($_.Name):$($_.State)" }) -join ", "
    Write-Error "Не все Infisical services запущены: $names"
}

Write-Output "Проверка Infisical status endpoint: $BaseUrl/api/status"
$deadline = (Get-Date).AddSeconds($StartupWaitSeconds)
$lastError = $null
$response = $null

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "$BaseUrl/api/status" `
            -Method Get `
            -TimeoutSec $TimeoutSeconds

        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            break
        }
        $lastError = "HTTP $($response.StatusCode)"
    }
    catch {
        $lastError = $_.Exception.Message
    }
    Start-Sleep -Seconds 3
}

if (-not $response -or $response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
    Write-Error "Infisical status endpoint не готов: $lastError"
}

Write-Output "Infisical доступен: $BaseUrl"
