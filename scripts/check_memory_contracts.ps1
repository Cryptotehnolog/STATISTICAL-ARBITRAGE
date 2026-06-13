$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentsDir = Join-Path $repoRoot "src\stat_arb\agents"
$cliDir = Join-Path $repoRoot "src\stat_arb\cli"
$dashboardDir = Join-Path $repoRoot "src\stat_arb\dashboard"
$policyFile = Join-Path $repoRoot "src\stat_arb\memory\policy.py"
$AllowedDirectApeRagFiles = @(
    "scripts\seed_aperag_curated.ps1",
    "scripts\check_aperag_memory_fresh.ps1",
    "scripts\check_aperag_knowledge.ps1",
    "scripts\enable_aperag_curated_graph.ps1",
    "scripts\export_aperag_graph.ps1",
    "src\stat_arb\memory\aperag_client.py"
)

Write-Output "Проверка memory contracts..."

if (-not (Test-Path -LiteralPath $policyFile)) {
    Write-Error "Memory Agent policy layer не найден: $policyFile"
}

$directClientUses = @()
$scanRoots = @($agentsDir, $cliDir, $dashboardDir)
foreach ($scanRoot in $scanRoots) {
    if (Test-Path -LiteralPath $scanRoot) {
        $directClientUses += @(
            Get-ChildItem -LiteralPath $scanRoot -Recurse -Filter "*.py" |
                Select-String -Pattern "ApeRAGMemoryClient|write_markdown_document|/api/v1/collections|httpx|requests|urllib" |
                Where-Object {
                    $relativePath = Resolve-Path -LiteralPath $_.Path -Relative
                    $normalized = $relativePath -replace "^[.][\\/]", ""
                    $AllowedDirectApeRagFiles -notcontains $normalized
                }
        )
    }
}

if ($directClientUses.Count -gt 0) {
    $directClientUses | ForEach-Object {
        Write-Output "$($_.Path):$($_.LineNumber): $($_.Line.Trim())"
    }
    Write-Error "Agents должны писать в память через MemoryAgentService, а не напрямую в ApeRAGMemoryClient."
}

Write-Output "Проверка memory contracts прошла."
