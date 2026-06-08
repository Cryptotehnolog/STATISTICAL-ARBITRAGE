$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checkScript = Join-Path $PSScriptRoot "check.ps1"
$russianCheckScript = Join-Path $PSScriptRoot "check_user_facing_russian.ps1"
$secretLeakCheckScript = Join-Path $PSScriptRoot "check_secret_leaks.ps1"
$memoryContractsCheckScript = Join-Path $PSScriptRoot "check_memory_contracts.ps1"
$pairAlignmentBoundaryCheckScript = Join-Path $PSScriptRoot "check_pair_alignment_boundary.ps1"
$hypothesisAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_hypothesis_agent_boundaries.ps1"
$backtestAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_backtest_agent_boundaries.ps1"
$criticAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_critic_agent_boundaries.ps1"
$criticPipelineCheckScript = Join-Path $PSScriptRoot "check_critic_pipeline.ps1"
$legacyMemoryBackendSurfaceCheckScript = Join-Path $PSScriptRoot "check_no_legacy_memory_backend_user_surface.ps1"
$legacyMemoryBackendImportsCheckScript = Join-Path $PSScriptRoot "check_no_legacy_memory_backend_imports.ps1"

Write-Output "Запуск локального pre-commit checklist..."
Write-Output "- Русификация user-facing текста: check_user_facing_russian.ps1"
Write-Output "- Secret leak guard: check_secret_leaks.ps1"
Write-Output "- Проверка memory contracts: check_memory_contracts.ps1"
Write-Output "- Проверка pair alignment boundary: check_pair_alignment_boundary.ps1"
Write-Output "- Проверка Hypothesis Agent boundaries: check_hypothesis_agent_boundaries.ps1"
Write-Output "- Проверка Backtest Agent boundaries: check_backtest_agent_boundaries.ps1"
Write-Output "- Проверка Critic Agent boundaries: check_critic_agent_boundaries.ps1"
Write-Output "- Проверка Critic Agent pipeline: check_critic_pipeline.ps1"
Write-Output "- Проверка активной пользовательской memory surface: check_no_legacy_memory_backend_user_surface.ps1"
Write-Output "- Проверка отсутствия legacy memory backend imports: check_no_legacy_memory_backend_imports.ps1"
Write-Output "- Unit и lint baseline: check.ps1"
Write-Output "- LLM readiness намеренно исключен; отдельно запускайте check_omniroute.ps1."

Push-Location $repoRoot
try {
    & $russianCheckScript
    & $secretLeakCheckScript
    & $memoryContractsCheckScript
    & $pairAlignmentBoundaryCheckScript
    & $hypothesisAgentBoundaryCheckScript
    & $backtestAgentBoundaryCheckScript
    & $criticAgentBoundaryCheckScript
    & $criticPipelineCheckScript
    & $legacyMemoryBackendSurfaceCheckScript
    & $legacyMemoryBackendImportsCheckScript
    & $checkScript
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
