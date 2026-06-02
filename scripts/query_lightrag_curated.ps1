param(
    [string]$Model = "my-ai",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ApiKey = $env:OMNIROUTE_API_KEY,
    [int]$TimeoutSeconds = 180,
    [string]$Query = "",
    [string[]]$Expect = @()
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
        "stat_arb.scripts.query_lightrag_curated",
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
    if ($Query) {
        $argsList += @("--query", $Query)
    }
    foreach ($term in $Expect) {
        $argsList += @("--expect", $term)
    }
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
