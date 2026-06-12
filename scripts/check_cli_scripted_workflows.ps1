$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка scripted CLI workflows..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/integration/test_cli_scripted_workflows.py `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка scripted CLI workflows прошла."
