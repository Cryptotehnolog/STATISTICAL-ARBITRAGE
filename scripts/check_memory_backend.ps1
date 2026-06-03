param(
    [ValidateSet("aperag")]
    [string]$Backend = "aperag",
    [switch]$IncludeGraphSmoke,
    [switch]$RequireGraph
)

$ErrorActionPreference = "Stop"

Write-Output "Проверка активного memory backend: $Backend"

if ($Backend -eq "aperag") {
    .\scripts\check_aperag_memory_fresh.ps1 `
        -IncludeGraphSmoke:$IncludeGraphSmoke `
        -RequireCuratedGraph:$RequireGraph | Write-Output
    Write-Output "Активный memory backend OK: ApeRAG"
    exit 0
}

Write-Error "Memory backend не поддерживается: $Backend"
