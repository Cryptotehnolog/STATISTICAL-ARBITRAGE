param(
    [string[]]$Paths = @(
        "README.md",
        "docs",
        "scripts",
        "src/stat_arb/scripts/export_lightrag_graph.py"
    )
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$excludedPathParts = @(
    "docs\knowledge",
    "docs\knowledge_graph",
    "scripts\check_user_facing_russian.ps1",
    ".kiro",
    "data",
    ".venv"
)

$bannedPatterns = @(
    "\bEntity:",
    "\bRelation:",
    "\bDegree:",
    "Source chunks",
    "Choose a node",
    "Select node",
    "nodes</span>",
    "edges</span>",
    "visible nodes",
    "visible edges",
    "Dry-run mode",
    "Running local pre-commit checklist",
    "Checking Docker container",
    "Checking OmniRoute",
    "Large markdown files",
    "Candidate sections",
    "Suggested action",
    "Expected virtualenv Python"
)

function Test-IsExcluded {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "/", "\"
    foreach ($part in $excludedPathParts) {
        if ($normalized.StartsWith($part, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-TargetFiles {
    foreach ($path in $Paths) {
        $resolved = Join-Path $repoRoot $path
        if (-not (Test-Path -LiteralPath $resolved)) {
            continue
        }

        $item = Get-Item -LiteralPath $resolved
        if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $resolved -Recurse -File |
                Where-Object { $_.Extension -in @(".md", ".ps1", ".py", ".html") }
        }
        else {
            $item
        }
    }
}

$violations = @()

foreach ($file in Get-TargetFiles | Sort-Object FullName -Unique) {
    $relative = $file.FullName.Substring($repoRoot.Length + 1)
    if (Test-IsExcluded -RelativePath $relative) {
        continue
    }

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
    Write-Output "Найдены английские user-facing labels/messages:"
    $violations | Format-Table -AutoSize
    Write-Error "Проверка русификации user-facing текста не прошла."
}

Write-Output "Проверка русификации user-facing текста прошла."
