$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentPath = Join-Path $repoRoot "src\stat_arb\agents\coordinator.py"

if (-not (Test-Path -LiteralPath $agentPath)) {
    Write-Error "Coordinator Agent boundary не найден: $agentPath"
}

$source = Get-Content -LiteralPath $agentPath -Raw

if ($source -match "ApeRAGMemoryClient|write_markdown_document|aperag_client") {
    Write-Error "Coordinator Agent не должен писать напрямую в ApeRAG; используйте MemoryAgentService."
}

if ($source -notmatch "MemoryWriteRequest" -or $source -notmatch "memory_service\.write") {
    Write-Error "Coordinator lifecycle events должны проходить через MemoryAgentService-compatible writer."
}

if (
    $source -notmatch "Experiment" -or
    $source -notmatch "CoordinatorTask" -or
    $source -notmatch "session\.flush\(\)" -or
    $source -notmatch "ALLOWED_TRANSITIONS"
) {
    Write-Error "Coordinator Agent должен валидировать transitions и сохранять state в registry."
}

if ($source -notmatch "max_attempts" -or $source -notmatch "attempt_count" -or $source -notmatch "priority") {
    Write-Error "Coordinator task queue должен явно хранить priority и retry accounting."
}

if (
    $source -notmatch "CoordinatorResourcePolicy" -or
    $source -notmatch "max_running_tasks" -or
    $source -notmatch "max_running_tasks_per_agent" -or
    $source -notmatch "_running_task_count"
) {
    Write-Error "Coordinator task queue должен явно ограничивать global/per-agent parallelism через resource policy."
}

if (
    $source -notmatch "CoordinatorFinalDecisionPolicy" -or
    $source -notmatch "CoordinatorFinalDecisionEvidence" -or
    $source -notmatch "decide_coordinator_final_decision" -or
    $source -notmatch "apply_coordinator_final_decision" -or
    $source -notmatch "require_retest_justification" -or
    $source -notmatch "critic_status_to_decision"
) {
    Write-Error "Coordinator final decision должен иметь explicit policy/evidence boundary и retest justification guard."
}

if (
    $source -notmatch "apply_coordinator_final_decision" -or
    $source -notmatch 'transition_experiment_lifecycle\(' -or
    $source -notmatch "memory_service: MemoryWriter"
) {
    Write-Error "Coordinator final decision integration должен идти через transition_experiment_lifecycle и MemoryAgentService-compatible writer."
}

if (
    $source -match "target_status: ExperimentLifecycleStatus =|final_decision: ExperimentFinalDecision =|priority: int =|max_attempts: int =|max_running_tasks: int =|max_running_tasks_per_agent: dict\[str, int\] =|policy: CoordinatorResourcePolicy \| None =|require_retest_justification: bool =|critic_status_to_decision: .* =|policy: CoordinatorFinalDecisionPolicy \| None ="
) {
    Write-Error "Coordinator Agent не должен прятать lifecycle/task/resource defaults в request config."
}

$applySignature = [regex]::Match($source, '(?s)def apply_coordinator_final_decision\((.*?)\) -> CoordinatorTransitionResult:')
if (-not $applySignature.Success) {
    Write-Error "Coordinator final decision apply function не найден."
}

if ($applySignature.Groups[1].Value -match 'memory_service: MemoryWriter \| None') {
    Write-Error "Coordinator final decision apply не должен делать memory_service optional."
}

Write-Output "Проверка Coordinator Agent boundaries прошла."
