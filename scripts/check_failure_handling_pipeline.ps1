$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$failureHandlingPath = Join-Path $repoRoot "src\stat_arb\agents\failure_handling.py"

if (-not (Test-Path -LiteralPath $failureHandlingPath)) {
    Write-Error "Failure handling boundary не найден: $failureHandlingPath"
}

$source = Get-Content -LiteralPath $failureHandlingPath -Raw

if ($source -match "ApeRAGMemoryClient|write_markdown_document|aperag_client") {
    Write-Error "Failure handling не должен писать напрямую в ApeRAG; используйте MemoryAgentService/MemoryWriter boundary."
}

if (
    $source -notmatch "DataFreshnessPolicy" -or
    $source -notmatch "RetryPolicy" -or
    $source -notmatch "FailureHandlingPolicy" -or
    $source -notmatch "ResourceBudgetPolicy" -or
    $source -notmatch "safe_mode_components"
) {
    Write-Error "Failure handling должен иметь explicit policy contracts для freshness, retry, safe mode и runtime budgets."
}

if (
    $source -match "max_outage_age: timedelta =|max_stale_signal_age: timedelta =|max_attempts: int =|base_delay: timedelta =|max_delay: timedelta =|multiplier: float =|abnormal_spread_z_score: float =|warn_usage_ratio: float =|safe_mode_components: frozenset\[str\] ="
) {
    Write-Error "Failure handling не должен прятать thresholds/retry/resource defaults в policy configs."
}

if (
    $source -notmatch "transition_experiment_lifecycle" -or
    $source -notmatch "fail_coordinator_task" -or
    $source -notmatch "memory_service: MemoryWriter"
) {
    Write-Error "Failure handling должен мутировать registry через Coordinator boundary и MemoryWriter."
}

Write-Output "Проверка Failure Handling pipeline: Task 17..."
Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_failure_handling.py `
        tests/unit/test_check_failure_handling_pipeline.py `
        tests/unit/test_check_runtime_resource_budget.py `
        -q `
        --no-cov `
        -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка Failure Handling pipeline прошла."
