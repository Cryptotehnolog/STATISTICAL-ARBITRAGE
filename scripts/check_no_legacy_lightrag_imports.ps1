param(
    [string[]]$Paths = @(
        "src/stat_arb/agents",
        "src/stat_arb/memory"
    )
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bannedPatterns = @(
    "LightRAGClient",
    "LightRAGConfig",
    "stat_arb\.memory\.lightrag_client",
    "from lightrag",
    "import lightrag"
)

function Get-TargetFiles {
    foreach ($path in $Paths) {
        $resolved = Join-Path $repoRoot $path
        if (-not (Test-Path -LiteralPath $resolved)) {
            continue
        }

        $item = Get-Item -LiteralPath $resolved
        if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $resolved -Recurse -File |
                Where-Object { $_.Extension -eq ".py" }
        }
        else {
            $item
        }
    }
}

$violations = @()

foreach ($file in Get-TargetFiles | Sort-Object FullName -Unique) {
    $relative = $file.FullName.Substring($repoRoot.Length + 1)
    $lines = Get-Content -LiteralPath $file.FullName
    for ($index = 0; $index -lt $lines.Count; $index++) {
        foreach ($pattern in $bannedPatterns) {
            if ($lines[$index] -match $pattern) {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Pattern = $pattern
                    Text = $lines[$index].Trim()
                }
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Output "Найдены legacy LightRAG imports в agent-facing коде:"
    $violations | Format-Table -AutoSize
    Write-Error "Agent-facing modules должны использовать ApeRAG через MemoryAgentService."
}

Write-Output "Проверка отсутствия legacy LightRAG imports прошла."
