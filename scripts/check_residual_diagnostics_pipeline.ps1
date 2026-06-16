$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    Write-Output "Проверка residual diagnostics pipeline: Statistical Testing -> Critic signals..."
    uv run pytest `
        tests/unit/test_residual_diagnostics.py `
        tests/unit/test_statistical_testing_agent.py `
        tests/unit/test_critic_agent.py::test_critic_weak_assumption_detection_flags_residual_diagnostics `
        tests/unit/test_check_residual_diagnostics_pipeline.py `
        -q

    if ($LASTEXITCODE -ne 0) {
        throw "Проверка residual diagnostics pipeline завершилась с ошибкой."
    }

    Write-Output "Проверка residual diagnostics pipeline прошла."
}
finally {
    Pop-Location
}
