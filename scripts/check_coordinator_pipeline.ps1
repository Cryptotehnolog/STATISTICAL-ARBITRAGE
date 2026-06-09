$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$boundaryCheckScript = Join-Path $PSScriptRoot "check_coordinator_agent_boundaries.ps1"

Write-Output "Проверка Coordinator Agent pipeline: lifecycle, queue, resource policy, final decision, tool permissions, integration smoke..."
Push-Location $repoRoot
try {
    & $boundaryCheckScript
    uv run pytest `
        tests/unit/test_coordinator_agent.py `
        tests/unit/test_check_coordinator_pipeline.py `
        tests/integration/test_coordinator_agent_integration.py `
        -q `
        --no-cov `
        -p no:cacheprovider
}
finally {
    Pop-Location
}
