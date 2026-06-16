$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка rolling stability diagnostics pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_stability_diagnostics.py `
        tests/unit/test_statistical_testing_agent.py `
        tests/unit/test_critic_agent.py::test_critic_weak_assumption_detection_flags_stability_diagnostics `
        tests/unit/test_check_stability_diagnostics_pipeline.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка rolling stability diagnostics pipeline прошла."
