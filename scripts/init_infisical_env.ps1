param(
    [string]$EnvPath = "infra/infisical/.env",
    [int]$Port = 8080,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$targetPath = Join-Path $repoRoot $EnvPath
$targetDir = Split-Path -Parent $targetPath

function New-RandomBase64 {
    param([int]$Bytes = 32)

    $buffer = [byte[]]::new($Bytes)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($buffer)
    }
    finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($buffer)
}

function New-RandomHex {
    param([int]$Bytes = 16)

    $buffer = [byte[]]::new($Bytes)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($buffer)
    }
    finally {
        $rng.Dispose()
    }
    return -join ($buffer | ForEach-Object { $_.ToString("x2") })
}

if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
    Write-Output "Infisical .env уже существует: $EnvPath"
    Write-Output "Для пересоздания используйте -Force. Старый файл содержит ключи шифрования, не удаляйте его без backup."
    exit 0
}

if (-not (Test-Path -LiteralPath $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

$postgresPassword = New-RandomHex -Bytes 24
$content = @"
# Локальная self-host конфигурация Infisical.
# Файл содержит bootstrap-secrets и не должен попадать в Git.

INFISICAL_IMAGE_TAG=latest
INFISICAL_HOST_PORT=$Port

ENCRYPTION_KEY=$(New-RandomHex -Bytes 16)
AUTH_SECRET=$(New-RandomBase64 -Bytes 32)

INFISICAL_POSTGRES_USER=infisical
INFISICAL_POSTGRES_PASSWORD=$postgresPassword
INFISICAL_POSTGRES_DB=infisical

SMTP_HOST=
SMTP_PORT=
SMTP_FROM_ADDRESS=
SMTP_FROM_NAME=
SMTP_USERNAME=
SMTP_PASSWORD=

OTEL_TELEMETRY_COLLECTION_ENABLED=false
OTEL_EXPORT_TYPE=prometheus
"@

Set-Content -LiteralPath $targetPath -Value $content -Encoding UTF8
Write-Output "Infisical .env создан: $EnvPath"
Write-Output "Ключи не выводятся в консоль. Сохраните backup этого файла перед удалением Docker volumes."
