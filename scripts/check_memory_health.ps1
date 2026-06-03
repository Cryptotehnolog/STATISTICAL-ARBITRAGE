param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$AgentCollectionTitle = "stat-arb-agent-memory",
    [int]$AgentTimeoutSeconds = 120,
    [switch]$IncludeGraphSmoke,
    [switch]$SkipCuratedGraph,
    [switch]$SkipAgentMemory
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка memory health..."

Push-Location $repoRoot
try {
    if (-not $SkipCuratedGraph) {
        Write-Output "- Project memory freshness и graph"
        .\scripts\check_memory_backend.ps1 `
            -RequireGraph `
            -IncludeGraphSmoke:$IncludeGraphSmoke | Write-Output
    }
    else {
        Write-Output "- Project memory freshness пропущена"
    }

    if (-not $SkipAgentMemory) {
        Write-Output "- Operational agent memory"
        .\scripts\check_aperag_agent_memory.ps1 `
            -EnvFile $EnvFile `
            -CollectionTitle $AgentCollectionTitle `
            -TimeoutSeconds $AgentTimeoutSeconds | Write-Output
    }
    else {
        Write-Output "- Operational agent memory пропущена"
    }
}
finally {
    Pop-Location
}

Write-Output "Memory health OK."
