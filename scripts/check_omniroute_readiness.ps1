param(
    [string]$ContainerName = "omniroute",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$Model = "my-ai",
    [string]$Provider = "kiro",
    [int]$TimeoutSeconds = 60,
    [int]$MaxChatLatencyMs = 30000,
    [int]$WarnTokenExpiresMinutes = 15,
    [int]$RecentLogTail = 300,
    [switch]$WarnOnly
)

$ErrorActionPreference = "Stop"

function Add-ReadinessIssue {
    param(
        [System.Collections.Generic.List[string]]$ReadinessIssue,
        [string]$Message
    )

    $ReadinessIssue.Add($Message) | Out-Null
    Write-Output "WARNING: $Message"
}

function New-OmniRouteHeaders {
    if ($env:OMNIROUTE_API_KEY) {
        return @{ Authorization = "Bearer $env:OMNIROUTE_API_KEY" }
    }
    return @{}
}

function Copy-OmniRouteSqlite {
    param([string]$ContainerName)

    $tempDir = Join-Path $env:TEMP "omniroute-readiness-$([guid]::NewGuid())"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    docker cp "${ContainerName}:/app/data/storage.sqlite" (Join-Path $tempDir "storage.sqlite") | Out-Null
    foreach ($sqliteSidecar in @("storage.sqlite-wal", "storage.sqlite-shm")) {
        docker cp "${ContainerName}:/app/data/$sqliteSidecar" (Join-Path $tempDir $sqliteSidecar) 2>$null
    }
    return $tempDir
}

Write-Output "Проверка OmniRoute readiness: $ContainerName / $Model"
$issues = [System.Collections.Generic.List[string]]::new()

$containerId = docker ps --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' не запущен."
}

$health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerName
if ($health -ne "healthy" -and $health -ne "none") {
    Add-ReadinessIssue -ReadinessIssue $issues -Message "Docker health='$health'."
}
else {
    Write-Output "Docker container OK: $ContainerName ($health)"
}

.\scripts\check_omniroute_state.ps1 -ContainerName $ContainerName -RequireMyAiCombo | Write-Output

$headers = New-OmniRouteHeaders
$ModelsPath = "/v1/models"
$ChatPath = "/v1/chat/completions"
$modelsResponse = Invoke-RestMethod `
    -Uri "$BaseUrl$($ModelsPath.Substring(3))" `
    -Method Get `
    -Headers $headers `
    -TimeoutSec $TimeoutSeconds
$modelIds = @($modelsResponse.data | ForEach-Object { $_.id })
if ($modelIds.Count -lt 1) {
    Add-ReadinessIssue -ReadinessIssue $issues -Message "Models endpoint вернул 0 models."
}
elseif ($modelIds -notcontains $Model) {
    Add-ReadinessIssue -ReadinessIssue $issues -Message "Model '$Model' отсутствует в /v1/models."
}
else {
    Write-Output "Models endpoint OK: $($modelIds.Count) model(s), '$Model' найден."
}

$body = @{
    model = $Model
    messages = @(
        @{
            role = "user"
            content = "Reply with OK only."
        }
    )
    temperature = 0
    max_tokens = 8
    stream = $false
} | ConvertTo-Json -Depth 10

