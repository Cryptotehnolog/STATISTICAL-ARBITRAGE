Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Проверка Critic Agent pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_critic_agent.py `
        tests/unit/test_check_critic_pipeline.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Host "Проверка Critic Agent pipeline прошла."
