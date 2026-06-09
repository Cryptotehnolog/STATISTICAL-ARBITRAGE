$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$boundaryCheckScript = Join-Path $PSScriptRoot "check_coordinator_agent_boundaries.ps1"

Write-Output "Проверка Coordinator Agent pipeline..."
Push-Location $repoRoot
try {
    & $boundaryCheckScript
    uv run pytest tests/unit/test_coordinator_agent.py -q
}
finally {
    Pop-Location
}
