$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checkScript = Join-Path $PSScriptRoot "check.ps1"
$docsLinksCheckScript = Join-Path $PSScriptRoot "check_docs_links.ps1"
$russianCheckScript = Join-Path $PSScriptRoot "check_user_facing_russian.ps1"
$deferredWorkChecklistScript = Join-Path $PSScriptRoot "check_deferred_work_checklist.ps1"
$secretLeakCheckScript = Join-Path $PSScriptRoot "check_secret_leaks.ps1"
$memoryContractsCheckScript = Join-Path $PSScriptRoot "check_memory_contracts.ps1"
$researchDefaultsCheckScript = Join-Path $PSScriptRoot "check_research_defaults.ps1"
$pairAlignmentBoundaryCheckScript = Join-Path $PSScriptRoot "check_pair_alignment_boundary.ps1"
$hypothesisAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_hypothesis_agent_boundaries.ps1"
$backtestAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_backtest_agent_boundaries.ps1"
$criticAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_critic_agent_boundaries.ps1"
$criticPipelineCheckScript = Join-Path $PSScriptRoot "check_critic_pipeline.ps1"
$coordinatorAgentBoundaryCheckScript = Join-Path $PSScriptRoot "check_coordinator_agent_boundaries.ps1"
$coordinatorPipelineCheckScript = Join-Path $PSScriptRoot "check_coordinator_pipeline.ps1"
$failureHandlingPipelineCheckScript = Join-Path $PSScriptRoot "check_failure_handling_pipeline.ps1"
$reportPipelineCheckScript = Join-Path $PSScriptRoot "check_report_pipeline.ps1"
$cliPipelineCheckScript = Join-Path $PSScriptRoot "check_cli_pipeline.ps1"
$pairScreeningPipelineCheckScript = Join-Path $PSScriptRoot "check_pair_screening_pipeline.ps1"
$statisticalTestingWorkflowCheckScript = Join-Path $PSScriptRoot "check_statistical_testing_workflow.ps1"
$residualDiagnosticsPipelineCheckScript = Join-Path $PSScriptRoot "check_residual_diagnostics_pipeline.ps1"
$stabilityDiagnosticsPipelineCheckScript = Join-Path $PSScriptRoot "check_stability_diagnostics_pipeline.ps1"
$backtestWorkflowCheckScript = Join-Path $PSScriptRoot "check_backtest_workflow.ps1"
$reproducibilityWorkflowCheckScript = Join-Path $PSScriptRoot "check_reproducibility_workflow.ps1"
$mvpAcceptanceCheckScript = Join-Path $PSScriptRoot "check_mvp_acceptance.ps1"
$agentsCheckpointScript = Join-Path $PSScriptRoot "check_agents_checkpoint.ps1"
$dashboardStructureCheckScript = Join-Path $PSScriptRoot "check_dashboard_structure.ps1"
$propertyIntegrationCheckScript = Join-Path $PSScriptRoot "check_property_integration.ps1"
$legacyMemoryBackendSurfaceCheckScript = Join-Path $PSScriptRoot "check_no_legacy_memory_backend_user_surface.ps1"
$legacyMemoryBackendImportsCheckScript = Join-Path $PSScriptRoot "check_no_legacy_memory_backend_imports.ps1"

function Invoke-RequiredCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $global:LASTEXITCODE = 0
    & $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Проверка завершилась с ошибкой: $ScriptPath (exit code $LASTEXITCODE)"
    }
}

