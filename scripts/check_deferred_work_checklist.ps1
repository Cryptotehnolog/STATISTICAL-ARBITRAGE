$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$technicalDebtPath = Join-Path $repoRoot "docs\technical_debt.md"
$futureIdeasPath = Join-Path $repoRoot "docs\knowledge\future_ideas.md"
$checklistPath = Join-Path $repoRoot "docs\deferred_work_checklist.md"

foreach ($path in @($technicalDebtPath, $futureIdeasPath, $checklistPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Error "Файл не найден: $path"
    }
}

$technicalDebt = Get-Content -Raw -LiteralPath $technicalDebtPath
$futureIdeas = Get-Content -Raw -LiteralPath $futureIdeasPath
$checklist = Get-Content -Raw -LiteralPath $checklistPath

$openTechnicalDebt = ($technicalDebt -split "## Resolved", 2)[0]
$tdMatches = [regex]::Matches($openTechnicalDebt, "(?m)^### (TD-\d{4}):")
$tdIds = @($tdMatches | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)

$ideaIds = @()
$ideaBlocks = [regex]::Split($futureIdeas, "(?m)^## ")
foreach ($block in $ideaBlocks) {
    if ($block -match "Status:\s*proposed" -and $block -match "(IDEA-\d{4})") {
        $ideaIds += $matches[1]
    }
}
$ideaIds = @($ideaIds | Sort-Object -Unique)

$missing = @()
foreach ($id in @($tdIds + $ideaIds)) {
    if ($checklist -notmatch [regex]::Escape($id)) {
        $missing += $id
    }
}

if ($missing.Count -gt 0) {
    Write-Error "docs\deferred_work_checklist.md не содержит deferred IDs: $($missing -join ', ')"
}

Write-Output "Проверка deferred work checklist прошла: TD=$($tdIds.Count), IDEA=$($ideaIds.Count)"
