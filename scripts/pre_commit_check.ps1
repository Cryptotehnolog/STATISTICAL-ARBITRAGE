$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checkScript = Join-Path $PSScriptRoot "check.ps1"

Write-Output "Running local pre-commit checklist..."
Write-Output "- Unit and lint baseline: check.ps1"
Write-Output "- LLM readiness is intentionally excluded; run check_omniroute.ps1 separately."

Push-Location $repoRoot
try {
    & $checkScript
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
