param(
    [string]$EnvFile = "data\aperag\.env",
    [int]$IndexWaitTimeoutSeconds = 300,
    [switch]$SkipGraph,
    [switch]$SkipSemanticQa
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    Write-Output "Проверка качества памяти ApeRAG..."

    Write-Output "- Local embedding endpoint"
    .\scripts\start_aperag_embedding_server.ps1 -HealthWaitSeconds 180 | Write-Output

    Write-Output "- Freshness, runtime health и graph readiness"
    if ($SkipGraph) {
        .\scripts\check_aperag_memory_fresh.ps1 `
            -EnvFile $EnvFile `
            -IndexWaitTimeoutSeconds $IndexWaitTimeoutSeconds | Write-Output
    }
    else {
        .\scripts\check_aperag_memory_fresh.ps1 `
            -EnvFile $EnvFile `
            -RequireCuratedGraph `
            -IndexWaitTimeoutSeconds $IndexWaitTimeoutSeconds | Write-Output
    }

    if (-not $SkipSemanticQa) {
        Write-Output "- Semantic QA: Future paper/live trading roles"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "Regime Switch Detector Execution and Slippage Simulator Dynamic Risk and Capital Allocator future paper live trading roles" `
            -Keywords @("Regime", "Switch", "Execution", "Slippage", "Simulator", "Dynamic", "Risk", "Allocator") `
            -TopK 20 `
            -ExpectedText @(
                "Regime Switch Detector",
                "Execution and Slippage Simulator",
                "Dynamic Risk and Capital Allocator"
            ) | Write-Output

        Write-Output "- Semantic QA: agent observability inspired by patoles/agent-flow"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "What is the deferred idea inspired by patoles/agent-flow for visualizing agent work?" `
            -Keywords @("patoles", "agent-flow", "observability", "timeline", "graph") `
            -TopK 20 `
            -ExpectedText @(
                "patoles/agent-flow",
                "live graph",
                "structured events"
            ) | Write-Output

        Write-Output "- Semantic QA: Rust boundary policy"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "When should Rust be introduced in the Statistical Arbitrage project?" `
            -Keywords @("Rust", "profiling", "hotspot", "Python", "boundary") `
            -TopK 20 `
            -ExpectedText @(
                "profiling identifies",
                "Python reference",
                "API"
            ) | Write-Output

        Write-Output "- Semantic QA: ApeRAG memory separation"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "How is ApeRAG memory separated between project knowledge and agent operational memory?" `
            -Keywords @("ApeRAG", "project", "agent", "memory", "collection") `
            -TopK 20 `
            -ExpectedText @(
                "stat-arb-project-knowledge",
                "stat-arb-agent-memory",
                "Memory Agent policy"
            ) | Write-Output
    }

    Write-Output "Memory quality OK."
}
finally {
    Pop-Location
}
