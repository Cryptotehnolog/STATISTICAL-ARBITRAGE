param(
    [string]$EnvFile = "data\aperag\.env",
    [int]$IndexWaitTimeoutSeconds = 300,
    [switch]$SkipGraph,
    [switch]$SkipSemanticQa,
    [switch]$SkipAnswerEval
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

        Write-Output "- Semantic QA: GitHub Actions Node.js 24 migration"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "What is the status of the GitHub Actions Node.js 24 migration?" `
            -Keywords @("GitHub", "Actions", "Node.js", "24", "checkout", "setup-python", "setup-uv") `
            -TopK 20 `
            -ExpectedText @(
                "GitHub Actions Node.js 24",
                "actions/checkout@v6",
                "actions/setup-python@v6",
                "astral-sh/setup-uv@v8.2.0"
            ) | Write-Output

        Write-Output "- Semantic QA: One-bar DataQualityReport"
        .\scripts\check_aperag_knowledge.ps1 `
            -EnvFile $EnvFile `
            -Query "What is the one-bar DataQualityReport contract decision?" `
            -Keywords @("One-bar", "DataQualityReport", "diagnostic", "Dataset", "start_date", "end_date") `
            -TopK 20 `
            -ExpectedText @(
                "DataQualityReport",
                "is_valid=false",
                "passed=false",
                "insufficient_data"
            ) | Write-Output
    }

    if (-not $SkipAnswerEval) {
        Write-Output "- Answer eval: контракт One-bar DataQualityReport"
        .\scripts\check_aperag_answer_eval.ps1 `
            -EnvFile $EnvFile `
            -Question "What is the one-bar DataQualityReport contract decision?" `
            -Keywords @("One-bar", "DataQualityReport", "diagnostic", "insufficient_data") `
            -TopK 20 `
            -RequiredFacts @(
                "DataQualityReport",
                "is_valid=false",
                "passed=false",
                "insufficient_data"
            ) `
            -ForbiddenClaims @(
                "one-bar DataQualityReport passed=true",
                "one-bar data is clean",
                "single bar is sufficient for quality metrics"
            ) | Write-Output

        Write-Output "- Answer eval: границы RLM и Context Engine routing"
        .\scripts\check_aperag_answer_eval.ps1 `
            -EnvFile $EnvFile `
            -Question "Should RLMs or a Context Engine replace ApeRAG now?" `
            -Keywords @("RLM", "Context", "Engine", "ApeRAG", "routing", "provenance") `
            -TopK 20 `
            -RequiredFacts @(
                "ApeRAG",
                "RLM",
                "Context Engine",
                "routing"
            ) `
            -ForbiddenClaims @(
                "RLMs should replace ApeRAG now",
                "Context Engine may bypass Memory Agent policy",
                "invisible provenance is acceptable"
            ) | Write-Output
    }

    Write-Output "Memory quality OK."
}
finally {
    Pop-Location
}
