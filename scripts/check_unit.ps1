param(
    [switch]$WithCoverage
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

$pytestArgs = @(
    "-m", "pytest",
    "tests/unit",
    "-m", "not slow",
    "-p", "no:cacheprovider"
)

if (-not $WithCoverage) {
    $pytestArgs += "--no-cov"
}

Push-Location $repoRoot
try {
    & $python @pytestArgs
}
finally {
    Pop-Location
}
