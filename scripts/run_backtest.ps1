param(
    [Parameter(Mandatory = $true)]
    [string]$ExperimentId,

    [Parameter(Mandatory = $true)]
    [string]$PayloadJson,

    [Parameter(Mandatory = $true)]
    [int]$Priority,

    [Parameter(Mandatory = $true)]
    [int]$MaxAttempts,

    [Parameter(Mandatory = $true)]
    [string]$Reason,

    [Parameter(Mandatory = $true)]
    [string]$Actor,

    [Parameter(Mandatory = $true)]
    [int]$MaxRunningTasks,

    [Parameter(Mandatory = $true)]
    [int]$MaxRunningTasksPerAgent,

    [Parameter(Mandatory = $true)]
    [string]$DbPath
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$payloadPath = Resolve-Path -LiteralPath $PayloadJson -ErrorAction Stop
if (-not (Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
    throw "PayloadJson должен быть файлом: $PayloadJson"
}

Push-Location $repoRoot
try {
    Write-Output "Запуск backtest workflow..."

    # Граница workflow: uv run stat-arb experiment run-stage
    $runStageOutput = & uv run stat-arb experiment run-stage `
        --experiment-id $ExperimentId `
        --stage backtesting `
        --task-type run_backtest `
        --agent-name backtest_agent `
        --priority $Priority `
        --max-attempts $MaxAttempts `
        --payload-json $payloadPath.Path `
        --advance-lifecycle `
        --reason $Reason `
        --actor $Actor `
        --db-path $DbPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    $runStageOutput | Write-Output

    $taskLine = $runStageOutput | Where-Object { $_ -match "^Stage task поставлен в очередь: " } | Select-Object -First 1
    if (-not $taskLine) {
        throw "Не удалось определить task_id из вывода run-stage."
    }
    $taskId = ($taskLine -replace "^Stage task поставлен в очередь: ", "").Trim()
    if (-not $taskId) {
        throw "Пустой task_id из вывода run-stage."
    }

    # Граница workflow: uv run stat-arb experiment execute-stage
    uv run stat-arb experiment execute-stage `
        --task-id $taskId `
        --stage backtesting `
        --max-running-tasks $MaxRunningTasks `
        --max-running-tasks-per-agent $MaxRunningTasksPerAgent `
        --db-path $DbPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Output "Backtest workflow прошел: $taskId"
}
finally {
    Pop-Location
}
