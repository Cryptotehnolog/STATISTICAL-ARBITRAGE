Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Проверка Critic Agent pipeline..."
& $python -m pytest tests/unit/test_critic_agent.py tests/unit/test_check_critic_pipeline.py --no-cov -p no:cacheprovider
Write-Host "Проверка Critic Agent pipeline прошла."