$timer = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $chatResponse = Invoke-WebRequest `
        -UseBasicParsing `
        -Uri "$BaseUrl$($ChatPath.Substring(3))" `
        -Method Post `
        -ContentType "application/json" `
        -Headers $headers `
        -Body $body `
        -TimeoutSec $TimeoutSeconds
    $timer.Stop()
}
catch {
    $timer.Stop()
    Add-ReadinessIssue -ReadinessIssue $issues -Message "Chat endpoint failed: $($_.Exception.Message)"
}

if ($chatResponse) {
    if ($chatResponse.StatusCode -lt 200 -or $chatResponse.StatusCode -ge 300) {
        Add-ReadinessIssue -ReadinessIssue $issues -Message "Chat endpoint вернул HTTP $($chatResponse.StatusCode)."
    }
    elseif ($chatResponse.Content -notmatch "OK") {
        Add-ReadinessIssue -ReadinessIssue $issues -Message "Chat endpoint не вернул ожидаемый OK response."
    }
    else {
        Write-Output "Chat endpoint OK: $([int]$timer.ElapsedMilliseconds) ms"
    }
    if ($timer.ElapsedMilliseconds -gt $MaxChatLatencyMs) {
        Add-ReadinessIssue -ReadinessIssue $issues -Message "Chat latency $([int]$timer.ElapsedMilliseconds) ms выше порога $MaxChatLatencyMs ms."
    }
}

$tempDir = $null
try {
    $tempDir = Copy-OmniRouteSqlite -ContainerName $ContainerName
    $env:OMNIROUTE_READINESS_DB = Join-Path $tempDir "storage.sqlite"
    $env:OMNIROUTE_PROVIDER = $Provider
    $env:OMNIROUTE_WARN_TOKEN_EXPIRES_MINUTES = [string]$WarnTokenExpiresMinutes

    $pythonScript = @'
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

db_path = os.environ["OMNIROUTE_READINESS_DB"]
provider = os.environ["OMNIROUTE_PROVIDER"]
warn_token_expires_minutes = int(os.environ["OMNIROUTE_WARN_TOKEN_EXPIRES_MINUTES"])
terminal_statuses = {"credits_exhausted", "quota_exhausted", "expired", "revoked"}
warning_error_types = {"quota_exhausted", "rate_limited", "auth_error", "cooldown"}
issues = []
rows = []

def parse_datetime(value):
    if not value:
        return None
    normalized = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

with sqlite3.connect(db_path) as con:
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    tables = {row[0] for row in cur.execute("select name from sqlite_master where type = 'table'")}
    if "provider_connections" not in tables:
        issues.append("provider_connections table отсутствует.")
    else:
        rows = [
            dict(row)
            for row in cur.execute(
                """
                select id, provider, is_active, test_status, error_code, last_error,
                       last_error_type, backoff_level, rate_limited_until, expires_at,
                       updated_at
                from provider_connections
                where provider = ?
                """,
                (provider,),
            )
        ]
        if not rows:
            issues.append(f"Нет provider_connections для provider={provider}.")
        active_rows = [row for row in rows if row.get("is_active") == 1]
        if not active_rows:
            issues.append(f"Нет active provider_connections для provider={provider}.")
        for row in rows:
            status = (row.get("test_status") or "").lower()
            error_type = (row.get("last_error_type") or "").lower()
            if status in terminal_statuses:
                issues.append(f"{row['id'][:8]} terminal test_status={row.get('test_status')}.")
            if error_type in warning_error_types:
                issues.append(f"{row['id'][:8]} last_error_type={row.get('last_error_type')}.")
            if row.get("rate_limited_until"):
                issues.append(f"{row['id'][:8]} rate_limited_until={row.get('rate_limited_until')}.")
            if row.get("backoff_level") and int(row["backoff_level"]) > 0:
                issues.append(f"{row['id'][:8]} backoff_level={row.get('backoff_level')}.")
            expires_at = parse_datetime(row.get("expires_at"))
            if expires_at:
                minutes_left = (expires_at - datetime.now(timezone.utc)).total_seconds() / 60
                if minutes_left <= warn_token_expires_minutes:
                    issues.append(
                        f"{row['id'][:8]} token expires soon: {minutes_left:.1f} minutes left."
                    )

print(json.dumps({"connections": rows, "issues": issues}, ensure_ascii=False, default=str, indent=2))
if issues:
    sys.exit(1)
'@

    $pythonScript | python -
    if ($LASTEXITCODE -ne 0) {
        Add-ReadinessIssue -ReadinessIssue $issues -Message "Provider connection status содержит quota/cooldown/auth риск."
    }
}
finally {
    if ($tempDir -and (Test-Path $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Force -Recurse
    }
    Remove-Item Env:\OMNIROUTE_READINESS_DB -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_PROVIDER -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_WARN_TOKEN_EXPIRES_MINUTES -ErrorAction SilentlyContinue
}

$recentLogs = (& cmd.exe /c "docker logs $ContainerName --tail $RecentLogTail 2>&1") -join "`n"
$logRiskPatterns = @(
    "credits_exhausted",
    "quota_exhausted",
    "You have reached the limit",
    "all .* accounts unavailable",
    "all .* accounts in cooldown",
    "No credentials for provider",
    "HTTP 402",
    "Payment Required"
)
foreach ($pattern in $logRiskPatterns) {
    if ([regex]::IsMatch($recentLogs, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
        Add-ReadinessIssue -ReadinessIssue $issues -Message "Recent OmniRoute logs contain risk pattern: $pattern"
    }
}

if ($issues.Count -gt 0) {
    Write-Output "OmniRoute readiness warnings: $($issues.Count)"
    if (-not $WarnOnly) {
        Write-Error "OmniRoute readiness failed. Используйте -WarnOnly только для наблюдения без fail-fast."
    }
}

Write-Output "OmniRoute readiness OK."
