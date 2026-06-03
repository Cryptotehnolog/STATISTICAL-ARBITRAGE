param(
    [string[]]$Paths = @(
        "README.md",
        "docs/repository_structure.md"
    )
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$bannedPatterns = @(
    "init_lightrag",
    "seed_lightrag",
    "query_lightrag",
    "smoke_lightrag",
    "benchmark_lightrag",
    "export_lightrag_graph",
    "check_lightrag_graph_export",
    "check_lightrag_memory_fresh",
    "serve_lightrag_graph",
    "open_lightrag_graph",
    "create_lightrag_graph_shortcut",
    "LightRAG Operations",
    "LightRAG \(Memory\)",
    "через LightRAG",
    "LightRAG memory",
    "LightRAG graph",
    "LightRAG storage",
    "LightRAG stores"
)

$violations = @()

foreach ($path in $Paths) {
    $resolved = Join-Path $repoRoot $path
    if (-not (Test-Path -LiteralPath $resolved)) {
        continue
    }

    $lines = Get-Content -LiteralPath $resolved
    for ($index = 0; $index -lt $lines.Count; $index++) {
        foreach ($pattern in $bannedPatterns) {
            if ($lines[$index] -match $pattern) {
                $violations += [pscustomobject]@{
                    File = $path
                    Line = $index + 1
                    Pattern = $pattern
                    Text = $lines[$index].Trim()
                }
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Output "Найдены активные legacy memory backend упоминания в пользовательской поверхности:"
    $violations | Format-Table -AutoSize
    Write-Error "Legacy memory backend не должен возвращаться в README/docs как активный backend."
}

Write-Output "Проверка активной пользовательской legacy memory backend поверхности прошла."
