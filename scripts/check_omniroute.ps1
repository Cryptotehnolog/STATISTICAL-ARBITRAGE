param(
    [string]$ContainerName = "omniroute",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$Model = "my-ai",
    [string]$ApiKey = $env:OMNIROUTE_API_KEY,
    [int]$TimeoutSeconds = 60,
    [double]$SmokeTimeoutSeconds = 180,
    [switch]$SkipDocStatus,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$smokeScript = Join-Path $PSScriptRoot "smoke_lightrag_omniroute.ps1"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

function New-OmniRouteHeaders {
    if ($ApiKey) {
        return @{ Authorization = "Bearer $ApiKey" }
    }
    return @{}
}

Write-Output "Checking Docker container: $ContainerName"
$containerId = docker ps --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' is not running."
}

$health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerName
if ($health -ne "healthy" -and $health -ne "none") {
    Write-Error "Docker container '$ContainerName' health is '$health'."
}
Write-Output "Docker container OK: $ContainerName ($health)"

$headers = New-OmniRouteHeaders

Write-Output "Checking OmniRoute models endpoint: $BaseUrl/models"
$modelsResponse = Invoke-RestMethod `
    -Uri "$BaseUrl/models" `
    -Method Get `
    -Headers $headers `
    -TimeoutSec $TimeoutSeconds

if (-not $modelsResponse.data -or $modelsResponse.data.Count -lt 1) {
    Write-Error "No models returned from $BaseUrl/models."
}
Write-Output "Models endpoint OK: $($modelsResponse.data.Count) model(s)"

Write-Output "Checking OmniRoute chat endpoint with model: $Model"
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

$chatResponse = Invoke-WebRequest `
    -UseBasicParsing `
    -Uri "$BaseUrl/chat/completions" `
    -Method Post `
    -ContentType "application/json" `
    -Headers $headers `
    -Body $body `
    -TimeoutSec $TimeoutSeconds

if ($chatResponse.StatusCode -lt 200 -or $chatResponse.StatusCode -ge 300) {
    Write-Error "Chat endpoint returned HTTP $($chatResponse.StatusCode)."
}
if ($chatResponse.Content -notmatch "OK") {
    Write-Error "Chat endpoint did not return expected OK response."
}
Write-Output "Chat endpoint OK"

if (-not $SkipDocStatus) {
    Write-Output "Checking persistent LightRAG doc_status..."
    Push-Location $repoRoot
    try {
        & $python -m stat_arb.scripts.check_lightrag_doc_status
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipSmoke) {
    Write-Output "Running LightRAG OmniRoute smoke..."
    Push-Location $repoRoot
    try {
        if ($ApiKey) {
            & $smokeScript `
                -Model $Model `
                -BaseUrl $BaseUrl `
                -ApiKey $ApiKey `
                -TimeoutSeconds $SmokeTimeoutSeconds
        }
        else {
            & $smokeScript `
                -Model $Model `
                -BaseUrl $BaseUrl `
                -TimeoutSeconds $SmokeTimeoutSeconds
        }
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

Write-Output "OmniRoute check passed."
