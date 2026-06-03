param(
    [string]$ApiBaseUrl = "http://127.0.0.1:18000",
    [string]$FrontendUrl = "http://127.0.0.1:13000/web/",
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Output "- $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Output "Проверка ApeRAG..."

if (-not $SkipDocker) {
    Invoke-Check "Docker containers" {
        $required = @(
            "aperag-postgres",
            "aperag-redis",
            "aperag-qdrant",
            "aperag-es",
            "aperag-api",
            "aperag-celeryworker",
            "aperag-celerybeat",
            "aperag-frontend"
        )
        $containers = docker ps --format "{{.Names}}|{{.Status}}"
        foreach ($name in $required) {
            $line = $containers | Where-Object { $_ -like "$name|*" } | Select-Object -First 1
            if (-not $line) {
                Write-Error "ApeRAG container не запущен: $name"
            }
            if ($line -match "unhealthy|restarting|exited|dead") {
                Write-Error "ApeRAG container unhealthy: $line"
            }
        }
        Write-Output "ApeRAG containers OK: $($required.Count)"
    }
}
else {
    Write-Output "- Docker containers пропущены по флагу -SkipDocker"
}

Invoke-Check "API health" {
    $health = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -TimeoutSec 15
    if ($health.status -ne "healthy") {
        Write-Error "ApeRAG API health не healthy: $($health | ConvertTo-Json -Compress)"
    }
    Write-Output "ApeRAG API OK: $($health.service)"
}

Invoke-Check "API docs" {
    $response = Invoke-WebRequest -Uri "$ApiBaseUrl/docs" -UseBasicParsing -TimeoutSec 15
    if ($response.StatusCode -ne 200) {
        Write-Error "ApeRAG API docs вернул status $($response.StatusCode)"
    }
    Write-Output "ApeRAG API docs OK"
}

Invoke-Check "Local embedding endpoint" {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:18101/health" -TimeoutSec 15
    if ($health.status -ne "healthy") {
        Write-Error "ApeRAG embedding endpoint не healthy: $($health | ConvertTo-Json -Compress)"
    }
    Write-Output "ApeRAG embedding endpoint OK: $($health.model)"
}

Invoke-Check "Frontend" {
    try {
        $response = Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 0
        $statusCode = [int]$response.StatusCode
    }
    catch {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    if ($statusCode -notin @(200, 307, 308)) {
        Write-Error "ApeRAG frontend вернул status $statusCode"
    }
    Write-Output "ApeRAG frontend OK: HTTP $statusCode"
}

Write-Output "Проверка ApeRAG прошла."
