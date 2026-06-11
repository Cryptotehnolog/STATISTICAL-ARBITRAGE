$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка CLI pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_cli_data.py `
        tests/unit/test_cli_stage_support.py `
        tests/unit/test_check_cli_pipeline.py `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка CLI pipeline прошла."
