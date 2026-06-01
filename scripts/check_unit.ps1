param(
    [switch]$WithCoverage
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
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

& $python @pytestArgs
