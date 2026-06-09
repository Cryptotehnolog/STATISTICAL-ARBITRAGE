param(
    [string]$SecretKey = "STAT_ARB_INFISICAL_SMOKE_SECRET",
    [string]$ApiUrl = "",
    [string]$Environment = "",
    [string]$SecretPath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$linuxPython = Join-Path $repoRoot ".venv/bin/python"
$python = if (Test-Path -LiteralPath $windowsPython) { $windowsPython } else { $linuxPython }

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $windowsPython или $linuxPython. Сначала выполните 'uv sync'."
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
