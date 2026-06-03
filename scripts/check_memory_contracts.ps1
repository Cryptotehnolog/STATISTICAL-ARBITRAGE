$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$agentsDir = Join-Path $repoRoot "src\stat_arb\agents"
$policyFile = Join-Path $repoRoot "src\stat_arb\memory\policy.py"

Write-Output "Проверка memory contracts..."

if (-not (Test-Path -LiteralPath $policyFile)) {
    Write-Error "Memory Agent policy layer не найден: $policyFile"
}

$directClientUses = @()
if (Test-Path -LiteralPath $agentsDir) {
    $directClientUses = @(
        Get-ChildItem -LiteralPath $agentsDir -Recurse -Filter "*.py" |
            Select-String -Pattern "ApeRAGMemoryClient|write_markdown_document" |
            Where-Object { $_.Path -notlike "*memory_agent*" }
    )
}

if ($directClientUses.Count -gt 0) {
    $directClientUses | ForEach-Object {
        Write-Output "$($_.Path):$($_.LineNumber): $($_.Line.Trim())"
    }
    Write-Error "Agents должны писать в память через MemoryAgentService, а не напрямую в ApeRAGMemoryClient."
}

Write-Output "Проверка memory contracts прошла."
