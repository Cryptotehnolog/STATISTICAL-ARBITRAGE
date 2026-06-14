$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка reproducibility workflow: один scripted experiment прогоняется дважды и сравнивает metrics/hashes/artifacts..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/integration/test_reproducibility_workflow.py `
        tests/unit/test_check_reproducibility_workflow.py `
        -q `
        --no-cov `
        -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка reproducibility workflow прошла."
