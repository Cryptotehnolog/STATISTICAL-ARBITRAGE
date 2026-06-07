param(
    [string]$EnvFile = "data\aperag\.env"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

if (-not $env:APERAG_API_BASE_URL) {
    Write-Error "APERAG_API_BASE_URL не задан в $envPath"
}
if (-not $env:APERAG_API_KEY) {
    Write-Error "APERAG_API_KEY не задан в $envPath"
}

$headers = @{
    Authorization = "Bearer $env:APERAG_API_KEY"
    "Content-Type" = "application/json"
}

$quota = Invoke-RestMethod `
    -Method "GET" `
    -Uri "$env:APERAG_API_BASE_URL/api/v1/quotas" `
    -Headers $headers `
    -TimeoutSec 60

$result = Invoke-RestMethod `
    -Method "POST" `
    -Uri "$env:APERAG_API_BASE_URL/api/v1/quotas/$($quota.user_id)/recalculate" `
    -Headers $headers `
    -TimeoutSec 60

$updatedQuota = Invoke-RestMethod `
    -Method "GET" `
    -Uri "$env:APERAG_API_BASE_URL/api/v1/quotas" `
    -Headers $headers `
    -TimeoutSec 60

Write-Output "Quota recalculation завершен: user=$($updatedQuota.username), success=$($result.success)"
$updatedQuota.quotas |
    Sort-Object quota_type |
    ForEach-Object {
        Write-Output "- $($_.quota_type): usage=$($_.current_usage), limit=$($_.quota_limit), remaining=$($_.remaining)"
    }

