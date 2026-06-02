param(
    [string]$Model = "my-ai",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ApiKey = $env:OMNIROUTE_API_KEY,
    [double]$TimeoutSeconds = 180,
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

Push-Location $repoRoot
try {
    $argsList = @(
        "-m",
        "stat_arb.scripts.smoke_lightrag_omniroute",
        "--model",
        $Model,
        "--base-url",
        $BaseUrl,
        "--timeout",
        $TimeoutSeconds
    )
    if ($ApiKey) {
        $argsList += @("--api-key", $ApiKey)
    }
    if ($KeepData) {
        $argsList += "--keep-data"
    }
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
