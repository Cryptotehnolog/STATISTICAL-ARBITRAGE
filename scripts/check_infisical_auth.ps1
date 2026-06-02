param(
    [string]$SecretKey = "STAT_ARB_INFISICAL_SMOKE_SECRET",
    [string]$ApiUrl = "",
    [string]$Environment = "",
    [string]$SecretPath = ""
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
        "stat_arb.scripts.check_infisical_auth",
        "--secret-key",
        $SecretKey
    )
    if ($ApiUrl) {
        $argsList += @("--api-url", $ApiUrl)
    }
    if ($Environment) {
        $argsList += @("--environment", $Environment)
    }
    if ($SecretPath) {
        $argsList += @("--secret-path", $SecretPath)
    }

    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
