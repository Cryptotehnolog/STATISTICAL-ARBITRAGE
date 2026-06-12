$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка pair-screening workflow..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_pair_screening_workflow.py `
        tests/unit/test_cli_data.py::test_hypothesis_generate_uses_rule_based_agent_boundary `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка pair-screening workflow прошла."
