$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка statistical-testing workflow..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_statistical_testing_workflow.py `
        tests/unit/test_cli_data.py::test_experiment_execute_stage_runs_statistical_testing_and_completes_task `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка statistical-testing workflow прошла."
