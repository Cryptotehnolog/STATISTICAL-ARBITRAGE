param(
    [switch]$Stop,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$aperagRoot = Join-Path $repoRoot "data\external\aperag"

if (-not (Test-Path -LiteralPath (Join-Path $aperagRoot "docker-compose.yml"))) {
    Write-Error "ApeRAG upstream clone не найден: $aperagRoot. Ожидался ignored clone из https://github.com/apecloud/ApeRAG."
}

Push-Location $aperagRoot
try {
    if ($Stop) {
        docker compose stop
        exit $LASTEXITCODE
    }

    if ($Restart) {
        docker compose restart
        exit $LASTEXITCODE
    }

    docker compose up -d --no-build
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