Write-Output "Запуск локального pre-commit checklist..."
Write-Output "- Проверка local markdown links: check_docs_links.ps1"
Write-Output "- Русификация user-facing текста: check_user_facing_russian.ps1"
Write-Output "- Проверка deferred work checklist: check_deferred_work_checklist.ps1"
Write-Output "- Secret leak guard: check_secret_leaks.ps1"
Write-Output "- Проверка memory contracts: check_memory_contracts.ps1"
Write-Output "- Проверка research defaults: check_research_defaults.ps1"
Write-Output "- Проверка pair alignment boundary: check_pair_alignment_boundary.ps1"
Write-Output "- Проверка Hypothesis Agent boundaries: check_hypothesis_agent_boundaries.ps1"
Write-Output "- Проверка Backtest Agent boundaries: check_backtest_agent_boundaries.ps1"
Write-Output "- Проверка Critic Agent boundaries: check_critic_agent_boundaries.ps1"
Write-Output "- Проверка Critic Agent pipeline: check_critic_pipeline.ps1"
Write-Output "- Проверка Coordinator Agent boundaries: check_coordinator_agent_boundaries.ps1"
Write-Output "- Проверка Coordinator Agent pipeline: check_coordinator_pipeline.ps1"
Write-Output "- Проверка Failure Handling pipeline: check_failure_handling_pipeline.ps1"
Write-Output "- Проверка Report Agent pipeline: check_report_pipeline.ps1"
Write-Output "- Проверка CLI pipeline: check_cli_pipeline.ps1"
Write-Output "- Проверка pair-screening workflow: check_pair_screening_pipeline.ps1"
Write-Output "- Проверка statistical-testing workflow: check_statistical_testing_workflow.ps1"
Write-Output "- Проверка residual diagnostics pipeline: check_residual_diagnostics_pipeline.ps1"
Write-Output "- Проверка rolling stability diagnostics pipeline: check_stability_diagnostics_pipeline.ps1"
Write-Output "- Проверка backtest workflow: check_backtest_workflow.ps1"
Write-Output "- Проверка reproducibility workflow: check_reproducibility_workflow.ps1"
Write-Output "- Проверка Task 22 MVP acceptance: check_mvp_acceptance.ps1"
Write-Output "- Проверка Task 14 agents checkpoint: check_agents_checkpoint.ps1"
Write-Output "- Проверка dashboard structure: check_dashboard_structure.ps1"
Write-Output "- Property/integration smoke: check_property_integration.ps1"
Write-Output "- Проверка активной пользовательской memory surface: check_no_legacy_memory_backend_user_surface.ps1"
Write-Output "- Проверка отсутствия legacy memory backend imports: check_no_legacy_memory_backend_imports.ps1"
Write-Output "- Unit, lint и typecheck baseline: check.ps1"
Write-Output "- LLM readiness намеренно исключен; отдельно запускайте check_omniroute.ps1."

Push-Location $repoRoot
try {
    Invoke-RequiredCheck $docsLinksCheckScript
    Invoke-RequiredCheck $russianCheckScript
    Invoke-RequiredCheck $deferredWorkChecklistScript
    Invoke-RequiredCheck $secretLeakCheckScript
    Invoke-RequiredCheck $memoryContractsCheckScript
    Invoke-RequiredCheck $researchDefaultsCheckScript
    Invoke-RequiredCheck $pairAlignmentBoundaryCheckScript
    Invoke-RequiredCheck $hypothesisAgentBoundaryCheckScript
    Invoke-RequiredCheck $backtestAgentBoundaryCheckScript
    Invoke-RequiredCheck $criticAgentBoundaryCheckScript
    Invoke-RequiredCheck $criticPipelineCheckScript
    Invoke-RequiredCheck $coordinatorAgentBoundaryCheckScript
    Invoke-RequiredCheck $coordinatorPipelineCheckScript
    Invoke-RequiredCheck $failureHandlingPipelineCheckScript
    Invoke-RequiredCheck $reportPipelineCheckScript
    Invoke-RequiredCheck $cliPipelineCheckScript
    Invoke-RequiredCheck $pairScreeningPipelineCheckScript
    Invoke-RequiredCheck $statisticalTestingWorkflowCheckScript
    Invoke-RequiredCheck $residualDiagnosticsPipelineCheckScript
    Invoke-RequiredCheck $stabilityDiagnosticsPipelineCheckScript
    Invoke-RequiredCheck $backtestWorkflowCheckScript
    Invoke-RequiredCheck $reproducibilityWorkflowCheckScript
    Invoke-RequiredCheck $mvpAcceptanceCheckScript
    Invoke-RequiredCheck $agentsCheckpointScript
    Invoke-RequiredCheck $dashboardStructureCheckScript
    Invoke-RequiredCheck $propertyIntegrationCheckScript
    Invoke-RequiredCheck $legacyMemoryBackendSurfaceCheckScript
    Invoke-RequiredCheck $legacyMemoryBackendImportsCheckScript
    Invoke-RequiredCheck $checkScript
    exit 0
}
finally {
    Pop-Location
}
