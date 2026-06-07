$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка Hypothesis Agent pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_hypothesis_agent.py `
        tests/unit/test_check_hypothesis_agent_boundaries.py `
        tests/unit/test_check_hypothesis_pipeline.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка Hypothesis Agent pipeline прошла."
